# Zap 2: Clay Export Automation
## Automatic Lead Enrichment Queue Management

**Purpose:** Monitor enrichment queues, automatically export to Clay when threshold reached, poll for completion, and import results back to Supabase.

**Priority:** HIGH (Replaces manual CSV export/import workflow)

---

## 📋 Zap Configuration

### Basic Info
- **Name:** Rise Local - Clay Export Automation
- **Folder:** Rise Local / Phase 1
- **Status:** Active
- **Description:** Automates Clay enrichment workflow end-to-end

---

## 🔧 Zap Steps (Part A: Export Trigger)

### Step 1: Schedule by Zapier (Trigger)

**Configuration:**
- **Frequency:** Every hour
- **Time:** On the hour (:00)

**Purpose:** Check enrichment queue regularly for pending leads.

---

### Step 2: HTTP GET - Check Queue Count

**Method:** GET

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/enrichment_queue`

**Headers:**
```json
{
  "apikey": "{{process.env.SUPABASE_SERVICE_KEY}}",
  "Authorization": "Bearer {{process.env.SUPABASE_SERVICE_KEY}}",
  "Content-Type": "application/json"
}
```

**Query Parameters:**
```
select=count
queue_type=eq.builtwith
status=eq.pending
```

**Output:**
```json
{
  "count": 47
}
```

---

### Step 3: Filter by Zapier - Check Threshold

**Configuration:**
- **Continue Only If:** `count` (Number) Greater than `25`

**Purpose:** Only export when we have enough leads (minimum 25 for efficiency).

---

### Step 4: HTTP GET - Fetch Leads for Export

**Method:** GET

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/enrichment_queue`

**Headers:** Same as Step 2

**Query Parameters:**
```
select=lead_id,business_name,website_url
queue_type=eq.builtwith
status=eq.pending
limit=100
```

**Output:**
```json
[
  {
    "lead_id": "lead-abc-123",
    "business_name": "Austin Electric",
    "website_url": "https://austinelectric.com"
  },
  ...
]
```

---

### Step 5: Code by Zapier - Format Clay CSV

**Language:** Python 3.9

**Input Data:**
- `leads`: `{{Step 4: all leads as JSON}}`

**Code:**
```python
import csv
import io
import json
from datetime import datetime

# Parse leads
leads = json.loads(input_data.get('leads', '[]'))

# Create CSV in memory
output = io.StringIO()
writer = csv.DictWriter(output, fieldnames=['lead_id', 'business_name', 'website'])

# Write header
writer.writeheader()

# Write rows
for lead in leads:
    writer.writerow({
        'lead_id': lead['lead_id'],
        'business_name': lead['business_name'],
        'website': lead['website_url']
    })

csv_content = output.getvalue()
output.close()

# Generate export metadata
export_id = f"builtwith_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
export_filename = f"{export_id}.csv"

return {
    'csv_content': csv_content,
    'export_id': export_id,
    'export_filename': export_filename,
    'lead_count': len(leads),
    'lead_ids': [lead['lead_id'] for lead in leads]
}
```

**Output:**
```json
{
  "csv_content": "lead_id,business_name,website\nlead-abc-123,Austin Electric,https://austinelectric.com\n...",
  "export_id": "builtwith_20251222_100000",
  "export_filename": "builtwith_20251222_100000.csv",
  "lead_count": 47,
  "lead_ids": ["lead-abc-123", ...]
}
```

---

### Step 6: HTTP POST - Upload to Clay

**Method:** POST

**URL:** `https://api.clay.com/v1/tables/{{process.env.CLAY_BUILTWITH_TABLE_ID}}/import`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.CLAY_API_KEY}}",
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "import_type": "csv",
  "csv_content": "{{Step 5: csv_content}}",
  "filename": "{{Step 5: export_filename}}",
  "skip_duplicates": true,
  "auto_enrich": true
}
```

**Output:**
```json
{
  "import_id": "imp_xyz789",
  "table_id": "tbl_builtwith",
  "status": "processing",
  "rows_imported": 47
}
```

---

### Step 7: Create Agent Job Record

**Action:** Create Record in Tables

**Table:** agent_jobs

**Fields:**
- `id` → Generate UUID
- `job_type` → "enrichment"
- `status` → "running"
- `initiated_by` → "zapier_clay_exporter"
- `initiated_by_type` → "zapier_agent"
- `parameters` → JSON:
  ```json
  {
    "export_id": "{{Step 5: export_id}}",
    "clay_import_id": "{{Step 6: import_id}}",
    "lead_count": {{Step 5: lead_count}},
    "queue_type": "builtwith"
  }
  ```
- `created_at` → NOW()
- `started_at` → NOW()

---

### Step 8: Update Enrichment Queue Status

**Method:** PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/enrichment_queue`

**Headers:** Same as Step 2

**Query Parameters:**
```
lead_id=in.({{Step 5: lead_ids joined by comma}})
```

**Body:**
```json
{
  "status": "exported",
  "exported_at": "{{NOW}}",
  "export_id": "{{Step 5: export_id}}"
}
```

---

## 🔧 Zap Steps (Part B: Import Monitor - Separate Zap)

**Name:** Rise Local - Clay Import Monitor

### Step 1: Schedule by Zapier

**Frequency:** Every 5 minutes

---

### Step 2: HTTP GET - Find Running Imports

