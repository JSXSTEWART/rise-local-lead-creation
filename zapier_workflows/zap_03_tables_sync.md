# Zap 3: Zapier Tables ↔ Supabase Sync
## Bidirectional Data Synchronization

**Purpose:** Keep Zapier Tables and Supabase in sync bidirectionally for the 4 agent orchestration tables.

**Priority:** CRITICAL (Foundation for all agent workflows)

---

## 📋 Overview

This is actually **8 separate Zaps** (4 tables × 2 directions):

### Direction A: Zapier Tables → Supabase (4 Zaps)
- Zapier agents write to Tables first (fast)
- Webhook triggers async sync to Supabase (durable)
- 30-second lag acceptable

### Direction B: Supabase → Zapier Tables (4 Zaps)
- Claude agents write to Supabase directly
- Webhook triggers sync to Zapier Tables
- Enables Zapier workflows to react to Claude decisions

---

## 🔄 Sync Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ WRITE PATH 1: Zapier Agent → Tables → Supabase              │
│ - Zapier writes to Tables (<1ms)                            │
│ - Webhook on record created → POST to Supabase API          │
│ - Conflict resolution: UPSERT with updated_at comparison    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WRITE PATH 2: Claude Agent → Supabase → Tables              │
│ - Claude writes to Supabase directly (MCP tools)            │
│ - PostgreSQL trigger → Supabase webhook                     │
│ - Webhook → Zapier catches → UPSERT to Tables               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Zap 3A: agent_jobs (Tables → Supabase)

### Step 1: Tables - New Record in agent_jobs

**Trigger:** New Record Created in Table

**Table:** agent_jobs

**Output:**
```json
{
  "id": "abc-123-def-456",
  "job_type": "discovery",
  "status": "queued",
  "initiated_by": "zapier_discovery_coordinator",
  "initiated_by_type": "zapier_agent",
  "parameters": "{\"metro\": \"Austin\", \"radius\": 15}",
  "created_at": "2025-12-22T10:00:00Z"
}
```

---

### Step 2: Code by Zapier - Parse JSON Fields

**Language:** Python 3.9

**Input:**
- `record`: `{{Step 1: entire record}}`

**Code:**
```python
import json
from datetime import datetime

record = input_data.get('record', {})

# Parse JSON fields
parameters = json.loads(record.get('parameters', '{}')) if record.get('parameters') else None
results = json.loads(record.get('results', '{}')) if record.get('results') else None

# Format timestamps for PostgreSQL
def format_timestamp(ts):
    if not ts:
        return None
    # Handle various timestamp formats
    if isinstance(ts, str):
        return ts
    return ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

return {
    'id': record.get('id'),
    'job_type': record.get('job_type'),
    'status': record.get('status'),
    'initiated_by': record.get('initiated_by'),
    'initiated_by_type': record.get('initiated_by_type'),
    'parameters': parameters,
    'results': results,
    'error_message': record.get('error_message'),
    'retry_count': record.get('retry_count', 0),
    'created_at': format_timestamp(record.get('created_at')),
    'started_at': format_timestamp(record.get('started_at')),
    'completed_at': format_timestamp(record.get('completed_at')),
    'updated_at': format_timestamp(record.get('updated_at'))
}
```

---

### Step 3: HTTP POST - Upsert to Supabase

