"""
FastAPI Server for Claude Qualification Agent
Exposes qualification agent as HTTP API for Zapier integration
"""

import asyncio
import os
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from qualification_validator import QualificationValidator


# Pydantic models for API
class QualificationRequest(BaseModel):
    """Request model for qualification API"""
    agent: str = Field(..., description="Agent type: 'qualification_validator'")
    mode: str = Field(default="standard", description="Mode: 'standard' or 'council'")
    job_id: str = Field(..., description="UUID of agent_jobs record")
    lead_id: str = Field(..., description="UUID of lead to qualify")
    context: Dict[str, Any] = Field(..., description="Lead context with enrichment data")
    tools_enabled: Optional[list] = Field(default=None, description="List of MCP tools to enable")


class QualificationResponse(BaseModel):
    """Response model for qualification API"""
    job_id: str
    agent_session_id: str
    status: str
    message: str
    estimated_completion: str
    decision: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    mcp_server: str
    supabase: str


# FastAPI app
app = FastAPI(
    title="Claude Qualification Agent API",
    description="Intelligent lead qualification with MCP tool integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global validator instance
validator: Optional[QualificationValidator] = None


async def get_validator() -> QualificationValidator:
    """Dependency to get validator instance"""
    global validator
    if validator is None:
        validator = QualificationValidator()
    return validator


@app.on_event("startup")
async def startup_event():
    """Initialize validator on startup"""
    global validator
    validator = QualificationValidator()
    print("✅ Claude Qualification Agent API started")
    print(f"   MCP Server: {validator.mcp_server_url}")
    print(f"   Supabase: {validator.supabase_url}")
    print(f"   Model: {validator.model}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if validator:
        await validator.close()
    print("👋 Claude Qualification Agent API shutdown")


@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "service": "Claude Qualification Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "invoke": "/api/agents/claude/invoke",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""

    mcp_status = "unknown"
    supabase_status = "unknown"

    # Check MCP server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{os.getenv('MCP_SERVER_URL', 'http://localhost:8000')}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                mcp_status = "healthy"
            else:
                mcp_status = "unhealthy"
    except Exception as e:
        mcp_status = f"error: {str(e)}"

    # Check Supabase
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        if supabase_url:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{supabase_url}/rest/v1/",
                    headers={"apikey": os.getenv("SUPABASE_SERVICE_KEY", "")},
                    timeout=5.0
                )
                if response.status_code in [200, 401]:  # 401 is ok, means auth is working
                    supabase_status = "healthy"
                else:
                    supabase_status = "unhealthy"
        else:
            supabase_status = "not configured"
    except Exception as e:
        supabase_status = f"error: {str(e)}"

    overall_status = "healthy" if mcp_status == "healthy" and "healthy" in supabase_status else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "mcp_server": mcp_status,
        "supabase": supabase_status
    }


@app.post("/api/agents/claude/invoke", response_model=QualificationResponse)
async def invoke_qualification_agent(
    request: QualificationRequest,
    background_tasks: BackgroundTasks,
    validator: QualificationValidator = Depends(get_validator)
):
    """
    Invoke Claude qualification agent.

    This endpoint is called by Zapier to trigger lead qualification.
    It runs the qualification asynchronously and writes results to Supabase.
    """

    if request.agent != "qualification_validator":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {request.agent}. Expected 'qualification_validator'"
        )

    # Generate session ID
    session_id = str(uuid4())

    # Validate context
    required_fields = ["lead_id", "business_name"]
    for field in required_fields:
        if field not in request.context:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field in context: {field}"
            )

    # Start qualification in background
    background_tasks.add_task(
        run_qualification,
        validator,
        request.job_id,
        request.lead_id,
        request.context,
        request.mode
    )

    # Estimate completion time
    completion_seconds = 120 if request.mode == "council" else 60
    estimated_completion = datetime.utcnow().timestamp() + completion_seconds

    return QualificationResponse(
        job_id=request.job_id,
        agent_session_id=session_id,
        status="running",
        message=f"Claude qualification agent started in {request.mode} mode",
        estimated_completion=datetime.fromtimestamp(estimated_completion).isoformat()
    )


