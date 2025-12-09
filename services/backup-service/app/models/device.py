# ============================================================================
# Re-export device models from shared module to avoid duplication
# All device model definitions are maintained in shared/models/device.py
# ============================================================================

from shared.models.device import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    DiscoveryRequest,
)

__all__ = [
    'Device',
    'DeviceCreate',
    'DeviceUpdate',
    'DiscoveryRequest',
]