**Method:** GET

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/agent_jobs`

**Query:**
```
select=*
job_type=eq.enrichment
status=eq.running
```

---

### Step 3: Loop by Zapier

**Loop Over:** Each job from Step 2

---

### Step 4: HTTP GET - Check Clay Import Status

**Method:** GET

**URL:** `https://api.clay.com/v1/imports/{{Loop Item: parameters.clay_import_id}}`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.CLAY_API_KEY}}"
}
```

**Output:**
```json
{
  "import_id": "imp_xyz789",
  "status": "completed",
  "rows_processed": 47,
  "rows_succeeded": 45,
  "rows_failed": 2,
  "completed_at": "2025-12-22T10:45:00Z"
}
```

---

### Step 5: Filter - Only if Completed

**Condition:** `status` equals "completed"

---

### Step 6: HTTP GET - Fetch Enriched Data from Clay

**Method:** GET

**URL:** `https://api.clay.com/v1/tables/{{process.env.CLAY_BUILTWITH_TABLE_ID}}/records`

**Query Parameters:**
```
import_id={{Loop Item: parameters.clay_import_id}}
limit=100
```

**Output:**
```json
{
  "records": [
    {
      "lead_id": "lead-abc-123",
      "business_name": "Austin Electric",
      "tech_stack": ["WordPress", "Google Analytics", "Stripe"],
      "has_crm": true,
      "has_booking": false,
      "cms_detected": "WordPress"
    },
    ...
  ]
}
```

---

### Step 7: Code by Zapier - Transform Clay Data

**Language:** Python 3.9

**Code:**
```python
import json

# Parse enriched records
records = json.loads(input_data.get('records', '[]'))

# Transform to Supabase format
updates = []

for record in records:
    update = {
        'lead_id': record['lead_id'],
        'tech_stack': json.dumps(record.get('tech_stack', [])),
        'has_crm': record.get('has_crm', False),
        'has_booking': record.get('has_booking', False),
        'cms_detected': record.get('cms_detected'),
        'phase_1_completed_at': datetime.utcnow().isoformat()
    }
    updates.append(update)

return {
    'updates': updates,
    'update_count': len(updates)
}
```

---

### Step 8: HTTP PATCH - Update Leads in Supabase

**Method:** PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

**Body:** Use Looping to update each lead individually, or use bulk upsert.

---

### Step 9: Update Agent Job - Mark Complete

**Action:** Update Record in Tables

**Table:** agent_jobs

**Find By:** `id` equals `{{Loop Item: id}}`

**Update:**
- `status` → "completed"
- `completed_at` → NOW()
- `results` → JSON:
  ```json
  {
    "rows_processed": {{Step 4: rows_processed}},
    "rows_succeeded": {{Step 4: rows_succeeded}},
    "rows_failed": {{Step 4: rows_failed}}
  }
  ```

---

### Step 10: Update Enrichment Queue - Mark Ready

**Method:** PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/enrichment_queue`

**Query:**
```
export_id=eq.{{Loop Item: parameters.export_id}}
```

**Body:**
```json
{
  "status": "ready",
  "imported_at": "{{NOW}}"
}
```

---

## 📧 Email Notification (Step 11 - Optional)

**Action:** Email by Zapier

**To:** Your email

**Subject:** Clay Enrichment Complete - {{Step 4: rows_succeeded}} Leads Ready

**Body:**
```
Hi,

Clay enrichment job completed successfully!

Export ID: {{Loop Item: parameters.export_id}}
Leads Processed: {{Step 4: rows_processed}}
Successfully Enriched: {{Step 4: rows_succeeded}}
Failed: {{Step 4: rows_failed}}

Next: These leads are now ready for qualification.

View in dashboard: https://dashboard.riselocal.com/enrichment/{{Loop Item: parameters.export_id}}
```

---

## 🧪 Testing Procedure

### Test 1: Export Trigger

1. Create 30+ test leads in enrichment_queue (status='pending')
2. Trigger Zap manually
3. Verify CSV generated correctly
4. Check Clay dashboard for import job
5. Verify enrichment_queue updated to 'exported'

---

### Test 2: Import Monitor

1. Wait for Clay to complete enrichment (~5-10 minutes)
2. Monitor Zap runs every 5 minutes
3. Verify status check succeeds
4. Check Supabase for enriched data
5. Verify enrichment_queue updated to 'ready'
6. Verify agent_jobs status='completed'

---

### Test 3: Error Handling

1. Send invalid CSV to Clay (missing columns)
2. Verify Zap handles error gracefully
3. Check agent_jobs marked as 'failed'
4. Verify error_message populated
5. Check audit_log for error entry

---

## 💰 Cost Savings

**Before (Manual):**
- 30 minutes per export/import cycle
- 2 cycles per day = 1 hour daily
- 5 hours per week = 20 hours per month
- **Cost:** 20 hours × $50/hr = $1,000/month

**After (Automated):**
- Fully automated
- No manual intervention
- **Cost:** $0 (included in Zapier plan)

**Savings:** $1,000/month = $12,000/year

---

## 🔧 Environment Variables

```bash
SUPABASE_URL=https://jitawzicdwgbhatvjblh.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
CLAY_API_KEY=your-clay-api-key
CLAY_BUILTWITH_TABLE_ID=tbl_your_builtwith_table
CLAY_CONTACT_TABLE_ID=tbl_your_contact_table
```

---

## 📊 Success Metrics

- **Export Frequency:** 3-5 times per day
- **Average Export Size:** 30-50 leads
- **Success Rate:** >95% enrichment success
- **Time to Complete:** <15 minutes export → import
- **Manual Intervention:** 0 (fully automated)

---

## 🐛 Troubleshooting

### Clay API Rate Limit

**Fix:** Check rate_limits table, add delay between batches

### Duplicate Exports

**Fix:** Add deduplication check, query recent agent_jobs

### Import Never Completes

**Fix:** Check Clay dashboard, increase polling interval to 10 minutes

---

**Created:** December 22, 2025
**Status:** Ready to implement
**Estimated Setup Time:** 1 hour (2 Zaps)
**Priority:** HIGH
**ROI:** $12,000/year savings
