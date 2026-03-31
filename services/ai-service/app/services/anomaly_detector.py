"""
Anomaly Detection Service for Configuration Drift
Scores configuration changes to reduce alert fatigue.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from models.schemas import (
    AnomalyDetectionRequest, AnomalyDetectionResponse, AnomalyScore,
    AnomalySeverity, LLMRequest, InteractionType,
)
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")

# Heuristic scoring weights
WEIGHTS = {
    "off_hours": 0.3,         # Changes outside business hours
    "large_change": 0.25,     # Large number of lines changed
    "critical_section": 0.35, # Changes to security/routing/ACL sections
    "multi_device": 0.2,      # Same change across multiple devices
    "no_audit_trail": 0.3,    # Change without corresponding audit log
    "frequency": 0.15,        # Unusually frequent changes
}

# Sections considered critical
CRITICAL_SECTIONS = [
    "bgp", "ospf", "isis", "ldp", "mpls", "rsvp",
    "acl", "access-list", "prefix-list", "route-policy",
    "ssh", "aaa", "tacacs", "radius", "snmp", "ntp",
    "crypto", "ipsec", "ikev2", "keychain",
    "management", "console", "vty", "line",
]


async def detect_anomalies(
    request: AnomalyDetectionRequest,
    db: Session,
) -> AnomalyDetectionResponse:
    """Analyze recent config changes and score them for anomalies"""

    # Fetch recent config changes
    changes = await _fetch_config_changes(request.device_id, request.hours_back)

    if not changes:
        return AnomalyDetectionResponse(
            anomalies=[],
            total_changes_analyzed=0,
            anomalies_found=0,
            analysis_window_hours=request.hours_back,
        )

    # Score each change using heuristics
    scored_changes = []
    for change in changes:
        score, reasons = _score_change_heuristic(change, changes)
        if score >= request.min_score:
            scored_changes.append({
                "change": change,
                "score": score,
                "reasons": reasons,
            })

    # For high-scoring changes, use LLM for deeper analysis
    anomalies = []
    high_score_changes = [sc for sc in scored_changes if sc["score"] >= 0.5]

    if high_score_changes:
        ai_scores = await _ai_analyze_changes(high_score_changes[:10])  # Limit to 10 for cost
        for sc, ai_result in zip(high_score_changes[:10], ai_scores):
            # Blend heuristic and AI scores
            final_score = (sc["score"] * 0.4) + (ai_result.get("score", sc["score"]) * 0.6)
            reasons = sc["reasons"] + ai_result.get("additional_reasons", [])
            anomalies.append(_build_anomaly_score(sc["change"], final_score, reasons))
    else:
        # Use heuristic scores only for lower-scoring items
        for sc in scored_changes:
            anomalies.append(_build_anomaly_score(sc["change"], sc["score"], sc["reasons"]))

    # Add remaining heuristic-only results
    remaining = [sc for sc in scored_changes if sc["score"] < 0.5]
    for sc in remaining:
        anomalies.append(_build_anomaly_score(sc["change"], sc["score"], sc["reasons"]))

    # Sort by score descending
    anomalies.sort(key=lambda a: a.score, reverse=True)

    # Deduplicate
    seen_ids = set()
    unique_anomalies = []
    for a in anomalies:
        if a.change_event_id not in seen_ids:
            seen_ids.add(a.change_event_id)
            unique_anomalies.append(a)

    # Log summary
    interaction_id = None
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.ANOMALY.value,
            input_prompt=f"Anomaly detection: device={request.device_id}, hours={request.hours_back}",
            ai_response={
                "total_changes": len(changes),
                "anomalies_found": len(unique_anomalies),
                "top_score": unique_anomalies[0].score if unique_anomalies else 0,
            },
            model_used="heuristic+llm",
            tokens_used=0,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        interaction_id = interaction.id
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return AnomalyDetectionResponse(
        anomalies=unique_anomalies,
        total_changes_analyzed=len(changes),
        anomalies_found=len(unique_anomalies),
        analysis_window_hours=request.hours_back,
        interaction_id=interaction_id,
    )


def _score_change_heuristic(change: dict, all_changes: list) -> tuple:
    """Score a config change using heuristic rules"""
    score = 0.0
    reasons = []

    # Check time of change
    try:
        ts = datetime.fromisoformat(change.get("timestamp", "").replace("Z", "+00:00"))
        hour = ts.hour
        if hour < 6 or hour > 22:  # Off hours
            score += WEIGHTS["off_hours"]
            reasons.append(f"Change occurred at off-hours ({ts.strftime('%H:%M')})")
        if ts.weekday() >= 5:  # Weekend
            score += WEIGHTS["off_hours"] * 0.5
            reasons.append("Change occurred on weekend")
    except (ValueError, AttributeError):
        pass

    # Check change size
    summary = change.get("change_summary", {})
    if isinstance(summary, dict):
        added = summary.get("added_lines", 0)
        removed = summary.get("removed_lines", 0)
        total_lines = added + removed
        if total_lines > 50:
            score += WEIGHTS["large_change"]
            reasons.append(f"Large change: {total_lines} lines modified")
        elif total_lines > 20:
            score += WEIGHTS["large_change"] * 0.5
            reasons.append(f"Moderate change: {total_lines} lines modified")

    # Check for critical section changes
    diff_text = (change.get("diff_text") or "").lower()
    change_type = (change.get("change_type") or "").lower()
    critical_hits = [section for section in CRITICAL_SECTIONS if section in diff_text]
    if critical_hits:
        score += WEIGHTS["critical_section"]
        reasons.append(f"Critical sections affected: {', '.join(critical_hits[:5])}")

    # Check severity
    severity = (change.get("severity") or "").lower()
    if severity == "critical":
        score += 0.2
        reasons.append("Severity: critical")
    elif severity == "high":
        score += 0.1
        reasons.append("Severity: high")

    # Check if change type is unknown/drift
    if change_type in ("drift", "unknown"):
        score += 0.15
        reasons.append(f"Change type: {change_type} (not from planned operation)")

    # Check for multi-device pattern
    device_id = change.get("device_id")
    same_time_changes = [
        c for c in all_changes
        if c.get("device_id") != device_id
        and c.get("change_type") == change_type
        and abs(_time_diff_minutes(c.get("timestamp"), change.get("timestamp"))) < 30
    ]
    if same_time_changes:
        score += WEIGHTS["multi_device"]
        reasons.append(f"Similar changes on {len(same_time_changes)} other device(s) within 30 min")

    return min(score, 1.0), reasons


def _time_diff_minutes(ts1: str, ts2: str) -> float:
    """Calculate time difference in minutes between two timestamps"""
    try:
        t1 = datetime.fromisoformat((ts1 or "").replace("Z", "+00:00"))
        t2 = datetime.fromisoformat((ts2 or "").replace("Z", "+00:00"))
        return abs((t1 - t2).total_seconds()) / 60
    except (ValueError, AttributeError):
        return float("inf")


async def _ai_analyze_changes(scored_changes: list) -> list:
    """Use LLM for deeper analysis of suspicious changes"""
    changes_text = json.dumps(
        [{"diff": sc["change"].get("diff_text", "")[:500],
          "type": sc["change"].get("change_type"),
          "severity": sc["change"].get("severity"),
          "heuristic_score": sc["score"],
          "heuristic_reasons": sc["reasons"]}
         for sc in scored_changes],
        indent=2
    )

    prompt = f"""Analyze these network configuration changes for anomalies.
