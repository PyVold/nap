"""
Multi-Agent Network Operations
Orchestrator that delegates complex tasks to specialized AI agents.
"""

import json
import os
import asyncio
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.schemas import LLMRequest
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:3004")

# Agent definitions
AGENTS = {
    "audit": {
        "name": "Audit Agent",
        "description": "Runs audits, creates rules, analyzes compliance findings",
        "capabilities": ["run_audit", "check_compliance", "analyze_findings", "create_rules"],
    },
    "config": {
        "name": "Config Agent",
        "description": "Manages config backups, diffs, drift detection, config optimization",
        "capabilities": ["get_config", "compare_configs", "check_drift", "optimize_config"],
    },
    "health": {
        "name": "Health Agent",
        "description": "Checks device reachability, health status, hardware inventory",
        "capabilities": ["check_health", "ping_device", "check_netconf", "get_inventory"],
    },
    "report": {
        "name": "Report Agent",
        "description": "Generates reports, summaries, trend analysis, and documentation",
        "capabilities": ["generate_report", "summarize_findings", "analyze_trends"],
    },
}

ORCHESTRATOR_PROMPT = """You are the Orchestrator Agent for the Network Audit Platform.
Your job is to decompose complex network operations into subtasks and delegate them to specialized agents.

AVAILABLE AGENTS:
1. audit: Runs audits, checks compliance, analyzes findings, creates rules
2. config: Manages configs, diffs, drift detection, optimization
3. health: Checks device health, reachability, hardware inventory
4. report: Generates reports, summaries, trend analysis

RULES:
- Analyze the user's request and create a plan of parallel/sequential agent tasks
- Each task should specify: agent, action, parameters, and dependencies
- Tasks with no dependencies can run in parallel
- Always include a final report/summary task

Return a JSON execution plan:
{
  "plan_summary": "Brief description of the overall plan",
  "tasks": [
    {
      "id": "task_1",
      "agent": "health",
      "action": "check_health",
      "description": "Check health of all affected devices",
      "parameters": {"device_ids": [1, 2, 3]},
      "depends_on": [],
      "critical": true
    },
    {
      "id": "task_2",
      "agent": "config",
      "action": "get_config",
      "description": "Get current configs for comparison",
      "parameters": {"device_ids": [1, 2, 3]},
      "depends_on": [],
      "critical": false
    },
    {
      "id": "task_3",
      "agent": "report",
      "action": "summarize_findings",
      "description": "Compile final report",
      "parameters": {},
      "depends_on": ["task_1", "task_2"],
      "critical": true
    }
  ]
}"""


async def orchestrate(
    request: str,
    db: Session,
    context: Optional[Dict[str, Any]] = None,
) -> dict:
    """Orchestrate a complex multi-agent operation"""

    # Step 1: Plan the operation
    plan = await _create_plan(request, context)

    if not plan or not plan.get("tasks"):
        return {"error": "Failed to create execution plan", "raw_plan": plan}

    # Step 2: Execute tasks respecting dependencies
    results = {}
    tasks = plan.get("tasks", [])
    completed = set()
    max_rounds = 10  # Safety limit

    for _ in range(max_rounds):
        # Find tasks ready to execute (all dependencies met)
        ready = [
            t for t in tasks
            if t["id"] not in completed
            and all(dep in completed for dep in t.get("depends_on", []))
        ]

        if not ready:
            break

        # Execute ready tasks in parallel
        parallel_results = await asyncio.gather(
            *[_execute_agent_task(t, results, db) for t in ready],
            return_exceptions=True,
        )

        for task, result in zip(ready, parallel_results):
            if isinstance(result, Exception):
                results[task["id"]] = {"error": str(result), "agent": task["agent"]}
            else:
                results[task["id"]] = result
            completed.add(task["id"])

    # Step 3: Compile final summary
    summary = await _compile_summary(request, plan, results)

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type="multi_agent",
            input_prompt=request[:2000],
            ai_response={
                "tasks_planned": len(tasks),
                "tasks_completed": len(completed),
                "agents_used": list(set(t["agent"] for t in tasks)),
            },
            model_used="orchestrator",
            tokens_used=0,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return {
        "plan": plan.get("plan_summary", ""),
        "tasks_executed": len(completed),
        "tasks_total": len(tasks),
        "results": results,
        "summary": summary,
    }


