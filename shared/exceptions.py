# ============================================================================
# utils/exceptions.py
# ============================================================================

class NetworkAuditException(Exception):
    """Base exception for network audit platform"""
    pass

class DeviceConnectionError(NetworkAuditException):
    """Raised when device connection fails"""
    pass

class RuleExecutionError(NetworkAuditException):
    """Raised when rule execution fails"""
    pass

class RuleNotFoundError(NetworkAuditException):
    """Raised when rule is not found"""
    pass

class DeviceNotFoundError(NetworkAuditException):
    """Raised when device is not found"""
    pass

class InvalidConfigurationError(NetworkAuditException):
    """Raised when configuration is invalid"""
    pass
