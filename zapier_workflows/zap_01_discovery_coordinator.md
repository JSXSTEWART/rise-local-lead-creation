# Zap 1: Discovery Job Coordinator
## Automated Lead Discovery Scheduler

**Purpose:** Automatically trigger lead discovery jobs on a schedule, track them in agent_jobs table, and monitor completion.

**Priority:** HIGH (Foundation for agent orchestration)

---

## 📋 Zap Configuration

### Basic Info
- **Name:** Rise Local - Discovery Job Coordinator
- **Folder:** Rise Local / Phase 1
- **Status:** Active
- **Description:** Schedules daily lead discovery jobs and tracks progress in agent_jobs table

---

## 🔧 Zap Steps

### Step 1: Schedule by Zapier (Trigger)

**Configuration:**
- **Frequency:** Daily
- **Time:** 9:00 AM (your timezone)
- **Days:** Monday - Friday (weekdays only)

**Output:**
```json
{
  "scheduled_time": "2025-12-22T09:00:00Z"
}
```

---

### Step 2: Code by Zapier - Check Rate Limit

**Language:** Python 3.9

**Input Data:**
- `service_name`: "google_places"
- `quota_limit`: 100 (daily quota)

**Code:**
```python
# Check if we're within daily Google Places API quota
import datetime

# Input
service_name = input_data.get('service_name', 'google_places')
quota_limit = int(input_data.get('quota_limit', 100))

# Get current hour window
now = datetime.datetime.utcnow()
window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
reset_at = window_start + datetime.timedelta(days=1)

# Simulate rate limit check (in production, query Supabase rate_limits table)
# For now, assume we're under quota
request_count = 0  # Would query: SELECT request_count FROM rate_limits WHERE...

allowed = request_count < quota_limit
remaining = quota_limit - request_count

return {
    'allowed': allowed,
    'remaining': remaining,
    'request_count': request_count,
    'quota_limit': quota_limit,
    'reset_at': reset_at.isoformat(),
    'service_name': service_name
}
```

**Output:**
```json
{
  "allowed": true,
  "remaining": 100,
  "service_name": "google_places"
}
```

---

### Step 3: Filter by Zapier - Only if Allowed

**Configuration:**
- **Continue Only If:** `allowed` equals `true`

**Explanation:** Stops the Zap if we've exceeded the daily quota.

---

### Step 4: Code by Zapier - Create Agent Job Record

**Language:** Python 3.9

**Input Data:**
- `metro_areas`: "Austin,Dallas-Fort Worth" (comma-separated)
- `radius`: 15
- `initiated_by`: "zapier_discovery_coordinator"

**Code:**
```python
import json
import uuid
from datetime import datetime

# Input
metro_areas = input_data.get('metro_areas', 'Austin').split(',')
radius = int(input_data.get('radius', 15))
initiated_by = input_data.get('initiated_by', 'zapier_discovery_coordinator')

# Create job record for each metro
jobs = []

for metro in metro_areas:
    metro = metro.strip()

    job = {
        'id': str(uuid.uuid4()),
        'job_type': 'discovery',
        'status': 'queued',
        'initiated_by': initiated_by,
        'initiated_by_type': 'zapier_agent',
        'parameters': json.dumps({
            'metro': metro,
            'radius': radius,
            'scheduled_time': datetime.utcnow().isoformat()
        }),
        'results': None,
        'error_message': None,
        'retry_count': 0,
        'created_at': datetime.utcnow().isoformat(),
        'started_at': None,
        'completed_at': None,
        'updated_at': datetime.utcnow().isoformat()
    }

    jobs.append(job)

# Return first job (will loop for multiple metros)
return jobs[0] if jobs else {}
```

**Output:**
```json
{
  "id": "abc-123-def-456",
  "job_type": "discovery",
  "status": "queued",
  "parameters": "{\"metro\": \"Austin\", \"radius\": 15}",
  "initiated_by": "zapier_discovery_coordinator"
}
```

---

### Step 5: Create Record in Tables (Zapier Tables)

**Table:** agent_jobs

**Fields Mapping:**
- `id` → `{{Step 4: id}}`
- `job_type` → `{{Step 4: job_type}}`
- `status` → `{{Step 4: status}}`
- `initiated_by` → `{{Step 4: initiated_by}}`
- `initiated_by_type` → `{{Step 4: initiated_by_type}}`
- `parameters` → `{{Step 4: parameters}}`
- `created_at` → `{{Step 4: created_at}}`
- `updated_at` → `{{Step 4: updated_at}}`

**Output:**
```json
{
  "record_id": "rec_abc123",
  "id": "abc-123-def-456",
  "status": "queued"
}
```

---

### Step 6: HTTP POST - Trigger Supabase Edge Function

**Method:** POST

**URL:** `{{process.env.SUPABASE_URL}}/functions/v1/discover-leads`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.SUPABASE_SERVICE_KEY}}",
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "job_id": "{{Step 4: id}}",
  "metro_area": "{{Step 4: parameters.metro}}",
  "radius_miles": {{Step 4: parameters.radius}}
}
```

**Output:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "running",
  "message": "Discovery job started"
}
```

