# ============================================================================
# shared/models/device.py - Canonical device model definitions
# All services should import device models from here to avoid duplication
# ============================================================================

from pydantic import BaseModel, Field, field_serializer
from typing import Optional, Dict, Any
from .enums import VendorType, DeviceStatus

class Device(BaseModel):
    """Device representation for API responses.

    SECURITY: Password is excluded from serialization to prevent credential exposure.
    Use DeviceInternal for internal operations that need password access.
    """
    id: Optional[int] = None
    hostname: str
    vendor: VendorType
    ip: Optional[str] = None
    port: int = 830
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, exclude=True)  # SECURITY: Never expose in API
    status: DeviceStatus = DeviceStatus.DISCOVERED
    last_audit: Optional[str] = None
    compliance: int = 0
    metadata: Optional[Dict[str, Any]] = None
    backoff_status: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class DeviceInternal(Device):
    """Internal device model that includes password for internal operations.

    WARNING: Only use this model for internal service-to-service communication.
    Never return this model directly in API responses.
    """
    password: Optional[str] = None  # Override to include password

    class Config:
        use_enum_values = True

class DeviceCreate(BaseModel):
    """Request model for creating a new device"""
    hostname: str
    vendor: VendorType
    ip: Optional[str] = None
    port: int = 830
    username: Optional[str] = None
    password: Optional[str] = None

class DeviceUpdate(BaseModel):
    """Request model for updating an existing device"""
    hostname: Optional[str] = None
    vendor: Optional[VendorType] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    status: Optional[DeviceStatus] = None

class DiscoveryRequest(BaseModel):
    """Request model for device discovery"""
    subnet: str = Field(..., description="Subnet in CIDR notation (e.g., 192.168.1.0/24)")
    username: str = Field(..., description="NETCONF username for discovery")
    password: str = Field(..., description="NETCONF password for discovery")
    port: int = Field(default=830, description="NETCONF port (default 830)")
