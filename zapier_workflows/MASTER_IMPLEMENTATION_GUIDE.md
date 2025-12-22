# Zapier Workflows - Master Implementation Guide
## Rise Local Lead Creation - Complete Agent Orchestration System

**Date:** December 22, 2025
**Status:** Production-Ready Documentation
**Total Zaps:** 13 (5 core workflows + 7 sync + 1 monitor)

---

## 📋 Executive Summary

This guide provides complete implementation instructions for the Rise Local agent orchestration system powered by Zapier workflows and Claude agents working in harmony.

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: DISCOVERY (Automated Daily)                       │
│ Zap 1: Discovery Job Coordinator                           │
│ ├─ Scheduled trigger (9am weekdays)                        │
│ ├─ Rate limit check                                        │
│ ├─ Trigger Supabase discovery job                          │
│ └─ Track in agent_jobs table                               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (30-50 new leads created)
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: ENRICHMENT (Automated on Threshold)               │
│ Zap 2: Clay Export Automation (2-part)                     │
│ Part A: Export Trigger                                     │
│ ├─ Monitor enrichment_queue (hourly)                       │
│ ├─ Export CSV when ≥25 leads pending                       │
│ ├─ POST to Clay API                                        │
│ └─ Update queue status to 'exported'                       │
│ Part B: Import Monitor                                     │
│ ├─ Poll Clay every 5 min for completion                    │
│ ├─ Download enriched results                               │
│ ├─ Update leads in Supabase                                │
│ └─ Trigger qualification workflow                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (45+ leads enriched with tech stack, etc.)
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: QUALIFICATION (Intelligent Decision-Making)       │
│ Zap 4: Lead Qualification Trigger                          │
│ ├─ Calculate preliminary pain score                        │
│ ├─ Path A: Auto-Qualify (score ≥60)                        │
│ ├─ Path B: Auto-Reject (score ≤30)                         │
│ └─ Path C: Claude Council Review (31-59)                   │
│     ├─ Invoke Claude agent via API                         │
│     ├─ LLMCouncil 4-agent vote                             │
│     ├─ Write decision to agent_decisions                   │
│     └─ Route based on consensus                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (27 qualified, need contact info)
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: CONTACT ENRICHMENT (Waterfall Method)             │
│ Zap 2 (Reused): Clay Waterfall Table                       │
│ ├─ Export qualified leads (lead_id, business, website)     │
│ ├─ Clay enriches: Apollo → Hunter → Manual fallback        │
│ ├─ Returns: email, first_name, linkedin_url                │
│ └─ Updates leads table with contact info                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (23 with valid email/LinkedIn)
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: DELIVERY (Multi-Channel Outreach)                 │
│ Zap 5: Delivery Channel Router                             │
│ ├─ Classify lead category (5 types)                        │
│ ├─ Invoke Claude Email Strategist                          │
│ │   ├─ Generate personalized email                         │
│ │   ├─ Select A/B variant                                  │
│ │   └─ Validate with HallucinationDetector                 │
│ ├─ Path A: Email → Instantly campaign                      │
│ ├─ Path B: LinkedIn → HeyReach campaign                    │
│ └─ Path C: Always → GHL CRM sync                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (Monitor engagement)
┌─────────────────────────────────────────────────────────────┐
│ PHASE 6: ENGAGEMENT TRACKING (Continuous)                  │
│ Zap 6: Engagement Monitor (future)                         │
│ ├─ Instantly webhooks (opens, clicks, replies)             │
│ ├─ HeyReach webhooks (connection accepted, messages)       │
│ ├─ Claude sentiment analysis on replies                    │
│ └─ Route: interested → schedule call, rejected → archive   │
└─────────────────────────────────────────────────────────────┘

