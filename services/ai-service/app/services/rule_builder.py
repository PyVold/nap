"""
Natural Language Rule Builder Service
Generates audit rules from plain English descriptions.
"""

import json
from typing import Optional
from sqlalchemy.orm import Session
from models.schemas import (
    RuleBuilderRequest, RuleBuilderResponse, GeneratedRule,
    GeneratedCheck, LLMRequest, InteractionType
)
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

SYSTEM_PROMPT = """You are an expert network compliance engineer for the Network Audit Platform (NAP).
Your job is to translate natural language compliance requirements into structured audit rules.

NAP supports two vendor types:
1. **cisco_xr** (Cisco IOS-XR) - Uses NETCONF with XML subtree filters
2. **nokia_sros** (Nokia SR OS) - Uses pysros with XPath queries and filter dicts

Each rule has one or more "checks". Each check has:
- name: Short descriptive name
- filter_xml: XML filter string for Cisco XR NETCONF get-config (null for Nokia)
- xpath: XPath expression for Nokia SROS (null for Cisco)
- filter: Dict filter for Nokia pysros (null for Cisco)
- comparison: One of: exact, contains, not_contains, regex, exists, not_exists, count
- reference_value: Expected value for comparison (string)
- error_message: Message shown when check fails
- success_message: Message shown when check passes

Severity levels: critical, high, medium, low
Common categories: Security, Authentication, Routing, Management, Encryption, Access-Control, Monitoring, NTP, SNMP, Logging

IMPORTANT RULES:
- Always generate vendor-specific checks (separate check per vendor if both are targeted)
- Use proper XML namespaces for Cisco IOS-XR NETCONF filters
- Use proper pysros paths for Nokia SR OS
- Be precise with XPath expressions
- Set appropriate severity based on security impact
- Generate both error and success messages

Respond with ONLY valid JSON in this exact format:
{
  "name": "Rule name",
  "description": "Detailed description",
  "severity": "high",
  "category": "Security",
  "vendors": ["cisco_xr"],
  "checks": [
    {
      "name": "Check name",
      "filter_xml": "<xml-filter/>",
      "xpath": null,
      "filter": null,
      "comparison": "exists",
      "reference_value": null,
      "error_message": "Failure message",
      "success_message": "Success message"
    }
  ],
  "explanation": "Brief explanation of what this rule checks and why"
}"""


async def generate_rule(
    request: RuleBuilderRequest,
    db: Session,
) -> RuleBuilderResponse:
    """Generate an audit rule from natural language description"""

    # Build the user prompt with context
    vendor_context = ""
    if request.vendor:
        vendor_context = f"\nTarget vendor: {request.vendor}"
    else:
        vendor_context = "\nTarget vendors: both cisco_xr and nokia_sros (generate checks for each)"

    severity_context = ""
    if request.severity:
        severity_context = f"\nSeverity: {request.severity}"

    category_context = ""
    if request.category:
        category_context = f"\nCategory: {request.category}"

    user_prompt = f"""Generate an audit rule for this compliance requirement:

"{request.description}"
{vendor_context}{severity_context}{category_context}

Return ONLY the JSON object, no markdown fences or extra text."""

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    # Parse the LLM response
    try:
        # Strip any markdown fences if present
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Raw response: {llm_response.content}")
        raise ValueError(f"AI generated invalid response. Please try rephrasing your request.")

    # Extract explanation before building the rule
    explanation = parsed.pop("explanation", "Rule generated from natural language description.")

    # Build the GeneratedRule
    checks = []
    for check_data in parsed.get("checks", []):
        checks.append(GeneratedCheck(
            name=check_data.get("name", "Check"),
            filter_xml=check_data.get("filter_xml"),
            xpath=check_data.get("xpath"),
            filter=check_data.get("filter"),
            comparison=check_data.get("comparison", "exists"),
            reference_value=check_data.get("reference_value"),
            error_message=check_data.get("error_message", "Check failed"),
            success_message=check_data.get("success_message", "Check passed"),
        ))

    generated_rule = GeneratedRule(
        name=parsed.get("name", "Generated Rule"),
        description=parsed.get("description", request.description),
        severity=parsed.get("severity", request.severity or "medium"),
        category=parsed.get("category", request.category or "General"),
        vendors=parsed.get("vendors", [request.vendor] if request.vendor else ["cisco_xr", "nokia_sros"]),
        checks=checks,
    )

    # Compute confidence based on response quality
    confidence = _compute_confidence(generated_rule, request)

    # Save draft to database
    from shared.db_models import AIRuleDraftDB
    draft = AIRuleDraftDB(
        source_prompt=request.description,
        generated_rule=generated_rule.model_dump(),
        confidence_score=confidence,
        status="pending",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # Log interaction
    interaction_id = _log_interaction(db, InteractionType.RULE_BUILDER, request.description, llm_response)

    return RuleBuilderResponse(
        draft_id=draft.id,
        generated_rule=generated_rule,
        confidence_score=confidence,
        explanation=explanation,
        original_prompt=request.description,
        interaction_id=interaction_id,
    )


def _compute_confidence(rule: GeneratedRule, request: RuleBuilderRequest) -> float:
    """Compute confidence score for generated rule"""
    score = 0.5  # Base score

    # Has checks
    if rule.checks:
        score += 0.15

    # Has vendor-specific filters
    for check in rule.checks:
        if check.filter_xml or check.xpath or check.filter:
            score += 0.1
            break

    # Has proper error/success messages
    has_messages = all(c.error_message and c.success_message for c in rule.checks)
    if has_messages:
        score += 0.1

    # Has proper name and description
    if rule.name and len(rule.name) > 5 and rule.description and len(rule.description) > 10:
        score += 0.1

    # Cap at 0.95 — always leave room for human review
    return min(score, 0.95)


def _log_interaction(db: Session, interaction_type: InteractionType, prompt: str, response):
    """Log AI interaction for feedback loop. Returns interaction_id or None."""
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=interaction_type.value,
            input_prompt=prompt,
            ai_response={"content": response.content[:2000]},
            model_used=response.model,
            tokens_used=response.tokens_used,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction.id
    except Exception as e:
        logger.warning(f"Failed to log AI interaction: {e}")
        return None
