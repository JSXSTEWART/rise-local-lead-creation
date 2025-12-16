"""
Run Pre-Qualification using FREE scrapers only (v2 Pipeline)

This script:
1. Fetches leads that have NOT been pre-qualified
2. Runs FREE scrapers (Screenshot, PageSpeed, Owner Extractor, TDLR, BBB, Address)
3. Calculates pre-qualification score (NO Clay/BuiltWith data)
4. Updates Supabase with results
5. Qualified leads are ready for Clay enrichment

Usage:
    python run_prequalification_batch.py --limit 10       # Process 10 leads
    python run_prequalification_batch.py --all            # Process all leads
    python run_prequalification_batch.py --lead-id <uuid> # Process specific lead
"""
import asyncio
import argparse
from datetime import datetime
from typing import List, Dict, Any

from rise_pipeline.services import IntelligenceServices
from rise_pipeline.scoring import calculate_pre_qualification_score
from rise_pipeline.models import (
    Lead, VisualAnalysis, TechnicalScores, DirectoryPresence,
    LicenseInfo, ReputationData, AddressVerification
)
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


class PreQualificationProcessor:
    """Process leads through FREE scrapers for pre-qualification"""

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
        """Fetch leads that need pre-qualification (no prequalification_status yet)"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            if lead_id:
                # Process specific lead
                resp = await client.get(
                    f"{self.base_url}/leads?id=eq.{lead_id}",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    return resp.json() or []
                return []

            # Fetch leads WITHOUT pre-qualification status
            url = f"{self.base_url}/leads"
            params = {
                "select": "id,business_name,website,address_city,address_state,phone,address_full,google_rating,google_review_count,address_zip",
                "prequalification_status": "is.null",
                "website": "not.is.null",  # Must have website
                "order": "created_at.desc"
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
        """Process a single lead through FREE scrapers for pre-qualification"""
        lead_id = lead_data['id']
        business_name = lead_data.get('business_name', 'Unknown')
        website = lead_data.get('website', '')

        print(f"\n{'='*60}")
        print(f"PRE-QUALIFYING: {business_name}")
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
                zip_code=lead_data.get('address_zip', ''),
                google_rating=float(lead_data.get('google_rating') or 0.0),
                review_count=int(lead_data.get('google_review_count') or 0)
            )

            # Gather FREE intelligence only
            print("  Running FREE scrapers...")
            print("    - Screenshot analysis (port 8004)")
            print("    - PageSpeed API (port 8003)")
            print("    - Owner Extractor (port 8005)")
            print("    - TDLR license lookup (port 8001)")
            print("    - BBB reputation check (port 8002)")
            print("    - Address verification (port 8006)")

            visual, technical, directory, license_info, reputation, address = await self.intelligence.gather_all(
                lead=lead,
                website_url=website
            )

            print(f"\n  FREE Scraper Results:")
            print(f"    Visual Score: {visual.visual_score}/100")
            print(f"    Design Era: {visual.design_era}")
            print(f"    Performance Score: {technical.performance_score}/100")
            print(f"    Has HTTPS: {technical.has_https}")
            print(f"    License Status: {license_info.license_status}")
            print(f"    Owner Name: {license_info.owner_name or 'Not found'}")
            print(f"    BBB Rating: {reputation.bbb_rating}")
            print(f"    Address Type: {address.address_type}")

            # Calculate pre-qualification score (FREE data only)
            print("\n  Calculating pre-qualification score...")
            prequal = calculate_pre_qualification_score(
                lead=lead,
                visual=visual,
                technical=technical,
                license_info=license_info,
                reputation=reputation,
                address=address
            )

            print(f"\n  PRE-QUALIFICATION RESULT:")
            print(f"    Score: {prequal.score}")
            print(f"    Status: {prequal.status.value.upper()}")
            print(f"    Send to Clay: {'YES' if prequal.send_to_clay else 'NO'}")
            print(f"    Top Signals:")
            for i, sig in enumerate(prequal.top_signals[:5], 1):
                print(f"      {i}. {sig}")

            # Update Supabase with pre-qualification results
            now = datetime.utcnow().isoformat()
            update_data = {
                # Pre-qualification results
                "prequalification_score": prequal.score,
                "prequalification_status": prequal.status.value,
                "prequalification_signals": {"signals": [{"signal": s.signal, "points": s.points, "category": s.category} for s in prequal.signals]},
                "prequalification_at": now,
                "send_to_clay": prequal.send_to_clay,

                # FREE scraper data
                "visual_score": visual.visual_score,
                "design_era": visual.design_era,
                "mobile_responsive_visual": visual.mobile_responsive,
                "has_hero_image": visual.has_hero_image,
                "has_clear_cta": visual.has_clear_cta,

                "performance_score": technical.performance_score,
                "mobile_score": technical.mobile_score,
                "seo_score": technical.seo_score,
                "accessibility_score": technical.accessibility_score,
                "has_https": technical.has_https,
                "largest_contentful_paint": technical.lcp_ms,
                "cumulative_layout_shift": float(technical.cls),

                "license_found": license_info.license_status.lower() not in ["unknown", "not found", ""],
                "license_number": license_info.license_number or None,
                "license_type": license_info.license_type or None,
                "license_status": license_info.license_status,
                "owner_name_from_license": license_info.owner_name or None,

                "bbb_found": reputation.bbb_rating != "NR",
                "bbb_rating": reputation.bbb_rating,
                "bbb_accredited": reputation.bbb_accredited,
                "bbb_complaints_total": reputation.complaints_total,
                "bbb_years_in_business": reputation.years_in_business,

                "is_residential": address.is_residential,
                "address_type": address.address_type,
                "address_verified": address.verified,

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
            if prequal.status.value == "qualified":
                self.stats["qualified"] += 1
            elif prequal.status.value == "marginal":
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
        """Run pre-qualification processing with concurrent batches"""
        print("\n" + "="*60)
        print("PRE-QUALIFICATION PROCESSOR (FREE Scrapers Only)")
        print("v2 Pipeline - Filter Before Clay")
        print("="*60)

        # Fetch leads
        print("\nFetching leads needing pre-qualification...")
        leads = await self.get_leads_for_processing(limit=limit, lead_id=lead_id)

        if not leads:
            print("No leads found for pre-qualification!")
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
            tasks = [self.process_lead(lead_data) for lead_data in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Print summary
        print("\n" + "="*60)
        print("PRE-QUALIFICATION SUMMARY")
        print("="*60)
        print(f"Total Leads:    {self.stats['total']}")
        print(f"Processed:      {self.stats['processed']}")
        print(f"Failed:         {self.stats['failed']}")
        print(f"\nPre-Qualification Results:")
        print(f"  QUALIFIED (send to Clay):  {self.stats['qualified']}")
        print(f"  MARGINAL (manual review):  {self.stats['marginal']}")
        print(f"  REJECTED (stop here):      {self.stats['rejected']}")

        if self.stats['qualified'] > 0:
            print(f"\n{self.stats['qualified']} leads are ready for Clay enrichment!")
            print("Use dashboard 'Export to Clay' button to send qualified leads.")

        print("="*60 + "\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run pre-qualification using FREE scrapers")
    parser.add_argument('--limit', type=int, help="Number of leads to process")
    parser.add_argument('--all', action='store_true', help="Process all leads")
    parser.add_argument('--lead-id', type=str, help="Process specific lead by ID")
    parser.add_argument('--batch-size', type=int, default=5, help="Concurrent leads per batch (default: 5)")

    args = parser.parse_args()

    lead_id = None
    if args.lead_id:
        limit = None
        lead_id = args.lead_id
    elif args.all:
        limit = None
    else:
        limit = args.limit or 10  # Default to 10

    processor = PreQualificationProcessor()
    await processor.run(limit=limit, lead_id=lead_id, batch_size=args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())