INFRASTRUCTURE (Always Running):
Zap 3: Zapier Tables ↔ Supabase Sync (7 Zaps, bidirectional)
├─ agent_jobs (Tables → Supabase + reverse)
├─ agent_decisions (Tables → Supabase + reverse)
├─ audit_log (Tables → Supabase, one-way)
└─ rate_limits (Tables → Supabase + reverse)
```

---

## 🚀 Implementation Roadmap

### Week 1: Foundation & Sync Infrastructure

**Day 1-2: Supabase Tables Setup**

✅ Already Complete:
- Supabase migrations run (4 tables)
- Python models created
- Initialization script tested

**Day 3-4: Zapier Tables Setup**

Tasks:
1. Create 4 Zapier Tables:
   - agent_jobs
   - agent_decisions
   - audit_log
   - rate_limits

2. Configure fields (follow `/ZAPIER_TABLES_SETUP.md`)

3. Enable webhooks on all tables:
   - Settings → Integrations → Zapier
   - Enable "Trigger Zaps on record changes"

**Day 5-7: Sync Zaps (Critical Infrastructure)**

Create 7 Zaps (follow `/zap_03_tables_sync.md`):

1. **Zap 3A:** agent_jobs (Tables → Supabase)
   - Trigger: New Record in Tables
   - Actions: Parse JSON, POST to Supabase, Audit log

2. **Zap 3B:** agent_jobs (Supabase → Tables)
   - Trigger: Webhook from Supabase
   - Actions: Format data, Find or Create in Tables

3. **Zap 3C:** agent_decisions (Tables → Supabase)
4. **Zap 3D:** agent_decisions (Supabase → Tables)
5. **Zap 3E:** audit_log (Tables → Supabase, one-way)
6. **Zap 3F:** rate_limits (Tables → Supabase)
7. **Zap 3G:** rate_limits (Supabase → Tables)

**Supabase Webhooks Configuration:**
- Go to: Supabase Dashboard → Database → Webhooks
- Create 3 webhooks:
  - agent_jobs → `https://hooks.zapier.com/hooks/catch/YOUR_ID/agent_jobs`
  - agent_decisions → `https://hooks.zapier.com/hooks/catch/YOUR_ID/agent_decisions`
  - rate_limits → `https://hooks.zapier.com/hooks/catch/YOUR_ID/rate_limits`
- Events: INSERT, UPDATE

**Testing:**
```bash
# Test Tables → Supabase sync
curl -X POST https://tables.zapier.com/api/v1/tables/YOUR_TABLE_ID/records \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{"id": "test-001", "job_type": "discovery", "status": "queued"}'

# Wait 5 seconds, then query Supabase
curl "{{SUPABASE_URL}}/rest/v1/agent_jobs?id=eq.test-001" \
  -H "apikey: {{KEY}}"

# Expected: Record found
```

---

### Week 2: Core Discovery & Enrichment Workflows

**Day 1-2: Zap 1 - Discovery Job Coordinator**

Follow `/zap_01_discovery_coordinator.md`:

1. **Create Zap** in Zapier dashboard
2. **Step 1:** Schedule by Zapier
   - Frequency: Daily
   - Time: 9:00 AM
   - Days: Monday-Friday

3. **Step 2:** Code by Zapier (Rate limit check)
   - Copy code from spec
   - Test with sample data

4. **Step 3:** Filter by Zapier
   - Condition: allowed = true

5. **Step 4:** Code by Zapier (Create job record)
   - Input: metro_areas = "Austin,Dallas-Fort Worth"
   - Test: Verify UUID generated

6. **Step 5:** Create Record in Tables (agent_jobs)
   - Map all fields from Step 4

7. **Step 6:** HTTP POST to Supabase Edge Function
   - URL: `{{SUPABASE_URL}}/functions/v1/discover-leads`
   - Test endpoint exists first

8. **Steps 7-10:** Delay, Update, Audit, Slack notification

**Testing:**
- Run manual test in Zap editor
- Verify agent_jobs record created
- Check Supabase edge function triggered
- Confirm Slack notification received

---

**Day 3-5: Zap 2 - Clay Export Automation (2-part)**

Follow `/zap_02_clay_export_automation.md`:

**Part A: Export Trigger**

1. **Create Zap A** in Zapier
2. **Step 1:** Schedule by Zapier (hourly)
3. **Step 2:** HTTP GET - Check queue count
4. **Step 3:** Filter (count > 25)
5. **Step 4:** HTTP GET - Fetch leads
6. **Step 5:** Code by Zapier - Format CSV
7. **Step 6:** HTTP POST - Upload to Clay
8. **Step 7:** Create agent_jobs record
9. **Step 8:** Update enrichment_queue status

**Part B: Import Monitor**

1. **Create Zap B** (separate Zap)
2. **Step 1:** Schedule by Zapier (every 5 min)
3. **Step 2:** HTTP GET - Find running imports
4. **Step 3:** Loop by Zapier (each job)
5. **Step 4:** HTTP GET - Check Clay status
6. **Step 5:** Filter (status = completed)
7. **Step 6:** HTTP GET - Fetch enriched data
8. **Step 7:** Code by Zapier - Transform data
9. **Step 8:** HTTP PATCH - Update leads
10. **Step 9:** Update agent_jobs (completed)
11. **Step 10:** Update enrichment_queue (ready)

