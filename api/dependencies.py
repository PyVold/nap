# ============================================================================
# api/dependencies.py
# ============================================================================

from services.device_service import DeviceService
from services.rule_service import RuleService
from services.audit_service import AuditService
from services.discovery_service import DiscoveryService
from engine.audit_engine import AuditEngine

# Singleton instances
_device_service = None
_rule_service = None
_audit_service = None
_discovery_service = None
_audit_engine = None

def get_device_service() -> DeviceService:
    """Get device service instance"""
    global _device_service
    if _device_service is None:
        _device_service = DeviceService()
    return _device_service

def get_rule_service() -> RuleService:
    """Get rule service instance"""
    global _rule_service
    if _rule_service is None:
        _rule_service = RuleService()
    return _rule_service

def get_audit_engine() -> AuditEngine:
    """Get audit engine instance"""
    global _audit_engine
    if _audit_engine is None:
        _audit_engine = AuditEngine()
    return _audit_engine

def get_audit_service() -> AuditService:
    """Get audit service instance"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService(get_audit_engine())
    return _audit_service

def get_discovery_service() -> DiscoveryService:
    """Get discovery service instance"""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = DiscoveryService()
    return _discovery_service

