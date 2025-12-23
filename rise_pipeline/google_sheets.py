"""
Google Sheets Client for Rise Local Pipeline v2

Handles automated sync with Clay via Google Sheets:
- Write qualified leads (after pre-qualification) to Google Sheet
- Clay reads from Sheet, enriches with BuiltWith + Contact Waterfall
- Read enriched leads back from Sheet

ONE sheet, ONE Clay table, ONE manual action.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import gspread
    from google.auth import default as google_auth_default
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logging.warning("gspread not installed. Run: pip install gspread google-auth")

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsClient:
    """
    Client for reading/writing leads to Google Sheets for Clay integration.

    v2: Uses Application Default Credentials (no JSON key file needed).
    Run: gcloud auth application-default login --scopes="..."

    Usage:
        client = GoogleSheetsClient()

        # Write qualified leads for Clay enrichment
        client.write_qualified_leads(leads)

        # Read enriched leads back
        enriched = client.read_enriched_leads()
    """

    def __init__(self):
        if not GSPREAD_AVAILABLE:
            raise ImportError("gspread not installed. Run: pip install gspread google-auth")

        self.sheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.tab_qualified = os.getenv("GOOGLE_SHEETS_TAB_QUALIFIED", "qualified_leads")

        # Legacy tab names (for backward compatibility)
        self.tab_tech = os.getenv("GOOGLE_SHEETS_TAB_TECH", "leads_for_tech_enrichment")
        self.tab_contacts = os.getenv("GOOGLE_SHEETS_TAB_CONTACTS", "leads_for_contact_enrichment")

        if not self.sheet_id:
            raise ValueError("GOOGLE_SHEET_ID not set in environment")

        self._client = None
        self._spreadsheet = None

    def _get_client(self) -> gspread.Client:
        """Get or create authenticated gspread client using Application Default Credentials."""
        if self._client is None:
            try:
                # Try Application Default Credentials first (gcloud auth application-default login)
                credentials, project = google_auth_default(scopes=SCOPES)
                self._client = gspread.authorize(credentials)
                logger.info("Using Application Default Credentials")
            except Exception as e:
                # Fall back to service account file if ADC not available
                credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", ".credentials/google-sheets-key.json")
                if os.path.exists(credentials_path):
                    credentials = Credentials.from_service_account_file(
                        credentials_path,
                        scopes=SCOPES
                    )
                    self._client = gspread.authorize(credentials)
                    logger.info("Using service account credentials")
                else:
                    raise ValueError(f"No credentials found. Run: gcloud auth application-default login. Error: {e}")
        return self._client

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """Get the spreadsheet instance."""
        if self._spreadsheet is None:
            client = self._get_client()
            self._spreadsheet = client.open_by_key(self.sheet_id)
        return self._spreadsheet

    def test_connection(self) -> str:
        """Test the connection to Google Sheets."""
        try:
            spreadsheet = self._get_spreadsheet()
            return f"Connected to: {spreadsheet.title}"
        except Exception as e:
            return f"Connection failed: {str(e)}"

    # =========================================================================
    # V2 PIPELINE: UNIFIED CLAY ENRICHMENT (BuiltWith + Contact Waterfall)
    # =========================================================================

    def write_qualified_leads(self, leads: List[Dict[str, Any]]) -> int:
        """
        Write pre-qualified leads to Google Sheet for Clay enrichment.

        Clay will enrich with BOTH:
        - BuiltWith (tech stack detection)
        - Contact Waterfall (owner email/phone)

        Args:
            leads: List of lead dicts with keys:
                - lead_id (required)
                - business_name
                - website
                - city, state, zip_code
                - phone, address
                - google_rating, google_review_count
                - owner_first_name, owner_last_name (from TDLR)
                - prequalification_score
                - prequalification_status

        Returns:
            Number of leads written
        """
        spreadsheet = self._get_spreadsheet()

        # Get or create the qualified_leads tab
        try:
            worksheet = spreadsheet.worksheet(self.tab_qualified)
        except gspread.WorksheetNotFound:
            # Create the worksheet with headers
            worksheet = spreadsheet.add_worksheet(title=self.tab_qualified, rows=1000, cols=30)
            headers = [
                # Input columns (we write these)
                "lead_id", "business_name", "website", "city", "state", "zip_code",
                "phone", "address", "google_rating", "google_review_count",
                "owner_first_name", "owner_last_name", "prequalification_score",
                # Output columns (Clay fills these)
                "technologies_list", "tech_count", "has_wordpress", "has_wix", "has_squarespace",
                "owner_email", "owner_email_confidence", "owner_business_phone",
                "owner_personal_email", "owner_personal_phone", "owner_linkedin",
                "enrichment_source", "enriched_at"
            ]
            worksheet.append_row(headers)
            logger.info(f"Created worksheet '{self.tab_qualified}' with headers")

        # Get existing lead_ids to avoid duplicates
        existing_data = worksheet.get_all_records()
        existing_ids = {row.get('lead_id') for row in existing_data if row.get('lead_id')}

        # Filter out duplicates
        new_leads = [l for l in leads if l.get('lead_id') not in existing_ids]

        if not new_leads:
            logger.info("No new qualified leads to write (all already exist)")
            return 0

        # Prepare rows
        rows = []
        for lead in new_leads:
            rows.append([
                lead.get('lead_id', ''),
                lead.get('business_name', ''),
                lead.get('website', ''),
                lead.get('city', ''),
                lead.get('state', 'TX'),
                lead.get('zip_code', ''),
                lead.get('phone', ''),
                lead.get('address', ''),
                lead.get('google_rating', ''),
                lead.get('google_review_count', ''),
                lead.get('owner_first_name', ''),
                lead.get('owner_last_name', ''),
                lead.get('prequalification_score', '')
            ])

        # Append rows to sheet
        worksheet.append_rows(rows, value_input_option='USER_ENTERED')

        logger.info(f"Wrote {len(rows)} qualified leads to '{self.tab_qualified}' for Clay enrichment")
        return len(rows)

    def read_enriched_leads(self, only_enriched: bool = True) -> List[Dict[str, Any]]:
        """
        Read Clay-enriched leads from Google Sheet.

        Returns leads with both tech stack AND contact data from Clay.

        Args:
            only_enriched: If True, only return rows where Clay has added data

        Returns:
            List of lead dicts with enrichment data
        """
        spreadsheet = self._get_spreadsheet()

        try:
            worksheet = spreadsheet.worksheet(self.tab_qualified)
        except gspread.WorksheetNotFound:
            logger.warning(f"Worksheet '{self.tab_qualified}' not found")
            return []

        records = worksheet.get_all_records()

        if only_enriched:
            # Filter to rows where Clay has added tech OR contact data
            records = [
                r for r in records
                if r.get('technologies_list') or r.get('owner_email') or r.get('tech_count')
            ]

        logger.info(f"Read {len(records)} enriched leads from '{self.tab_qualified}'")
        return records

    def get_leads_pending_enrichment(self) -> List[Dict[str, Any]]:
        """Get qualified leads that are in the sheet but not yet enriched by Clay."""
        spreadsheet = self._get_spreadsheet()

        try:
            worksheet = spreadsheet.worksheet(self.tab_qualified)
        except gspread.WorksheetNotFound:
            return []

        records = worksheet.get_all_records()

        # Filter to rows without enrichment data
        pending = [
            r for r in records
            if r.get('lead_id') and not r.get('technologies_list') and not r.get('owner_email')
        ]

        logger.info(f"Found {len(pending)} leads pending Clay enrichment")
        return pending

    # =========================================================================
    # LEGACY: TECH ENRICHMENT (BuiltWith) - Separate Tab
    # =========================================================================

    def write_leads_for_tech_enrichment(self, leads: List[Dict[str, Any]]) -> int:
        """
        Write leads to Google Sheet for Clay BuiltWith enrichment.

        Args:
            leads: List of lead dicts with keys:
                - lead_id (required)
                - business_name
                - website
                - city
                - state
                - phone
                - address
                - google_rating
                - google_review_count

        Returns:
            Number of leads written
        """
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_tech)

        # Get existing lead_ids to avoid duplicates
        existing_data = worksheet.get_all_records()
        existing_ids = {row.get('lead_id') for row in existing_data if row.get('lead_id')}

        # Filter out duplicates
        new_leads = [l for l in leads if l.get('lead_id') not in existing_ids]

        if not new_leads:
            logger.info("No new leads to write (all already exist)")
            return 0

        # Prepare rows
        rows = []
        for lead in new_leads:
            rows.append([
                lead.get('lead_id', ''),
                lead.get('business_name', ''),
                lead.get('website', ''),
                lead.get('city', ''),
                lead.get('state', 'TX'),
                lead.get('phone', ''),
                lead.get('address', ''),
                lead.get('google_rating', ''),
                lead.get('google_review_count', '')
            ])

        # Append rows to sheet
        worksheet.append_rows(rows, value_input_option='USER_ENTERED')

        logger.info(f"Wrote {len(rows)} leads to tech enrichment sheet")
        return len(rows)

    def read_tech_enriched_leads(self, only_enriched: bool = True) -> List[Dict[str, Any]]:
        """
        Read tech-enriched leads from Google Sheet.

        Args:
            only_enriched: If True, only return rows where Clay has added data

        Returns:
            List of lead dicts with enrichment data
        """
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_tech)

        records = worksheet.get_all_records()

        if only_enriched:
            # Filter to only rows where Clay has added technologies
            records = [
                r for r in records
                if r.get('technologies_list') or r.get('tech_count')
            ]

        logger.info(f"Read {len(records)} tech-enriched leads from sheet")
        return records

    def get_leads_pending_tech_enrichment(self) -> List[Dict[str, Any]]:
        """Get leads that are in the sheet but not yet enriched by Clay."""
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_tech)

        records = worksheet.get_all_records()

        # Filter to rows without enrichment data
        pending = [
            r for r in records
            if r.get('lead_id') and not r.get('technologies_list')
        ]

        logger.info(f"Found {len(pending)} leads pending tech enrichment")
        return pending

    # =========================================================================
    # CONTACT ENRICHMENT (Waterfall)
    # =========================================================================

    def write_leads_for_contact_enrichment(self, leads: List[Dict[str, Any]]) -> int:
        """
        Write qualified leads to Google Sheet for Clay contact waterfall.

        Args:
            leads: List of lead dicts with keys:
                - lead_id (required)
                - business_name
                - website
                - owner_first_name (from TDLR)
                - owner_last_name (from TDLR)
                - city
                - state

        Returns:
            Number of leads written
        """
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_contacts)

        # Get existing lead_ids to avoid duplicates
        existing_data = worksheet.get_all_records()
        existing_ids = {row.get('lead_id') for row in existing_data if row.get('lead_id')}

        # Filter out duplicates
        new_leads = [l for l in leads if l.get('lead_id') not in existing_ids]

        if not new_leads:
            logger.info("No new leads to write for contact enrichment")
            return 0

        # Prepare rows
        rows = []
        for lead in new_leads:
            rows.append([
                lead.get('lead_id', ''),
                lead.get('business_name', ''),
                lead.get('website', ''),
                lead.get('owner_first_name', ''),
                lead.get('owner_last_name', ''),
                lead.get('city', ''),
                lead.get('state', 'TX')
            ])

        # Append rows to sheet
        worksheet.append_rows(rows, value_input_option='USER_ENTERED')

        logger.info(f"Wrote {len(rows)} leads to contact enrichment sheet")
        return len(rows)

    def read_contact_enriched_leads(self, only_enriched: bool = True) -> List[Dict[str, Any]]:
        """
        Read contact-enriched leads from Google Sheet.

        Args:
            only_enriched: If True, only return rows where Clay has found contact data

        Returns:
            List of lead dicts with contact data:
                - lead_id
                - owner_email
                - owner_email_confidence
                - owner_business_phone
                - owner_personal_email
                - owner_personal_phone
                - owner_linkedin
                - enrichment_source
        """
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_contacts)

        records = worksheet.get_all_records()

        if only_enriched:
            # Filter to only rows where Clay has found at least an email
            records = [
                r for r in records
                if r.get('owner_email') or r.get('owner_business_phone')
            ]

        logger.info(f"Read {len(records)} contact-enriched leads from sheet")
        return records

    def get_leads_pending_contact_enrichment(self) -> List[Dict[str, Any]]:
        """Get leads that are in the sheet but not yet enriched by Clay."""
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_contacts)

        records = worksheet.get_all_records()

        # Filter to rows without contact data
        pending = [
            r for r in records
            if r.get('lead_id') and not r.get('owner_email')
        ]

        logger.info(f"Found {len(pending)} leads pending contact enrichment")
        return pending

    # =========================================================================
    # SYNC STATUS
    # =========================================================================

    def get_sync_status(self) -> Dict[str, Any]:
        """Get overall sync status between pipeline and Clay."""
        spreadsheet = self._get_spreadsheet()
        result = {"last_checked": datetime.now().isoformat()}

        # V2: Unified enrichment status
        try:
            qualified_sheet = spreadsheet.worksheet(self.tab_qualified)
            qualified_records = qualified_sheet.get_all_records()
            qualified_total = len([r for r in qualified_records if r.get('lead_id')])
            qualified_tech = len([r for r in qualified_records if r.get('technologies_list') or r.get('tech_count')])
            qualified_contact = len([r for r in qualified_records if r.get('owner_email')])
            qualified_both = len([r for r in qualified_records if (r.get('technologies_list') or r.get('tech_count')) and r.get('owner_email')])
            qualified_pending = qualified_total - qualified_both

            result["v2_enrichment"] = {
                "total": qualified_total,
                "with_tech": qualified_tech,
                "with_contact": qualified_contact,
                "fully_enriched": qualified_both,
                "pending": qualified_pending,
                "completion_rate": f"{(qualified_both/qualified_total*100):.1f}%" if qualified_total > 0 else "N/A"
            }
        except gspread.WorksheetNotFound:
            result["v2_enrichment"] = {"status": "worksheet not found"}

        # Legacy: Tech enrichment status
        try:
            tech_sheet = spreadsheet.worksheet(self.tab_tech)
            tech_records = tech_sheet.get_all_records()
            tech_total = len([r for r in tech_records if r.get('lead_id')])
            tech_enriched = len([r for r in tech_records if r.get('technologies_list')])
            tech_pending = tech_total - tech_enriched

            result["legacy_tech_enrichment"] = {
                "total": tech_total,
                "enriched": tech_enriched,
                "pending": tech_pending,
                "completion_rate": f"{(tech_enriched/tech_total*100):.1f}%" if tech_total > 0 else "N/A"
            }
        except gspread.WorksheetNotFound:
            result["legacy_tech_enrichment"] = {"status": "worksheet not found"}

        # Legacy: Contact enrichment status
        try:
            contact_sheet = spreadsheet.worksheet(self.tab_contacts)
            contact_records = contact_sheet.get_all_records()
            contact_total = len([r for r in contact_records if r.get('lead_id')])
            contact_enriched = len([r for r in contact_records if r.get('owner_email')])
            contact_pending = contact_total - contact_enriched

            result["legacy_contact_enrichment"] = {
                "total": contact_total,
                "enriched": contact_enriched,
                "pending": contact_pending,
                "completion_rate": f"{(contact_enriched/contact_total*100):.1f}%" if contact_total > 0 else "N/A"
            }
        except gspread.WorksheetNotFound:
            result["legacy_contact_enrichment"] = {"status": "worksheet not found"}

        return result

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def clear_tech_sheet(self, keep_headers: bool = True):
        """Clear the tech enrichment sheet (for testing)."""
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_tech)

        if keep_headers:
            # Keep row 1, clear everything else
            worksheet.batch_clear(["A2:Z10000"])
        else:
            worksheet.clear()

        logger.info("Cleared tech enrichment sheet")

    def clear_contact_sheet(self, keep_headers: bool = True):
        """Clear the contact enrichment sheet (for testing)."""
        spreadsheet = self._get_spreadsheet()
        worksheet = spreadsheet.worksheet(self.tab_contacts)

        if keep_headers:
            worksheet.batch_clear(["A2:Z10000"])
        else:
            worksheet.clear()

        logger.info("Cleared contact enrichment sheet")


# =============================================================================
# CLI for testing
# =============================================================================

async def main():
    """Test the Google Sheets client."""
    print("\n" + "="*60)
    print("GOOGLE SHEETS CLIENT TEST (v2 Pipeline)")
    print("="*60)

    try:
        client = GoogleSheetsClient()

        # Test connection
        print("\n1. Testing connection...")
        result = client.test_connection()
        print(f"   {result}")

        if "Connected to" in result:
            print("   SUCCESS!")
        else:
            print("   FAILED - Check credentials and sheet ID")
            return

        # Get sync status
        print("\n2. Getting sync status...")
        status = client.get_sync_status()

        print("\n   V2 Enrichment (unified):")
        v2 = status.get('v2_enrichment', {})
        if v2.get('status') == 'worksheet not found':
            print("     Worksheet not created yet (will be created on first write)")
        else:
            print(f"     Total: {v2.get('total', 0)}")
            print(f"     With Tech Data: {v2.get('with_tech', 0)}")
            print(f"     With Contact Data: {v2.get('with_contact', 0)}")
            print(f"     Fully Enriched: {v2.get('fully_enriched', 0)}")
            print(f"     Pending: {v2.get('pending', 0)}")

        # Test v2 write with a test lead (commented out to avoid accidental writes)
        # print("\n3. Testing v2 write...")
        # count = client.write_qualified_leads([{
        #     "lead_id": "test-v2-123",
        #     "business_name": "Test Electric v2",
        #     "website": "https://example.com",
        #     "city": "Austin",
        #     "state": "TX",
        #     "zip_code": "78701",
        #     "owner_first_name": "John",
        #     "owner_last_name": "Doe",
        #     "prequalification_score": 5
        # }])
        # print(f"   Wrote {count} leads")

        print("\n" + "="*60)
        print("TEST COMPLETE - Connection successful!")
        print("="*60)
        print("\nNext steps:")
        print("1. Create Google Sheet and add GOOGLE_SHEET_ID to .env")
        print("2. Run pre-qualification batch to get qualified leads")
        print("3. Use dashboard to export qualified leads to Sheet")
        print("4. Configure Clay table to read from Sheet")
        print("="*60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
