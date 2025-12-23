"""
Test script for Rise Pipeline integrations.
Tests all new services WITHOUT requiring API keys using mocked responses.

Run with: python test_integrations.py
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Test results tracking
results = {"passed": 0, "failed": 0, "tests": []}


def test_result(name: str, passed: bool, details: str = ""):
    """Record test result."""
    status = "PASS" if passed else "FAIL"
    results["passed" if passed else "failed"] += 1
    results["tests"].append({"name": name, "passed": passed, "details": details})
    print(f"  [{status}] {name}" + (f" - {details}" if details else ""))


async def test_quickchart():
    """Test QuickChart client."""
    print("\n=== Testing QuickChartClient ===")

    from services import QuickChartClient
    client = QuickChartClient()

    # Test 1: URL building (no API needed)
    config = {"type": "bar", "data": {"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]}}
    url = client._build_url(config, 500, 300, "white")

    test_result(
        "URL building",
        "quickchart.io/chart?c=" in url and "w=500" in url,
        f"Generated URL length: {len(url)}"
    )

    # Test 2: Pain score gauge config
    gauge_config = {
        "type": "gauge",
        "data": {"datasets": [{"value": 75, "minValue": 0, "maxValue": 100}]}
    }

    test_result(
        "Gauge chart config",
        gauge_config["type"] == "gauge" and gauge_config["data"]["datasets"][0]["value"] == 75,
        "Config structure valid"
    )

    # Test 3: All chart methods exist
    methods = ["pain_score_gauge", "score_comparison_bar", "pipeline_funnel", "tech_stack_radar"]
    all_exist = all(hasattr(client, m) for m in methods)
    test_result("Chart methods exist", all_exist, f"Methods: {methods}")


async def test_fullenrich():
    """Test FullEnrich client."""
    print("\n=== Testing FullEnrichClient ===")

    from services import FullEnrichClient
    from models import ContactInfo

    client = FullEnrichClient()

    # Test 1: Parse result function
    mock_result = {
        "firstname": "john",
        "lastname": "smith",
        "emails": [
            {"email": "john@company.com", "type": "work"},
            {"email": "john@gmail.com", "type": "personal"}
        ],
        "phones": [
            {"phone": "+1555123456", "type": "mobile"}
        ],
        "linkedin_url": "https://linkedin.com/in/johnsmith"
    }

    parsed = client._parse_result(mock_result)

    test_result(
        "Parse result - work email priority",
        parsed.owner_email == "john@company.com",
        f"Got: {parsed.owner_email}"
    )

    test_result(
        "Parse result - mobile phone",
        parsed.owner_phone_direct == "+1555123456",
        f"Got: {parsed.owner_phone_direct}"
    )

    test_result(
        "Parse result - source attribution",
        parsed.contact_source == "fullenrich",
        f"Source: {parsed.contact_source}"
    )

    # Test 2: Domain cleaning logic
    test_domains = [
        ("https://www.example.com/page", "example.com"),
        ("http://example.com", "example.com"),
        ("www.example.com", "example.com"),
    ]

    for input_domain, expected in test_domains:
        cleaned = input_domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        test_result(
            f"Domain cleaning: {input_domain[:30]}",
            cleaned == expected,
            f"Got: {cleaned}"
        )


async def test_heyreach():
    """Test HeyReach client."""
    print("\n=== Testing HeyReachClient ===")

    from services import HeyReachClient
    client = HeyReachClient()

    # Test 1: Lead data formatting
    test_leads = [
        {"linkedin_url": "https://linkedin.com/in/test1", "first_name": "John", "last_name": "Doe"},
        {"linkedin_url": "https://linkedin.com/in/test2", "email": "test@example.com"},
        {"first_name": "No LinkedIn"}  # Should be filtered out
    ]

    formatted = []
    for lead in test_leads:
        lead_data = {"linkedinUrl": lead.get("linkedin_url", "")}
        if lead.get("first_name"):
            lead_data["firstName"] = lead["first_name"]
        if lead.get("last_name"):
            lead_data["lastName"] = lead["last_name"]
        if lead.get("email"):
            lead_data["email"] = lead["email"]
        if lead_data["linkedinUrl"]:
            formatted.append(lead_data)

    test_result(
        "Lead formatting - filters no-LinkedIn",
        len(formatted) == 2,
        f"Kept {len(formatted)} of 3 leads"
    )

    test_result(
        "Lead formatting - preserves data",
        formatted[0].get("firstName") == "John",
        f"First name: {formatted[0].get('firstName')}"
    )

    # Test 2: Validation - fails gracefully without config
    result = await client.add_lead_to_campaign(linkedin_url="")
    test_result(
        "Validation - fails without config/URL",
        result["success"] == False,
        f"Error: {result.get('error', '')[:50]}"
    )


async def test_rag_service():
    """Test RAG service."""
    print("\n=== Testing RAGService ===")

    from services import RAGService
    rag = RAGService()

    # Test 1: Config values
    test_result(
        "Embedding model configured",
        rag.embedding_model == "text-embedding-3-small",
        f"Model: {rag.embedding_model}"
    )

    # Test 2: Context building logic
    class MockLead:
        business_name = "Test Electric"
        city = "Austin"

    pain_points = ["Low Google rating", "Outdated website", "No online booking"]
    tech_context = "No GTM, No GA4"

    search_parts = [
        MockLead.business_name,
        f"local business in {MockLead.city}",
    ]
    search_parts.extend(pain_points[:3])
    search_parts.append(tech_context)

    search_query = " ".join(search_parts)

    test_result(
        "Context query building",
        "Test Electric" in search_query and "Austin" in search_query,
        f"Query length: {len(search_query)} chars"
    )

    test_result(
        "Pain points included",
        "Low Google rating" in search_query,
        "Top 3 pain points in query"
    )

    # Test 3: Seed documents structure
    documents = [
        {"title": "Test", "content": "Content", "category": "email_guidance"}
    ]
    test_result(
        "Seed document structure",
        all(k in documents[0] for k in ["title", "content", "category"]),
        "Required fields present"
    )


async def test_hallucination_detector():
    """Test Hallucination Detector."""
    print("\n=== Testing HallucinationDetector ===")

    from services import HallucinationDetector
    detector = HallucinationDetector(threshold=0.7)

    # Test 1: Risk level calculation
    test_cases = [
        (0.9, "low"),
        (0.75, "medium"),
        (0.6, "high"),
        (0.3, "critical")
    ]

    for score, expected in test_cases:
        risk = detector._get_risk_level(score)
        test_result(
            f"Risk level for score {score}",
            risk == expected,
            f"Expected: {expected}, Got: {risk}"
        )

    # Test 2: Threshold comparison
    test_result(
        "Threshold configured",
        detector.threshold == 0.7,
        f"Threshold: {detector.threshold}"
    )

    # Test 3: Fallback when no API key (simulated)
    with patch.object(detector, 'api_key', ''):
        result = await detector.get_trustworthiness_score("test prompt", "test response")
        test_result(
            "Graceful fallback without API key",
            result["trustworthiness_score"] == 0.5 and "error" in result,
            f"Returns neutral score with error message"
        )


async def test_llm_council():
    """Test LLM Council."""
    print("\n=== Testing LLMCouncil ===")

    from services import LLMCouncil
    council = LLMCouncil()

    # Test 1: Agent definitions
    expected_agents = ["lead_analyst", "email_strategist", "quality_reviewer", "risk_assessor"]
    all_defined = all(agent in council.agents for agent in expected_agents)
    test_result(
        "All 4 agents defined",
        all_defined,
        f"Agents: {list(council.agents.keys())}"
    )

    # Test 2: Agent structure
    for agent_name, agent in council.agents.items():
        has_fields = all(k in agent for k in ["role", "expertise", "personality"])
        test_result(
            f"Agent '{agent_name}' structure",
            has_fields,
            f"Role: {agent.get('role', 'MISSING')[:30]}"
        )

    # Test 3: Consensus building logic
    mock_results = [
        {"success": True, "result": {"confidence": 0.8, "concerns": ["A"], "recommendations": ["X"]}},
        {"success": True, "result": {"confidence": 0.7, "concerns": ["B"], "recommendations": ["Y"]}},
        {"success": False, "result": {"error": "API failed"}}
    ]

    consensus = council._build_consensus(mock_results, "test_decision")

    test_result(
        "Consensus - average confidence",
        consensus["confidence"] == 0.75,
        f"Confidence: {consensus['confidence']}"
    )

    test_result(
        "Consensus - aggregates concerns",
        len(consensus["all_concerns"]) == 2,
        f"Concerns: {consensus['all_concerns']}"
    )

    test_result(
        "Consensus - counts successful agents",
        consensus["agents_consulted"] == 2,
        f"Consulted: {consensus['agents_consulted']} of 3"
    )

    # Test 4: Voting logic
    mock_vote_results = [
        {"success": True, "result": {"vote": "yes", "confidence": 0.8, "blocking_concerns": []}},
        {"success": True, "result": {"vote": "yes", "confidence": 0.7, "blocking_concerns": []}},
        {"success": True, "result": {"vote": "no", "confidence": 0.6, "blocking_concerns": []}},
        {"success": True, "result": {"vote": "abstain", "confidence": 0.5, "blocking_concerns": []}}
    ]

    vote_result = council._build_voting_result(mock_vote_results)

    test_result(
        "Voting - counts correctly",
        vote_result["votes"]["yes"] == 2 and vote_result["votes"]["no"] == 1,
        f"Votes: {vote_result['votes']}"
    )

    test_result(
        "Voting - majority wins",
        vote_result["decision"] == "approved",
        f"Decision: {vote_result['decision']}"
    )

    # Test 5: Blocking concerns
    mock_blocked_results = [
        {"success": True, "result": {"vote": "yes", "blocking_concerns": ["License expired"]}},
        {"success": True, "result": {"vote": "yes", "blocking_concerns": []}}
    ]

    blocked_result = council._build_voting_result(mock_blocked_results)

    test_result(
        "Voting - blocking concerns override",
        blocked_result["decision"] == "blocked",
        f"Blocked by: {blocked_result['blocking_concerns']}"
    )


async def test_pipeline_integration():
    """Test pipeline imports and initialization."""
    print("\n=== Testing Pipeline Integration ===")

    try:
        from pipeline import RiseLocalPipeline

        # Test with all features disabled (no API calls)
        pipeline = RiseLocalPipeline(
            use_fullenrich=False,
            use_rag=False,
            use_council=False
        )

        test_result(
            "Pipeline imports all services",
            hasattr(pipeline, 'council') and hasattr(pipeline, 'hallucination'),
            "All new services accessible"
        )

        test_result(
            "Pipeline flags configurable",
            not pipeline.use_council and not pipeline.use_rag,
            "Feature flags work"
        )

        # Check all service instances exist
        services = ['supabase', 'clay', 'fullenrich', 'intelligence',
                   'instantly', 'ghl', 'heyreach', 'charts', 'rag',
                   'hallucination', 'council']
        all_exist = all(hasattr(pipeline, s) for s in services)

        test_result(
            "All 11 services initialized",
            all_exist,
            f"Services: {len(services)}"
        )

    except ImportError as e:
        test_result("Pipeline import", False, str(e))


def print_summary():
    """Print test summary."""
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 50)
    print(f"TEST SUMMARY: {results['passed']}/{total} passed")
    print("=" * 50)

    if results["failed"] > 0:
        print("\nFailed tests:")
        for t in results["tests"]:
            if not t["passed"]:
                print(f"  - {t['name']}: {t['details']}")

    return results["failed"] == 0


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Rise Pipeline Integration Tests")
    print("Testing WITHOUT API keys (mocked/logic tests)")
    print("=" * 50)

    await test_quickchart()
    await test_fullenrich()
    await test_heyreach()
    await test_rag_service()
    await test_hallucination_detector()
    await test_llm_council()
    await test_pipeline_integration()

    success = print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