**Method:** POST

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/agent_jobs`

**Headers:**
```json
{
  "apikey": "{{process.env.SUPABASE_SERVICE_KEY}}",
  "Authorization": "Bearer {{process.env.SUPABASE_SERVICE_KEY}}",
  "Content-Type": "application/json",
  "Prefer": "resolution=merge-duplicates"
}
```

**Body:**
```json
{
  "id": "{{Step 2: id}}",
  "job_type": "{{Step 2: job_type}}",
  "status": "{{Step 2: status}}",
  "initiated_by": "{{Step 2: initiated_by}}",
  "initiated_by_type": "{{Step 2: initiated_by_type}}",
  "parameters": {{Step 2: parameters}},
  "results": {{Step 2: results}},
  "error_message": "{{Step 2: error_message}}",
  "retry_count": {{Step 2: retry_count}},
  "created_at": "{{Step 2: created_at}}",
  "started_at": "{{Step 2: started_at}}",
  "completed_at": "{{Step 2: completed_at}}",
  "updated_at": "{{Step 2: updated_at}}"
}
```

**Note:** `Prefer: resolution=merge-duplicates` enables UPSERT behavior

---

### Step 4: Filter by Zapier - Only if Success

**Continue Only If:** `{{Step 3: status_code}}` equals `201` OR `200`

---

### Step 5: Create Audit Log Entry

**Action:** Create Record in Tables

**Table:** audit_log

**Fields:**
- `timestamp` → NOW()
- `actor` → `{{Step 2: initiated_by}}`
- `actor_type` → `zapier_sync`
- `action` → `agent_job_synced`
- `resource_type` → `job`
- `resource_id` → `{{Step 2: id}}`
- `metadata` → `{"sync_direction": "tables_to_supabase", "job_type": "{{Step 2: job_type}}"}`
- `severity` → `debug`

---

## 🔧 Zap 3B: agent_jobs (Supabase → Tables)

### Step 1: Webhooks by Zapier

**Trigger:** Catch Hook

**Webhook URL:** `https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/`

**Expected Payload:** (From Supabase webhook)
```json
{
  "type": "INSERT",
  "table": "agent_jobs",
  "record": {
    "id": "abc-123-def-456",
    "job_type": "qualification",
    "status": "queued",
    "initiated_by": "claude_qualifier",
    "initiated_by_type": "claude_agent",
    "parameters": {"lead_id": "lead-xyz-789"},
    "created_at": "2025-12-22T10:05:00Z"
  },
  "old_record": null
}
```

---

### Step 2: Filter - Only Process INSERT and UPDATE

**Continue Only If:** `{{Step 1: type}}` is in `INSERT,UPDATE`

---

### Step 3: Code by Zapier - Format for Zapier Tables

**Code:**
```python
import json

webhook_data = input_data.get('webhook', {})
record = webhook_data.get('record', {})

# Stringify JSON fields for Zapier Tables
parameters_str = json.dumps(record.get('parameters', {})) if record.get('parameters') else None
results_str = json.dumps(record.get('results', {})) if record.get('results') else None

return {
    'id': record.get('id'),
    'job_type': record.get('job_type'),
    'status': record.get('status'),
    'initiated_by': record.get('initiated_by'),
    'initiated_by_type': record.get('initiated_by_type'),
    'parameters': parameters_str,
    'results': results_str,
    'error_message': record.get('error_message'),
    'retry_count': record.get('retry_count', 0),
    'created_at': record.get('created_at'),
    'started_at': record.get('started_at'),
    'completed_at': record.get('completed_at'),
    'updated_at': record.get('updated_at')
}
```

---

### Step 4: Tables - Find or Create Record

**Action:** Find or Create Record in Table

**Table:** agent_jobs

**Search Field:** `id` equals `{{Step 3: id}}`

**Create If Not Found:** Yes

**Fields to Update:**
- All fields from Step 3

---

## 🔧 Zap 3C: agent_decisions (Tables → Supabase)

### Steps 1-5: Same pattern as Zap 3A

**Key Differences:**

**Step 2 Code:**
```python
# Parse metadata JSONB field
metadata = json.loads(record.get('metadata', '{}')) if record.get('metadata') else None

return {
    'id': record.get('id'),
    'lead_id': record.get('lead_id'),
    'decision_type': record.get('decision_type'),
    'agent_name': record.get('agent_name'),
    'agent_type': record.get('agent_type'),
    'decision': record.get('decision'),
    'confidence': float(record.get('confidence', 0.0)),
    'reasoning': record.get('reasoning'),
    'metadata': metadata,
    'overridden_by': record.get('overridden_by'),
    'override_reason': record.get('override_reason'),
    'overridden_at': format_timestamp(record.get('overridden_at')),
    'created_at': format_timestamp(record.get('created_at'))
}
```

**Step 3 URL:** `{{process.env.SUPABASE_URL}}/rest/v1/agent_decisions`

---

## 🔧 Zap 3D: agent_decisions (Supabase → Tables)

Same pattern as Zap 3B, adjusted for agent_decisions schema.

---

## 🔧 Zap 3E: audit_log (Tables → Supabase)

### Important: One-Way Sync Only

**Audit logs should only sync Tables → Supabase** (append-only compliance)

### Steps 1-3: Same pattern as Zap 3A

**Step 2 Code:**
```python
metadata = json.loads(record.get('metadata', '{}')) if record.get('metadata') else None
compliance_tags = record.get('compliance_tags', '').split(',') if record.get('compliance_tags') else []

