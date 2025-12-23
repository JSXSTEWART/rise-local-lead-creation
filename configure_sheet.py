"""
Configure Google Sheet for Rise Local Pipeline v2

After manually creating a Google Sheet, run this script to:
1. Add the Sheet ID to .env
2. Set up the worksheet headers
3. Test the connection

Usage: python configure_sheet.py <SHEET_ID>
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


def update_env_file(sheet_id):
    """Add GOOGLE_SHEET_ID to .env file."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")

    with open(env_path, 'r') as f:
        content = f.read()

    if "GOOGLE_SHEET_ID=" in content:
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith("GOOGLE_SHEET_ID="):
                new_lines.append(f"GOOGLE_SHEET_ID={sheet_id}")
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)
    else:
        content += f"\n# Google Sheets for Clay Integration\nGOOGLE_SHEET_ID={sheet_id}\n"

    with open(env_path, 'w') as f:
        f.write(content)

    print(f"Updated .env with GOOGLE_SHEET_ID")


def setup_sheet_headers(sheet_id):
    """Set up the worksheet with headers using OAuth."""
    import gspread
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    print("\n" + "="*60)
    print("CONFIGURING GOOGLE SHEET")
    print("="*60)

    # Credentials file path
    creds_dir = os.path.join(os.path.dirname(__file__), ".credentials")
    os.makedirs(creds_dir, exist_ok=True)
    token_path = os.path.join(creds_dir, "gsheets_token.json")

    # OAuth client credentials (for desktop app)
    # Using gspread's built-in OAuth
    print("\n1. Authenticating with Google...")

    try:
        # Try to use existing token
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # If no valid credentials, use gspread's OAuth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Use gspread's built-in OAuth flow
                gc = gspread.oauth(
                    scopes=SCOPES,
                    credentials_filename=os.path.join(creds_dir, "credentials.json") if os.path.exists(os.path.join(creds_dir, "credentials.json")) else None,
                    authorized_user_filename=token_path
                )
                print("   SUCCESS - Authenticated via OAuth")
                client = gc
        else:
            client = gspread.authorize(creds)
            print("   SUCCESS - Using cached credentials")

    except Exception as e:
        # Fallback: Try ADC with quota project workaround
        print(f"   OAuth failed: {e}")
        print("   Trying Application Default Credentials...")

        try:
            from google.auth import default as google_auth_default
            credentials, project = google_auth_default(scopes=SCOPES)

            # Add quota project header manually via requests
            import requests
            from google.auth.transport.requests import AuthorizedSession

            authed_session = AuthorizedSession(credentials)

            # Test with direct API call
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
            response = authed_session.get(url)

            if response.status_code == 200:
                print("   SUCCESS - Using ADC with direct API")
                data = response.json()
                print(f"\n2. Connected to: {data.get('properties', {}).get('title', 'Unknown')}")

                # Set up headers via direct API
                print("\n3. Setting up headers...")
                headers = [
                    "lead_id", "business_name", "website", "city", "state", "zip_code",
                    "phone", "address", "google_rating", "google_review_count",
                    "owner_first_name", "owner_last_name", "prequalification_score",
                    "technologies_list", "tech_count", "has_wordpress", "has_wix", "has_squarespace",
                    "owner_email", "owner_email_confidence", "owner_business_phone",
                    "owner_personal_email", "owner_personal_phone", "owner_linkedin",
                    "enrichment_source", "enriched_at"
                ]

                # Get first sheet ID
                sheets = data.get('sheets', [])
                if sheets:
                    first_sheet_id = sheets[0].get('properties', {}).get('sheetId', 0)

                    # Update sheet title
                    rename_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate"
                    rename_body = {
                        "requests": [{
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": first_sheet_id,
                                    "title": "qualified_leads"
                                },
                                "fields": "title"
                            }
                        }]
                    }
                    authed_session.post(rename_url, json=rename_body)
                    print("   Renamed sheet to 'qualified_leads'")

                    # Write headers
                    values_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/A1:Z1?valueInputOption=USER_ENTERED"
                    values_body = {"values": [headers]}
                    resp = authed_session.put(values_url, json=values_body)

                    if resp.status_code == 200:
                        print(f"   Added {len(headers)} column headers")
                        print("\n" + "="*60)
                        print("SETUP COMPLETE!")
                        print("="*60)
                        print(f"\nSheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
                        return True
                    else:
                        print(f"   Failed to write headers: {resp.text}")
                        return False
            else:
                print(f"   API Error: {response.status_code} - {response.text}")
                return False

        except Exception as e2:
            print(f"   ADC also failed: {e2}")
            return False

    # Continue with gspread client
    print(f"\n2. Opening sheet {sheet_id[:20]}...")
    try:
        spreadsheet = client.open_by_key(sheet_id)
        print(f"   Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

    print("\n3. Setting up 'qualified_leads' worksheet...")
    try:
        try:
            worksheet = spreadsheet.worksheet("qualified_leads")
            print("   Found existing 'qualified_leads' worksheet")
        except:
            try:
                worksheet = spreadsheet.sheet1
                worksheet.update_title("qualified_leads")
                print("   Renamed Sheet1 to 'qualified_leads'")
            except:
                worksheet = spreadsheet.add_worksheet(title="qualified_leads", rows=1000, cols=30)
                print("   Created 'qualified_leads' worksheet")

        headers = [
            "lead_id", "business_name", "website", "city", "state", "zip_code",
            "phone", "address", "google_rating", "google_review_count",
            "owner_first_name", "owner_last_name", "prequalification_score",
            "technologies_list", "tech_count", "has_wordpress", "has_wix", "has_squarespace",
            "owner_email", "owner_email_confidence", "owner_business_phone",
            "owner_personal_email", "owner_personal_phone", "owner_linkedin",
            "enrichment_source", "enriched_at"
        ]

        existing = worksheet.row_values(1)
        if existing and existing[0] == "lead_id":
            print("   Headers already exist")
        else:
            worksheet.update('A1:Z1', [headers])
            worksheet.format('A1:Z1', {'textFormat': {'bold': True}})
            print(f"   Added {len(headers)} column headers")

        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print(f"\nSheet URL: {spreadsheet.url}")
        return True

    except Exception as e:
        print(f"   FAILED: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if sheet_id:
            print(f"Using existing GOOGLE_SHEET_ID from .env")
        else:
            print("Usage: python configure_sheet.py <SHEET_ID>")
            sys.exit(1)
    else:
        sheet_id = sys.argv[1].strip()
        update_env_file(sheet_id)

    setup_sheet_headers(sheet_id)
