
# ============================================================================
# models/rule.py
# ============================================================================

from pydantic import BaseModel
from typing import List, Optional
from .enums import VendorType, SeverityLevel, ComparisonType

class RuleCheck(BaseModel):
    name: Optional[str] = "Check"  # Optional with default for backward compatibility
    filter_xml: Optional[str] = None
    xpath: Optional[str] = None
    comparison: Optional[ComparisonType] = None  # Optional for backward compatibility
    reference_value: Optional[str] = None
    reference_config: Optional[str] = None
    error_message: Optional[str] = "Check failed"  # Optional with default for backward compatibility
    success_message: Optional[str] = "Check passed"  # Optional with default for backward compatibility

    # Legacy fields for backward compatibility with old check format
    expected_value: Optional[str] = None
    check_type: Optional[str] = None

class AuditRule(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    severity: SeverityLevel
    category: str
    enabled: bool = True
    vendors: List[VendorType]
    checks: List[RuleCheck]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AuditRuleCreate(BaseModel):
    name: str
    description: str
    severity: SeverityLevel
    category: str
    enabled: bool = True
    vendors: List[VendorType]
    checks: List[RuleCheck]

class AuditRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    category: Optional[str] = None
    enabled: Optional[bool] = None
    vendors: Optional[List[VendorType]] = None
    checks: Optional[List[RuleCheck]] = None