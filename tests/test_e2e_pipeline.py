"""
End-to-End Pipeline Test
========================
Tests the complete lead creation flow:
1. Discover/fetch 10 new leads
2. Run enrichment (tech, visual, pagespeed, TDLR, BBB)
3. Score and qualify leads
4. Generate emails for qualified leads

Usage:
    python test_e2e_pipeline.py                    # Full test with 10 leads
    python test_e2e_pipeline.py --count 5          # Test with custom lead count
    python test_e2e_pipeline.py --dry-run          # Test without saving to DB
    python test_e2e_pipeline.py --skip-delivery    # Skip Instantly/GHL delivery
    python test_e2e_pipeline.py --lead-id UUID     # Test single specific lead

Prerequisites:
    1. Docker scrapers running (ports 8001-8004)
    2. .env file configured with API keys
    3. Supabase with leads in 'new' status
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
    TDLR_SCRAPER_URL, BBB_SCRAPER_URL,
    PAGESPEED_API_URL, SCREENSHOT_SERVICE_URL,
    ANTHROPIC_API_KEY
)


class TestResults:
    """Track test results across all stages"""
    def __init__(self):
        self.start_time = datetime.now()
        self.leads_fetched = 0
        self.leads_enriched = 0
        self.leads_scored = 0
        self.leads_qualified = 0
        self.leads_marginal = 0
        self.leads_rejected = 0
        self.emails_generated = 0
        self.emails_delivered = 0
        self.errors: List[Dict[str, Any]] = []
        self.stage_results: Dict[str, List[Dict]] = {
            "fetch": [],
            "enrichment": [],
            "scoring": [],
            "email": [],
            "delivery": []
        }

    def add_error(self, stage: str, lead_id: str, error: str):
        self.errors.append({
            "stage": stage,
            "lead_id": lead_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def summary(self) -> str:
        duration = (datetime.now() - self.start_time).total_seconds()
        return f"""
================================================================================
                        END-TO-END PIPELINE TEST RESULTS
================================================================================

Duration: {duration:.1f} seconds

STAGE BREAKDOWN:
----------------
  Leads Fetched:     {self.leads_fetched}
  Leads Enriched:    {self.leads_enriched}
  Leads Scored:      {self.leads_scored}

QUALIFICATION:
--------------
  Qualified:         {self.leads_qualified} ({self._pct(self.leads_qualified, self.leads_scored)})
  Marginal:          {self.leads_marginal} ({self._pct(self.leads_marginal, self.leads_scored)})
  Rejected:          {self.leads_rejected} ({self._pct(self.leads_rejected, self.leads_scored)})

EMAIL GENERATION:
-----------------
  Emails Generated:  {self.emails_generated}
  Emails Delivered:  {self.emails_delivered}

ERRORS:
-------
  Total Errors:      {len(self.errors)}

{"ERRORS DETAIL:" if self.errors else ""}
{self._format_errors()}

