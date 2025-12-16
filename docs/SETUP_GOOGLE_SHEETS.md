# Rise Local - Google Sheets + Clay Automation Setup Guide

**Version:** 1.0
**Date:** December 2024
**Author:** Rise Local Pipeline Team

---

## Table of Contents

1. [Overview](#overview)
2. [Part 1: Google Cloud Setup](#part-1-google-cloud-setup)
3. [Part 2: Google Sheets Setup](#part-2-google-sheets-setup)
4. [Part 3: Clay BuiltWith Enrichment Table](#part-3-clay-builtwith-enrichment-table)
5. [Part 4: Clay Contact Waterfall Table](#part-4-clay-contact-waterfall-table)
6. [Part 5: Pipeline Integration](#part-5-pipeline-integration)
7. [Testing & Verification](#testing--verification)

---

## Overview

### What This Automates

**BEFORE (Manual Process):**
1. Export leads from dashboard to CSV
2. Upload CSV to Clay manually
3. Wait for Clay to enrich
4. Download enriched CSV from Clay
5. Run import script to load back to Supabase
6. Repeat for contact enrichment

**AFTER (Automated Process):**
1. Pipeline writes leads to Google Sheet
2. Clay automatically enriches new rows
3. Pipeline reads enriched data back
4. No manual steps required!

### Data Flow Diagram

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Supabase   │────▶│  Google Sheets   │────▶│    Clay     │
│  (Leads)    │     │  (Sync Layer)    │     │ (Enrichment)│
└─────────────┘     └──────────────────┘     └─────────────┘
       ▲                     │                      │
       │                     │                      │
       └─────────────────────┴──────────────────────┘
              Pipeline reads enriched data back
```

---

## Part 1: Google Cloud Setup

### Step 1.1: Create Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Click the project dropdown (top-left, next to "Google Cloud")
3. Click **"New Project"**
4. Enter:
   - **Project name:** `rise-local-pipeline`
   - **Organization:** Leave as default
5. Click **"Create"**
6. Wait for project creation (30 seconds)
7. Make sure the new project is selected in the dropdown

### Step 1.2: Enable Google Sheets API

1. In Google Cloud Console, go to **APIs & Services > Library**
   - Or direct link: https://console.cloud.google.com/apis/library
2. Search for: `Google Sheets API`
3. Click on **"Google Sheets API"**
4. Click **"Enable"**
5. Wait for it to enable (10 seconds)

### Step 1.3: Create Service Account

1. Go to **APIs & Services > Credentials**
   - Or direct link: https://console.cloud.google.com/apis/credentials
2. Click **"+ Create Credentials"** (top of page)
3. Select **"Service Account"**
4. Enter:
   - **Service account name:** `pipeline-bot`
   - **Service account ID:** `pipeline-bot` (auto-filled)
   - **Description:** `Automated pipeline for Rise Local lead processing`
5. Click **"Create and Continue"**
6. For "Grant this service account access" - click **"Continue"** (skip)
7. For "Grant users access" - click **"Done"** (skip)

### Step 1.4: Create & Download Key

1. In the Credentials page, find your new service account
2. Click on **"pipeline-bot@rise-local-pipeline.iam.gserviceaccount.com"**
3. Go to the **"Keys"** tab
4. Click **"Add Key" > "Create new key"**
5. Select **"JSON"**
6. Click **"Create"**
7. A JSON file will download automatically
8. **IMPORTANT:** Save this file as:
   ```
   C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation\.credentials\google-sheets-key.json
   ```
9. Create the `.credentials` folder if it doesn't exist

### Step 1.5: Note Your Service Account Email

From the JSON file or the console, copy the service account email. It looks like:
```
pipeline-bot@rise-local-pipeline.iam.gserviceaccount.com
```

**Save this email - you'll need it to share the Google Sheet!**

---

## Part 2: Google Sheets Setup

### Step 2.1: Create the Google Sheet

1. Go to: https://sheets.google.com/
2. Click **"+ Blank"** to create a new spreadsheet
3. Name it: `Rise Local - Clay Sync`
4. Note the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID_HERE]/edit
   ```
   Example: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

### Step 2.2: Create Tab 1 - Tech Enrichment

1. Right-click the "Sheet1" tab at the bottom
2. Rename to: `leads_for_tech_enrichment`
3. Add these column headers in Row 1:

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| lead_id | business_name | website | city | state | phone | address | google_rating | google_review_count |

**Column Details:**
- `lead_id` - UUID from Supabase (required for matching back)
- `business_name` - Company name
- `website` - Full URL (Clay uses this for BuiltWith)
- `city` - City name
- `state` - State code (TX)
- `phone` - Business phone
- `address` - Full address
- `google_rating` - Star rating (e.g., 4.2)
- `google_review_count` - Number of reviews

### Step 2.3: Create Tab 2 - Contact Enrichment

1. Click the **"+"** button to add a new tab
2. Name it: `leads_for_contact_enrichment`
3. Add these column headers in Row 1:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| lead_id | business_name | website | owner_first_name | owner_last_name | city | state |

**Column Details:**
- `lead_id` - UUID from Supabase
- `business_name` - Company name
- `website` - Company website
- `owner_first_name` - From TDLR license lookup
- `owner_last_name` - From TDLR license lookup
- `city` - City name
- `state` - State code

### Step 2.4: Share with Service Account

1. Click **"Share"** button (top-right)
2. In the "Add people" field, paste your service account email:
   ```
   pipeline-bot@rise-local-pipeline.iam.gserviceaccount.com
   ```
3. Set permission to **"Editor"**
4. Uncheck "Notify people"
5. Click **"Share"**

**The service account can now read/write to this sheet!**

### Step 2.5: Save Sheet ID to Environment

Add to your `.env` file:
```
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
GOOGLE_SHEETS_CREDENTIALS_PATH=.credentials/google-sheets-key.json
```

---

## Part 3: Clay BuiltWith Enrichment Table

### Step 3.1: Create New Clay Table

1. Log in to Clay: https://app.clay.com/
2. Click **"+ New Table"**
3. Name it: `Rise Local - Tech Enrichment`

### Step 3.2: Connect Google Sheets as Source

1. In the new table, click **"Add Source"** or **"Import Data"**
2. Select **"Google Sheets"**
3. Click **"Connect Google Account"** (if not already connected)
4. Authorize Clay to access your Google Sheets
5. Find and select: `Rise Local - Clay Sync`
6. Select the tab: `leads_for_tech_enrichment`
7. Click **"Import"**

### Step 3.3: Configure Auto-Sync

1. After import, click the **Google Sheets icon** in the source area
2. Enable **"Auto-sync"** or **"Watch for new rows"**
3. Set sync frequency: **Every 15 minutes** (or fastest available on your plan)
4. This means:
   - When pipeline adds a new row to Google Sheet
   - Clay will detect it within 15 minutes
   - Clay will automatically enrich the new row

### Step 3.4: Add BuiltWith Enrichment Column

1. Click **"+ Add Column"** (or the + at the end of columns)
2. Search for: `BuiltWith`
3. Select **"BuiltWith - Get Technologies"**
4. Configure:
   - **Website URL:** Select the `website` column
   - **Output format:** All technologies (or detailed)
5. Click **"Add Column"**

### Step 3.5: Add Parsed Technology Columns

Clay will create the BuiltWith column. Now add helper columns:

**Column: Technologies List**
1. Click **"+ Add Column"**
2. Select **"Formula"** or **"AI Extract"**
3. Name: `technologies_list`
4. Extract: All technology names as comma-separated list

**Column: Technology Count**
1. Click **"+ Add Column"**
2. Select **"Formula"**
3. Name: `tech_count`
4. Formula: Count of technologies found

### Step 3.6: Enable Auto-Enrichment

1. Click on the **BuiltWith column header**
2. In the column settings, enable **"Auto-run for new rows"**
3. This means new rows will automatically be enriched

### Step 3.7: Configure Write-Back to Google Sheets

1. Click **"Export"** or **"Destinations"**
2. Select **"Google Sheets"**
3. Choose: `Rise Local - Clay Sync`
4. Select tab: `leads_for_tech_enrichment`
5. Configure column mapping:
   - Map `technologies_list` → New column J (or add to sheet)
   - Map `tech_count` → New column K
6. Enable **"Auto-sync results back"**

**Now the flow is:**
```
Pipeline → Google Sheet → Clay auto-enriches → Results back to Sheet → Pipeline reads
```

---

## Part 4: Clay Contact Waterfall Table

### Step 4.1: Create Contact Enrichment Table

1. In Clay, click **"+ New Table"**
2. Name it: `Rise Local - Contact Waterfall`

### Step 4.2: Connect Google Sheets Source

1. Click **"Add Source"** → **"Google Sheets"**
2. Select: `Rise Local - Clay Sync`
3. Select tab: `leads_for_contact_enrichment`
4. Click **"Import"**
5. Enable **"Auto-sync"** / **"Watch for new rows"**

### Step 4.3: Understanding the Waterfall

Since you already have `owner_first_name` and `owner_last_name` from TDLR, the waterfall only needs to find:

| Field | Description | Use Case |
|-------|-------------|----------|
| Owner Email (Business) | Work email | Primary outreach |
| Owner Business Phone | Direct work line | Follow-up calls |
| Personal Email | Gmail, etc. | Backup outreach |
| Personal Phone | Cell/home | Last resort |

### Step 4.4: Add Find Person Column

1. Click **"+ Add Column"**
2. Search for: `Find Person` or `Enrich Person`
3. Select an enrichment provider (e.g., **"Apollo"**, **"Clearbit"**, **"FullContact"**)
4. Configure:
   - **First Name:** `owner_first_name` column
   - **Last Name:** `owner_last_name` column
   - **Company:** `business_name` column
   - **Company Website:** `website` column
5. Click **"Add Column"**

### Step 4.5: Add Email Waterfall

Clay's waterfall tries multiple providers until one succeeds:

**Option A: Clay's Built-in Waterfall**
1. Click **"+ Add Column"**
2. Search for: `Email Waterfall` or `Find Email`
3. Select **"Waterfall Enrichment"**
4. Configure sources (in order):
   - **Source 1:** Dropcontact
   - **Source 2:** Hunter.io
   - **Source 3:** Apollo
   - **Source 4:** Clearbit
5. Input mapping:
   - First Name: `owner_first_name`
   - Last Name: `owner_last_name`
   - Company: `business_name`
   - Domain: `website`

**Option B: Manual Waterfall (More Control)**

Create separate columns, each with "Only run if previous is empty":

1. **Email - Dropcontact**
   - Add Dropcontact enrichment
   - Input: first_name, last_name, company, website
   - Output: email

2. **Email - Hunter** (fallback)
   - Add Hunter enrichment
   - Set condition: "Only run if Email - Dropcontact is empty"
   - Input: first_name, last_name, domain

3. **Email - Apollo** (fallback)
   - Add Apollo enrichment
   - Set condition: "Only run if Email - Hunter is empty"

### Step 4.6: Add Phone Enrichment

1. Click **"+ Add Column"**
2. Search for: `Phone` or `Find Phone Number`
3. Options:
   - **Cognism** - Best for direct dials
   - **Lusha** - Good for mobile numbers
   - **Apollo** - Includes phone in person data
4. Configure:
   - First Name: `owner_first_name`
   - Last Name: `owner_last_name`
   - Company: `business_name`

### Step 4.7: Create Output Columns

Add these columns to organize the results:

| Column Name | Source | Description |
|-------------|--------|-------------|
| `owner_email` | Best email from waterfall | Primary contact email |
| `owner_email_confidence` | Confidence score (0-100) | Email validity score |
| `owner_business_phone` | Phone enrichment | Work phone number |
| `owner_personal_email` | Secondary email found | Backup email |
| `owner_personal_phone` | Mobile/personal phone | Backup phone |
| `owner_linkedin` | LinkedIn URL | For HeyReach integration |
| `enrichment_source` | Which provider succeeded | Tracking |

**Use Formula columns to consolidate:**
```
owner_email = COALESCE(dropcontact_email, hunter_email, apollo_email)
```

### Step 4.8: Enable Auto-Enrichment

For each enrichment column:
1. Click the column header
2. Enable **"Auto-run for new rows"**
3. Set appropriate rate limits to avoid API overages

### Step 4.9: Configure Write-Back to Google Sheets

1. Click **"Export"** → **"Google Sheets"**
2. Select: `Rise Local - Clay Sync`
3. Select tab: `leads_for_contact_enrichment`
4. Map output columns:

| Clay Column | Sheet Column |
|-------------|--------------|
| owner_email | H |
| owner_email_confidence | I |
| owner_business_phone | J |
| owner_personal_email | K |
| owner_personal_phone | L |
| owner_linkedin | M |
| enrichment_source | N |

5. Enable **"Auto-sync results"**

---

## Part 5: Pipeline Integration

### Step 5.1: Install Python Dependencies

```bash
pip install gspread google-auth
```

### Step 5.2: Update .env File

Add these variables:
```
# Google Sheets Configuration
GOOGLE_SHEET_ID=your_sheet_id_here
GOOGLE_SHEETS_CREDENTIALS_PATH=.credentials/google-sheets-key.json
GOOGLE_SHEETS_TAB_TECH=leads_for_tech_enrichment
GOOGLE_SHEETS_TAB_CONTACTS=leads_for_contact_enrichment
```

### Step 5.3: Pipeline Flow Updates

**Discovery Phase (existing):**
- Discovers leads via Google Places API
- Saves to Supabase
- **NEW:** Also writes to Google Sheet (tech enrichment tab)

**Tech Enrichment Phase:**
- **OLD:** Manual CSV export/import
- **NEW:**
  - Check Google Sheet for Clay-enriched rows
  - Read enriched data back
  - Run AI analysis (Claude Haiku)
  - Update Supabase

**Contact Enrichment Phase:**
- **OLD:** Manual process
- **NEW:**
  - Write qualified leads to Google Sheet (contact tab)
  - Wait for Clay waterfall
  - Read enriched contacts back
  - Update Supabase

### Step 5.4: Code Files to Create/Modify

1. **NEW:** `rise_pipeline/google_sheets.py` - Google Sheets client
2. **MODIFY:** `rise_pipeline/services.py` - Add GoogleSheetsClient
3. **MODIFY:** `rise_pipeline/pipeline.py` - Use sheets instead of CSV
4. **REMOVE:** Dashboard CSV export/import buttons

---

## Testing & Verification

### Test 1: Google Sheets Connection

```python
# Run this to verify connection
from rise_pipeline.google_sheets import GoogleSheetsClient

client = GoogleSheetsClient()
print(client.test_connection())  # Should print sheet name
```

### Test 2: Write Test Lead

```python
# Write a test lead to the tech enrichment sheet
client.write_lead_for_tech_enrichment({
    "lead_id": "test-123",
    "business_name": "Test Electric Co",
    "website": "https://example.com",
    "city": "Austin",
    "state": "TX"
})
```

### Test 3: Verify Clay Auto-Enrichment

1. Check Clay table - new row should appear
2. Wait for enrichment to complete (watch the BuiltWith column)
3. Check Google Sheet - enriched data should sync back

### Test 4: Read Enriched Data

```python
# Read back the enriched lead
enriched = client.read_tech_enriched_leads()
print(enriched[0])  # Should include technologies
```

### Test 5: Full Pipeline Run

```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
python -m rise_pipeline.pipeline --lead-id [test_lead_id]
```

---

## Troubleshooting

### "Permission denied" on Google Sheet
- Verify service account email is added as Editor
- Check credentials JSON path is correct

### Clay not auto-enriching
- Verify auto-sync is enabled on the source
- Check that auto-run is enabled on enrichment columns
- Clay Starter plan may have limits on auto-enrichment

### Data not syncing back to Sheet
- Verify export destination is configured
- Check auto-sync is enabled on export
- May need to manually trigger first sync

### Rate limits / API errors
- Reduce batch sizes
- Add delays between enrichments
- Check Clay credit balance

---

## Appendix: Column Reference

### Tech Enrichment Sheet - Final Columns

| Col | Name | Source | Description |
|-----|------|--------|-------------|
| A | lead_id | Pipeline | Supabase UUID |
| B | business_name | Pipeline | Company name |
| C | website | Pipeline | Company URL |
| D | city | Pipeline | City |
| E | state | Pipeline | State code |
| F | phone | Pipeline | Business phone |
| G | address | Pipeline | Full address |
| H | google_rating | Pipeline | Star rating |
| I | google_review_count | Pipeline | Review count |
| J | technologies_list | Clay | Comma-separated techs |
| K | tech_count | Clay | Number of technologies |

### Contact Enrichment Sheet - Final Columns

| Col | Name | Source | Description |
|-----|------|--------|-------------|
| A | lead_id | Pipeline | Supabase UUID |
| B | business_name | Pipeline | Company name |
| C | website | Pipeline | Company URL |
| D | owner_first_name | Pipeline/TDLR | From license lookup |
| E | owner_last_name | Pipeline/TDLR | From license lookup |
| F | city | Pipeline | City |
| G | state | Pipeline | State code |
| H | owner_email | Clay | Business email |
| I | owner_email_confidence | Clay | Confidence 0-100 |
| J | owner_business_phone | Clay | Work phone |
| K | owner_personal_email | Clay | Personal email |
| L | owner_personal_phone | Clay | Mobile/personal |
| M | owner_linkedin | Clay | LinkedIn URL |
| N | enrichment_source | Clay | Which provider found |

---

## Next Steps After Setup

1. [ ] Complete Google Cloud setup (Part 1)
2. [ ] Create and configure Google Sheet (Part 2)
3. [ ] Set up Clay BuiltWith table (Part 3)
4. [ ] Set up Clay Contact Waterfall table (Part 4)
5. [ ] Test with 1 lead manually
6. [ ] Request pipeline code updates (Part 5)
7. [ ] Run full integration test
8. [ ] Process 100 leads to verify
9. [ ] Scale to 1,000 leads

---

**Document End**

*For questions or issues, refer to the troubleshooting section or check Clay's documentation at https://docs.clay.com/*