---

### Step 7: Delay for 30 seconds

**Wait Time:** 30 seconds

**Purpose:** Give the discovery job time to start running.

---

### Step 8: Update Record in Tables (Zapier Tables)

**Table:** agent_jobs

**Find Record By:** `id` equals `{{Step 4: id}}`

**Update Fields:**
- `status` → "running"
- `started_at` → `{{Step 6: started_at}}` or NOW()
- `updated_at` → NOW()

---

### Step 9: Audit Log Entry (Create Record in Tables)

**Table:** audit_log

**Fields:**
- `timestamp` → NOW()
- `actor` → "zapier_discovery_coordinator"
- `actor_type` → "zapier_agent"
- `action` → "discovery_job_created"
- `resource_type` → "job"
- `resource_id` → `{{Step 4: id}}`
- `metadata` → JSON with metro, radius, job_id
- `severity` → "info"

---

### Step 10: Send Slack Notification (Optional)

**Channel:** #rise-pipeline

**Message:**
```
🚀 Discovery Job Started
Metro: {{Step 4: parameters.metro}}
Radius: {{Step 4: parameters.radius}} miles
Job ID: {{Step 4: id}}
Status: Running

Track progress: https://dashboard.riselocal.com/jobs/{{Step 4: id}}
```

---

## 🧪 Testing Procedure

### Test 1: Manual Run

1. Go to Zapier Dashboard
2. Find "Rise Local - Discovery Job Coordinator"
3. Click "Test" in top right
4. Select "Test & Review"
5. Verify each step executes successfully
6. Check Zapier Tables for new agent_jobs record
7. Check Supabase for matching record (after sync)

**Expected Results:**
- ✅ Rate limit check passes
- ✅ Job record created in Zapier Tables
- ✅ Supabase edge function triggered
- ✅ Job status updated to "running"
- ✅ Audit log entry created
- ✅ Slack notification sent (if configured)

---

### Test 2: Schedule Test

1. Set schedule to "Every 5 minutes" temporarily
2. Wait for 2-3 automatic runs
3. Check Zapier Tables for multiple job records
4. Verify no duplicate jobs for same metro/time
5. Check Zap History for any errors
6. Reset schedule to daily 9am

---

### Test 3: Rate Limit Test

1. Manually set `request_count` in rate_limits table to 99
2. Run Zap manually
3. Verify it continues (under quota)
4. Set `request_count` to 100
5. Run Zap again
6. Verify it stops at Step 3 (Filter)
7. Check audit log for rate limit exceeded entry

---

## 🔧 Environment Variables Needed

Add these to Zapier:

```bash
SUPABASE_URL=https://jitawzicdwgbhatvjblh.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**How to Add:**
1. Go to Zapier Dashboard
2. Settings → Environment Variables
3. Add each variable
4. Reference in Zaps as `{{process.env.VARIABLE_NAME}}`

---

## 📊 Success Metrics

**Track These:**
- Jobs created per day
- Job success rate (completed / total)
- Average job duration
- Rate limit hit rate (should be 0%)
- Override rate (human cancellations)

**Query:**
```sql
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_jobs,
  COUNT(*) FILTER (WHERE status='completed') as completed,
  COUNT(*) FILTER (WHERE status='failed') as failed,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM agent_jobs
WHERE job_type = 'discovery'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## 🐛 Common Issues & Fixes

### Issue 1: Zap Times Out

**Symptom:** Step 6 (HTTP POST) times out after 30 seconds

**Fix:**
- Discovery jobs take longer than 30s
- Don't wait for completion in this Zap
- Create separate "Discovery Job Monitor" Zap (polling)
- Remove Step 7 (Delay) and Step 8 (Update)

---

### Issue 2: Duplicate Jobs Created

**Symptom:** Multiple jobs for same metro on same day

**Fix:**
- Add deduplication check in Step 4
- Query Zapier Tables for existing jobs with same metro + date
- Skip if already exists
- Add unique constraint in database

---

### Issue 3: Rate Limit Check Fails

**Symptom:** Step 2 returns error

**Fix:**
- Ensure rate_limits table exists in Supabase
- Update code to query actual table instead of mock
- Add error handling with default allow=true
- Log failures to audit_log

---

## 🔄 Enhancements (Future)

1. **Multi-Metro Parallel:** Use Looping by Zapier to process multiple metros in parallel
2. **Dynamic Scheduling:** Read schedule from config table instead of hardcoded
3. **Smart Radius:** Adjust radius based on metro size (Austin: 20mi, Dallas: 30mi)
4. **Cost Tracking:** Calculate estimated cost before triggering
5. **Quota Prediction:** ML model to predict optimal discovery times
6. **Failure Recovery:** Automatic retry with exponential backoff

---

## 📁 Related Files

- Supabase Edge Function: `/supabase/functions/discover-leads/index.ts`
- Agent Models: `/rise_pipeline/agent_models.py`
- Rate Limits Table: `/supabase/migrations/004_create_rate_limits_table.sql`

---

**Created:** December 22, 2025
**Status:** Ready to implement
**Estimated Setup Time:** 30 minutes
**Priority:** HIGH
