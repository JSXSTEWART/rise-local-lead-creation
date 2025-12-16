"""
Reprocess Phase 2 Intelligence Gathering on Existing Leads

This script re-runs all Phase 2 services on existing leads to:
1. Add address verification data (Phase 2F - new!)
2. Update any stale intelligence data
3. Test and measure processing speed

Usage:
    python -m rise_pipeline.reprocess_phase2 --limit 10
    python -m rise_pipeline.reprocess_phase2 --all  # Process all leads
"""

import asyncio
import time
from datetime import datetime
from typing import List, Dict
import argparse

from .services import SupabaseClient, IntelligenceServices
from .models import Lead

class Phase2Reprocessor:
    """Reprocess Phase 2 intelligence gathering on existing leads"""

    def __init__(self):
        self.supabase = SupabaseClient()
        self.intelligence = IntelligenceServices()
        self.stats = {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "residential": 0,
            "commercial": 0,
            "unknown": 0,
            "start_time": None,
            "end_time": None
        }

    async def fetch_leads(self, limit: int = None) -> List[Dict]:
        """Fetch leads from Supabase"""
        params = {"select": "*", "order": "created_at.desc"}

        if limit:
            params["limit"] = limit

        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.supabase.base_url}/leads",
                headers=self.supabase._headers(),
                params=params
            )

            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Error fetching leads: {resp.status_code} - {resp.text}")
                return []

    async def process_lead(self, lead_data: Dict) -> bool:
        """Run Phase 2 intelligence gathering on a single lead"""
        try:
            # Convert dict to Lead object
            lead = Lead(
                id=str(lead_data.get("id", "")),
                business_name=str(lead_data.get("business_name", "")),
                address=str(lead_data.get("address_full") or lead_data.get("address_street") or ""),
                city=str(lead_data.get("address_city", "")),
                state=str(lead_data.get("address_state", "TX")),
                zip_code=str(lead_data.get("address_zip", "")),
                phone=str(lead_data.get("phone") or ""),
                website_url=str(lead_data.get("website") or ""),
                google_rating=float(lead_data.get("google_rating") or 0),
                review_count=int(lead_data.get("google_review_count") or 0),
                place_id=str(lead_data.get("place_id") or "")
            )

            print(f"\n[{self.stats['processed'] + 1}/{self.stats['total']}] Processing: {lead.business_name}")
            print(f"  Address: {lead.address}, {lead.city}, {lead.state} {lead.zip_code}")

            # Run all Phase 2 intelligence gathering in parallel
            visual, technical, directory, license_info, reputation, address = await self.intelligence.gather_all(
                lead=lead,
                website_url=lead.website_url
            )

            # Track address type stats
            if address.is_residential:
                self.stats["residential"] += 1
            elif address.address_type == "commercial":
                self.stats["commercial"] += 1
            else:
                self.stats["unknown"] += 1

            print(f"  [OK] Visual: {visual.visual_score}/100")
            print(f"  [OK] Performance: {technical.performance_score}/100")
            print(f"  [OK] Directory: {directory.listings_score}/100")
            print(f"  [OK] License: {license_info.license_status}")
            print(f"  [OK] BBB: {reputation.bbb_rating}")
            print(f"  [OK] Address: {address.address_type} (residential={address.is_residential})")

            # Update Supabase with all intelligence data
            update_data = {
                # Phase 2A: Visual Analysis
                "visual_score": visual.visual_score,
                "design_era": visual.design_era or None,
                "mobile_responsive_visual": visual.mobile_responsive,
                "has_hero_image": visual.has_hero_image,
                "has_clear_cta": visual.has_clear_cta,
                "has_trust_signals": visual.trust_signals > 0,
                "social_links_count": sum([1 for s in [visual.social_facebook, visual.social_instagram, visual.social_linkedin] if s]),
                "phase_2a_completed_at": datetime.utcnow().isoformat(),

                # Phase 2B: Technical Scores
                "performance_score": technical.performance_score,
                "mobile_score": technical.mobile_score,
                "seo_score": technical.seo_score,
                "phase_2b_completed_at": datetime.utcnow().isoformat(),

                # Phase 2C: Directory Presence
                "yext_score": directory.listings_score,
                "yext_scan_id": directory.scan_id or None,
                "nap_consistency": directory.nap_consistency if directory.nap_consistency else None,
                "phase_2c_completed_at": datetime.utcnow().isoformat(),

                # Phase 2D: License Info
                "license_status": license_info.license_status or None,
                "license_number": license_info.license_number or None,
                "owner_name_from_license": license_info.owner_name or None,
                "phase_2d_completed_at": datetime.utcnow().isoformat(),

                # Phase 2E: Reputation
                "bbb_rating": reputation.bbb_rating or None,
                "bbb_accredited": reputation.bbb_accredited,
                "bbb_years_in_business": reputation.years_in_business or None,
                "reputation_gap": reputation.reputation_gap or None,
                "phase_2e_completed_at": datetime.utcnow().isoformat(),

                # Phase 2F: Address Verification (NEW!)
                "is_residential": address.is_residential,
                "address_type": address.address_type,
                "address_verified": address.verified,
                "formatted_address": address.formatted_address if address.formatted_address else None,
                "address_verified_at": datetime.utcnow().isoformat() if address.verified else None,
                "phase_2f_completed_at": datetime.utcnow().isoformat(),

                # Update processing timestamp
                "updated_at": datetime.utcnow().isoformat()
            }

            await self.supabase.update_lead(lead.id, update_data)

            self.stats["processed"] += 1
            return True

        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            self.stats["failed"] += 1
            return False

    async def run(self, limit: int = None):
        """Run Phase 2 reprocessing on all matching leads"""
        print("=" * 80)
        print("PHASE 2 REPROCESSING - Intelligence Gathering with Address Verification")
        print("=" * 80)

        # Fetch leads
        print(f"\nFetching leads from Supabase...")
        if limit:
            print(f"  Limit: {limit} leads")
        else:
            print(f"  Processing ALL leads")

        leads = await self.fetch_leads(limit=limit)

        if not leads:
            print("No leads found!")
            return

        self.stats["total"] = len(leads)
        print(f"\n[OK] Found {len(leads)} leads to process\n")

        # Start timer
        self.stats["start_time"] = time.time()

        # Process leads sequentially (for now)
        for lead_data in leads:
            await self.process_lead(lead_data)

        # End timer
        self.stats["end_time"] = time.time()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print processing summary"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        avg_time = duration / self.stats["processed"] if self.stats["processed"] > 0 else 0

        print("\n" + "=" * 80)
        print("PROCESSING COMPLETE")
        print("=" * 80)
        print(f"\nStats:")
        print(f"  Total leads: {self.stats['total']}")
        print(f"  [OK] Processed: {self.stats['processed']}")
        print(f"  [X] Failed: {self.stats['failed']}")
        print(f"\nAddress Classification:")
        print(f"  Residential: {self.stats['residential']}")
        print(f"  Commercial: {self.stats['commercial']}")
        print(f"  Unknown: {self.stats['unknown']}")
        print(f"\nPerformance:")
        print(f"  Total time: {duration:.2f}s")
        print(f"  Average per lead: {avg_time:.2f}s")
        print(f"  Rate: {self.stats['processed'] / duration * 60:.1f} leads/minute")
        print("\n" + "=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="Reprocess Phase 2 intelligence gathering")
    parser.add_argument("--limit", type=int, help="Limit number of leads to process (default: 10)")
    parser.add_argument("--all", action="store_true", help="Process all leads (no limit)")

    args = parser.parse_args()

    limit = None if args.all else (args.limit or 10)

    reprocessor = Phase2Reprocessor()
    await reprocessor.run(limit=limit)


if __name__ == "__main__":
    asyncio.run(main())