**Clay API Setup:**
- Get API key from Clay dashboard
- Get table IDs:
  - BuiltWith table: for tech stack enrichment
  - Waterfall table: for contact enrichment
- Add to Zapier environment variables

**Testing:**
```bash
# 1. Create 30 test leads in enrichment_queue
psql $DATABASE_URL -c "
  INSERT INTO enrichment_queue (lead_id, queue_type, status, business_name, website_url)
  SELECT gen_random_uuid(), 'builtwith', 'pending', 'Test Business ' || i, 'https://example' || i || '.com'
  FROM generate_series(1, 30) i;
"

# 2. Wait for Zap A to trigger (next hour mark)
# 3. Check Clay dashboard for import job
# 4. Wait 5-10 minutes for Clay to process
# 5. Verify Zap B polls and imports results
# 6. Check leads table for tech_stack data
```

---

### Week 3: Intelligent Qualification & Delivery

**Day 1-3: Zap 4 - Lead Qualification Trigger**

Follow `/zap_04_qualification_trigger.md`:

1. **Create Zap** in Zapier
2. **Step 1:** Webhook trigger (catch hook)
   - Copy webhook URL for later

3. **Step 2:** HTTP GET - Fetch lead data

4. **Step 3:** Code by Zapier - Prepare context
   - Calculate preliminary pain score
   - Identify pain signals
   - Determine if Claude needed

5. **Step 4:** Paths by Zapier (3 paths)
   - Path A: Auto-Qualified (≥60)
   - Path B: Auto-Rejected (≤30)
   - Path C: Marginal (31-59) → Claude

**Path C: Claude Agent Integration**

6. **Create Agent Job** record
7. **HTTP POST** to Claude agent API:
   - URL: `http://localhost:8080/api/agents/claude/invoke`
   - Body: Full context with lead data
   - Timeout: 120s

8. **Delay** 90 seconds (agent execution time)
9. **HTTP GET** Poll for decision in agent_decisions table
10. **Filter** Check decision found
11. **Update** agent_jobs status
12. **Paths** Route based on Claude decision
13. **Slack** Detailed notification with council votes

**Claude Agent Setup:**
- Ensure MCP server is running (port 8000)
- Start Claude agent API server:
  ```bash
  cd /home/user/rise-local-lead-creation/agents
  python qualification_validator.py
  # Runs on port 8080
  ```
- Test health endpoint: `curl http://localhost:8080/health`

**Configure Supabase Webhook:**
- Database → Webhooks → Create webhook
- Table: leads
- Events: UPDATE
- Condition: `NEW.status = 'enriched'`
- URL: Zapier webhook URL from Step 1

**Testing:**
```bash
# Test auto-qualified
curl -X POST "{{SUPABASE_URL}}/rest/v1/leads" \
  -d '{
    "status": "enriched",
    "business_name": "High Pain Co",
    "visual_score": 30,
    "performance_score": 25,
    "mobile_responsive": false,
    "has_crm": false
  }'
# Expected: status='qualified' after 5 seconds

# Test marginal → Claude
curl -X POST "{{SUPABASE_URL}}/rest/v1/leads" \
  -d '{
    "status": "enriched",
    "business_name": "Marginal Co",
    "visual_score": 55,
    "performance_score": 50
  }'
# Expected: agent_jobs created, Claude invoked, decision after 90s
```

---

**Day 4-5: Zap 5 - Delivery Channel Router**

Follow `/zap_05_delivery_router.md`:

1. **Create Zap** in Zapier
2. **Step 1:** Webhook trigger (catch hook)
3. **Step 2:** HTTP GET - Fetch lead + contacts
4. **Step 3:** Code by Zapier - Classify & select strategy
   - Determine category
   - Select A/B variant
   - Identify channels

5. **Step 4:** Filter (must have contact method)
6. **Step 5:** Create agent_jobs record
7. **Step 6:** HTTP POST - Invoke Claude Email Strategist
   - Generates personalized email
   - Validates with HallucinationDetector
   - Returns subject, body, confidence

8. **Step 7:** Filter (email validated)
9. **Step 8:** Create agent_decisions (email_variant)

10. **Step 9:** Paths by Zapier (3 channels)

