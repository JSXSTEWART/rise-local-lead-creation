"""
Run Phase 2 intelligence gathering for all tech-enriched leads

This script:
1. Fetches all leads with tech_analysis_at NOT NULL
2. Runs Phase 2 intelligence gathering (visual, pagespeed, TDLR, BBB)
3. Runs Phase 3 pain point scoring with AI tech data
4. Updates Supabase with results

Usage:
    python run_phase_2_batch.py --limit 10          # Process 10 leads
    python run_phase_2_batch.py --all               # Process all leads
    python run_phase_2_batch.py --lead-id <uuid>    # Process specific lead
"""
import asyncio
import argparse
import sys
from datetime import datetime
from typing import List, Dict, Any

from rise_pipeline.services import IntelligenceServices
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
from rise_pipeline.scoring import calculate_pain_score_with_ai_tech
from rise_pipeline.models import (
    Lead, VisualAnalysis, TechnicalScores, DirectoryPresence,
    LicenseInfo, ReputationData
)

class Phase2Processor:
    """Process Phase 2 intelligence gathering in batch"""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.base_url = f"{self.supabase_url}/rest/v1"
        self.intelligence = IntelligenceServices()
        self.stats = {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "qualified": 0,
            "marginal": 0,
            "rejected": 0
        }

    def _headers(self):
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def get_leads_for_processing(self, limit: int = None, lead_id: str = None) -> List[Dict]:
        """Fetch leads that need Phase 2 processing"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            if lead_id:
                # Process specific lead
                resp = await client.get(
                    f"{self.base_url}/leads?id=eq.{lead_id}",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    results = resp.json()
                    return results if results else []
                return []

            # Fetch leads with tech analysis but no Phase 2 data
            url = f"{self.base_url}/leads"
            params = {
                "select": "id,business_name,website,address_city,address_state,phone,address_full,google_rating,google_review_count",
                "tech_analysis_at": "not.is.null",
                "phase_2a_completed_at": "is.null",
                "order": "tech_stack_ai_score.asc.nullslast"
            }

            if limit:
                params["limit"] = limit

            resp = await client.get(url, headers=self._headers(), params=params)

            print(f"  Query URL: {resp.url}")
            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                results = resp.json()
                print(f"  Found {len(results)} leads")
                return results
            else:
                print(f"  Error: {resp.text}")
            return []

    async def process_lead(self, lead_data: Dict) -> bool:
        """Process a single lead through Phase 2"""
        lead_id = lead_data['id']
        business_name = lead_data.get('business_name', 'Unknown')
        website = lead_data.get('website', '')

        print(f"\n{'='*60}")
        print(f"Processing: {business_name}")
        print(f"Lead ID: {lead_id}")
        print(f"Website: {website}")
        print(f"{'='*60}")

        try:
            # Create Lead object
            lead = Lead(
                id=lead_id,
                business_name=business_name,
                website_url=website,
                city=lead_data.get('address_city', ''),
                state=lead_data.get('address_state', 'TX'),
                phone=lead_data.get('phone', ''),
                address=lead_data.get('address_full', ''),
                google_rating=float(lead_data.get('google_rating', 0.0)),
                review_count=int(lead_data.get('google_review_count', 0))
            )

            # Gather intelligence (Phase 2A-2E)
            print("  Running intelligence gathering...")
            print("    - Screenshot analysis (Phase 2A)")
            print("    - PageSpeed API (Phase 2B)")
            print("    - TDLR license lookup (Phase 2D)")
            print("    - BBB reputation check (Phase 2E)")

            visual, technical, directory, license_info, reputation, address = await self.intelligence.gather_all(
                lead=lead,
                website_url=website
            )

            print(f"  Visual Score: {visual.visual_score}/100")
            print(f"  Performance Score: {technical.performance_score}/100")
            print(f"  License Status: {license_info.license_status}")
            print(f"  BBB Rating: {reputation.bbb_rating}")
            print(f"  Address Type: {address.address_type} (residential={address.is_residential})")

            # Get tech analysis from database
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.base_url}/leads?id=eq.{lead_id}&select=tech_analysis,tech_stack_ai_score,website_type",
                    headers=self._headers()
                )

                if resp.status_code != 200 or not resp.json():
                    print("  ERROR: No tech analysis found!")
                    self.stats["failed"] += 1
                    return False

                tech_data = resp.json()[0]
                tech_analysis = tech_data.get('tech_analysis', {})

            # Calculate pain score with AI tech data
            print("  Calculating unified pain score...")
            pain_score = calculate_pain_score_with_ai_tech(
                lead=lead,
                tech_analysis=tech_analysis,
                visual=visual,
                technical=technical,
                directory=directory,
                license_info=license_info,
                reputation=reputation
            )

            print(f"  Pain Score: {pain_score.score}")
            print(f"  Status: {pain_score.status.value}")
            print(f"  Top Pain Points:")
            for i, pp in enumerate(pain_score.top_pain_points[:5], 1):
                print(f"    {i}. {pp}")

            # Update Supabase with all Phase 2 data
            now = datetime.utcnow().isoformat()
            update_data = {
                # Phase 2A - Visual
                "screenshot_url": visual.screenshot_url if hasattr(visual, 'screenshot_url') else None,
                "visual_score": visual.visual_score,
                "design_era": visual.design_era,
                "mobile_responsive_visual": visual.mobile_responsive,
                "has_hero_image": visual.has_hero_image,
                "has_clear_cta": visual.has_clear_cta,
                "phase_2a_completed_at": now,

                # Phase 2B - Technical
                "performance_score": technical.performance_score,
                "mobile_score": technical.mobile_score,
                "seo_score": technical.seo_score,
                "accessibility_score": technical.accessibility_score,
                "largest_contentful_paint": technical.lcp_ms,
                "first_input_delay": technical.fid_ms,
                "cumulative_layout_shift": float(technical.cls),
                "phase_2b_completed_at": now,

                # Phase 2C - Directory (Yext) - skipped for now
                "phase_2c_completed_at": None,

                # Phase 2D - License
                "license_found": license_info.license_status != "Unknown",
                "license_number": license_info.license_number,
                "license_type": license_info.license_type,
                "license_status": license_info.license_status,
                "owner_name_from_license": license_info.owner_name,
                "phase_2d_completed_at": now,

                # Phase 2E - Reputation
                "bbb_found": reputation.bbb_rating != "NR",
                "bbb_rating": reputation.bbb_rating,
                "bbb_accredited": reputation.bbb_accredited,
                "bbb_complaints_total": reputation.complaints_total,
                "bbb_years_in_business": reputation.years_in_business,
                "phase_2e_completed_at": now,

                # Phase 2F - Address Verification
                "is_residential": address.is_residential,
                "address_type": address.address_type,
                "address_verified": address.verified,
                "formatted_address": address.formatted_address if address.formatted_address else None,
                "address_verified_at": now if address.verified else None,
                "phase_2f_completed_at": now,

                # Phase 3 - Pain Scoring
                "pain_point_score": pain_score.score,
                "pain_point_details": {"signals": [{"signal": s.signal, "points": s.points, "category": s.category} for s in pain_score.signals]},
                "qualification_status": pain_score.status.value,
                "phase_3_completed_at": now,

                # Update status
                "status": pain_score.status.value,
                "updated_at": now
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.patch(
                    f"{self.base_url}/leads?id=eq.{lead_id}",
                    headers=self._headers(),
                    json=update_data
                )

                if resp.status_code not in [200, 204]:
                    print(f"  ERROR updating Supabase: {resp.status_code} - {resp.text}")
                    self.stats["failed"] += 1
                    return False

            print(f"  Saved to Supabase")

            self.stats["processed"] += 1
            if pain_score.status.value == "qualified":
                self.stats["qualified"] += 1
            elif pain_score.status.value == "marginal":
                self.stats["marginal"] += 1
            else:
                self.stats["rejected"] += 1

            return True

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            self.stats["failed"] += 1
            return False

    async def run(self, limit: int = None, lead_id: str = None, batch_size: int = 5):
        """Run Phase 2 processing with concurrent batches"""
        print("\n" + "="*60)
        print("PHASE 2 INTELLIGENCE GATHERING - BATCH PROCESSOR")
        print("="*60)

        # Fetch leads
        print("\nFetching leads...")
        leads = await self.get_leads_for_processing(limit=limit, lead_id=lead_id)

        if not leads:
            print("No leads found for processing!")
            return

        self.stats["total"] = len(leads)
        print(f"Found {len(leads)} leads to process")
        print(f"Batch size: {batch_size} concurrent leads\n")

        # Process leads in concurrent batches
        for batch_start in range(0, len(leads), batch_size):
            batch_end = min(batch_start + batch_size, len(leads))
            batch = leads[batch_start:batch_end]

            print(f"\nProcessing batch {batch_start//batch_size + 1} (leads {batch_start+1}-{batch_end})...")

            # Process batch concurrently
            tasks = []
            for i, lead_data in enumerate(batch, start=batch_start+1):
                tasks.append(self.process_lead(lead_data))

            # Wait for all leads in batch to complete
            await asyncio.gather(*tasks, return_exceptions=True)

        # Print summary
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Total Leads:    {self.stats['total']}")
        print(f"Processed:      {self.stats['processed']}")
        print(f"Failed:         {self.stats['failed']}")
        print(f"\nQualification Results:")
        print(f"  Qualified:    {self.stats['qualified']}")
        print(f"  Marginal:     {self.stats['marginal']}")
        print(f"  Rejected:     {self.stats['rejected']}")
        print("="*60 + "\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Phase 2 intelligence gathering")
    parser.add_argument('--limit', type=int, help="Number of leads to process")
    parser.add_argument('--all', action='store_true', help="Process all leads")
    parser.add_argument('--lead-id', type=str, help="Process specific lead by ID")
    parser.add_argument('--batch-size', type=int, default=5, help="Number of leads to process concurrently (default: 5)")

    args = parser.parse_args()

    lead_id = None
    if args.lead_id:
        limit = None
        lead_id = args.lead_id
    elif args.all:
        limit = None
    else:
        limit = args.limit or 10  # Default to 10

    processor = Phase2Processor()
    await processor.run(limit=limit, lead_id=lead_id, batch_size=args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())
