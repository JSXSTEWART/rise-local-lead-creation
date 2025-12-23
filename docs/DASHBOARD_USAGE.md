# Dashboard Usage Guide

## Overview

The dashboard tracks enrichment progress and provides CSV export/import functionality for Clay integration.

**URL:** `http://localhost:8080`

---

## Current Status (After Fix)

### BuiltWith Queue
- **Pending:** 2 leads (with websites, not yet enriched)
- **Completed:** 79 leads (tech analysis done)

### Clay Waterfall Queue
- **Pending:** 79 leads (ready for contact enrichment)
- **Completed:** 0 leads (no contact info yet)

---

## Enrichment Cards

### 1. BuiltWith Enrichment Card

**Purpose:** Track leads needing tech stack enrichment via Clay

**Buttons:**
- **"Refresh Queue"** - Reload counts from database
- **"Export CSV for Clay"** - Downloads CSV for Clay BuiltWith import
- **"Import Enriched CSV"** - Upload enriched results from Clay back to database

**Workflow:**
1. Click "Export CSV for Clay"
2. Import CSV to Clay BuiltWith table
3. Run Clay enrichment
4. Export enriched CSV from Clay
5. Click "Import Enriched CSV" and select file
6. Dashboard updates lead counts

### 2. Clay Waterfall Card

**Purpose:** Track qualified leads needing contact enrichment

**Buttons:**
- **"Refresh Queue"** - Reload counts from database
- **"Export CSV for Clay"** - Downloads CSV for Clay Waterfall import
- **"Import Enriched CSV"** - Upload enriched results from Clay back to database

**Workflow:**
1. Click "Export CSV for Clay"
2. Import CSV to Clay Waterfall table
3. Run Clay contact enrichment
4. Export enriched CSV from Clay
5. Click "Import Enriched CSV" and select file
6. Dashboard updates lead counts

---

## Recent CSV Exports Table

**Location:** Below the enrichment cards

**Columns:**
- **Date:** When the export was created
- **Type:** "BuiltWith" or "Waterfall"
- **Leads:** Number of leads in the export
- **Status:** "ready", "imported", or "processing"
- **Action:** "Mark Imported" button

**How It Works:**
1. When you export a CSV, a new row appears with status "ready"
2. After you upload to Clay and complete enrichment, click "Mark Imported"
3. Status changes to "imported" ✅
4. Keeps last 20 exports in the log

**Example Log:**
```
| Date | Type | Leads | Status | Action |
|------|------|-------|--------|--------|
| 12/11/2025 2:30 PM | Waterfall | 79 | ready | Mark Imported |
| 12/11/2025 10:15 AM | BuiltWith | 79 | imported | Done ✅ |
```

---

## Email Notifications

**Location:** Settings panel at bottom

**How to Enable:**
1. Check "Enable Email Notifications"
2. Enter your email address
3. Set threshold for each queue (default: 25 leads)
4. Save settings

**When Emails Are Sent:**
1. **Queue Threshold Reached:** When pending leads ≥ threshold
2. **CSV Export:** When you export a CSV for Clay
3. **Import Complete:** When you import enriched data back

**Email Contains:**
- Export type (BuiltWith or Waterfall)
- Number of leads
- Filename
- Link to dashboard

---

## Step-by-Step: BuiltWith Enrichment

### ✅ Already Complete (79 leads)

1. ✅ Export CSV from dashboard → `builtwith_enrichment_2025-12-11.csv`
2. ✅ Import to Clay BuiltWith table
3. ✅ Run Clay enrichment
4. ✅ Export from Clay with tech data
5. ✅ Run Python script: `python import_clay_builtwith.py <csv_file>`
6. ✅ AI analysis complete with Claude Haiku
7. ✅ All 79 leads enriched

**Result:** 79 leads with tech_analysis, pain scores, classifications

---

## Step-by-Step: Waterfall Enrichment

### ⏳ Ready to Start (79 leads pending)

#### Step 1: Export from Dashboard
```
1. Open http://localhost:8080
2. Clay Waterfall card → Click "Export CSV for Clay"
3. File downloads: waterfall_enrichment_2025-12-11.csv
4. New row appears in exports table with status "ready"
```

