"""
Config Change Impact Analysis Service
Predicts the blast radius and risk of proposed configuration changes.
"""

import json
import os
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.schemas import (
    ImpactAnalysisRequest, ImpactAnalysisResponse, ImpactPrediction,
    LLMRequest, InteractionType,
)
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")

SYSTEM_PROMPT = """You are an expert network impact analyst. Given a proposed configuration change
and the current device context, predict the blast radius and risk.

ANALYSIS AREAS:
- BGP: peer sessions, route advertisements, community/AS-path impacts
- IGP (OSPF/ISIS): adjacency changes, metric changes, traffic shifts
- MPLS/LDP/RSVP: LSP impacts, label distribution changes
- Interfaces: link state, bandwidth, MTU, IP addressing
- ACL/Prefix-lists: traffic filtering changes, security impact
- Management: SSH, SNMP, NTP, syslog impacts
- QoS: traffic classification, policing, shaping changes

VENDORS:
- cisco_xr: IOS-XR CLI/NETCONF syntax
- nokia_sros: SR OS CLI/pysros syntax

For each affected area, provide:
- risk_level: low, medium, high, critical
- description: what could happen
- affected_peers: list of peer IPs/interfaces affected
- mitigation: how to reduce risk

Respond with ONLY valid JSON:
{
  "overall_risk": "low|medium|high|critical",
  "predictions": [
    {
      "affected_area": "BGP",
      "risk_level": "high",
      "description": "Changing BGP policy will affect route advertisements to PE peers",
      "affected_peers": ["10.0.0.1", "10.0.0.2"],
      "mitigation": "Apply during maintenance window, have rollback ready"
    }
  ],
  "safe_to_apply": true|false,
  "recommended_window": "Recommended change window description or null",
  "warnings": ["List of critical warnings"]
}"""


async def analyze_impact(
    request: ImpactAnalysisRequest,
    db: Session,
) -> ImpactAnalysisResponse:
    """Analyze the potential impact of a proposed config change"""

    # Get device info and context
    device_info = await _get_device_info(request.device_id)
    if not device_info:
        raise ValueError(f"Device {request.device_id} not found")

    # Get current config for context
    current_config = await _get_current_config(request.device_id)

    # Get device metadata (BGP peers, IGP neighbors, MPLS info)
    metadata = device_info.get("metadata") or device_info.get("device_metadata") or {}

    # Get recent audit results for compliance context
    audit_context = await _get_recent_audit(request.device_id)

    # Get related devices (same group, same subnet, BGP peers)
    related_devices = await _get_related_devices(request.device_id, metadata)

    user_prompt = f"""Analyze the impact of this proposed configuration change:

DEVICE:
- Hostname: {device_info.get('hostname', 'Unknown')}
- Vendor: {device_info.get('vendor', 'Unknown')}
- IP: {device_info.get('ip', 'Unknown')}
- Current compliance: {device_info.get('compliance', 'Unknown')}%

DEVICE METADATA (BGP peers, IGP, MPLS):
{json.dumps(metadata, indent=2, default=str)[:3000]}

CURRENT CONFIG (last 3000 chars):
{(current_config or '')[-3000:]}

PROPOSED CHANGE:
{request.proposed_config}

{f'DESCRIPTION: {request.description}' if request.description else ''}

RELATED DEVICES (same group/peers):
{json.dumps(related_devices, indent=2, default=str)[:1500]}

RECENT AUDIT STATUS:
{json.dumps(audit_context, indent=2, default=str)[:1000]}

Analyze ALL potential impacts. Return ONLY the JSON object."""

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    # Parse response
    try:
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content.strip())
    except json.JSONDecodeError:
        raise ValueError("AI impact analysis returned invalid response. Please try again.")

    predictions = []
    for pred in parsed.get("predictions", []):
        predictions.append(ImpactPrediction(
            affected_area=pred.get("affected_area", "Unknown"),
            risk_level=pred.get("risk_level", "medium"),
            description=pred.get("description", ""),
            affected_peers=pred.get("affected_peers", []),
            mitigation=pred.get("mitigation"),
        ))

    response = ImpactAnalysisResponse(
        device_id=request.device_id,
        device_name=device_info.get("hostname", "Unknown"),
        overall_risk=parsed.get("overall_risk", "medium"),
        predictions=predictions,
        safe_to_apply=parsed.get("safe_to_apply", False),
        recommended_window=parsed.get("recommended_window"),
        warnings=parsed.get("warnings", []),
    )

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.IMPACT_ANALYSIS.value,
            input_prompt=f"Impact analysis for device {request.device_id}: {request.proposed_config[:200]}",
            ai_response={
                "overall_risk": response.overall_risk,
                "predictions_count": len(predictions),
                "safe_to_apply": response.safe_to_apply,
            },
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return response


async def _get_device_info(device_id: int) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/{device_id}")
            return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        logger.error(f"Failed to get device {device_id}: {e}")
        return None


async def _get_current_config(device_id: int) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/history",
                params={"limit": 1},
            )
            if resp.status_code == 200:
                backups = resp.json()
                return backups[0].get("config_data", "") if backups else None
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
    return None


async def _get_recent_audit(device_id: int) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/results/{device_id}")
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list) and results:
                    latest = results[0]
                    return {
                        "compliance": latest.get("compliance"),
                        "status": latest.get("status"),
                        "findings_count": len(latest.get("findings", [])),
                        "top_findings": [f.get("rule_name", f.get("check_name", ""))
                                         for f in latest.get("findings", [])[:5]
                                         if f.get("status") == "fail"],
                    }
    except Exception as e:
        logger.error(f"Failed to get audit: {e}")
    return None


async def _get_related_devices(device_id: int, metadata: dict) -> List[dict]:
    """Find devices that might be affected by changes to this device"""
    related = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all devices
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
            if resp.status_code != 200:
                return []

            all_devices = resp.json()

            # Find BGP peers
            bgp_peers = metadata.get("bgp", {}).get("peers", [])
            peer_ips = set()
            for peer in bgp_peers if isinstance(bgp_peers, list) else []:
                if isinstance(peer, dict):
                    peer_ips.add(peer.get("peer_ip", ""))
                elif isinstance(peer, str):
                    peer_ips.add(peer)

            for device in all_devices:
                if device.get("id") == device_id:
                    continue
                if device.get("ip") in peer_ips:
                    related.append({
                        "hostname": device.get("hostname"),
                        "ip": device.get("ip"),
                        "relation": "BGP peer",
                    })

            # Get devices in the same groups
            resp = await client.get(f"{DEVICE_SERVICE_URL}/device-groups/")
            if resp.status_code == 200:
                groups = resp.json()
                for group in groups:
                    members = group.get("members", group.get("devices", []))
                    member_ids = []
                    for m in members:
                        if isinstance(m, dict):
                            member_ids.append(m.get("device_id") or m.get("id"))
                        elif isinstance(m, int):
                            member_ids.append(m)

                    if device_id in member_ids:
                        for mid in member_ids:
                            if mid != device_id:
                                for d in all_devices:
                                    if d.get("id") == mid and d.get("hostname") not in [r.get("hostname") for r in related]:
                                        related.append({
                                            "hostname": d.get("hostname"),
                                            "ip": d.get("ip"),
                                            "relation": f"Same group: {group.get('name', '')}",
                                        })

    except Exception as e:
        logger.error(f"Failed to get related devices: {e}")

    return related[:10]  # Limit to 10