**Path A: Instantly (Email)**
- HTTP POST to Instantly API
- Add contact to campaign
- Include custom variables (pain points)
- Update lead.delivery_sequence_id

**Path B: HeyReach (LinkedIn)**
- HTTP POST to HeyReach API
- Add contact to campaign
- Schedule connection request

**Path C: GHL (CRM) - Always**
- HTTP POST to GoHighLevel API
- Create/update contact
- Add tags: category, pain_score, ab_variant
- Store custom fields

11. **Final Steps:**
    - Update agent_jobs (completed)
    - Create audit_log entry
    - Send Slack notification (all channels)

**External API Setup:**

**Instantly:**
```bash
# Get API key: Instantly dashboard → Settings → API
# Get campaign ID: Campaigns → Your campaign → URL
export INSTANTLY_API_KEY="your-key"
export INSTANTLY_CAMPAIGN_ID="camp-abc-123"
```

**HeyReach:**
```bash
# Get API key: HeyReach dashboard → Integrations → API
export HEYREACH_API_KEY="your-key"
export HEYREACH_CAMPAIGN_ID="camp-xyz-789"
```

**GoHighLevel:**
```bash
# Get API key: GHL Settings → API → Create API Key
export GHL_API_KEY="your-key"
```

**Testing:**
```bash
# Trigger delivery with test lead
curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_ID/delivery" \
  -d '{
    "event": "contacts_enriched",
    "lead_id": "test-lead-id",
    "contacts": [{
      "first_name": "Test",
      "email": "test@example.com",
      "linkedin_url": "https://linkedin.com/in/test"
    }]
  }'

# Verify:
# 1. Email generated by Claude (check agent_jobs)
# 2. Contact added to Instantly (check campaign)
# 3. Contact added to HeyReach
# 4. Contact created in GHL (check CRM)
# 5. Lead status = 'delivered'
```

---

## 📊 Complete Zap Inventory

| # | Zap Name | Type | Priority | Setup Time | Monthly Cost |
|---|----------|------|----------|------------|--------------|
| 1 | Discovery Job Coordinator | Core | HIGH | 30 min | $0.50 |
| 2A | Clay Export - Part A | Core | HIGH | 30 min | $1.20 |
| 2B | Clay Import - Part B | Core | HIGH | 30 min | $1.20 |
| 3A | agent_jobs → Supabase | Sync | CRITICAL | 20 min | $0.80 |
| 3B | agent_jobs ← Supabase | Sync | CRITICAL | 20 min | $0.80 |
| 3C | agent_decisions → Supabase | Sync | CRITICAL | 20 min | $0.80 |
| 3D | agent_decisions ← Supabase | Sync | CRITICAL | 20 min | $0.80 |
| 3E | audit_log → Supabase | Sync | CRITICAL | 15 min | $0.40 |
| 3F | rate_limits → Supabase | Sync | MEDIUM | 15 min | $0.20 |
| 3G | rate_limits ← Supabase | Sync | MEDIUM | 15 min | $0.20 |
| 4 | Lead Qualification Trigger | Core | HIGH | 45 min | $137.10 |
| 5 | Delivery Channel Router | Core | HIGH | 2 hours | $106.20 |
| 6 | Engagement Monitor (future) | Monitor | MEDIUM | 1 hour | $5.00 |

**Total Setup Time:** 8 hours
**Total Monthly Cost:** $255.20 (at 3,000 leads/month)

---

## 💰 Complete Cost Breakdown

### Infrastructure Costs

**Zapier:**
- Professional Plan: $49/month (50,000 tasks)
- Estimated task usage: 15,000 tasks/month
- Headroom: 35,000 tasks

**Zapier Tables:**
- Operations: 48,000/month (sync operations)
- Cost: $4.80/month ($0.10 per 1,000 ops)

**Supabase:**
- Free tier (sufficient for 3,000 leads/month)
- Storage: ~200 MB/year
- Database operations: <1M requests/month

### Per-Lead Costs (3,000 leads/month)

| Stage | Operations | Cost per Lead | Monthly Total |
|-------|-----------|---------------|---------------|
| Discovery | Discovery job + sync | $0.002 | $6.00 |
| Enrichment | Clay BuiltWith + sync | $0.015 | $45.00 |
| Qualification (Auto) | Zapier tasks only | $0.001 | $2.10 |
| Qualification (Claude) | 30% need Claude review | $0.150 | $135.00 |
| Contact Enrichment | Clay waterfall (60% qualified) | $0.025 | $45.00 |
| Delivery | Email gen + routing | $0.059 | $106.20 |

