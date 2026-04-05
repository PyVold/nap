"""
MCP (Model Context Protocol) Server for NAP
Exposes NAP tools, resources, and prompts via MCP protocol.
"""

import json
import os
import httpx
from typing import Any, Dict, List, Optional
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:3004")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin-service:3005")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:3006")


# ============================================================================
# MCP Tool Definitions
# ============================================================================

MCP_TOOLS = [
    {
        "name": "nap_get_devices",
        "description": "List and filter network devices managed by NAP. Returns device hostname, vendor, IP, status, and compliance score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vendor": {"type": "string", "enum": ["cisco_xr", "nokia_sros"], "description": "Filter by vendor type"},
                "status": {"type": "string", "description": "Filter by device status (online, offline, degraded)"},
                "min_compliance": {"type": "number", "description": "Minimum compliance score (0-100)"},
            },
        },
    },
    {
        "name": "nap_get_device_config",
        "description": "Retrieve the current or historical configuration for a specific network device.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Device ID"},
                "version": {"type": "string", "description": "Config version: 'latest' or backup ID"},
            },
            "required": ["device_id"],
        },
    },
    {
        "name": "nap_compare_configs",
        "description": "Compare two configuration versions and return the unified diff.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "backup_id_1": {"type": "integer", "description": "First backup ID"},
                "backup_id_2": {"type": "integer", "description": "Second backup ID"},
            },
            "required": ["backup_id_1", "backup_id_2"],
        },
    },
    {
        "name": "nap_get_audit_results",
        "description": "Retrieve audit results with compliance findings. Can filter by device or get fleet-wide results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Filter by device ID"},
                "latest_only": {"type": "boolean", "default": True, "description": "Only return latest results per device"},
            },
        },
    },
    {
        "name": "nap_get_compliance_score",
        "description": "Get current compliance score and summary for the fleet or a specific device.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "nap_get_config_changes",
        "description": "List recent configuration changes with diffs and metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Filter by device ID"},
                "limit": {"type": "integer", "default": 20, "description": "Maximum number of changes to return"},
            },
        },
    },
    {
        "name": "nap_get_health_status",
        "description": "Get device health check results including ping, NETCONF, and SSH status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Filter by device ID"},
            },
        },
    },
    {
        "name": "nap_get_hardware_inventory",
        "description": "Retrieve hardware inventory for a device (chassis, cards, power supplies, fans).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Device ID"},
            },
            "required": ["device_id"],
        },
    },
    {
        "name": "nap_search_rules",
        "description": "Search audit rules by keyword, category, or severity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Filter by category"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                "enabled_only": {"type": "boolean", "default": True},
            },
        },
    },
    {
        "name": "nap_get_drift_summary",
        "description": "Get configuration drift detection summary across the fleet.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "nap_run_audit",
        "description": "Execute a compliance audit on specific devices. Requires human approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_ids": {"type": "array", "items": {"type": "integer"}, "description": "Device IDs to audit"},
                "rule_ids": {"type": "array", "items": {"type": "integer"}, "description": "Rule IDs to check (null = all)"},
            },
            "required": ["device_ids"],
        },
    },
    {
        "name": "nap_query_knowledge_base",
        "description": "Search the vendor knowledge base for best practices, troubleshooting guides, configuration standards, and documentation. Use this for technical questions about BGP, MPLS, NTP, ACLs, NETCONF, drift prevention, etc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'BGP best practices for Cisco IOS-XR')"},
                "category": {"type": "string", "enum": ["best_practices", "troubleshooting", "general"], "description": "Filter by category"},
                "vendor": {"type": "string", "enum": ["cisco_xr", "nokia_sros"], "description": "Filter by vendor"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "nap_get_backup_history",
        "description": "Get configuration backup history for a specific device, including timestamps, sizes, and change indicators.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Device ID"},
                "limit": {"type": "integer", "default": 10, "description": "Max backups to return"},
            },
            "required": ["device_id"],
        },
    },
    {
        "name": "nap_get_device_detail",
        "description": "Get detailed information for a specific device including metadata (software version, chassis, BGP ASN, ISIS NET, interfaces).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Device ID"},
            },
            "required": ["device_id"],
        },
    },
]

# ============================================================================
# MCP Resource Definitions
# ============================================================================