@app.post("/api/agents/claude/invoke-sync", response_model=Dict[str, Any])
async def invoke_qualification_agent_sync(
    request: QualificationRequest,
    validator: QualificationValidator = Depends(get_validator)
):
    """
    Invoke Claude qualification agent synchronously (for testing).

    This endpoint waits for qualification to complete before returning.
    Use the async endpoint (/invoke) for production.
    """

    if request.agent != "qualification_validator":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {request.agent}"
        )

    try:
        # Run qualification
        decision = await validator.qualify_lead(
            lead_id=request.lead_id,
            context=request.context,
            mode=request.mode
        )

        # Save decision
        decision_id = await validator.save_decision(
            lead_id=request.lead_id,
            decision=decision,
            agent_name="claude_qualifier"
        )

        # Update lead status
        await validator.update_lead_status(request.lead_id, decision)

        # Update job status
        await update_agent_job(
            validator,
            request.job_id,
            status="completed",
            results=decision
        )

        return {
            "job_id": request.job_id,
            "decision_id": decision_id,
            "decision": decision["decision"],
            "confidence": decision["confidence"],
            "pain_score": decision.get("pain_score"),
            "reasoning": decision["reasoning"],
            "metadata": decision.get("metadata", {})
        }

    except Exception as e:
        # Update job with error
        await update_agent_job(
            validator,
            request.job_id,
            status="failed",
            error_message=str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Qualification failed: {str(e)}"
        )


async def run_qualification(
    validator: QualificationValidator,
    job_id: str,
    lead_id: str,
    context: Dict[str, Any],
    mode: str
):
    """
    Background task to run qualification.

    This runs asynchronously after the API returns to Zapier.
    Results are written to Supabase for Zapier to poll.
    """

    try:
        # Update job to running
        await update_agent_job(
            validator,
            job_id,
            status="running",
            started_at=datetime.utcnow().isoformat()
        )

        # Run qualification
        decision = await validator.qualify_lead(
            lead_id=lead_id,
            context=context,
            mode=mode
        )

        # Save decision
        decision_id = await validator.save_decision(
            lead_id=lead_id,
            decision=decision,
            agent_name="claude_qualifier" if mode == "standard" else "claude_council"
        )

        # Update lead status
        await validator.update_lead_status(lead_id, decision)

        # Update job to completed
        await update_agent_job(
            validator,
            job_id,
            status="completed",
            completed_at=datetime.utcnow().isoformat(),
            results={
                "decision_id": decision_id,
                "decision": decision["decision"],
                "confidence": decision["confidence"],
                "pain_score": decision.get("pain_score"),
                "category": decision.get("category")
            }
        )

        print(f"✅ Qualification completed for lead {lead_id}: {decision['decision']}")

    except Exception as e:
        # Update job with error
        await update_agent_job(
            validator,
            job_id,
            status="failed",
            completed_at=datetime.utcnow().isoformat(),
            error_message=str(e)
        )

        print(f"❌ Qualification failed for lead {lead_id}: {str(e)}")


async def update_agent_job(
    validator: QualificationValidator,
    job_id: str,
    status: str,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    results: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
    """Update agent_jobs table in Supabase"""

    if not validator.supabase_url or not validator.supabase_key:
        return

    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }

    if started_at:
        update_data["started_at"] = started_at
    if completed_at:
        update_data["completed_at"] = completed_at
    if results:
        update_data["results"] = results
    if error_message:
        update_data["error_message"] = error_message

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{validator.supabase_url}/rest/v1/agent_jobs?id=eq.{job_id}",
                headers={
                    "apikey": validator.supabase_key,
                    "Authorization": f"Bearer {validator.supabase_key}",
                    "Content-Type": "application/json"
                },
                json=update_data
            )
            response.raise_for_status()
    except Exception as e:
        print(f"⚠️  Failed to update agent_jobs: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # Run server
    port = int(os.getenv("PORT", 8080))

    print("\n" + "="*70)
    print("  Claude Qualification Agent API")
    print("="*70)
    print(f"  Starting server on http://0.0.0.0:{port}")
    print(f"  Docs available at http://localhost:{port}/docs")
    print("="*70 + "\n")

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