**Total Infrastructure:** $49 (Zapier) + $4.80 (Tables) = $53.80/month
**Total Per-Lead:** $339.30/month
**Grand Total:** $393.10/month

**Revenue (10% close rate, $500 avg close):**
- 3,000 leads → 1,800 qualified → 180 closed → $90,000/month
- **ROI:** 228x ($90,000 / $393 = 228.8)

---

## 🧪 Complete Testing Strategy

### Phase 1: Unit Tests (Per Zap)

Test each Zap individually with sample data:

```bash
# Test script: /home/user/rise-local-lead-creation/tests/test_zaps.sh

#!/bin/bash

# Test Zap 1: Discovery Coordinator
echo "Testing Zap 1: Discovery Coordinator"
curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_ID/discovery-test" \
  -d '{"metro": "Austin", "radius": 15}'

sleep 5
psql $DATABASE_URL -c "SELECT * FROM agent_jobs WHERE job_type='discovery' ORDER BY created_at DESC LIMIT 1;"

# Test Zap 2A: Clay Export
echo "Testing Zap 2A: Clay Export"
psql $DATABASE_URL -c "
  INSERT INTO enrichment_queue (lead_id, queue_type, status, business_name, website_url)
  SELECT gen_random_uuid(), 'builtwith', 'pending', 'Test ' || i, 'https://test' || i || '.com'
  FROM generate_series(1, 30) i;
"

# Wait for hourly trigger or manual trigger
echo "Wait for Zap 2A to trigger (hourly schedule)"

# Test Zap 4: Qualification Trigger
echo "Testing Zap 4: Qualification Trigger"
curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_ID/qualification" \
  -d '{
    "event": "lead_enriched",
    "lead_id": "test-lead-001",
    "business_name": "Test Electric",
    "visual_score": 35,
    "performance_score": 30
  }'

sleep 10
psql $DATABASE_URL -c "SELECT status FROM leads WHERE id='test-lead-001';"
# Expected: status='qualified'

# Continue for all Zaps...
```

---

### Phase 2: Integration Tests (End-to-End)

Test complete pipeline from discovery to delivery:

