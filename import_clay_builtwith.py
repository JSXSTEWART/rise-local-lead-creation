"""
Import Clay BuiltWith CSV and enrich leads with AI tech stack analysis

Usage:
    python import_clay_builtwith.py <csv_file_path>

Example:
    python import_clay_builtwith.py "C:\\Users\\Owner\\Downloads\\builtwith_enrichment_2025-12-11.csv"
"""
import asyncio
import csv
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import httpx
from dotenv import load_dotenv

# Import our tech stack scorer
from rise_pipeline.tech_stack_scorer import analyze_tech_stack

load_dotenv()


class ClayBuiltWithImporter:
    """Import Clay BuiltWith CSV and run AI tech analysis"""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")

        self.base_url = f"{self.supabase_url}/rest/v1"
        self.stats = {
            "total_rows": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

    def _headers(self) -> Dict[str, str]:
        """Get Supabase headers"""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

    def read_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """Read Clay BuiltWith CSV export"""
        print(f"\n Reading CSV: {csv_path}")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        print(f" Found {len(rows)} rows in CSV")
        self.stats["total_rows"] = len(rows)
        return rows

    async def process_lead(self, row: Dict[str, Any]) -> bool:
        """Process a single lead: run AI analysis and update Supabase"""
        lead_id = row.get('lead_id', '').strip()
        business_name = row.get('business_name', '').strip()
        website = row.get('website', '').strip()

        # Get BuiltWith data from Clay
        technologies = row.get('Technologiesfound', '').strip()
        tech_count_str = row.get('Numberoftotaltechnologies', '0').strip()

        try:
            tech_count = int(tech_count_str) if tech_count_str else 0
        except ValueError:
            tech_count = 0

        # Validate required fields
        if not lead_id:
            print(f"  Skipping row: missing lead_id")
            self.stats["skipped"] += 1
            return False

        if not business_name:
            print(f"  Skipping {lead_id}: missing business_name")
            self.stats["skipped"] += 1
            return False

        if not technologies:
            print(f"  Skipping {lead_id}: no technologies found")
            self.stats["skipped"] += 1
            return False

        print(f"\n Processing: {business_name}")
        print(f"   Lead ID: {lead_id}")
        print(f"   Tech Count: {tech_count}")
        print(f"   Website: {website}")

        try:
            # Run AI tech stack analysis
            print(f"    Running Claude Haiku analysis...")
            tech_analysis = await analyze_tech_stack(
                business_name=business_name,
                technologies=technologies,
                tech_count=tech_count
            )

            # Extract fields for easy querying
            tech_stack_ai_score = tech_analysis.get("tech_score", 0)
            website_type = tech_analysis.get("website_type", "Unknown")
            cms_platform_ai = tech_analysis.get("cms_platform", "Unknown")
            has_gtm = tech_analysis.get("has_gtm", False)
            has_ga4 = tech_analysis.get("has_ga4", False)
            has_crm = tech_analysis.get("has_crm", False)
            has_booking_system = tech_analysis.get("has_booking_system", False)
            has_email_marketing = tech_analysis.get("has_email_marketing", False)
            has_lead_capture = tech_analysis.get("has_lead_capture", False)

            print(f"    AI Analysis Complete:")
            print(f"      Tech Score: {tech_stack_ai_score}/10")
            print(f"      Website Type: {website_type}")
            print(f"      CMS: {cms_platform_ai}")
            print(f"      Pain Points: {len(tech_analysis.get('pain_points', []))}")

            # Update Supabase
            now = datetime.utcnow().isoformat()
            update_data = {
                # Raw BuiltWith data
                "tech_raw_list": technologies[:5000],  # Limit to 5000 chars
                "tech_count": tech_count,

                # AI analysis
                "tech_analysis": tech_analysis,  # Full JSONB
                "tech_stack_ai_score": tech_stack_ai_score,
                "website_type": website_type,
                "cms_platform_ai": cms_platform_ai,
                "tech_analysis_model": "claude-3-5-haiku-20241022",
                "tech_analysis_at": now,

                # Boolean fields for easy filtering
                "has_gtm": has_gtm,
                "has_ga4": has_ga4,
                "has_crm": has_crm,
                "has_booking_system": has_booking_system,
                "has_email_marketing": has_email_marketing,
                "has_lead_capture": has_lead_capture,

                # Also update legacy cms_platform field
                "cms_platform": cms_platform_ai,

                # Update timestamp
                "updated_at": now
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.patch(
                    f"{self.base_url}/leads?id=eq.{lead_id}",
                    headers=self._headers(),
                    json=update_data
                )

                if resp.status_code in [200, 204]:
                    print(f"    Saved to Supabase")
                    self.stats["processed"] += 1
                    return True
                else:
                    error_msg = f"Supabase update failed: {resp.status_code} - {resp.text}"
                    print(f"    {error_msg}")
                    self.stats["errors"] += 1
                    self.stats["error_details"].append({
                        "lead_id": lead_id,
                        "business_name": business_name,
                        "error": error_msg
                    })
                    return False

        except Exception as e:
            error_msg = f"Error processing lead: {str(e)}"
            print(f"    {error_msg}")
            self.stats["errors"] += 1
            self.stats["error_details"].append({
                "lead_id": lead_id,
                "business_name": business_name,
                "error": error_msg
            })
            return False

    async def import_csv(self, csv_path: str):
        """Import entire CSV file"""
        print("\n" + "="*60)
        print("CLAY BUILTWITH IMPORT STARTING")
        print("="*60)

        # Read CSV
        rows = self.read_csv(csv_path)

        if not rows:
            print(" No rows found in CSV")
            return

        # Process each row
        print(f"\n Processing {len(rows)} leads...")
        for i, row in enumerate(rows, 1):
            print(f"\n[{i}/{len(rows)}]", end=" ")
            await self.process_lead(row)

        # Print summary
        print("\n" + "="*60)
        print(" IMPORT SUMMARY")
        print("="*60)
        print(f"Total Rows:     {self.stats['total_rows']}")
        print(f"Processed:      {self.stats['processed']} ")
        print(f"Skipped:        {self.stats['skipped']} ")
        print(f"Errors:         {self.stats['errors']} ")

        if self.stats["error_details"]:
            print(f"\n Errors:")
            for error in self.stats["error_details"]:
                print(f"   - {error['business_name']} ({error['lead_id']})")
                print(f"     {error['error']}")

        print("\n" + "="*60)

        # Calculate cost estimate
        processed = self.stats['processed']
        cost_per_lead = 0.001  # $0.001 per Claude Haiku call
        total_cost = processed * cost_per_lead
        print(f" Estimated Cost: ${total_cost:.4f} ({processed} × ${cost_per_lead})")
        print("="*60 + "\n")


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python import_clay_builtwith.py <csv_file_path>")
        print("\nExample:")
        print('  python import_clay_builtwith.py "C:\\Users\\Owner\\Downloads\\builtwith_export.csv"')
        sys.exit(1)

    csv_path = sys.argv[1]

    # Validate file exists
    if not os.path.exists(csv_path):
        print(f" File not found: {csv_path}")
        sys.exit(1)

    # Create importer and run
    importer = ClayBuiltWithImporter()
    await importer.import_csv(csv_path)


if __name__ == "__main__":
    asyncio.run(main())

