# Clay BuiltWith Enrichment Workflow

## Current Reality

**Clay BuiltWith export provides:**
- `Technologiesfound` - Comma-separated list of technologies
- `Numberoftotaltechnologies` - Count of technologies found
- Basic lead info (business_name, website, phone, address, etc.)

**Clay does NOT provide:**
- Parsed boolean fields (has_gtm, has_ga4, etc.)
- Tech stack scoring
- Pain point analysis

## Why Dashboard Import Won't Work (Yet)

The dashboard's current `importCSV` function (lines 1746-1806 in `dashboard/app.js`) expects parsed fields from Clay that Clay doesn't provide on the Starter plan.

### Expected by Dashboard:
```csv
lead_id,has_gtm,has_ga4,cms_platform,has_crm,has_booking_system,tech_stack_score
abc-123,true,false,WordPress,false,true,65
```

### What Clay Actually Provides:
```csv
lead_id,business_name,Technologiesfound,Numberoftotaltechnologies
abc-123,Hart Electrical,"Wix, Google Cloud, ...",8
```

## Current Workflow (Manual - Working)

### Step 1: Export from Dashboard
1. Open dashboard: `http://localhost:8080`
2. Go to "Clay Enrichment Queues" section
3. Click "Export CSV for Clay" under BuiltWith card
4. Downloads: `builtwith_export_YYYY-MM-DD.csv`

### Step 2: Import to Clay & Enrich
1. Go to Clay dashboard
2. Import CSV to BuiltWith table
3. Run BuiltWith enrichment
4. Export enriched CSV from Clay

### Step 3: Run Python Script (AI Analysis)
```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
python import_clay_builtwith.py "C:\Users\Owner\Downloads\builtwith_enrichment_2025-12-11.csv"
```

**This script:**
- Reads Clay CSV with raw technology lists
- Runs Claude Haiku AI analysis on each lead
- Extracts pain points, scores, classifications
- Updates Supabase with enriched data
- **Cost:** ~$0.001 per lead

### Step 4: Continue Pipeline
Leads are now enriched and ready for Phase 2 intelligence gathering

## Future Workflow Option 1: Server-Side Import

**Add a backend API endpoint** that:
1. Accepts Clay CSV upload via dashboard
2. Runs AI analysis server-side
3. Updates Supabase
4. Returns results to dashboard

**Pros:**
- No command line needed
- All in dashboard UI
- Progress tracking in browser

**Cons:**
- Requires Flask/FastAPI backend
- More complex deployment

**Implementation Estimate:** 2-3 hours

## Future Workflow Option 2: Client-Side AI (Not Recommended)

**Run AI analysis in browser** using Anthropic API directly from JavaScript

**Pros:**
- No backend needed
- Fully client-side

**Cons:**
- ❌ Exposes API key in browser
- ❌ Slower (sequential processing)
- ❌ Browser API rate limits

**Status:** Not recommended for production

## Recommended: Keep Current Python Script Approach

### Why?
1. ✅ **Secure**: API keys stay server-side
2. ✅ **Fast**: Async processing, handle 100+ leads efficiently
3. ✅ **Simple**: One command, handles everything
4. ✅ **Logging**: Clear console output and error tracking
5. ✅ **Cost tracking**: Shows exactly what was spent

### Usage:
```powershell
# Navigate to project
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"

# Run import
python import_clay_builtwith.py "C:\Users\Owner\Downloads\builtwith_enrichment_2025-12-11.csv"

# Expected output:
# 🚀 CLAY BUILTWITH IMPORT STARTING
# 📂 Reading CSV: ...
# ✅ Found 105 rows in CSV
# 🔄 Processing 105 leads...
# [1/105] 🔍 Processing: Hart Electrical
#    🤖 Running Claude Haiku analysis...
#    ✅ AI Analysis Complete: Tech Score: 3/10, Website Type: DIY Builder
#    💾 Saved to Supabase
# ...
# 📊 IMPORT SUMMARY
# Total Rows:     105
# Processed:      103 ✅
# 💰 Estimated Cost: $0.1030
```

## Dashboard Update Needed

**Update dashboard button to clarify workflow:**

Change "Import Enriched CSV" button to show instructions:
- Change text to "View Import Instructions"
- On click, show modal with:
  1. Download Clay CSV
  2. Run Python script command
  3. Verify in dashboard

**Alternatively:**
- Keep "Export CSV for Clay" as-is
- Remove "Import Enriched CSV" button
- Add "Refresh Queue" button (already exists)
- After running Python script, user clicks "Refresh" to see updated counts

## What Gets Updated in Supabase

When `import_clay_builtwith.py` runs, it updates these fields per lead:

### Raw Data
- `tech_raw_list` - Full comma-separated technology list
- `tech_count` - Number of technologies

### AI Analysis
- `tech_analysis` - Full JSONB response from Claude
- `tech_stack_ai_score` - AI score 0-10
- `website_type` - "DIY Builder", "Professional", etc.
- `cms_platform_ai` - Detected CMS

### Boolean Flags
- `has_gtm` - Has Google Tag Manager
- `has_ga4` - Has Google Analytics 4
- `has_crm` - Has CRM system
- `has_booking_system` - Has booking system
- `has_email_marketing` - Has email marketing
- `has_lead_capture` - Has lead capture forms

### Metadata
- `tech_analysis_model` - "claude-3-5-haiku-20241022"
- `tech_analysis_at` - Timestamp
- `updated_at` - Updated timestamp

## Verification

After running the Python script:

### Check Supabase Directly
```sql
SELECT
  business_name,
  tech_count,
  tech_stack_ai_score,
  website_type,
  has_gtm,
  has_ga4,
  tech_analysis_at
FROM leads
WHERE tech_analysis_at IS NOT NULL
ORDER BY tech_analysis_at DESC
LIMIT 10;
```

### Or Check Dashboard
1. Refresh dashboard
2. "BuiltWith Queue" count should decrease
3. "Completed" count should increase

---

**Last Updated:** 2025-12-11
**Status:** Python script approach is production-ready
**Next Steps:** Test with real Clay CSV (105 leads)
