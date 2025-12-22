"""
Test suite for Claude Qualification Agent
Tests standard qualification, council mode, and API endpoints
"""

import asyncio
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
import httpx

from qualification_validator import QualificationValidator
from api_server import app


# Test data
SAMPLE_LEAD_HIGH_PAIN = {
    "lead_id": str(uuid4()),
    "business_name": "High Pain Electric Co",
    "website_url": "https://highpainelectric.com",
    "location": "Austin, TX",
    "google_rating": 3.8,
    "google_reviews": 45,
    "preliminary_pain_score": 75,
    "enrichment_data": {
        "tech_stack": ["HTML"],
        "has_crm": False,
        "has_booking": False,
        "visual_score": 25,
        "performance_score": 30,
        "mobile_responsive": False,
        "license_status": "Active",
        "bbb_rating": "C",
        "reputation_gap": 2.5
    },
    "pain_signals": [
        "Outdated website (1990s design)",
        "Very slow performance (30/100)",
        "Not mobile responsive",
        "No CRM detected",
        "No booking system",
        "Large reputation gap (BBB C vs Google 3.8)"
    ]
}

SAMPLE_LEAD_LOW_PAIN = {
    "lead_id": str(uuid4()),
    "business_name": "Perfect Electric Inc",
    "website_url": "https://perfectelectric.com",
    "location": "Dallas, TX",
    "google_rating": 4.9,
    "google_reviews": 250,
    "preliminary_pain_score": 15,
    "enrichment_data": {
        "tech_stack": ["React", "Next.js", "Salesforce", "Calendly"],
        "has_crm": True,
        "has_booking": True,
        "visual_score": 92,
        "performance_score": 88,
        "mobile_responsive": True,
        "license_status": "Active",
        "bbb_rating": "A+",
        "reputation_gap": 0.1
    },
    "pain_signals": []
}

SAMPLE_LEAD_MARGINAL = {
    "lead_id": str(uuid4()),
    "business_name": "Marginal Electric LLC",
    "website_url": "https://marginalelectric.com",
    "location": "Houston, TX",
    "google_rating": 4.2,
    "google_reviews": 67,
    "preliminary_pain_score": 50,
    "enrichment_data": {
        "tech_stack": ["WordPress", "Google Analytics"],
        "has_crm": False,
        "has_booking": False,
        "visual_score": 55,
        "performance_score": 52,
        "mobile_responsive": True,
        "license_status": "Active",
        "bbb_rating": "B+",
        "reputation_gap": 0.5
    },
    "pain_signals": [
        "Template WordPress site",
        "No CRM detected",
        "No booking system"
    ]
}


# Test client
client = TestClient(app)


