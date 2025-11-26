# ============================================================================
# models/enums.py
# ============================================================================

from enum import Enum

class VendorType(str, Enum):
    CISCO_XR = "cisco_xr"
    NOKIA_SROS = "nokia_sros"

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AuditStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"

class ComparisonType(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    COUNT = "count"

class DeviceStatus(str, Enum):
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    ERROR = "error"
