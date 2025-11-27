# ============================================================================
# models/audit.py
# ============================================================================

from pydantic import BaseModel
from typing import List, Optional
from .enums import AuditStatus, SeverityLevel

class AuditFinding(BaseModel):
    rule: str
    status: AuditStatus
    message: str
    details: Optional[str] = None
    severity: SeverityLevel
    check_name: Optional[str] = None
    actual_config: Optional[str] = None  # Actual configuration from device
    expected_config: Optional[str] = None  # Reference/expected configuration
    comparison_details: Optional[str] = None  # Detailed comparison/diff
    xpath: Optional[str] = None  # XPath used for Nokia SROS remediation
    filter_xml: Optional[str] = None  # Filter XML used for Cisco XR remediation

class AuditResult(BaseModel):
    device_id: int
    device_name: str
    device_ip: Optional[str] = None  # Device IP address
    timestamp: str
    findings: List[AuditFinding]
    compliance: int

class AuditRequest(BaseModel):
    device_ids: Optional[List[int]] = None
    rule_ids: Optional[List[int]] = None