return {
    'timestamp': format_timestamp(record.get('timestamp')),
    'actor': record.get('actor'),
    'actor_type': record.get('actor_type'),
    'action': record.get('action'),
    'resource_type': record.get('resource_type'),
    'resource_id': record.get('resource_id'),
    'metadata': metadata,
    'ip_address': record.get('ip_address'),
    'user_agent': record.get('user_agent'),
    'session_id': record.get('session_id'),
    'severity': record.get('severity', 'info'),
    'data_classification': record.get('data_classification'),
    'compliance_tags': compliance_tags,
    'retention_days': int(record.get('retention_days', 2555))
}
```

**Step 3: Use POST (not UPSERT)** - audit logs are append-only

---

## 🔧 Zap 3F: rate_limits (Tables → Supabase)

### Steps 1-5: Same pattern as Zap 3A

**Step 2 Code:**
```python
metadata = json.loads(record.get('metadata', '{}')) if record.get('metadata') else None

return {
    'id': record.get('id'),
    'service_name': record.get('service_name'),
    'window_start': format_timestamp(record.get('window_start')),
    'request_count': int(record.get('request_count', 0)),
    'quota_limit': int(record.get('quota_limit')),
    'reset_at': format_timestamp(record.get('reset_at')),
    'metadata': metadata,
    'created_at': format_timestamp(record.get('created_at')),
    'updated_at': format_timestamp(record.get('updated_at'))
}
```

---

## 🔧 Zap 3G: rate_limits (Supabase → Tables)

Same pattern as Zap 3B, adjusted for rate_limits schema.

---

## 🔧 Conflict Resolution Strategy

### Scenario 1: Simultaneous Writes to Same Record

**Problem:** Zapier agent writes to Tables, Claude agent writes to Supabase at same time

**Resolution:**
```python
# In sync Zap, compare timestamps before update
def should_update(supabase_updated_at, tables_updated_at):
    """
    Only update if source is newer than destination
    """
    if not tables_updated_at:
        return True  # No existing record, always update

    # Parse timestamps
    source_time = datetime.fromisoformat(supabase_updated_at)
    dest_time = datetime.fromisoformat(tables_updated_at)

    return source_time > dest_time

# In Zap Step 3 (before upsert)
if should_update(source_updated_at, destination_updated_at):
    # Proceed with update
else:
    # Skip update, destination is newer
    # Log to audit_log: sync_skipped_stale_data
```

---

### Scenario 2: Sync Loop Prevention

**Problem:** Tables → Supabase → Tables infinite loop

**Resolution:**

**Add to webhook payloads:**
```json
{
  "sync_source": "zapier_tables",
  "sync_id": "unique-sync-operation-id"
}
```

**In sync Zaps, add filter:**
```
Continue Only If:
  {{metadata.sync_source}} does not equal "zapier_tables"
  OR
  {{metadata.sync_source}} is empty
```

This prevents re-syncing records that came from the same source.

---

## 🧪 Testing Procedure

### Test 1: Tables → Supabase Sync

```bash
# 1. Create record in Zapier Tables (via API or manually)
curl -X POST https://tables.zapier.com/api/v1/tables/YOUR_TABLE_ID/records \
  -H "Authorization: Bearer YOUR_ZAPIER_API_KEY" \
  -d '{
    "id": "test-job-001",
    "job_type": "discovery",
    "status": "queued"
  }'

# 2. Wait 5 seconds for sync