================================================================================
"""

    def _pct(self, num: int, total: int) -> str:
        if total == 0:
            return "0%"
        return f"{(num/total)*100:.0f}%"

    def _format_errors(self) -> str:
        if not self.errors:
            return ""
        lines = []
        for err in self.errors[:10]:  # Show first 10 errors
            lines.append(f"  [{err['stage']}] {err['lead_id'][:8]}...: {err['error'][:60]}")
        if len(self.errors) > 10:
            lines.append(f"  ... and {len(self.errors) - 10} more errors")
        return "\n".join(lines)


async def check_prerequisites() -> Dict[str, bool]:
    """Check all required services are available"""
    import httpx

    print("\n=== Checking Prerequisites ===\n")

    checks = {
        "supabase": False,
        "tdlr_scraper": False,
        "bbb_scraper": False,
        "pagespeed_api": False,
        "screenshot_service": False,
        "anthropic_api": False
    }

    # Check Supabase
    print(f"  Supabase URL: {SUPABASE_URL}")
    if SUPABASE_URL and SUPABASE_SERVICE_KEY and "your" not in SUPABASE_SERVICE_KEY.lower():
        checks["supabase"] = True
        print("    [OK] Supabase configured")
    else:
        print("    [FAIL] Supabase not configured")

    # Check Docker scrapers
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in [
            ("tdlr_scraper", TDLR_SCRAPER_URL),
            ("bbb_scraper", BBB_SCRAPER_URL),
            ("pagespeed_api", PAGESPEED_API_URL),
            ("screenshot_service", SCREENSHOT_SERVICE_URL)
        ]:
            try:
                resp = await client.get(f"{url}/health")
                if resp.status_code == 200:
                    checks[name] = True
                    print(f"    [OK] {name} @ {url}")
                else:
                    print(f"    [FAIL] {name} @ {url} - Status {resp.status_code}")
            except Exception as e:
                print(f"    [FAIL] {name} @ {url} - {str(e)[:40]}")

    # Check Anthropic
    if ANTHROPIC_API_KEY and "your" not in ANTHROPIC_API_KEY.lower() and len(ANTHROPIC_API_KEY) > 20:
        checks["anthropic_api"] = True
        print(f"    [OK] Anthropic API key configured")
    else:
        print(f"    [FAIL] Anthropic API key not configured")

    # Summary
    passed = sum(checks.values())
    total = len(checks)
    print(f"\n  Prerequisites: {passed}/{total} passed")

    return checks


async def fetch_test_leads(count: int, specific_lead_id: str = None, status: str = "discovered") -> List[Dict]:
    """Fetch leads from Supabase for testing"""
    from .services import SupabaseClient

    print(f"\n=== Fetching {count} Test Leads (status={status}) ===\n")

    client = SupabaseClient()

    if specific_lead_id:
        # Fetch specific lead - returns Lead object, need to convert to dict
        lead = await client.get_lead(specific_lead_id)
        if lead:
            # Convert Lead object to dict for consistency
            lead_dict = {
                'id': lead.id,
                'business_name': lead.business_name,
                'address_street': lead.address,
                'address_city': lead.city,
                'address_state': lead.state,
                'address_zip': lead.zip_code,
                'phone': lead.phone,
                'website': lead.website_url,
                'google_rating': lead.google_rating,
                'google_review_count': lead.review_count,
                'place_id': lead.place_id,
                'status': lead.status
            }
            print(f"  Found specific lead: {lead.business_name}")
            return [lead_dict]
        else:
            print(f"  [ERROR] Lead {specific_lead_id} not found")
            return []

    # Fetch leads by status (default: 'discovered', can also use 'new')
    leads = await client.fetch_new_leads(count, status=status)

    print(f"  Found {len(leads)} leads with status '{status}'")
    for i, lead in enumerate(leads[:5]):
        print(f"    {i+1}. {lead.get('business_name', 'Unknown')} - {lead.get('address_city', 'Unknown')}, {lead.get('address_state', '')}")
    if len(leads) > 5:
        print(f"    ... and {len(leads) - 5} more")

    return leads


async def run_enrichment(lead: Dict, results: TestResults, dry_run: bool = False) -> Dict:
    """Run all enrichment services on a lead"""
    from .services import IntelligenceServices
    from .models import Lead

    lead_id = lead.get('id', 'unknown')
    business_name = lead.get('business_name', 'Unknown')

    print(f"\n  Enriching: {business_name}")

    enrichment_data = {
        "lead_id": lead_id,
        "tech": None,
        "visual": None,
        "technical": None,
        "directory": None,
        "license": None,
        "reputation": None
    }

    # Create Lead model from dict
    lead_model = Lead(
        id=str(lead.get('id', '')),
        business_name=str(lead.get('business_name', '')),
        address=str(lead.get('address_full') or lead.get('address_street') or ''),
        city=str(lead.get('address_city', '')),
        state=str(lead.get('address_state', 'TX')),
        zip_code=str(lead.get('address_zip', '')),
        phone=str(lead.get('phone') or ''),
        website_url=str(lead.get('website') or ''),
        google_rating=float(lead.get('google_rating') or 0),
        review_count=int(lead.get('google_review_count') or 0),
        place_id=str(lead.get('place_id') or ''),
        status=str(lead.get('status', 'discovered'))
    )

    # Run parallel intelligence gathering
    try:
        # Visual Analysis (requires website)
        if lead_model.website_url:
            try:
                visual = await IntelligenceServices.get_visual_analysis(lead_model)
                enrichment_data["visual"] = visual
                print(f"    [OK] Visual: score={visual.visual_score if visual else 'N/A'}")
            except Exception as e:
                print(f"    [FAIL] Visual: {str(e)[:40]}")
                results.add_error("enrichment", lead_id, f"Visual: {e}")

        # PageSpeed Analysis (requires website)
        if lead_model.website_url:
            try:
                technical = await IntelligenceServices.get_pagespeed(lead_model)
                enrichment_data["technical"] = technical
                print(f"    [OK] PageSpeed: perf={technical.performance_score if technical else 'N/A'}")
            except Exception as e:
                print(f"    [FAIL] PageSpeed: {str(e)[:40]}")
                results.add_error("enrichment", lead_id, f"PageSpeed: {e}")

        # TDLR License
        try:
            license_info = await IntelligenceServices.get_tdlr_license(lead_model)
            enrichment_data["license"] = license_info
            print(f"    [OK] TDLR: status={license_info.license_status if license_info else 'N/A'}")
        except Exception as e:
            print(f"    [FAIL] TDLR: {str(e)[:40]}")
            results.add_error("enrichment", lead_id, f"TDLR: {e}")

        # BBB Reputation
        try:
            reputation = await IntelligenceServices.get_bbb_reputation(lead_model)
            enrichment_data["reputation"] = reputation
            print(f"    [OK] BBB: rating={reputation.bbb_rating if reputation else 'N/A'}")
        except Exception as e:
            print(f"    [FAIL] BBB: {str(e)[:40]}")
            results.add_error("enrichment", lead_id, f"BBB: {e}")

        results.leads_enriched += 1
        results.stage_results["enrichment"].append({
            "lead_id": lead_id,
            "business": business_name,
            "success": True
        })

    except Exception as e:
        results.add_error("enrichment", lead_id, str(e))
        results.stage_results["enrichment"].append({
            "lead_id": lead_id,
            "business": business_name,
            "success": False,
            "error": str(e)
        })

    return enrichment_data


async def run_scoring(lead: Dict, enrichment_data: Dict, results: TestResults) -> Dict:
    """Score and qualify the lead"""
    from .models import Lead, TechEnrichment, VisualAnalysis, TechnicalScores, DirectoryPresence, LicenseInfo, ReputationData
    from .scoring import calculate_pain_score

    lead_id = lead.get('id', 'unknown')
    business_name = lead.get('business_name', 'Unknown')

    print(f"\n  Scoring: {business_name}")

    try:
        # Create Lead model
        lead_model = Lead(
            id=lead_id,
            business_name=business_name,
            address=lead.get('address_street', ''),
            city=lead.get('address_city', ''),
            state=lead.get('address_state', 'TX'),
            zip_code=lead.get('address_zip', ''),
            phone=lead.get('phone', ''),
            website_url=lead.get('website') or lead.get('website_url', ''),
            google_rating=lead.get('google_rating', 0),
            review_count=lead.get('google_review_count', 0),
            place_id=lead.get('place_id', ''),
            status=lead.get('status', 'new')
        )

        # Create tech enrichment (from DB or default)
        tech = TechEnrichment(
            has_gtm=lead.get('has_gtm') or False,
            has_ga4=lead.get('has_ga4') or False,
            has_chat_widget=lead.get('has_chat_widget') or False,
            has_booking_system=lead.get('has_booking_system') or False,
            cms_platform=lead.get('cms_platform') or '',
            crm_detected=lead.get('crm_platform') or '',
            tech_score=lead.get('tech_stack_score') or 0
        )

        # Calculate pain score - use default objects for any missing enrichment
        pain_result = calculate_pain_score(
            lead=lead_model,
            tech=tech,
            visual=enrichment_data.get("visual") or VisualAnalysis(),
            technical=enrichment_data.get("technical") or TechnicalScores(),
            directory=enrichment_data.get("directory") or DirectoryPresence(),
            license_info=enrichment_data.get("license") or LicenseInfo(),
            reputation=enrichment_data.get("reputation") or ReputationData()
        )

        results.leads_scored += 1

        status = pain_result.status.value
        if status == "qualified":
            results.leads_qualified += 1
        elif status == "marginal":
            results.leads_marginal += 1
        else:
            results.leads_rejected += 1

        print(f"    Pain Score: {pain_result.score}")
        print(f"    Status: {status.upper()}")
        print(f"    Top Signals: {', '.join(pain_result.top_pain_points[:3])}")

        results.stage_results["scoring"].append({
            "lead_id": lead_id,
            "business": business_name,
            "score": pain_result.score,
            "status": status,
            "signals": len(pain_result.signals)
        })

        return {
            "pain_score": pain_result,
            "proceed": pain_result.proceed,
            "status": status
        }

    except Exception as e:
        results.add_error("scoring", lead_id, str(e))
        return {"pain_score": None, "proceed": False, "status": "error"}


async def generate_email(lead: Dict, enrichment_data: Dict, scoring_result: Dict, results: TestResults) -> Dict:
    """Generate email for qualified lead"""
    from .email_generator import EmailGenerator

    lead_id = lead.get('id', 'unknown')
    business_name = lead.get('business_name', 'Unknown')

    print(f"\n  Generating Email: {business_name}")

    try:
        generator = EmailGenerator()

        # Build context for email
        pain_score = scoring_result.get("pain_score")

        email_result = await generator.generate_email(
            lead=lead,
            pain_score=pain_score,
            visual=enrichment_data.get("visual"),
            technical=enrichment_data.get("technical"),
            license_info=enrichment_data.get("license"),
            reputation=enrichment_data.get("reputation"),
            use_rag=False  # Disable RAG for testing
        )

        if email_result and email_result.subject:
            results.emails_generated += 1
            print(f"    [OK] Subject: {email_result.subject[:50]}...")
            print(f"    [OK] Confidence: {email_result.confidence:.2f}")
            print(f"    [OK] Variant: {email_result.variant}")

            results.stage_results["email"].append({
                "lead_id": lead_id,
                "business": business_name,
                "subject": email_result.subject,
                "confidence": email_result.confidence,
                "variant": email_result.variant,
                "success": True
            })

            return {"email": email_result, "success": True}
        else:
            print(f"    [FAIL] No email generated")
            results.add_error("email", lead_id, "No email generated")
            return {"email": None, "success": False}

    except Exception as e:
        print(f"    [FAIL] {str(e)[:50]}")
        results.add_error("email", lead_id, str(e))
        return {"email": None, "success": False}


async def run_e2e_test(count: int = 10, dry_run: bool = False, skip_delivery: bool = True, lead_id: str = None):
    """Run the complete end-to-end test"""
    results = TestResults()

    print("=" * 80)
    print("           RISE LOCAL - END-TO-END PIPELINE TEST")
    print("=" * 80)
    print(f"\nTest Configuration:")
    print(f"  Lead Count:     {count if not lead_id else '1 (specific)'}")
    print(f"  Dry Run:        {dry_run}")
    print(f"  Skip Delivery:  {skip_delivery}")
    print(f"  Started:        {results.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check prerequisites
    prereqs = await check_prerequisites()

    critical_failed = not prereqs["supabase"]
    if critical_failed:
        print("\n[ABORT] Critical prerequisites not met. Cannot continue.")
        return results

    # Warn about missing services but continue
    scrapers_ok = all([
        prereqs["tdlr_scraper"],
        prereqs["bbb_scraper"],
        prereqs["pagespeed_api"],
        prereqs["screenshot_service"]
    ])
    if not scrapers_ok:
        print("\n[WARN] Some scrapers unavailable. Enrichment will be partial.")
        print("       Run: docker compose up -d  in custom_tools/ directory")

    if not prereqs["anthropic_api"]:
        print("\n[WARN] Anthropic API not configured. Email generation will fail.")

    # Fetch leads
    leads = await fetch_test_leads(count, lead_id)
    results.leads_fetched = len(leads)

    if not leads:
        print("\n[ABORT] No leads to process.")
        return results

    # Process each lead
    print("\n" + "=" * 80)
    print("                     PROCESSING LEADS")
    print("=" * 80)

    for i, lead in enumerate(leads):
        lead_id = lead.get('id', 'unknown')
        business = lead.get('business_name', 'Unknown')

        print(f"\n{'='*40}")
        print(f"Lead {i+1}/{len(leads)}: {business}")
        print(f"ID: {lead_id}")
        print(f"{'='*40}")

        # Stage 1: Enrichment
        enrichment_data = await run_enrichment(lead, results, dry_run)

        # Stage 2: Scoring
        scoring_result = await run_scoring(lead, enrichment_data, results)

        # Stage 3: Email Generation (only for qualified/marginal)
        if scoring_result.get("proceed") or scoring_result.get("status") == "marginal":
            if prereqs["anthropic_api"]:
                email_result = await generate_email(lead, enrichment_data, scoring_result, results)
            else:
                print(f"\n  [SKIP] Email generation - Anthropic API not configured")
        else:
            print(f"\n  [SKIP] Email generation - Lead rejected (score too low)")

        # Stage 4: Delivery (skipped for testing)
        if not skip_delivery:
            print(f"\n  [TODO] Delivery stage not implemented in test")

    # Print summary
    print(results.summary())

    return results


def main():
    parser = argparse.ArgumentParser(description="End-to-End Pipeline Test")
    parser.add_argument("--count", type=int, default=10, help="Number of leads to test (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Don't save results to database")
    parser.add_argument("--skip-delivery", action="store_true", default=True, help="Skip email delivery (default: True)")
    parser.add_argument("--lead-id", type=str, help="Test a specific lead by ID")
    args = parser.parse_args()

    asyncio.run(run_e2e_test(
        count=args.count,
        dry_run=args.dry_run,
        skip_delivery=args.skip_delivery,
        lead_id=args.lead_id
    ))


if __name__ == "__main__":
    main()