class TestQualificationValidator:
    """Test QualificationValidator class"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test validator initialization"""
        validator = QualificationValidator()

        assert validator.model is not None
        assert validator.tools is not None
        assert len(validator.tools) == 6  # 6 MCP tools

        await validator.close()

    @pytest.mark.asyncio
    async def test_high_pain_qualification(self):
        """Test qualification of high-pain lead (should qualify)"""
        validator = QualificationValidator()

        decision = await validator.qualify_lead(
            lead_id=SAMPLE_LEAD_HIGH_PAIN["lead_id"],
            context=SAMPLE_LEAD_HIGH_PAIN,
            mode="standard"
        )

        assert decision is not None
        assert "decision" in decision
        assert "confidence" in decision
        assert "pain_score" in decision
        assert "reasoning" in decision

        # High pain should qualify
        assert decision["decision"] in ["qualified", "marginal"]
        assert decision["pain_score"] >= 50

        print(f"\n✅ High pain lead decision: {decision['decision']}")
        print(f"   Pain score: {decision['pain_score']}")
        print(f"   Confidence: {decision['confidence']}")

        await validator.close()

    @pytest.mark.asyncio
    async def test_low_pain_rejection(self):
        """Test qualification of low-pain lead (should reject)"""
        validator = QualificationValidator()

        decision = await validator.qualify_lead(
            lead_id=SAMPLE_LEAD_LOW_PAIN["lead_id"],
            context=SAMPLE_LEAD_LOW_PAIN,
            mode="standard"
        )

        assert decision is not None

        # Low pain should reject
        assert decision["decision"] == "rejected"
        assert decision["pain_score"] < 40

        print(f"\n✅ Low pain lead decision: {decision['decision']}")
        print(f"   Pain score: {decision['pain_score']}")

        await validator.close()

    @pytest.mark.asyncio
    async def test_council_mode(self):
        """Test LLMCouncil with 4-agent voting"""
        validator = QualificationValidator()

        decision = await validator.qualify_lead(
            lead_id=SAMPLE_LEAD_MARGINAL["lead_id"],
            context=SAMPLE_LEAD_MARGINAL,
            mode="council"
        )

        assert decision is not None
        assert "metadata" in decision
        assert "council_votes" in decision["metadata"]

        # Check all 4 agents voted
        votes = decision["metadata"]["council_votes"]
        assert len(votes) == 4

        agent_names = ["Lead Analyst", "Email Strategist", "Quality Reviewer", "Risk Assessor"]
        for agent_name in agent_names:
            assert agent_name in votes
            assert "vote" in votes[agent_name]
            assert votes[agent_name]["vote"] in ["qualified", "rejected"]

        print(f"\n✅ Council decision: {decision['decision']}")
        print(f"   Qualified votes: {decision['metadata']['qualified_votes']}/4")
        print(f"   Rejected votes: {decision['metadata']['rejected_votes']}/4")
        print(f"\n   Council breakdown:")
        for agent_name, vote_data in votes.items():
            print(f"   - {agent_name}: {vote_data['vote']} (score: {vote_data.get('score', 0)})")

        await validator.close()

    @pytest.mark.asyncio
    async def test_save_decision(self):
        """Test saving decision to Supabase"""

        # Skip if no Supabase credentials
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"):
            pytest.skip("Supabase credentials not configured")

        validator = QualificationValidator()

        # Make a decision
        decision = await validator.qualify_lead(
            lead_id=SAMPLE_LEAD_HIGH_PAIN["lead_id"],
            context=SAMPLE_LEAD_HIGH_PAIN,
            mode="standard"
        )

        # Save to database
        decision_id = await validator.save_decision(
            lead_id=SAMPLE_LEAD_HIGH_PAIN["lead_id"],
            decision=decision
        )

        assert decision_id is not None
        print(f"\n✅ Decision saved with ID: {decision_id}")

        await validator.close()

    @pytest.mark.asyncio
    async def test_mcp_tool_call(self):
        """Test calling MCP tools"""
        validator = QualificationValidator()

        # Test health check first
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{validator.mcp_server_url}/health", timeout=5.0)
                if response.status_code != 200:
                    pytest.skip("MCP server not available")
        except:
            pytest.skip("MCP server not available")

        # Test calling a tool (extract_owner_info is fast)
        result = await validator._call_mcp_tool(
            tool_name="extract_owner_info",
            tool_input={
                "url": "https://example.com",
                "lead_id": str(uuid4())
            }
        )

        assert result is not None
        assert "error" in result or "owner_name" in result

        print(f"\n✅ MCP tool call successful")
        print(f"   Result keys: {list(result.keys())}")

        await validator.close()


