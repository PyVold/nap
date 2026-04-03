"""
Compliance Posture Prediction Service
Forecasts future compliance scores based on historical trends and current drift patterns.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.schemas import LLMRequest, InteractionType
from services.llm_adapter import call_llm
from services.llm_response_parser import safe_extract_json
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:3006")


async def predict_compliance(
    db: Session,
    device_id: Optional[int] = None,
    device_group_id: Optional[int] = None,
    forecast_days: int = 30,
) -> dict:
    """Predict future compliance posture based on historical data"""

    # Gather historical compliance data
    data = await _gather_compliance_history(device_id, device_group_id)

    if not data.get("history"):
        return {
            "status": "insufficient_data",
            "message": "Not enough historical data for predictions. Run at least 3 audits first.",
            "forecast_days": forecast_days,
        }

    # Statistical trend analysis (without LLM)
    trend_analysis = _analyze_trends(data["history"], forecast_days)

    # Get drift rate data
    drift_data = await _get_drift_rate(device_id)

    # Use LLM for narrative and deeper insights
    prompt = f"""Analyze this network compliance data and predict the compliance posture:

CURRENT STATE:
{json.dumps(data.get('current', {}), indent=2, default=str)[:2000]}

HISTORICAL COMPLIANCE SCORES (newest first):
{json.dumps(data.get('history', [])[:30], indent=2, default=str)[:3000]}

STATISTICAL TREND:
{json.dumps(trend_analysis, indent=2, default=str)}

CONFIG DRIFT RATE:
{json.dumps(drift_data, indent=2, default=str)[:1000]}

FORECAST PERIOD: {forecast_days} days

Provide:
1. Predicted compliance score in {forecast_days} days
2. Confidence interval (optimistic/pessimistic)
3. Key risk factors driving the prediction
4. Devices most likely to drift out of compliance
5. Recommended preventive actions

