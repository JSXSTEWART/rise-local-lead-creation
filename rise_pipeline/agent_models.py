"""
Agent Orchestration Data Models
Pydantic models for agent_jobs, agent_decisions, audit_log, rate_limits tables
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal


# ============================================================================
# AgentJob Model
# ============================================================================

class AgentJob(BaseModel):
    """
    Represents an agent-initiated job (discovery, enrichment, qualification, delivery)
    """
    id: UUID = Field(default_factory=uuid4, description="Unique job identifier")
    job_type: Literal['discovery', 'enrichment', 'qualification', 'delivery', 'manual'] = Field(
        ..., description="Type of job being executed"
    )
    status: Literal['queued', 'running', 'completed', 'failed', 'cancelled'] = Field(
        default='queued', description="Current job status"
    )
    initiated_by: Optional[str] = Field(None, description="User ID or agent name")
    initiated_by_type: Optional[Literal['human', 'zapier_agent', 'claude_agent']] = Field(
        None, description="Type of actor that initiated job"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Job-specific input parameters"
    )
    results: Optional[Dict[str, Any]] = Field(
        None, description="Job output data and metrics"
    )
    error_message: Optional[str] = Field(None, description="Error details if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc-123-def-456",
                "job_type": "discovery",
                "status": "completed",
                "initiated_by": "zapier_discovery_coordinator",
                "initiated_by_type": "zapier_agent",
                "parameters": {
                    "metro_id": "austin",
                    "radius": 15,
                    "zip_code": "78701"
                },
                "results": {
                    "leads_created": 47,
                    "places_found": 89,
                    "cost_cents": 235
                },
                "retry_count": 0
            }
        }

    @validator('status')
    def validate_status_transition(cls, v, values):
        """Validate status transitions are logical"""
        # Can add state machine validation here
        return v


# ============================================================================
# AgentDecision Model
# ============================================================================

class AgentDecision(BaseModel):
    """
    Represents an agent decision with reasoning and override capability
    """
    id: UUID = Field(default_factory=uuid4, description="Unique decision identifier")
    lead_id: UUID = Field(..., description="UUID of lead being decided on")
    decision_type: Literal['qualification', 'scoring', 'routing', 'email_variant', 'category_assignment'] = Field(
        ..., description="Type of decision being made"
    )
    agent_name: str = Field(..., description="Name of agent making decision")
    agent_type: Literal['zapier_agent', 'claude_agent', 'council'] = Field(
        ..., description="Type of agent"
    )
    decision: str = Field(..., description="The actual decision made")
    confidence: Optional[Decimal] = Field(
        None, ge=0.0, le=1.0, description="Confidence score 0.00 to 1.00"
    )
    reasoning: Optional[str] = Field(None, description="Human-readable explanation")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional context (council votes, pain signals)"
    )
    overridden_by: Optional[str] = Field(None, description="User who overrode decision")
    override_reason: Optional[str] = Field(None, description="Reason for override")
    overridden_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "def-456-ghi-789",
                "lead_id": "lead-abc-123",
                "decision_type": "qualification",
                "agent_name": "claude_qualifier",
                "agent_type": "claude_agent",
                "decision": "qualified",
                "confidence": 0.87,
                "reasoning": "Active TECL license, 4.5 BBB rating, modern responsive website",
                "metadata": {
                    "pain_score": 72,
                    "icp_score": 85,
                    "council_votes": {
                        "lead_analyst": "approve",
                        "risk_assessor": "approve"
                    }
                }
            }
        }

    @validator('confidence')
    def validate_confidence_range(cls, v):
        """Ensure confidence is between 0 and 1"""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Confidence must be between 0.00 and 1.00")
        return v


# ============================================================================
# AuditLog Model
# ============================================================================

class AuditLog(BaseModel):
    """
    Comprehensive audit trail entry for compliance and debugging
    """
    id: Optional[int] = Field(None, description="Auto-increment ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = Field(..., description="User ID, agent name, or 'system'")
    actor_type: Literal['human', 'zapier_agent', 'claude_agent', 'system'] = Field(
        ..., description="Type of actor"
    )
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="Identifier of resource")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Full context of action"
    )
    ip_address: Optional[str] = Field(None, description="IP address (for humans)")
    user_agent: Optional[str] = Field(None, description="User agent (for humans)")
    session_id: Optional[str] = Field(None, description="Session identifier")
    severity: Literal['debug', 'info', 'warning', 'error', 'critical'] = Field(
        default='info', description="Log severity"
    )
    data_classification: Optional[Literal['public', 'internal', 'confidential', 'restricted']] = Field(
        None, description="Data classification for compliance"
    )
    compliance_tags: Optional[List[str]] = Field(
        None, description="Compliance tags (gdpr, soc2, pii)"
    )
    retention_days: int = Field(default=2555, description="Days to retain (default 7 years)")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-12-22T10:00:00Z",
                "actor": "user@example.com",
                "actor_type": "human",
                "action": "discovery_started",
                "resource_type": "job",
                "resource_id": "abc-123-def-456",
                "metadata": {
                    "metro": "austin",
                    "radius": 15,
                    "estimated_cost_cents": 200
                },
                "severity": "info",
                "compliance_tags": ["audit", "soc2"]
            }
        }


# ============================================================================
# RateLimit Model
# ============================================================================

class RateLimit(BaseModel):
    """
    Track API rate limits for external services and agent quotas
    """
    id: UUID = Field(default_factory=uuid4, description="Unique rate limit record")
    service_name: str = Field(..., description="Service or agent identifier")
    window_start: datetime = Field(..., description="Start of rate limit window")
    request_count: int = Field(default=0, description="Requests in this window")
    quota_limit: int = Field(..., description="Maximum requests allowed")
    reset_at: datetime = Field(..., description="When window resets")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional info (cost per request, plan)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "rate-abc-123",
                "service_name": "clay",
                "window_start": "2025-12-22T10:00:00Z",
                "request_count": 47,
                "quota_limit": 1000,
                "reset_at": "2025-12-22T11:00:00Z",
                "metadata": {
                    "cost_per_request": 0.01,
                    "plan": "professional"
                }
            }
        }

    @validator('request_count')
    def validate_request_count(cls, v, values):
        """Ensure request count doesn't exceed quota"""
        if 'quota_limit' in values and v > values['quota_limit']:
            raise ValueError(f"Request count {v} exceeds quota {values['quota_limit']}")
        return v

    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded"""
        return self.request_count >= self.quota_limit

    def remaining(self) -> int:
        """Get remaining requests in window"""
        return max(0, self.quota_limit - self.request_count)


# ============================================================================
# Helper Functions
# ============================================================================

def create_agent_job(
    job_type: str,
    initiated_by: str,
    initiated_by_type: str,
    parameters: Dict[str, Any]
) -> AgentJob:
    """Helper to create a new agent job"""
    return AgentJob(
        job_type=job_type,
        initiated_by=initiated_by,
        initiated_by_type=initiated_by_type,
        parameters=parameters,
        status='queued'
    )


def create_agent_decision(
    lead_id: UUID,
    decision_type: str,
    agent_name: str,
    agent_type: str,
    decision: str,
    confidence: float,
    reasoning: str,
    metadata: Optional[Dict[str, Any]] = None
) -> AgentDecision:
    """Helper to create a new agent decision"""
    return AgentDecision(
        lead_id=lead_id,
        decision_type=decision_type,
        agent_name=agent_name,
        agent_type=agent_type,
        decision=decision,
        confidence=Decimal(str(confidence)),
        reasoning=reasoning,
        metadata=metadata
    )


def create_audit_log(
    actor: str,
    actor_type: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    severity: str = 'info'
) -> AuditLog:
    """Helper to create audit log entry"""
    return AuditLog(
        actor=actor,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        severity=severity
    )


def create_rate_limit(
    service_name: str,
    quota_limit: int,
    window_minutes: int = 60,
    metadata: Optional[Dict[str, Any]] = None
) -> RateLimit:
    """Helper to create rate limit record"""
    from datetime import timedelta

    now = datetime.utcnow()
    # Align to window boundary
    window_start = now.replace(minute=0, second=0, microsecond=0)
    reset_at = window_start + timedelta(minutes=window_minutes)

    return RateLimit(
        service_name=service_name,
        window_start=window_start,
        request_count=0,
        quota_limit=quota_limit,
        reset_at=reset_at,
        metadata=metadata
    )