```bash
# Integration test: /tests/integration_test.sh

#!/bin/bash

echo "======================================================================"
echo "  INTEGRATION TEST: Complete Pipeline (Discovery → Delivery)"
echo "======================================================================"

# Step 1: Trigger discovery
echo "[1/6] Triggering discovery job..."
curl -X POST "{{SUPABASE_URL}}/functions/v1/discover-leads" \
  -H "Authorization: Bearer {{SERVICE_KEY}}" \
  -d '{"metro": "Austin", "radius": 15, "test_mode": true}'

DISCOVERY_JOB_ID=$(psql $DATABASE_URL -t -c "SELECT id FROM agent_jobs WHERE job_type='discovery' ORDER BY created_at DESC LIMIT 1;")
echo "Discovery job ID: $DISCOVERY_JOB_ID"

# Wait for discovery to complete
echo "Waiting 60s for discovery to complete..."
sleep 60

# Verify leads created
LEAD_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM leads WHERE created_at > NOW() - INTERVAL '5 minutes';")
echo "Leads created: $LEAD_COUNT"

if [ "$LEAD_COUNT" -lt 1 ]; then
  echo "❌ FAILED: No leads created"
  exit 1
fi

# Step 2: Trigger enrichment (manual for test)
echo "[2/6] Triggering enrichment..."
SAMPLE_LEAD_ID=$(psql $DATABASE_URL -t -c "SELECT id FROM leads ORDER BY created_at DESC LIMIT 1;")
psql $DATABASE_URL -c "
  INSERT INTO enrichment_queue (lead_id, queue_type, status, business_name, website_url)
  SELECT id, 'builtwith', 'pending', business_name, website_url
  FROM leads WHERE id='$SAMPLE_LEAD_ID';
"

# Manually trigger Zap 2A or wait for hourly
echo "Manually trigger Zap 2A in Zapier dashboard, or wait for next hour"
read -p "Press enter when enrichment complete..."

# Step 3: Verify enrichment
ENRICHED_LEAD=$(psql $DATABASE_URL -t -c "SELECT tech_stack FROM leads WHERE id='$SAMPLE_LEAD_ID';")
echo "Enrichment data: $ENRICHED_LEAD"

if [ -z "$ENRICHED_LEAD" ]; then
  echo "❌ FAILED: Lead not enriched"
  exit 1
fi

# Step 4: Trigger qualification
echo "[3/6] Triggering qualification..."
psql $DATABASE_URL -c "UPDATE leads SET status='enriched' WHERE id='$SAMPLE_LEAD_ID';"
sleep 120  # Wait for Claude agent

# Verify qualification decision
DECISION=$(psql $DATABASE_URL -t -c "SELECT decision FROM agent_decisions WHERE lead_id='$SAMPLE_LEAD_ID' AND decision_type='qualification' ORDER BY created_at DESC LIMIT 1;")
echo "Qualification decision: $DECISION"

if [ "$DECISION" != "qualified" ]; then
  echo "⚠️  Lead not qualified (decision: $DECISION), stopping test"
  exit 0
fi

# Step 5: Trigger contact enrichment
echo "[4/6] Triggering contact enrichment..."
psql $DATABASE_URL -c "
  INSERT INTO enrichment_queue (lead_id, queue_type, status, business_name, website_url, city, state)
  SELECT id, 'waterfall', 'pending', business_name, website_url, city, state
  FROM leads WHERE id='$SAMPLE_LEAD_ID';
"

echo "Wait for Clay waterfall to complete (5-10 minutes)..."
read -p "Press enter when contacts enriched..."

# Step 6: Trigger delivery
echo "[5/6] Triggering delivery..."
CONTACT_EMAIL=$(psql $DATABASE_URL -t -c "SELECT contact_email FROM leads WHERE id='$SAMPLE_LEAD_ID';")

if [ -z "$CONTACT_EMAIL" ]; then
  echo "❌ FAILED: No contact email found"
  exit 1
fi

curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_ID/delivery" \
  -d "{
    \"event\": \"contacts_enriched\",
    \"lead_id\": \"$SAMPLE_LEAD_ID\",
    \"contacts\": [{\"email\": \"$CONTACT_EMAIL\", \"first_name\": \"Test\"}]
  }"

sleep 120  # Wait for email generation + delivery

# Verify delivery
DELIVERY_STATUS=$(psql $DATABASE_URL -t -c "SELECT status FROM leads WHERE id='$SAMPLE_LEAD_ID';")
echo "Final lead status: $DELIVERY_STATUS"

if [ "$DELIVERY_STATUS" == "delivered" ]; then
  echo "✅ INTEGRATION TEST PASSED"
  echo "Complete pipeline executed successfully:"
  echo "  Discovery → Enrichment → Qualification → Contacts → Delivery"
else
  echo "❌ INTEGRATION TEST FAILED"
  echo "Expected status='delivered', got '$DELIVERY_STATUS'"
  exit 1
fi

echo "======================================================================"
```

---

### Phase 3: Stress Tests (Load & Performance)

Test system under load:

```bash
# Stress test: /tests/stress_test.sh

# Test 1: High discovery volume
# Create 10 concurrent discovery jobs
for i in {1..10}; do
  curl -X POST "{{SUPABASE_URL}}/functions/v1/discover-leads" \
    -d '{"metro": "Austin", "radius": 15}' &
done
wait

# Verify: All jobs complete without errors
# Check: rate_limits table not exceeded

# Test 2: Enrichment queue buildup
# Create 200 leads in enrichment_queue
psql $DATABASE_URL -c "
  INSERT INTO enrichment_queue (lead_id, queue_type, status, business_name, website_url)
  SELECT gen_random_uuid(), 'builtwith', 'pending', 'Stress Test ' || i, 'https://test' || i || '.com'
  FROM generate_series(1, 200) i;
"

# Verify: Zap 2A processes in batches of 100
# Check: No Clay rate limit errors

# Test 3: Claude agent concurrency
# Trigger 50 marginal leads simultaneously
for i in {1..50}; do
  curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_ID/qualification" \
    -d "{\"event\": \"lead_enriched\", \"lead_id\": \"stress-$i\", \"pain_score\": 50}" &
done
wait

# Verify: All decisions complete within 5 minutes
# Check: No Claude API rate limit errors
```

---

## 🔒 Security Checklist

✅ **Credentials Management:**
- [ ] All API keys stored in Zapier environment variables
- [ ] No hardcoded credentials in Zap code
- [ ] Service account tokens rotated every 90 days
- [ ] Webhook URLs kept private (not in public docs)

✅ **Access Control:**
- [ ] Supabase RLS policies enabled on audit_log
- [ ] Zapier Tables restricted to team members only
- [ ] MCP server requires JWT authentication
- [ ] Claude agent API requires service token

