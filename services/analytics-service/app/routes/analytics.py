# ============================================================================
# routes/analytics.py - Analytics API
# ============================================================================

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from shared.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ============================================================================
# Compliance Trends
# ============================================================================

@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=365),
    device_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get compliance trends over time
    
    Args:
        days: Number of days to look back (1-365)
        device_id: Optional device ID to filter trends
        
    Returns:
        List of trend snapshots with compliance metrics
    """
    try:
        trends = await AnalyticsService.get_trends(db, device_id, days)
        
        return [{
            "id": t.id,
            "snapshot_date": t.snapshot_date.isoformat() if t.snapshot_date else None,
            "device_id": t.device_id,
            "overall_compliance": t.overall_compliance,
            "compliance_change": t.compliance_change,
            "total_devices": t.total_devices,
            "compliant_devices": t.compliant_devices,
            "failed_devices": t.failed_devices,
            "total_checks": t.total_checks,
            "passed_checks": t.passed_checks,
            "failed_checks": t.failed_checks,
            "warning_checks": t.warning_checks,
            "critical_failures": t.critical_failures,
            "high_failures": t.high_failures,
            "medium_failures": t.medium_failures,
            "low_failures": t.low_failures
        } for t in trends]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch trends: {str(e)}"
        )


@router.post("/trends/snapshot")
async def create_snapshot(
    device_id: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    Create a compliance snapshot for trend tracking
    
    Args:
        device_id: Optional device ID (None for overall snapshot)
        
    Returns:
        Created snapshot
    """
    try:
        snapshot = await AnalyticsService.create_snapshot(db, device_id)
        
        return {
            "id": snapshot.id,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "device_id": snapshot.device_id,
            "overall_compliance": snapshot.overall_compliance,
            "compliance_change": snapshot.compliance_change,
            "total_devices": snapshot.total_devices,
            "message": "Snapshot created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create snapshot: {str(e)}"
        )


# ============================================================================
# Compliance Forecasting
# ============================================================================

@router.get("/forecast")
async def get_forecast(
    device_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get existing compliance forecasts
    
    Args:
        device_id: Optional device ID to filter forecasts
        
    Returns:
        List of forecast predictions
    """
    try:
        forecasts = await AnalyticsService.get_forecasts(db, device_id)
        
        return [{
            "id": f.id,
            "forecast_date": f.forecast_date.isoformat(),
            "device_id": f.device_id,
            "predicted_compliance": f.predicted_compliance,
            "confidence_score": f.confidence_score,
            "predicted_failures": f.predicted_failures,
            "model_version": f.model_version,
            "training_data_points": f.training_data_points,
            "created_at": f.created_at.isoformat() if f.created_at else None
        } for f in forecasts]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch forecasts: {str(e)}"
        )


@router.post("/forecast/generate")
async def generate_forecast(
    device_id: Optional[int] = Body(None),
    days_ahead: int = Body(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Generate new compliance forecasts using historical data
    
    Args:
        device_id: Optional device ID (None for overall forecast)
        days_ahead: Number of days to forecast (1-90)
        
    Returns:
        Generated forecasts
    """
    try:
        forecasts = await AnalyticsService.generate_forecast(db, device_id, days_ahead)
        
        if not forecasts:
            return {
                "message": "Not enough historical data to generate forecast. Need at least 2 trend snapshots.",
                "forecasts": []
            }
        
        return {
            "message": f"Generated {len(forecasts)} forecast(s) for the next {days_ahead} days",
            "forecasts": [{
                "id": f.id,
                "forecast_date": f.forecast_date.isoformat(),
                "predicted_compliance": f.predicted_compliance,
                "confidence_score": f.confidence_score,
                "predicted_failures": f.predicted_failures
            } for f in forecasts]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate forecast: {str(e)}"
        )


# ============================================================================
# Anomaly Detection
# ============================================================================

@router.get("/anomalies")
async def get_anomalies(
    acknowledged: Optional[bool] = Query(None),
    device_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get detected compliance anomalies
    
    Args:
        acknowledged: Filter by acknowledgment status
        device_id: Optional device ID to filter anomalies
        
    Returns:
        List of detected anomalies
    """
    try:
        anomalies = await AnalyticsService.get_anomalies(db, device_id, acknowledged)
        
        return [{
            "id": a.id,
            "device_id": a.device_id,
            "detected_at": a.detected_at.isoformat(),
            "anomaly_type": a.anomaly_type,
            "severity": a.severity.value if a.severity else None,
            "description": a.description,
            "z_score": a.z_score,
            "expected_value": a.expected_value,
            "actual_value": a.actual_value,
            "acknowledged": a.acknowledged,
            "acknowledged_by": a.acknowledged_by,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "resolution_notes": a.resolution_notes
        } for a in anomalies]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch anomalies: {str(e)}"
        )


@router.post("/anomalies/detect")
async def detect_anomalies(
    device_id: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    Run anomaly detection on compliance data
    
    Args:
        device_id: Optional device ID (None for all devices)
        
    Returns:
        Detected anomalies
    """
    try:
        anomalies = await AnalyticsService.detect_anomalies(db, device_id)
        
        return {
            "message": f"Detected {len(anomalies)} anomalie(s)",
            "anomalies": [{
                "id": a.id,
                "device_id": a.device_id,
                "anomaly_type": a.anomaly_type,
                "severity": a.severity.value if a.severity else None,
                "description": a.description,
                "z_score": a.z_score
            } for a in anomalies]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect anomalies: {str(e)}"
        )


@router.post("/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    anomaly_id: int,
    acknowledged_by: str = Body(...),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Acknowledge an anomaly
    
    Args:
        anomaly_id: ID of the anomaly to acknowledge
        acknowledged_by: Username of person acknowledging
        notes: Optional resolution notes
        
    Returns:
        Updated anomaly
    """
    try:
        anomaly = await AnalyticsService.acknowledge_anomaly(
            db, anomaly_id, acknowledged_by, notes
        )
        
        return {
            "message": "Anomaly acknowledged",
            "anomaly": {
                "id": anomaly.id,
                "acknowledged": anomaly.acknowledged,
                "acknowledged_by": anomaly.acknowledged_by,
                "acknowledged_at": anomaly.acknowledged_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to acknowledge anomaly: {str(e)}"
        )


# ============================================================================
# Dashboard Summary
# ============================================================================

@router.get("/dashboard/summary")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get analytics dashboard summary with key metrics
    
    Returns:
        Summary statistics for the analytics dashboard
    """
    try:
        summary = await AnalyticsService.get_dashboard_summary(db)
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard summary: {str(e)}"
        )