# 3. Query Supabase to verify record exists
curl "{{SUPABASE_URL}}/rest/v1/agent_jobs?id=eq.test-job-001" \
  -H "apikey: {{SUPABASE_SERVICE_KEY}}"

# Expected: Record found with matching data
```

---

### Test 2: Supabase → Tables Sync

```bash
# 1. Insert record in Supabase (simulates Claude agent)
curl -X POST "{{SUPABASE_URL}}/rest/v1/agent_decisions" \
  -H "apikey: {{SUPABASE_SERVICE_KEY}}" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-decision-001",
    "lead_id": "lead-abc-123",
    "decision_type": "qualification",
    "agent_name": "claude_qualifier",
    "decision": "qualified",
    "confidence": 0.87
  }'

# 2. Wait for Supabase webhook to fire (check webhook logs)

# 3. Query Zapier Tables to verify
# Go to https://tables.zapier.com, check agent_decisions table

# Expected: Record found with confidence = 0.87
```

---

### Test 3: Conflict Resolution

```bash
# 1. Create record in both systems simultaneously
# Tables:
curl -X POST https://tables.zapier.com/... -d '{"id": "conflict-test", "status": "queued", "updated_at": "2025-12-22T10:00:00Z"}'

# Supabase (1 second later):
curl -X POST {{SUPABASE_URL}}/rest/v1/agent_jobs -d '{"id": "conflict-test", "status": "running", "updated_at": "2025-12-22T10:00:01Z"}'

# 2. Wait for both syncs to complete

# 3. Check final state in both systems
# Expected: Both should have status="running" (Supabase timestamp is newer)
```

---

### Test 4: Sync Loop Prevention

```bash
# 1. Manually add sync_source to metadata
# 2. Trigger sync Zap
# 3. Verify it stops at filter (does not create infinite loop)
# 4. Check Zap History for "Filtered" status
```

---

## 🔧 Supabase Webhook Configuration

### Setup Webhooks for Supabase → Zapier Sync

**Go to:** Supabase Dashboard → Database → Webhooks

**Create 4 webhooks (one per table):**

#### Webhook 1: agent_jobs

- **Name:** agent_jobs_to_zapier
- **Table:** agent_jobs
- **Events:** INSERT, UPDATE
- **Type:** HTTP
- **Method:** POST
- **URL:** `https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/agent_jobs`
- **Headers:**
  ```json
  {
    "Content-Type": "application/json"
  }
  ```

#### Webhook 2: agent_decisions

- **Name:** agent_decisions_to_zapier
- **Table:** agent_decisions
- **Events:** INSERT, UPDATE
- **URL:** `https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/agent_decisions`

#### Webhook 3: rate_limits

- **Name:** rate_limits_to_zapier
- **Table:** rate_limits
- **Events:** INSERT, UPDATE
- **URL:** `https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/rate_limits`

**Note:** No webhook for audit_log (one-way sync only)

---

## 📊 Monitoring & Alerts

### Metrics to Track

```sql
-- Sync Lag (how long does sync take?)
SELECT
  action,
  AVG(EXTRACT(EPOCH FROM (timestamp - (metadata->>'source_timestamp')::timestamp))) as avg_lag_seconds
FROM audit_log
WHERE action LIKE '%_synced'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY action;

-- Expected: <5 seconds average lag
```

### Alert Conditions

**Alert 1: Sync Failure Rate > 5%**
```
Query: SELECT COUNT(*) FROM audit_log
WHERE action='sync_failed'
AND timestamp > NOW() - INTERVAL '1 hour'

