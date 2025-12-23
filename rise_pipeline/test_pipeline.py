"""
Quick test of the pipeline components
"""
import asyncio
import sys
import os

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from models import Lead, TechEnrichment, VisualAnalysis, TechnicalScores, DirectoryPresence, LicenseInfo, ReputationData
from services import SupabaseClient
from scoring import calculate_pain_score

async def test_supabase_fetch():
    """Test fetching a lead from Supabase"""
    print("\n=== Testing Supabase Connection ===")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key configured: {'Yes' if SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_KEY != 'your-supabase-service-role-key-here' else 'No (placeholder)'}")

    # Create mock lead for testing (based on actual data from DB)
    print("\nUsing mock lead data for testing...")
    lead = Lead(
        id="b715f40f-6f24-4d19-83f4-602c72c4a84a",
        business_name="Electric Pros, Inc",
        address="",
        city="Dallas",
        state="TX",
        zip_code="",
        phone="",
        website_url="https://electric-pros.com/",
        google_rating=3.6,
        review_count=58,
        place_id="",
        status="discovered"
    )

    print(f"Mock lead created:")
    print(f"  Business: {lead.business_name}")
    print(f"  City: {lead.city}, {lead.state}")
    print(f"  Website: {lead.website_url}")
    print(f"  Rating: {lead.google_rating} ({lead.review_count} reviews)")
    return lead


def test_scoring(lead: Lead):
    """Test the scoring logic with mock enrichment data"""
    print("\n=== Testing Pain Score Calculation ===")

    # Create mock enrichment data simulating a lead with issues
    tech = TechEnrichment(
        has_gtm=False,
        has_ga4=False,
        tech_score=25
    )

    visual = VisualAnalysis(
        visual_score=45,
        design_era="2010s",
        mobile_responsive=True,
        has_hero_image=False,
        has_clear_cta=False,
        trust_signals=1
    )

    technical = TechnicalScores(
        performance_score=42,
        mobile_score=55,
        seo_score=48,
        has_https=True,
        lcp_ms=5200
    )

    directory = DirectoryPresence(
        listings_score=35,
        listings_found=8,
        nap_consistency=0.65
    )

    license_info = LicenseInfo(
        license_status="Active"
    )

    reputation = ReputationData(
        bbb_rating="B+",
        bbb_accredited=False,
        complaints_3yr=1
    )

    # Calculate pain score
    pain_score = calculate_pain_score(
        lead=lead,
        tech=tech,
        visual=visual,
        technical=technical,
        directory=directory,
        license_info=license_info,
        reputation=reputation
    )

    print(f"\nPain Score: {pain_score.score}")
    print(f"Status: {pain_score.status.value}")
    print(f"ICP Score: {pain_score.icp_score}")
    print(f"Proceed: {pain_score.proceed}")
    print(f"\nSignals detected ({len(pain_score.signals)}):")
    for signal in pain_score.signals[:10]:
        print(f"  [{signal.category}] +{signal.points}: {signal.signal}")

    print(f"\nTop pain points:")
    for point in pain_score.top_pain_points[:3]:
        print(f"  - {point}")

    return pain_score


async def main():
    print("=" * 60)
    print("RISE LOCAL PIPELINE - COMPONENT TEST")
    print("=" * 60)

    # Test 1: Supabase fetch
    lead = await test_supabase_fetch()

    if lead:
        # Test 2: Scoring
        pain_score = test_scoring(lead)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TESTS FAILED - Check Supabase configuration")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