MCP_RESOURCES = [
    {
        "uri": "nap://devices",
        "name": "Network Devices",
        "description": "Live inventory of all managed network devices with status and compliance",
        "mimeType": "application/json",
    },
    {
        "uri": "nap://compliance/dashboard",
        "name": "Compliance Dashboard",
        "description": "Fleet-wide compliance overview with scores and trend data",
        "mimeType": "application/json",
    },
    {
        "uri": "nap://changes/recent",
        "name": "Recent Changes",
        "description": "Recent configuration changes across the network",
        "mimeType": "application/json",
    },
    {
        "uri": "nap://health/summary",
        "name": "Health Summary",
        "description": "Network device health status summary",
        "mimeType": "application/json",
    },
    {
        "uri": "nap://rules",
        "name": "Audit Rules",
        "description": "All configured audit rules with their definitions",
        "mimeType": "application/json",
    },
]

# ============================================================================
# MCP Prompt Definitions
# ============================================================================

MCP_PROMPTS = [
    {
        "name": "network-troubleshoot",
        "description": "Guided troubleshooting for a network device using NAP data",
        "arguments": [
            {"name": "device_id", "description": "Device ID to troubleshoot", "required": True},
            {"name": "symptom", "description": "Symptom or issue description", "required": True},
        ],
    },
    {
        "name": "compliance-review",
        "description": "Comprehensive compliance review for a device or group",
        "arguments": [
            {"name": "target", "description": "Device ID or group name", "required": True},
            {"name": "framework", "description": "Compliance framework (SOX, PCI-DSS, NIST)", "required": False},
        ],
    },
    {
        "name": "change-review",
        "description": "Review recent configuration changes for risk assessment",
        "arguments": [
            {"name": "hours_back", "description": "Hours to look back (default 24)", "required": False},
        ],
    },
]


# ============================================================================
# Tool Execution
# ============================================================================

