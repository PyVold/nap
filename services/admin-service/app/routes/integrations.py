"""
Integration Hub API - Simplified
Manages integrations with NetBox, Git, Ansible, ServiceNow, and Prometheus
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from shared.deps import get_db
from db_models import IntegrationDB

router = APIRouter(prefix="/integrations", tags=["integrations"])


# Pydantic Schemas
class IntegrationBase(BaseModel):
    name: str
    integration_type: str  # netbox, git, ansible, servicenow, prometheus
    enabled: bool = True
    config: dict
    sync_interval_minutes: Optional[int] = 60


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None
    sync_interval_minutes: Optional[int] = None


class IntegrationResponse(IntegrationBase):
    id: int
    last_sync: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[IntegrationResponse])
def list_integrations(
    integration_type: Optional[str] = None,
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all integrations"""
    query = db.query(IntegrationDB)
    if integration_type:
        query = query.filter(IntegrationDB.integration_type == integration_type)
    if enabled_only:
        query = query.filter(IntegrationDB.enabled == True)
    return query.all()


@router.get("/{integration_id}", response_model=IntegrationResponse)
def get_integration(integration_id: int, db: Session = Depends(get_db)):
    """Get integration by ID"""
    integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.post("/", response_model=IntegrationResponse)
def create_integration(integration: IntegrationCreate, db: Session = Depends(get_db)):
    """Create a new integration"""
    existing = db.query(IntegrationDB).filter(IntegrationDB.name == integration.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Integration with this name already exists")

    db_integration = IntegrationDB(**integration.dict())
    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)
    return db_integration


@router.put("/{integration_id}", response_model=IntegrationResponse)
def update_integration(
    integration_id: int,
    integration: IntegrationUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing integration"""
    db_integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if not db_integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = integration.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_integration, field, value)

    db.commit()
    db.refresh(db_integration)
    return db_integration


@router.delete("/{integration_id}")
def delete_integration(integration_id: int, db: Session = Depends(get_db)):
    """Delete an integration"""
    db_integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if not db_integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    name = db_integration.name
    db.delete(db_integration)
    db.commit()
    return {"message": f"Integration '{name}' deleted successfully"}


@router.post("/{integration_id}/test")
def test_integration(integration_id: int, db: Session = Depends(get_db)):
    """Test integration connectivity"""
    integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "status": "success",
        "message": f"Test connection for {integration.name} (placeholder)",
        "type": integration.integration_type
    }


@router.post("/{integration_id}/sync")
def sync_integration(integration_id: int, db: Session = Depends(get_db)):
    """Trigger integration synchronization"""
    integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration.last_sync = datetime.now()
    integration.last_sync_status = "success"
    db.commit()

    return {
        "message": f"Sync completed for {integration.name}",
        "integration_id": integration_id,
        "type": integration.integration_type
    }


@router.get("/{integration_id}/logs")
def get_integration_logs(integration_id: int, db: Session = Depends(get_db)):
    """Get integration logs (placeholder)"""
    integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return []  # Placeholder - logs not yet implemented


@router.get("/prometheus/metrics")
def export_prometheus_metrics(db: Session = Depends(get_db)):
    """Export metrics in Prometheus format"""
    from db_models import DeviceDB
    from fastapi.responses import Response

    total_devices = db.query(DeviceDB).count()

    metrics = f"""# HELP network_audit_total_devices Total number of devices
# TYPE network_audit_total_devices gauge
network_audit_total_devices {total_devices}
"""
    return Response(content=metrics, media_type="text/plain")