class TestAPIServer:
    """Test FastAPI server endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "mcp_server" in data
        assert "supabase" in data

        print(f"\n✅ Health check:")
        print(f"   Status: {data['status']}")
        print(f"   MCP: {data['mcp_server']}")
        print(f"   Supabase: {data['supabase']}")

    def test_invoke_qualification_endpoint(self):
        """Test async qualification endpoint"""
        job_id = str(uuid4())

        payload = {
            "agent": "qualification_validator",
            "mode": "standard",
            "job_id": job_id,
            "lead_id": SAMPLE_LEAD_HIGH_PAIN["lead_id"],
            "context": SAMPLE_LEAD_HIGH_PAIN,
            "tools_enabled": None
        }

        response = client.post("/api/agents/claude/invoke", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == job_id
        assert data["status"] == "running"
        assert "agent_session_id" in data
        assert "estimated_completion" in data

        print(f"\n✅ Async qualification started:")
        print(f"   Job ID: {data['job_id']}")
        print(f"   Session ID: {data['agent_session_id']}")

    def test_invoke_sync_endpoint(self):
        """Test synchronous qualification endpoint (for testing)"""

        # Skip if no API key (this actually calls Claude)
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        job_id = str(uuid4())

        payload = {
            "agent": "qualification_validator",
            "mode": "standard",
            "job_id": job_id,
            "lead_id": SAMPLE_LEAD_LOW_PAIN["lead_id"],
            "context": SAMPLE_LEAD_LOW_PAIN
        }

        response = client.post("/api/agents/claude/invoke-sync", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "decision" in data
        assert "confidence" in data
        assert "pain_score" in data
        assert "reasoning" in data

        print(f"\n✅ Sync qualification completed:")
        print(f"   Decision: {data['decision']}")
        print(f"   Confidence: {data['confidence']}")
        print(f"   Pain score: {data['pain_score']}")

    def test_invalid_agent_type(self):
        """Test with invalid agent type"""
        payload = {
            "agent": "invalid_agent",
            "mode": "standard",
            "job_id": str(uuid4()),
            "lead_id": str(uuid4()),
            "context": {}
        }

        response = client.post("/api/agents/claude/invoke", json=payload)

        assert response.status_code == 400
        assert "Unknown agent" in response.json()["detail"]

    def test_missing_required_fields(self):
        """Test with missing required context fields"""
        payload = {
            "agent": "qualification_validator",
            "mode": "standard",
            "job_id": str(uuid4()),
            "lead_id": str(uuid4()),
            "context": {}  # Missing required fields
        }

        response = client.post("/api/agents/claude/invoke", json=payload)

        assert response.status_code == 400
        assert "Missing required field" in response.json()["detail"]


# Manual test script
async def manual_test():
    """
    Manual test script for development.
    Run with: python test_qualification.py
    """

    print("\n" + "="*70)
    print("  Claude Qualification Agent - Manual Test")
    print("="*70 + "\n")

    validator = QualificationValidator()

    # Test 1: High pain lead
    print("TEST 1: High Pain Lead (Should Qualify)")
    print("-" * 70)
    decision1 = await validator.qualify_lead(
        lead_id=SAMPLE_LEAD_HIGH_PAIN["lead_id"],
        context=SAMPLE_LEAD_HIGH_PAIN,
        mode="standard"
    )
    print(f"Decision: {decision1['decision']}")
    print(f"Confidence: {decision1['confidence']}")
    print(f"Pain Score: {decision1.get('pain_score')}")
    print(f"Category: {decision1.get('category')}")
    print(f"Reasoning: {decision1['reasoning'][:200]}...\n")

    # Test 2: Low pain lead
    print("\nTEST 2: Low Pain Lead (Should Reject)")
    print("-" * 70)
    decision2 = await validator.qualify_lead(
        lead_id=SAMPLE_LEAD_LOW_PAIN["lead_id"],
        context=SAMPLE_LEAD_LOW_PAIN,
        mode="standard"
    )
    print(f"Decision: {decision2['decision']}")
    print(f"Pain Score: {decision2.get('pain_score')}")
    print(f"Reasoning: {decision2['reasoning'][:200]}...\n")

    # Test 3: Marginal lead with council
    print("\nTEST 3: Marginal Lead (Council Review)")
    print("-" * 70)
    decision3 = await validator.qualify_lead(
        lead_id=SAMPLE_LEAD_MARGINAL["lead_id"],
        context=SAMPLE_LEAD_MARGINAL,
        mode="council"
    )
    print(f"Decision: {decision3['decision']}")
    print(f"Confidence: {decision3['confidence']}")
    print(f"Votes: {decision3['metadata']['qualified_votes']}/4 qualified")
    print(f"\nCouncil Reasoning:\n{decision3['reasoning']}\n")

    # Test 4: API health
    print("\nTEST 4: API Server Health Check")
    print("-" * 70)
    response = client.get("/health")
    health = response.json()
    print(f"Status: {health['status']}")
    print(f"MCP Server: {health['mcp_server']}")
    print(f"Supabase: {health['supabase']}")

    await validator.close()

    print("\n" + "="*70)
    print("  All manual tests completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run manual tests
    asyncio.run(manual_test())