async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute an MCP tool and return the result"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if tool_name == "nap_get_devices":
                return await _get_devices(client, arguments)
            elif tool_name == "nap_get_device_config":
                return await _get_device_config(client, arguments)
            elif tool_name == "nap_compare_configs":
                return await _compare_configs(client, arguments)
            elif tool_name == "nap_get_audit_results":
                return await _get_audit_results(client, arguments)
            elif tool_name == "nap_get_compliance_score":
                return await _get_compliance_score(client)
            elif tool_name == "nap_get_config_changes":
                return await _get_config_changes(client, arguments)
            elif tool_name == "nap_get_health_status":
                return await _get_health_status(client, arguments)
            elif tool_name == "nap_get_hardware_inventory":
                return await _get_hardware_inventory(client, arguments)
            elif tool_name == "nap_search_rules":
                return await _search_rules(client, arguments)
            elif tool_name == "nap_get_drift_summary":
                return await _get_drift_summary(client)
            elif tool_name == "nap_run_audit":
                return await _run_audit(client, arguments)
            elif tool_name == "nap_query_knowledge_base":
                return await _query_knowledge_base(arguments)
            elif tool_name == "nap_get_backup_history":
                return await _get_backup_history(client, arguments)
            elif tool_name == "nap_get_device_detail":
                return await _get_device_detail(client, arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {e}")
            return {"error": str(e)}


async def read_resource(uri: str) -> Any:
    """Read an MCP resource"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if uri == "nap://devices":
                resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
                return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch devices"}
            elif uri == "nap://compliance/dashboard":
                resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
                return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch compliance"}
            elif uri == "nap://changes/recent":
                return await _get_config_changes(client, {"limit": 50})
            elif uri == "nap://health/summary":
                resp = await client.get(f"{DEVICE_SERVICE_URL}/health/summary")
                return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch health"}
            elif uri == "nap://rules":
                resp = await client.get(f"{RULE_SERVICE_URL}/rules/")
                return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch rules"}
            else:
                return {"error": f"Unknown resource: {uri}"}
        except Exception as e:
            logger.error(f"Error reading MCP resource {uri}: {e}")
            return {"error": str(e)}


async def get_prompt(name: str, arguments: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate MCP prompt messages"""
    if name == "network-troubleshoot":
        device_id = arguments.get("device_id")
        symptom = arguments.get("symptom", "")
        device = await _fetch_json(f"{DEVICE_SERVICE_URL}/devices/{device_id}")
        health = await _fetch_json(f"{DEVICE_SERVICE_URL}/health/device/{device_id}")
        audit = await _fetch_json(f"{RULE_SERVICE_URL}/audit/results/{device_id}")

        return [
            {"role": "user", "content": f"""Troubleshoot this network device issue:

Device: {json.dumps(device, indent=2, default=str)[:1000]}
Symptom: {symptom}
Health Status: {json.dumps(health, indent=2, default=str)[:1000]}
Latest Audit: {json.dumps(audit, indent=2, default=str)[:2000]}

Analyze the device data and provide a troubleshooting plan."""}
        ]

    elif name == "compliance-review":
        target = arguments.get("target")
        framework = arguments.get("framework", "general")
        compliance = await _fetch_json(f"{RULE_SERVICE_URL}/audit/compliance")
        results = await _fetch_json(f"{RULE_SERVICE_URL}/audit/results?latest_only=true")

        return [
            {"role": "user", "content": f"""Perform a compliance review:

Target: {target}
Framework: {framework}
Compliance Summary: {json.dumps(compliance, indent=2, default=str)[:2000]}
Audit Results: {json.dumps(results[:10], indent=2, default=str)[:4000]}

Provide a comprehensive compliance assessment."""}
        ]

    elif name == "change-review":
        hours = arguments.get("hours_back", 24)
        changes = await _get_config_changes(None, {"limit": 50})

        return [
            {"role": "user", "content": f"""Review these recent network configuration changes for risk:

Time window: Last {hours} hours
Changes: {json.dumps(changes[:20] if isinstance(changes, list) else changes, indent=2, default=str)[:6000]}

Assess each change for risk and provide recommendations."""}
        ]

    return [{"role": "user", "content": f"Unknown prompt: {name}"}]


# ============================================================================
# Internal Tool Implementations
# ============================================================================

async def _get_devices(client: httpx.AsyncClient, args: dict) -> Any:
    resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
    if resp.status_code != 200:
        return {"error": "Failed to fetch devices"}
    devices = resp.json()

    # Apply filters
    vendor = args.get("vendor")
    status = args.get("status")
    min_compliance = args.get("min_compliance")

    if vendor:
        devices = [d for d in devices if d.get("vendor") == vendor]
    if status:
        devices = [d for d in devices if d.get("status") == status]
    if min_compliance is not None:
        devices = [d for d in devices if (d.get("compliance") or 0) >= min_compliance]

    return devices


async def _get_device_config(client: httpx.AsyncClient, args: dict) -> Any:
    device_id = args["device_id"]
    version = args.get("version", "latest")

    if version == "latest":
        resp = await client.get(
            f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/history",
            params={"limit": 1}
        )
        if resp.status_code == 200:
            backups = resp.json()
            return backups[0] if backups else {"message": "No config backups found"}
    else:
        resp = await client.get(f"{BACKUP_SERVICE_URL}/config-backups/{version}")
        return resp.json() if resp.status_code == 200 else {"error": f"Backup {version} not found"}

    return {"error": "Failed to fetch config"}


async def _compare_configs(client: httpx.AsyncClient, args: dict) -> Any:
    resp = await client.get(
        f"{BACKUP_SERVICE_URL}/config-backups/compare/{args['backup_id_1']}/{args['backup_id_2']}"
    )
    return resp.json() if resp.status_code == 200 else {"error": "Failed to compare configs"}


async def _get_audit_results(client: httpx.AsyncClient, args: dict) -> Any:
    params = {"latest_only": str(args.get("latest_only", True)).lower()}
    if args.get("device_id"):
        resp = await client.get(f"{RULE_SERVICE_URL}/audit/results/{args['device_id']}")
    else:
        resp = await client.get(f"{RULE_SERVICE_URL}/audit/results", params=params)
    return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch audit results"}


async def _get_compliance_score(client: httpx.AsyncClient) -> Any:
    resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
    return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch compliance"}


async def _get_config_changes(client: Optional[httpx.AsyncClient], args: dict) -> Any:
    should_close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)

    try:
        device_id = args.get("device_id")
        limit = args.get("limit", 20)

        if device_id:
            resp = await client.get(
                f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/changes",
                params={"limit": limit}
            )
            return resp.json() if resp.status_code == 200 else []
        else:
            # Get changes across all devices
            devices_resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
            if devices_resp.status_code != 200:
                return []

            all_changes = []
            for device in devices_resp.json()[:30]:
                try:
                    resp = await client.get(
                        f"{BACKUP_SERVICE_URL}/config-backups/device/{device['id']}/changes",
                        params={"limit": 5}
                    )
                    if resp.status_code == 200:
                        changes = resp.json()
                        for c in changes:
                            c["device_name"] = device.get("hostname")
                        all_changes.extend(changes)
                except Exception:
                    continue

            all_changes.sort(key=lambda c: c.get("timestamp", ""), reverse=True)
            return all_changes[:limit]
    finally:
        if should_close:
            await client.aclose()