async def _create_plan(request: str, context: Optional[dict]) -> dict:
    """Create an execution plan using the orchestrator LLM"""
    context_str = ""
    if context:
        context_str = f"\n\nADDITIONAL CONTEXT:\n{json.dumps(context, indent=2, default=str)[:2000]}"

    llm_request = LLMRequest(
        system_prompt=ORCHESTRATOR_PROMPT,
        user_prompt=f"User request: {request}{context_str}\n\nCreate an execution plan.",
        temperature=0.2,
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
        return {"plan_summary": "Failed to parse plan", "tasks": []}


async def _execute_agent_task(
    task: dict,
    previous_results: dict,
    db: Session,
) -> dict:
    """Execute a single agent task"""
    agent_name = task.get("agent")
    action = task.get("action")
    params = task.get("parameters", {})

    logger.info(f"Executing {agent_name}.{action}: {task.get('description')}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if agent_name == "health":
                return await _health_agent(client, action, params)
            elif agent_name == "config":
                return await _config_agent(client, action, params)
            elif agent_name == "audit":
                return await _audit_agent(client, action, params)
            elif agent_name == "report":
                return await _report_agent(action, params, previous_results, db)
            else:
                return {"error": f"Unknown agent: {agent_name}"}
    except Exception as e:
        logger.error(f"Agent task failed: {agent_name}.{action}: {e}")
        return {"error": str(e)}


async def _health_agent(client: httpx.AsyncClient, action: str, params: dict) -> dict:
    """Health agent actions"""
    if action == "check_health":
        device_ids = params.get("device_ids", [])
        results = {}
        if device_ids:
            for did in device_ids[:20]:
                resp = await client.get(f"{DEVICE_SERVICE_URL}/health/device/{did}")
                results[str(did)] = resp.json() if resp.status_code == 200 else {"error": "unreachable"}
        else:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/health/summary")
            results = resp.json() if resp.status_code == 200 else {}
        return {"action": action, "results": results}

    elif action in ("ping_device", "check_netconf"):
        device_id = params.get("device_id")
        resp = await client.get(f"{DEVICE_SERVICE_URL}/health/device/{device_id}")
        return {"action": action, "result": resp.json() if resp.status_code == 200 else {}}

    elif action == "get_inventory":
        device_id = params.get("device_id")
        resp = await client.get(f"{INVENTORY_SERVICE_URL}/hardware/device/{device_id}")
        return {"action": action, "result": resp.json() if resp.status_code == 200 else {}}

    return {"action": action, "error": "Unknown health action"}


async def _config_agent(client: httpx.AsyncClient, action: str, params: dict) -> dict:
    """Config agent actions"""
    if action == "get_config":
        device_ids = params.get("device_ids", [])
        configs = {}
        for did in device_ids[:10]:
            resp = await client.get(
                f"{BACKUP_SERVICE_URL}/config-backups/device/{did}/history",
                params={"limit": 1},
            )
            if resp.status_code == 200:
                backups = resp.json()
                configs[str(did)] = {
                    "has_backup": len(backups) > 0,
                    "lines": len(backups[0].get("config_data", "").split("\n")) if backups else 0,
                }
        return {"action": action, "configs": configs}

    elif action == "compare_configs":
        id1 = params.get("backup_id_1")
        id2 = params.get("backup_id_2")
        resp = await client.get(f"{BACKUP_SERVICE_URL}/config-backups/compare/{id1}/{id2}")
        return {"action": action, "result": resp.json() if resp.status_code == 200 else {}}

    elif action == "check_drift":
        resp = await client.get(f"{BACKUP_SERVICE_URL}/drift-detection/summary")
        return {"action": action, "result": resp.json() if resp.status_code == 200 else {}}

    return {"action": action, "error": "Unknown config action"}


async def _audit_agent(client: httpx.AsyncClient, action: str, params: dict) -> dict:
    """Audit agent actions"""
    if action == "run_audit":
        device_ids = params.get("device_ids", [])
        resp = await client.post(
            f"{RULE_SERVICE_URL}/audit/",
            json={"device_ids": device_ids},
        )
        return {"action": action, "result": resp.json() if resp.status_code in (200, 202) else {"error": resp.status_code}}

    elif action == "check_compliance":
        resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
        return {"action": action, "result": resp.json() if resp.status_code == 200 else {}}

    elif action == "analyze_findings":
        device_id = params.get("device_id")
        if device_id:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/results/{device_id}")
        else:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/results", params={"latest_only": "true"})
        return {"action": action, "result": resp.json() if resp.status_code == 200 else {}}

    return {"action": action, "error": "Unknown audit action"}


async def _report_agent(
    action: str,
    params: dict,
    previous_results: dict,
    db: Session,
) -> dict:
    """Report agent uses LLM to synthesize results"""
    if action in ("summarize_findings", "generate_report", "analyze_trends"):
        prompt = f"""Synthesize these multi-agent operation results into a clear summary:

PREVIOUS AGENT RESULTS:
{json.dumps(previous_results, indent=2, default=str)[:8000]}

ACTION: {action}
PARAMETERS: {json.dumps(params, indent=2)}

Provide a clear, actionable summary with:
1. Key findings
2. Current status
3. Recommended actions
4. Risk assessment

Use markdown formatting."""

        llm_request = LLMRequest(
            system_prompt="You are a network operations report synthesizer. Compile multi-agent findings into actionable summaries.",
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        response = await call_llm(llm_request)
        return {"action": action, "report": response.content}

    return {"action": action, "error": "Unknown report action"}


async def _compile_summary(request: str, plan: dict, results: dict) -> str:
    """Compile a final summary of the multi-agent operation"""
    prompt = f"""Compile a final summary of this multi-agent network operation:

ORIGINAL REQUEST: {request}

PLAN: {plan.get('plan_summary', '')}

ALL RESULTS:
{json.dumps(results, indent=2, default=str)[:8000]}

Provide a concise executive summary with key findings and recommended next steps.
Use markdown formatting."""

    llm_request = LLMRequest(
        system_prompt="You are a network operations summary writer. Be concise but thorough.",
        user_prompt=prompt,
        temperature=0.3,
        max_tokens=2048,
    )

    response = await call_llm(llm_request)
    return response.content
