"""
Licensing Management API - Placeholder
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from api.deps import get_db

router = APIRouter(prefix="/licensing", tags=["licensing"])


@router.get("/")
def list_licenses():
    """List licenses - Placeholder"""
    return []


@router.get("/alerts/")
def list_alerts():
    """List alerts - Placeholder"""
    return []


@router.get("/software/")
def list_software():
    """List software - Placeholder"""
    return []


@router.get("/stats/summary")
def get_stats():
    """Get stats - Placeholder"""
    return {
        "total_licenses": 0,
        "active_licenses": 0,
        "expiring_licenses": 0,
        "expired_licenses": 0,
        "total_cost": 0,
        "pending_alerts": 0
    }