async def _get_health_status(client: httpx.AsyncClient, args: dict) -> Any:
    device_id = args.get("device_id")
    if device_id:
        resp = await client.get(f"{DEVICE_SERVICE_URL}/health/device/{device_id}")
    else:
        resp = await client.get(f"{DEVICE_SERVICE_URL}/health/summary")
    return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch health"}


async def _get_hardware_inventory(client: httpx.AsyncClient, args: dict) -> Any:
    device_id = args["device_id"]
    resp = await client.get(f"{INVENTORY_SERVICE_URL}/hardware/device/{device_id}")
    return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch inventory"}


async def _search_rules(client: httpx.AsyncClient, args: dict) -> Any:
    resp = await client.get(f"{RULE_SERVICE_URL}/rules/")
    if resp.status_code != 200:
        return {"error": "Failed to fetch rules"}

    rules = resp.json()
    category = args.get("category")
    severity = args.get("severity")
    enabled_only = args.get("enabled_only", True)

    if enabled_only:
        rules = [r for r in rules if r.get("enabled", True)]
    if category:
        rules = [r for r in rules if (r.get("category") or "").lower() == category.lower()]
    if severity:
        rules = [r for r in rules if (r.get("severity") or "").lower() == severity.lower()]

    return rules


async def _get_drift_summary(client: httpx.AsyncClient) -> Any:
    resp = await client.get(f"{BACKUP_SERVICE_URL}/drift-detection/summary")
    return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch drift summary"}


async def _run_audit(client: httpx.AsyncClient, args: dict) -> Any:
    payload = {
        "device_ids": args["device_ids"],
    }
    if args.get("rule_ids"):
        payload["rule_ids"] = args["rule_ids"]

    resp = await client.post(f"{RULE_SERVICE_URL}/audit/", json=payload)
    if resp.status_code in (200, 202):
        return {"status": "audit_started", "details": resp.json()}
    return {"error": f"Failed to start audit: {resp.status_code}"}


async def _query_knowledge_base(args: dict) -> Any:
    """Search the knowledge base using text matching (RAG-style).
    Runs inside ai-service — no HTTP call needed."""
    from shared.database import SessionLocal
    from shared.db_models import KnowledgeBaseDB
    from sqlalchemy import or_

    query = args.get("query", "")
    category = args.get("category")
    vendor = args.get("vendor")

    db = SessionLocal()
    try:
        kb_query = db.query(KnowledgeBaseDB)
        if category:
            kb_query = kb_query.filter(KnowledgeBaseDB.category == category)
        if vendor:
            kb_query = kb_query.filter(
                or_(KnowledgeBaseDB.vendor == vendor, KnowledgeBaseDB.vendor.is_(None))
            )

        entries = kb_query.all()

        if not entries:
            # Bootstrap defaults
            from services.knowledge_base import _bootstrap_defaults
            await _bootstrap_defaults(db)
            entries = db.query(KnowledgeBaseDB).all()

        # Simple keyword relevance scoring
        query_words = set(query.lower().split())
        scored = []
        for e in entries:
            text = f"{e.title} {e.content} {' '.join(e.tags or [])}".lower()
            score = sum(1 for w in query_words if w in text)
            if score > 0:
                scored.append((score, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]  # Top 5 relevant entries

        if not top:
            return {"message": "No relevant knowledge base entries found", "query": query, "results": []}

        return {
            "query": query,
            "results": [
                {
                    "title": e.title,
                    "content": e.content,
                    "category": e.category,
                    "vendor": e.vendor,
                    "tags": e.tags or [],
                    "relevance_score": score,
                }
                for score, e in top
            ],
        }
    finally:
        db.close()


async def _get_backup_history(client: httpx.AsyncClient, args: dict) -> Any:
    device_id = args["device_id"]
    limit = args.get("limit", 10)
    resp = await client.get(
        f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/history",
        params={"limit": limit}
    )
    return resp.json() if resp.status_code == 200 else {"error": "Failed to fetch backup history"}


async def _get_device_detail(client: httpx.AsyncClient, args: dict) -> Any:
    device_id = args["device_id"]
    resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/{device_id}")
    return resp.json() if resp.status_code == 200 else {"error": f"Device {device_id} not found"}


async def _fetch_json(url: str) -> Any:
    """Utility to fetch JSON from a URL"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            return resp.json() if resp.status_code == 200 else {}
    except Exception:
        return {}