For each change, provide:
- score: 0.0 (routine) to 1.0 (definitely anomalous)
- additional_reasons: list of reasons beyond what heuristics found

Consider: unauthorized access patterns, configuration backdoors, security weakening,
unexpected routing changes, management plane modifications.

Changes:
{changes_text[:6000]}

Respond with JSON array of objects with "score" and "additional_reasons" fields.
One object per change, in the same order."""

    try:
        llm_request = LLMRequest(
            system_prompt="You are a network security analyst specializing in configuration anomaly detection. Analyze changes for suspicious patterns.",
            user_prompt=prompt,
            temperature=0.1,
            max_tokens=2048,
        )
        response = await call_llm(llm_request)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content.strip())
    except Exception as e:
        logger.warning(f"AI anomaly analysis failed: {e}")
        return [{"score": sc["score"], "additional_reasons": []} for sc in scored_changes]


def _build_anomaly_score(change: dict, score: float, reasons: list) -> AnomalyScore:
    """Build an AnomalyScore from change data"""
    if score >= 0.8:
        severity = AnomalySeverity.CRITICAL
    elif score >= 0.5:
        severity = AnomalySeverity.SUSPICIOUS
    elif score >= 0.3:
        severity = AnomalySeverity.NOTABLE
    else:
        severity = AnomalySeverity.ROUTINE

    summary = change.get("change_summary", {})
    if isinstance(summary, dict):
        change_desc = f"{summary.get('added_lines', 0)} added, {summary.get('removed_lines', 0)} removed"
    else:
        change_desc = str(summary)[:200]

    return AnomalyScore(
        change_event_id=change.get("id", 0),
        device_id=change.get("device_id", 0),
        device_name=change.get("device_name", "Unknown"),
        score=round(score, 3),
        severity=severity,
        reasons=reasons,
        change_summary=change_desc,
        timestamp=change.get("timestamp", datetime.utcnow().isoformat()),
    )


async def _fetch_config_changes(device_id: Optional[int], hours_back: int) -> list:
    """Fetch config change events from backup service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get all devices and their changes
            if device_id:
                resp = await client.get(
                    f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/changes",
                    params={"limit": 100}
                )
                return resp.json() if resp.status_code == 200 else []
            else:
                # Get all devices first, then changes
                devices_resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
                if devices_resp.status_code != 200:
                    return []

                all_changes = []
                for device in devices_resp.json()[:50]:  # Limit to 50 devices
                    try:
                        resp = await client.get(
                            f"{BACKUP_SERVICE_URL}/config-backups/device/{device['id']}/changes",
                            params={"limit": 20}
                        )
                        if resp.status_code == 200:
                            changes = resp.json()
                            for c in changes:
                                c["device_name"] = device.get("hostname", "Unknown")
                            all_changes.extend(changes)
                    except Exception:
                        continue

                # Filter by time window
                cutoff = datetime.utcnow() - timedelta(hours=hours_back)
                filtered = []
                for c in all_changes:
                    try:
                        ts = datetime.fromisoformat(c.get("timestamp", "").replace("Z", "+00:00"))
                        if ts.replace(tzinfo=None) >= cutoff:
                            filtered.append(c)
                    except (ValueError, AttributeError):
                        filtered.append(c)

                return filtered
    except Exception as e:
        logger.error(f"Error fetching config changes: {e}")
        return []
