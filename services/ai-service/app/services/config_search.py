"""
Embedding-Based Config Search Service
Semantic search over network configurations using vector embeddings.
"""

import json
import os
import hashlib
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.schemas import LLMRequest
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")

# In-memory embedding cache (replaced by pgvector in production)
_embedding_cache: Dict[str, Dict[str, Any]] = {}


async def semantic_search(
    query: str,
    db: Session,
    max_results: int = 10,
    vendor_filter: Optional[str] = None,
) -> dict:
    """Search configs using semantic similarity via LLM-powered analysis"""

    # Since full vector embeddings require pgvector infrastructure,
    # this implementation uses LLM-based semantic matching as a stepping stone.
    # Future: replace with actual embeddings + pgvector similarity search.

    # Get all devices and their config snippets
    configs = await _get_all_config_snippets(vendor_filter)

    if not configs:
        return {"results": [], "message": "No configuration data available"}

    # Use LLM to rank configs by semantic relevance
    prompt = f"""You are searching network device configurations for semantic matches.

SEARCH QUERY: "{query}"

DEVICE CONFIGURATIONS (hostname: config snippet):
{json.dumps({k: v[:800] for k, v in list(configs.items())[:30]}, indent=1)[:10000]}

Rank the devices by relevance to the search query. Return the top {max_results} matches.

Return JSON:
{{
  "results": [
    {{
      "hostname": "device-name",
      "relevance_score": 0.95,
      "matched_section": "The specific config section that matches",
      "explanation": "Why this matches the query"
    }}
  ],
  "query_interpretation": "How you interpreted the search query"
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network configuration search engine. Match search queries to config sections semantically, not just by keyword.",
        user_prompt=prompt,
        temperature=0.1,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    try:
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        result = json.loads(content.strip())
    except json.JSONDecodeError:
        result = {"results": [], "error": "Failed to parse search results"}

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type="config_search",
            input_prompt=query,
            ai_response={"results_count": len(result.get("results", []))},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return result


async def find_similar_configs(
    device_id: int,
    db: Session,
    section: Optional[str] = None,
) -> dict:
    """Find devices with similar configurations to a reference device"""

    # Get reference config
    ref_config = await _get_device_config(device_id)
    ref_device = await _get_device_info(device_id)

    if not ref_config or not ref_device:
        raise ValueError(f"Device {device_id} or its config not found")

    # Get all other configs
    configs = await _get_all_config_snippets()

    # Remove the reference device
    ref_hostname = ref_device.get("hostname", "")
    configs.pop(ref_hostname, None)

    if not configs:
        return {"similar_devices": [], "message": "No other devices to compare with"}

    ref_snippet = ref_config[:3000]
    if section:
        # Extract specific section from config
        section_text = _extract_section(ref_config, section)
        if section_text:
            ref_snippet = section_text[:3000]

    prompt = f"""Compare this reference device configuration with other devices and rank by similarity.

REFERENCE DEVICE: {ref_hostname} ({ref_device.get('vendor')})
{f'SECTION FOCUS: {section}' if section else ''}
REFERENCE CONFIG:
{ref_snippet}

OTHER DEVICE CONFIGS:
{json.dumps({k: v[:600] for k, v in list(configs.items())[:20]}, indent=1)[:8000]}

Rank devices by config similarity to the reference. Consider:
- Same protocol configurations (BGP, OSPF, MPLS)
- Similar interface configurations
- Same security policies
- Similar QoS configurations

Return JSON:
{{
  "similar_devices": [
    {{
      "hostname": "device-name",
      "similarity_score": 0.85,
      "common_sections": ["BGP", "ACL"],
      "key_differences": ["Different OSPF area", "Extra VRFs"]
    }}
  ],
  "outliers": [
    {{
      "hostname": "device-name",
      "reason": "Significantly different config pattern"
    }}
  ]
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network configuration similarity analyzer. Compare configs structurally, not just textually.",
        user_prompt=prompt,
        temperature=0.1,
        max_tokens=4096,
    )

    response = await call_llm(llm_request)

    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return {"similar_devices": [], "analysis": response.content}


def _extract_section(config: str, section_name: str) -> Optional[str]:
    """Extract a named section from a config"""
    lines = config.split("\n")
    in_section = False
    section_lines = []
    section_lower = section_name.lower()

    for line in lines:
        stripped = line.strip().lower()
        if section_lower in stripped and not line.startswith((" ", "\t")):
            in_section = True
            section_lines.append(line)
        elif in_section:
            if line.startswith((" ", "\t")) or not stripped:
                section_lines.append(line)
            elif stripped.startswith(("!", "#")):
                section_lines.append(line)
            else:
                break

    return "\n".join(section_lines) if section_lines else None


async def _get_all_config_snippets(vendor_filter: Optional[str] = None) -> Dict[str, str]:
    """Get config snippets for all devices"""
    configs = {}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
            if resp.status_code != 200:
                return {}

            devices = resp.json()
            if vendor_filter:
                devices = [d for d in devices if d.get("vendor") == vendor_filter]

            for device in devices[:50]:
                try:
                    resp = await client.get(
                        f"{BACKUP_SERVICE_URL}/config-backups/device/{device['id']}/history",
                        params={"limit": 1},
                    )
                    if resp.status_code == 200:
                        backups = resp.json()
                        if backups:
                            configs[device.get("hostname", f"device-{device['id']}")] = backups[0].get("config_data", "")
                except Exception:
                    continue

    except Exception as e:
        logger.error(f"Error fetching configs: {e}")

    return configs


async def _get_device_config(device_id: int) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/history",
                params={"limit": 1},
            )
            if resp.status_code == 200:
                backups = resp.json()
                return backups[0].get("config_data", "") if backups else None
    except Exception:
        return None


async def _get_device_info(device_id: int) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/{device_id}")
            return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None