✅ **Data Protection:**
- [ ] All API calls use HTTPS
- [ ] PII data encrypted at rest (Supabase default)
- [ ] Audit logs retain 7 years (compliance)
- [ ] Contact emails validated before delivery

✅ **Rate Limiting:**
- [ ] rate_limits table tracks all service quotas
- [ ] Pre-flight checks before API calls
- [ ] Fallback logic when limits exceeded
- [ ] Monitoring alerts at 80% quota usage

---

## 📈 Monitoring & Alerts

### Key Metrics Dashboard (Grafana/Supabase Dashboard)

**Pipeline Health:**
```sql
-- Jobs by status (last 24h)
SELECT
  job_type,
  status,
  COUNT(*) as count
FROM agent_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY job_type, status;
```

**Qualification Accuracy:**
```sql
-- Override rate (agent vs human decisions)
SELECT
  agent_name,
  COUNT(*) as total_decisions,
  COUNT(*) FILTER (WHERE overridden_by IS NOT NULL) as overrides,
  ROUND(100.0 * COUNT(*) FILTER (WHERE overridden_by IS NOT NULL) / COUNT(*), 2) as override_rate
FROM agent_decisions
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_name;

-- Target: <10% override rate
```

**Delivery Success:**
```sql
-- Delivery funnel
SELECT
  COUNT(*) FILTER (WHERE status='qualified') as qualified,
  COUNT(*) FILTER (WHERE status='delivered') as delivered,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status='delivered') /
        NULLIF(COUNT(*) FILTER (WHERE status='qualified'), 0), 2) as delivery_rate
FROM leads
WHERE qualified_at > NOW() - INTERVAL '7 days';

-- Target: >85% delivery rate
```

### Alerts Configuration

**Alert 1: High Error Rate**
```
Condition: (failed_jobs / total_jobs) > 0.05 in last 1 hour
Action: Send Slack alert to #rise-errors
Severity: WARNING
```

**Alert 2: Claude Agent Timeout**
```
Condition: agent_jobs.status='running' AND updated_at < NOW() - INTERVAL '10 minutes'
Action: Send PagerDuty alert
Severity: CRITICAL
```

**Alert 3: Rate Limit Approaching**
```
Condition: rate_limits.request_count > (quota_limit * 0.8)
Action: Send Slack alert to #rise-pipeline
Severity: INFO
```

**Alert 4: Delivery Failure Spike**
```
Condition: COUNT(status='failed_delivery') > 10 in last 30 min
Action: Send email to ops@riselocal.com
Severity: WARNING
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Zap Not Triggering

**Symptoms:**
- Scheduled Zap doesn't run at expected time
- Webhook doesn't catch events
- Table trigger doesn't fire

**Debug Steps:**
1. Check Zap History → Find skipped/missed runs
2. Verify trigger is enabled (toggle switch in Zap editor)
3. Check filters - may be blocking trigger
4. Test trigger manually in Zap editor

**Solutions:**
- **Scheduled:** Verify timezone settings match expectation
- **Webhook:** Test webhook URL with curl, check response
- **Table:** Verify webhook enabled in Table settings

---

### Issue 2: Claude Agent Not Responding

**Symptoms:**
- Qualification Zap times out at Step 8C
- No decision found in agent_decisions table
- agent_jobs.status stuck at 'running'

**Debug Steps:**
```bash
# Check if agent is running
curl http://localhost:8080/health

# Check agent logs
tail -f /var/log/claude_agent.log

# Check MCP server
curl http://localhost:8000/health

# Query stuck jobs
psql $DATABASE_URL -c "
  SELECT id, created_at, status, error_message
  FROM agent_jobs
  WHERE status='running' AND created_at < NOW() - INTERVAL '10 minutes';