Return JSON:
{{
  "predicted_score": 85.5,
  "confidence_interval": {{"optimistic": 92.0, "pessimistic": 78.0}},
  "trend_direction": "declining|stable|improving",
  "days_until_threshold": 14,
  "threshold": 80.0,
  "risk_factors": ["List of key risk factors"],
  "at_risk_devices": ["hostname1", "hostname2"],
  "preventive_actions": ["Action 1", "Action 2"],
  "narrative": "A 2-3 sentence executive summary of the prediction"
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a compliance analytics expert. Analyze network compliance trends and provide data-driven predictions. Be specific about numbers and timeframes.",
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    prediction = safe_extract_json(llm_response.content, fallback={
        "narrative": llm_response.content[:500],
        "predicted_score": trend_analysis.get("projected_score"),
        "trend_direction": trend_analysis.get("trend_direction", "stable"),
    })

    # Merge statistical and AI predictions
    result = {
        "current_score": data.get("current", {}).get("average_compliance"),
        "predicted_score": prediction.get("predicted_score"),
        "confidence_interval": prediction.get("confidence_interval", {}),
        "trend_direction": prediction.get("trend_direction", "stable"),
        "forecast_days": forecast_days,
        "days_until_threshold": prediction.get("days_until_threshold"),
        "threshold": prediction.get("threshold", 80.0),
        "risk_factors": prediction.get("risk_factors", []),
        "at_risk_devices": prediction.get("at_risk_devices", []),
        "preventive_actions": prediction.get("preventive_actions", []),
        "narrative": prediction.get("narrative", ""),
        "statistical_trend": trend_analysis,
        "data_points": len(data.get("history", [])),
    }

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type="compliance_prediction",
            input_prompt=f"Compliance prediction: device={device_id}, group={device_group_id}, days={forecast_days}",
            ai_response={"predicted_score": result["predicted_score"], "trend": result["trend_direction"]},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return result


async def what_if_analysis(
    db: Session,
    scenario: str,
    device_ids: Optional[List[int]] = None,
) -> dict:
    """Run what-if compliance scenario analysis"""

    # Get current state
    current_data = await _gather_compliance_history()

    prompt = f"""Run a what-if analysis on this compliance scenario:

CURRENT COMPLIANCE STATE:
{json.dumps(current_data.get('current', {}), indent=2, default=str)[:3000]}

SCENARIO: {scenario}

TARGET DEVICES: {json.dumps(device_ids) if device_ids else 'All devices'}

Analyze:
1. How would this scenario affect compliance scores?
2. Which devices would be most impacted?
3. What new findings would appear?
4. Overall risk assessment

Return JSON:
{{
  "scenario": "{scenario}",
  "current_score": 85.0,
  "projected_score": 78.0,
  "score_delta": -7.0,
  "affected_devices_count": 12,
  "new_findings": ["Expected new findings"],
  "risk_assessment": "Description of risks",
  "recommendation": "What to do about it"
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network compliance analyst. Evaluate what-if scenarios and predict their impact on compliance posture.",
        user_prompt=prompt,
        temperature=0.3,
        max_tokens=2048,
    )

    llm_response = await call_llm(llm_request)

    return safe_extract_json(llm_response.content, fallback={
        "scenario": scenario, "analysis": llm_response.content,
    })


def _analyze_trends(history: list, forecast_days: int) -> dict:
    """Simple statistical trend analysis"""
    if len(history) < 2:
        return {"trend_direction": "insufficient_data"}

    scores = []
    for entry in history:
        score = entry.get("compliance") or entry.get("average_compliance")
        if score is not None:
            scores.append(float(score))

    if not scores:
        return {"trend_direction": "no_data"}

    # Simple linear regression
    n = len(scores)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(scores) / n

    numerator = sum((x[i] - x_mean) * (scores[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        slope = 0
    else:
        slope = numerator / denominator

    # Project forward
    projected = scores[-1] + slope * forecast_days
    projected = max(0, min(100, projected))

    if slope > 0.5:
        direction = "improving"
    elif slope < -0.5:
        direction = "declining"
    else:
        direction = "stable"

    # Volatility (standard deviation)
    variance = sum((s - y_mean) ** 2 for s in scores) / n
    volatility = variance ** 0.5

    return {
        "trend_direction": direction,
        "slope_per_period": round(slope, 3),
        "projected_score": round(projected, 1),
        "current_score": round(scores[-1], 1),
        "average_score": round(y_mean, 1),
        "volatility": round(volatility, 2),
        "data_points": n,
    }


async def _gather_compliance_history(
    device_id: Optional[int] = None,
    device_group_id: Optional[int] = None,
) -> dict:
    """Gather compliance history data"""
    data = {"current": {}, "history": []}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Current compliance
        try:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
            if resp.status_code == 200:
                data["current"] = resp.json()
        except Exception as e:
            logger.warning(f"Failed to get compliance: {e}")

        # Historical audit results
        try:
            params = {"latest_only": "false"}
            if device_id:
                resp = await client.get(f"{RULE_SERVICE_URL}/audit/results/{device_id}")
            else:
                resp = await client.get(f"{RULE_SERVICE_URL}/audit/results", params=params)

            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list):
                    data["history"] = [
                        {
                            "timestamp": r.get("timestamp"),
                            "compliance": r.get("compliance"),
                            "device_name": r.get("device_name"),
                            "findings_count": len(r.get("findings", [])),
                        }
                        for r in results[:100]
                    ]
        except Exception as e:
            logger.warning(f"Failed to get audit history: {e}")

        # Trend data from analytics
        try:
            resp = await client.get(f"{ANALYTICS_SERVICE_URL}/analytics/trends")
            if resp.status_code == 200:
                data["trends"] = resp.json()
        except Exception:
            pass

    return data


async def _get_drift_rate(device_id: Optional[int] = None) -> dict:
    """Calculate configuration drift rate"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKUP_SERVICE_URL}/drift-detection/summary")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {}
