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
    DeviceInternal,
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
    'DeviceInternal',  # WARNING: Only for internal use, never return in API
    'DeviceCreate',
    'DeviceUpdate',
    'DiscoveryRequest',
]