#### Step 2: Upload to Clay
```
1. Open Clay dashboard
2. Go to Waterfall contact enrichment table
3. Import CSV
4. Map columns: lead_id, business_name, website, etc.
```

#### Step 3: Run Clay Enrichment
```
1. Configure waterfall providers in Clay
2. Run enrichment (costs $0.10-0.50 per lead)
3. Wait for completion (check progress in Clay)
```

#### Step 4: Export from Clay
```
1. Clay completes enrichment
2. Export enriched CSV
3. CSV now includes:
   - owner_email
   - owner_first_name
   - owner_last_name
   - owner_linkedin_url
   - verified_email
```

#### Step 5: Import Back to Dashboard
```
1. Dashboard → Clay Waterfall card → "Import Enriched CSV"
2. Select enriched CSV from Clay
3. Dashboard processes and updates Supabase
4. Waterfall Queue count decreases
5. Waterfall Completed count increases
```

#### Step 6: Mark as Complete
```
1. Go to "Recent CSV Exports" table
2. Find the Waterfall export row
3. Click "Mark Imported"
4. Status changes from "ready" to "imported" ✅
```

**Result:** 79 leads with contact info, ready for email generation

---

## Understanding the Counts

### BuiltWith Queue

**Pending Count Logic:**
```sql
SELECT COUNT(*) FROM leads
WHERE website IS NOT NULL
  AND tech_analysis_at IS NULL;
```
= Leads with websites that haven't been enriched yet

**Completed Count Logic:**
```sql
SELECT COUNT(*) FROM leads
WHERE tech_analysis_at IS NOT NULL;
```
= Leads with tech enrichment complete

### Waterfall Queue

**Pending Count Logic:**
```sql
SELECT COUNT(*) FROM leads
WHERE tech_analysis_at IS NOT NULL
  AND phase_3_completed_at IS NOT NULL
  AND qualification_status = 'qualified'
  AND owner_email IS NULL;
```
= Qualified leads without contact info yet

**Completed Count Logic:**
```sql
SELECT COUNT(*) FROM leads
WHERE owner_email IS NOT NULL;
```
= Leads with contact enrichment complete

---

## Troubleshooting

### "Pending count seems wrong"
- Click "Refresh Queue" button
- Check browser console for errors (F12)
- Verify Supabase connection in `dashboard/supabase.js`

### "Export button does nothing"
- Check browser console for errors
- Verify leads exist in database
- Check that query returns results

### "Import doesn't update counts"
- Verify CSV format matches expected columns
- Check Supabase service key is valid
- Click "Refresh Queue" after import
- Check console for error messages

### "Email notifications not working"
- Verify email address is saved in settings
- Check Supabase Edge Function is deployed
- Look for email delivery errors in Supabase logs

---

## Technical Details

### Files
- `dashboard/index.html` - UI layout
- `dashboard/app.js` - Business logic (lines 1367-1650 handle queues)
- `dashboard/styles.css` - Styling
- `dashboard/supabase.js` - Database connection

### Data Flow

**Export:**
```
User clicks "Export"
→ Query Supabase for pending leads
→ Generate CSV
→ Download to browser
→ Add row to exports table
→ Send email notification (if enabled)
→ Save export record to localStorage
```

**Import:**
```
User selects CSV file
→ Parse CSV rows
→ Match columns to database fields
→ Update Supabase via REST API
→ Show success/error toast
→ Refresh queue counts
→ Update exports table
```

---

## Next Steps After Waterfall

Once Waterfall enrichment is complete (79 leads with contact info):

1. **Phase 4:** Email Generation
   - AI generates personalized emails
   - Uses pain points + tech analysis + contact context
   - RAG retrieval for best practices

2. **Phase 5:** Outreach
   - Send via Instantly.ai or HeyReach
   - Track opens, clicks, replies
   - Follow-up sequences

3. **Phase 6:** CRM Integration
   - Export qualified leads to GHL/HubSpot
   - Track deal pipeline
   - Revenue attribution

---

**Last Updated:** 2025-12-11
**Status:** BuiltWith complete (79), Waterfall ready (79 pending)
**Next Action:** Export Waterfall CSV from dashboard
