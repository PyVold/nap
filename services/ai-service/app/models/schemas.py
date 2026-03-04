"""
Pydantic schemas for AI Service
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class AIProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"


class InteractionType(str, Enum):
    RULE_BUILDER = "rule_builder"
    REMEDIATION = "remediation"
    CHAT_QUERY = "chat_query"
    REPORT = "report"
    ANOMALY = "anomaly"
    IMPACT_ANALYSIS = "impact_analysis"


class DraftStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ReportFormat(str, Enum):
    EXECUTIVE = "executive"
    DETAILED = "detailed"
    FRAMEWORK = "framework"  # SOX, PCI-DSS, NIST, ISO27001


class AnomalySeverity(str, Enum):
    ROUTINE = "routine"
    NOTABLE = "notable"
    SUSPICIOUS = "suspicious"
    CRITICAL = "critical"


# ============================================================================
# LLM Adapter Schemas
# ============================================================================

class LLMRequest(BaseModel):
    """Internal LLM request"""
    system_prompt: str
    user_prompt: str
    temperature: float = 0.3
    max_tokens: int = 4096
    provider: Optional[AIProvider] = None


class LLMResponse(BaseModel):
    """Internal LLM response"""
    content: str
    model: str
    tokens_used: int
    provider: AIProvider


# ============================================================================
# Natural Language Rule Builder
# ============================================================================

class RuleBuilderRequest(BaseModel):
    """Request to generate audit rule from natural language"""
    description: str = Field(..., min_length=10, max_length=2000, description="Natural language description of the compliance check")
    vendor: Optional[str] = Field(None, description="Target vendor (cisco_xr, nokia_sros, or null for both)")
    severity: Optional[str] = Field(None, description="Rule severity (critical, high, medium, low)")
    category: Optional[str] = Field(None, description="Rule category")


class GeneratedCheck(BaseModel):
    name: str
    filter_xml: Optional[str] = None
    xpath: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    comparison: str
    reference_value: Optional[str] = None
    error_message: str
    success_message: str


class GeneratedRule(BaseModel):
    name: str
    description: str
    severity: str
    category: str
    vendors: List[str]
    checks: List[GeneratedCheck]


class RuleBuilderResponse(BaseModel):
    draft_id: Optional[int] = None
    generated_rule: GeneratedRule
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    original_prompt: str


class RuleDraftApproval(BaseModel):
    """Approve or reject a generated rule draft"""
    action: str = Field(..., description="approve, reject, or modify")
    modifications: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None


# ============================================================================
# Natural Language Network Query (AI Chat)
# ============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_history: Optional[List[ChatMessage]] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None
    query_executed: Optional[str] = None
    confidence: float = 0.0


# ============================================================================
# Remediation Advisor
# ============================================================================

class RemediationRequest(BaseModel):
    """Request AI-generated remediation plan"""
    device_id: int
    audit_result_id: Optional[int] = None
    finding_index: Optional[int] = None
    description: Optional[str] = None


class RemediationStep(BaseModel):
    step_number: int
    description: str
    command: Optional[str] = None
    command_type: str = "cli"  # cli, netconf, api
    risk_level: str = "low"  # low, medium, high
    rollback_command: Optional[str] = None
    verification: Optional[str] = None


class RemediationPlan(BaseModel):
    device_id: int
    device_name: str
    finding_summary: str
    steps: List[RemediationStep]
    risk_assessment: str
    estimated_impact: str
    rollback_plan: str
    prerequisites: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class RemediationResponse(BaseModel):
    plan: RemediationPlan
    confidence_score: float
    requires_approval: bool = True
    draft_id: Optional[int] = None


class RemediationApproval(BaseModel):
    action: str = Field(..., description="approve, reject, or modify")
    approved_steps: Optional[List[int]] = None
    feedback: Optional[str] = None


# ============================================================================
# Compliance Report Generation
# ============================================================================

class ReportRequest(BaseModel):
    """Request AI-generated compliance report"""
    report_type: ReportFormat = ReportFormat.EXECUTIVE
    framework: Optional[str] = Field(None, description="Compliance framework: SOX, PCI-DSS, NIST, ISO27001")
    device_group_id: Optional[int] = None
    device_ids: Optional[List[int]] = None
    date_range_days: int = Field(default=30, ge=1, le=365)
    include_trends: bool = True
    include_recommendations: bool = True


class ReportResponse(BaseModel):
    report_id: int
    title: str
    report_type: ReportFormat
    content: str  # Markdown formatted report
    executive_summary: str
    key_findings: List[str]
    recommendations: List[str]
    generated_at: str
    data_sources: Dict[str, int]  # What data was analyzed


# ============================================================================
# Anomaly Detection
# ============================================================================

class AnomalyScore(BaseModel):
    change_event_id: int
    device_id: int
    device_name: str
    score: float = Field(ge=0.0, le=1.0)
    severity: AnomalySeverity
    reasons: List[str]
    change_summary: str
    timestamp: str


class AnomalyDetectionRequest(BaseModel):
    device_id: Optional[int] = None
    hours_back: int = Field(default=24, ge=1, le=720)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)


class AnomalyDetectionResponse(BaseModel):
    anomalies: List[AnomalyScore]
    total_changes_analyzed: int
    anomalies_found: int
    analysis_window_hours: int


# ============================================================================
# Config Impact Analysis
# ============================================================================

class ImpactAnalysisRequest(BaseModel):
    device_id: int
    proposed_config: str = Field(..., min_length=1)
    description: Optional[str] = None


class ImpactPrediction(BaseModel):
    affected_area: str  # BGP, OSPF, MPLS, Interfaces, ACL, etc.
    risk_level: str  # low, medium, high, critical
    description: str
    affected_peers: List[str] = Field(default_factory=list)
    mitigation: Optional[str] = None


class ImpactAnalysisResponse(BaseModel):
    device_id: int
    device_name: str
    overall_risk: str
    predictions: List[ImpactPrediction]
    safe_to_apply: bool
    recommended_window: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# MCP Schemas
# ============================================================================

class MCPConnectionCreate(BaseModel):
    name: str
    server_url: str
    transport: str = "sse"  # sse or stdio
    auth_config: Optional[Dict[str, Any]] = None


class MCPConnectionResponse(BaseModel):
    id: int
    name: str
    server_url: str
    transport: str
    status: str
    capabilities: Optional[Dict[str, Any]] = None
    last_connected: Optional[str] = None


class MCPToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolResponse(BaseModel):
    tool_name: str
    result: Any
    is_error: bool = False


# ============================================================================
# Feedback
# ============================================================================

class AIFeedback(BaseModel):
    interaction_id: int
    rating: str = Field(..., description="positive, negative, or neutral")
    comment: Optional[str] = None
    correction: Optional[Dict[str, Any]] = None