"
```

**Solutions:**
- Restart agent: `systemctl restart claude-agent`
- Increase timeout in Zap Step 7C to 120 seconds
- Add retry logic with exponential backoff
- Implement fallback: Use preliminary pain score if Claude fails

---

### Issue 3: Duplicate Records in Tables

**Symptoms:**
- Multiple agent_decisions for same lead
- Duplicate agent_jobs entries
- Sync creates copies instead of updating

**Debug Steps:**
```sql
-- Find duplicates
SELECT lead_id, decision_type, COUNT(*)
FROM agent_decisions
GROUP BY lead_id, decision_type
HAVING COUNT(*) > 1;
```

**Solutions:**
- Add unique constraints:
  ```sql
  ALTER TABLE agent_decisions
  ADD CONSTRAINT unique_lead_decision
  UNIQUE (lead_id, decision_type, agent_name);
  ```
- Change Zap action from "Create" to "Find or Create"
- Add deduplication filter in Zap (check if record exists first)

---

### Issue 4: Clay API Rate Limit

**Symptoms:**
- Zap 2A fails with 429 error
- Clay webhook never fires (import stalled)
- No enrichment data returned

**Debug Steps:**
- Check Clay dashboard → Usage tab
- Query rate_limits table:
  ```sql
  SELECT * FROM rate_limits WHERE service_name='clay';
  ```

**Solutions:**
- Reduce export batch size from 100 to 50
- Increase polling interval from 5 min to 10 min
- Upgrade Clay plan (if at quota)
- Implement queue with delayed retry

---

## 📚 Reference Documentation

### Zapier Resources

- [Zapier Code by Zapier](https://help.zapier.com/hc/en-us/articles/8496309172237-Code-by-Zapier)
- [Zapier Webhooks](https://help.zapier.com/hc/en-us/articles/8496277690637-Trigger-Zaps-from-webhooks)
- [Zapier Tables](https://help.zapier.com/hc/en-us/sections/14938143177613-Tables-by-Zapier)
- [Zapier Paths](https://help.zapier.com/hc/en-us/articles/8496309164045-Add-branching-logic-to-Zaps-with-paths)

### External APIs

- [Clay API Docs](https://docs.clay.com/api-reference)
- [Instantly API Docs](https://developer.instantly.ai/)
- [HeyReach API Docs](https://docs.heyreach.io/)
- [GoHighLevel API Docs](https://highlevel.stoplight.io/)
- [Supabase API Docs](https://supabase.com/docs/guides/api)

### Project Files

| File | Purpose |
|------|---------|
| `/zapier_workflows/zap_01_discovery_coordinator.md` | Discovery automation spec |
| `/zapier_workflows/zap_02_clay_export_automation.md` | Enrichment automation spec |
| `/zapier_workflows/zap_03_tables_sync.md` | Bidirectional sync spec |
| `/zapier_workflows/zap_04_qualification_trigger.md` | Intelligent qualification spec |
| `/zapier_workflows/zap_05_delivery_router.md` | Multi-channel delivery spec |
| `/ZAPIER_TABLES_SETUP.md` | Tables configuration guide |
| `/TABLES_SCHEMA_IMPLEMENTATION.md` | Database schema reference |
| `/TABLES_QUICK_REFERENCE.md` | SQL queries cheat sheet |
| `/MCP_IMPLEMENTATION.md` | MCP server documentation |

---

## ✅ Final Checklist

### Pre-Launch

- [ ] All 13 Zaps created and tested individually
- [ ] Zapier Tables created with correct schemas
- [ ] Supabase webhooks configured (3 webhooks)
- [ ] Zapier environment variables set (15+ variables)
- [ ] MCP server deployed and health-checked
- [ ] Claude agent API running and tested
- [ ] External APIs configured (Clay, Instantly, HeyReach, GHL)
- [ ] Integration test passed (discovery → delivery)
- [ ] Monitoring dashboard configured
- [ ] Alert rules configured (4 alerts)
- [ ] Team trained on Zap History debugging
- [ ] Backup/rollback plan documented

### Post-Launch (Week 1)

- [ ] Monitor Zap History daily for errors
- [ ] Check agent_jobs table for stuck jobs
- [ ] Verify qualification decisions match expectations
- [ ] Review email generation confidence scores
- [ ] Confirm delivery to all channels working
- [ ] Check rate_limits table for quota usage
- [ ] Review audit_log for anomalies
- [ ] Collect feedback from sales team

### Optimization (Month 1)

- [ ] A/B test email variants, measure open rates
- [ ] Tune pain score thresholds based on close rates
- [ ] Optimize Claude agent prompts for accuracy
- [ ] Reduce unnecessary API calls (cost optimization)
- [ ] Implement caching for repeat service calls
- [ ] Add more sophisticated routing logic
- [ ] Build custom dashboard for pipeline metrics
- [ ] Document lessons learned and iterate

---

**Master Implementation Guide v1.0**
**Status:** Ready for Production Deployment
**Last Updated:** December 22, 2025
**Next Review:** January 15, 2025

