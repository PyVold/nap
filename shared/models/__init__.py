# ============================================================================
# shared/models/__init__.py - Central model exports
# Import all shared models from here for consistency across services
# ============================================================================

from .enums import (
    VendorType,
    SeverityLevel,
    AuditStatus,
    ComparisonType,
    DeviceStatus,
)

from .device import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    DiscoveryRequest,
)

__all__ = [
    # Enums
    'VendorType',
    'SeverityLevel',
    'AuditStatus',
    'ComparisonType',
    'DeviceStatus',
    # Device models
    'Device',
    'DeviceCreate',
    'DeviceUpdate',
    'DiscoveryRequest',
]
