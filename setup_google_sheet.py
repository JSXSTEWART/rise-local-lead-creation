"""
Setup Script: Create Google Sheet for Rise Local Pipeline v2

This script creates a new Google Sheet with the correct structure
for Clay enrichment integration.

OPTION 1: Use existing Sheet ID
OPTION 2: Manual creation instructions

Run: python setup_google_sheet.py
"""

import os
import sys
import webbrowser

def print_manual_instructions():
    """Print instructions for manual Google Sheet creation."""
    print("\n" + "="*60)
    print("RISE LOCAL - GOOGLE SHEET SETUP")
    print("="*60)

    print("""
MANUAL SETUP INSTRUCTIONS:
==========================

1. Go to Google Sheets: https://sheets.google.com

2. Create a new blank spreadsheet

3. Name it: "Rise Local - Clay Enrichment"

4. Rename "Sheet1" tab to: "qualified_leads"

5. Add these headers in row 1 (columns A through AA):

   INPUT COLUMNS (Pipeline writes these):
   A: lead_id
   B: business_name
   C: website
   D: city
   E: state
   F: zip_code
   G: phone
   H: address
   I: google_rating
   J: google_review_count
   K: owner_first_name
   L: owner_last_name
   M: prequalification_score

   OUTPUT COLUMNS (Clay fills these):
   N: technologies_list
   O: tech_count
   P: has_wordpress
   Q: has_wix
   R: has_squarespace
   S: owner_email
   T: owner_email_confidence
   U: owner_business_phone
   V: owner_personal_email
   W: owner_personal_phone
   X: owner_linkedin
   Y: enrichment_source
   Z: enriched_at

6. Get the Sheet ID from the URL:
   https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit

   The SHEET_ID is the long string between /d/ and /edit

7. Add to your .env file:
   GOOGLE_SHEET_ID=your-sheet-id-here
""")

    print("="*60)

    # Offer to open Google Sheets
    response = input("\nOpen Google Sheets in browser? (y/n): ").strip().lower()
    if response == 'y':
        webbrowser.open("https://sheets.google.com")

    # Get Sheet ID from user
    print("\n" + "-"*60)
    sheet_id = input("Enter your Sheet ID (or press Enter to skip): ").strip()

    if sheet_id:
        update_env_file(sheet_id)
        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print("\nNow run: python -m rise_pipeline.google_sheets")
        print("to test the connection.")
    else:
        print("\nRemember to add GOOGLE_SHEET_ID to your .env file later.")


def update_env_file(sheet_id):
    """Add GOOGLE_SHEET_ID to .env file."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")

    # Read existing .env
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            content = f.read()
    else:
        content = ""

    # Check if already exists
    if "GOOGLE_SHEET_ID=" in content:
        # Update existing
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith("GOOGLE_SHEET_ID="):
                new_lines.append(f"GOOGLE_SHEET_ID={sheet_id}")
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)

        with open(env_path, 'w') as f:
            f.write(content)
        print(f"\nUpdated GOOGLE_SHEET_ID in .env")
    else:
        # Append to .env
        with open(env_path, 'a') as f:
            f.write(f"\n# Google Sheets for Clay Integration\n")
            f.write(f"GOOGLE_SHEET_ID={sheet_id}\n")
        print(f"\nAdded GOOGLE_SHEET_ID to .env")


def try_gspread_oauth():
    """Try to use gspread OAuth flow."""
    try:
        import gspread
        from google.auth import default as google_auth_default

        print("\n" + "="*60)
        print("ATTEMPTING AUTOMATIC SHEET CREATION")
        print("="*60)

        print("\n1. Authenticating with Google...")

        try:
            credentials, project = google_auth_default(scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ])

            # Try to set quota project
            if project and hasattr(credentials, 'with_quota_project'):
                credentials = credentials.with_quota_project(project)

            client = gspread.authorize(credentials)
            print("   SUCCESS - Using Application Default Credentials")

            # Create spreadsheet
            print("\n2. Creating Google Sheet...")
            spreadsheet = client.create("Rise Local - Clay Enrichment")
            print(f"   Created: {spreadsheet.title}")
            print(f"   Sheet ID: {spreadsheet.id}")
            print(f"   URL: {spreadsheet.url}")

            # Setup worksheet
            print("\n3. Setting up 'qualified_leads' worksheet...")
            worksheet = spreadsheet.sheet1
            worksheet.update_title("qualified_leads")

            headers = [
                "lead_id", "business_name", "website", "city", "state", "zip_code",
                "phone", "address", "google_rating", "google_review_count",
                "owner_first_name", "owner_last_name", "prequalification_score",
                "technologies_list", "tech_count", "has_wordpress", "has_wix", "has_squarespace",
                "owner_email", "owner_email_confidence", "owner_business_phone",
                "owner_personal_email", "owner_personal_phone", "owner_linkedin",
                "enrichment_source", "enriched_at"
            ]
            worksheet.update('A1:Z1', [headers])
            worksheet.format('A1:Z1', {'textFormat': {'bold': True}})

            print(f"   Added {len(headers)} column headers")

            # Update .env
            update_env_file(spreadsheet.id)

            print("\n" + "="*60)
            print("SETUP COMPLETE!")
            print("="*60)
            print(f"\nSheet URL: {spreadsheet.url}")
            print("\nNow run: python -m rise_pipeline.google_sheets")
            print("to test the connection.")

            return True

        except Exception as e:
            error_msg = str(e)
            if "quota project" in error_msg.lower() or "403" in error_msg:
                print(f"   Quota project error - falling back to manual setup")
                return False
            else:
                print(f"   Error: {e}")
                return False

    except ImportError:
        print("gspread not installed")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("RISE LOCAL - GOOGLE SHEET SETUP")
    print("="*60)

    # Check for existing Sheet ID
    from dotenv import load_dotenv
    load_dotenv()

    existing_id = os.getenv("GOOGLE_SHEET_ID")
    if existing_id:
        print(f"\nExisting GOOGLE_SHEET_ID found: {existing_id[:20]}...")
        response = input("Keep existing Sheet ID? (y/n): ").strip().lower()
        if response == 'y':
            print("\nSetup complete - using existing Sheet ID.")
            print("Run: python -m rise_pipeline.google_sheets to test.")
            sys.exit(0)

    # Try automatic creation first
    print("\nAttempting automatic Sheet creation...")
    if try_gspread_oauth():
        sys.exit(0)

    # Fall back to manual instructions
    print("\nAutomatic creation failed. Switching to manual setup...")
    print_manual_instructions()