If count > (total_syncs * 0.05), send Slack alert
```

**Alert 2: Sync Lag > 30 seconds**
```
If avg_lag_seconds > 30, send alert to #rise-pipeline
```

**Alert 3: Conflict Resolution Frequency**
```
If conflict_resolution_count > 10 per hour, investigate
```

---

## 🐛 Troubleshooting

### Issue 1: Sync Zap Not Triggering

**Symptom:** Create record in Tables, but never appears in Supabase

**Debug:**
1. Check Zap History → find the trigger
2. Check if record matches trigger filters
3. Verify webhook is enabled in Zapier Tables settings
4. Test trigger manually

**Fix:**
- Go to Zapier Tables → Settings → Webhooks
- Ensure "Trigger Zaps on record changes" is enabled
- Re-test the trigger in Zap editor

---

### Issue 2: Supabase Webhook Not Firing

**Symptom:** Insert in Supabase, but Zapier never catches webhook

**Debug:**
1. Go to Supabase Dashboard → Database → Webhooks
2. Check webhook logs for delivery failures
3. Test webhook with "Send Test Payload"

**Fix:**
- Verify webhook URL is correct Zapier catch hook
- Check Supabase webhook has correct events enabled (INSERT, UPDATE)
- Ensure no RLS policies blocking webhook trigger

---

### Issue 3: JSON Parsing Errors

**Symptom:** Zap fails at Step 2 with "invalid JSON"

**Debug:**
- Check Zap History → Step 2 error details
- Inspect raw input from Step 1

**Fix:**
```python
# Add error handling in Step 2 Code
try:
    parameters = json.loads(record.get('parameters', '{}'))
except json.JSONDecodeError:
    parameters = {}  # Default to empty dict
    # Log error to audit_log
```

---

### Issue 4: Timestamp Format Mismatch

**Symptom:** Supabase rejects timestamp: "invalid input syntax for type timestamp"

**Fix:**
```python
def format_timestamp(ts):
    if not ts:
        return None

    # Handle ISO 8601 format
    if isinstance(ts, str):
        # Remove timezone suffix if present
        ts = ts.replace('Z', '+00:00')
        return ts

    # Handle datetime object
    if hasattr(ts, 'isoformat'):
        return ts.isoformat()

    return str(ts)
```

---

## 💰 Cost Estimate

### Zapier Task Usage

**Assumptions:**
- 100 leads/day × 8 table writes per lead = 800 writes/day
- 800 writes × 2 (bidirectional sync) = 1,600 sync tasks/day
- 1,600 × 30 = 48,000 tasks/month

**Cost:**
- 48,000 tasks ÷ 1,000 = 48 batches
- 48 × $0.10 = $4.80/month

**Total Sync Cost:** $4.80/month

---

## 📁 File Locations

| File | Location |
|------|----------|
| This spec | `/zapier_workflows/zap_03_tables_sync.md` |
| Schema migrations | `/supabase/migrations/*.sql` |
| Python models | `/rise_pipeline/agent_models.py` |
| Supabase webhooks | Supabase Dashboard → Database → Webhooks |

---

## ✅ Setup Checklist

**Zapier Tables Setup:**
- [ ] Enable webhooks on all 4 tables
- [ ] Test webhook delivery (Tables → Zapier)

**Supabase Setup:**
- [ ] Create 3 webhooks (agent_jobs, agent_decisions, rate_limits)
- [ ] Test webhook delivery (Supabase → Zapier)
- [ ] Verify RLS policies don't block webhooks

**Zapier Zaps:**
- [ ] Create Zap 3A: agent_jobs (Tables → Supabase)
- [ ] Create Zap 3B: agent_jobs (Supabase → Tables)
- [ ] Create Zap 3C: agent_decisions (Tables → Supabase)
- [ ] Create Zap 3D: agent_decisions (Supabase → Tables)
- [ ] Create Zap 3E: audit_log (Tables → Supabase, one-way)
- [ ] Create Zap 3F: rate_limits (Tables → Supabase)
- [ ] Create Zap 3G: rate_limits (Supabase → Tables)

**Testing:**
- [ ] Test 1: Tables → Supabase sync (all 4 tables)
- [ ] Test 2: Supabase → Tables sync (3 tables)
- [ ] Test 3: Conflict resolution (simultaneous writes)
- [ ] Test 4: Sync loop prevention
- [ ] Test 5: Error handling (invalid JSON, bad timestamps)

---

**Created:** December 22, 2025
**Status:** Ready to implement
**Estimated Setup Time:** 3-4 hours (7 Zaps + webhooks)
**Priority:** CRITICAL (blocks all agent workflows)
**Monthly Cost:** $4.80

