# Zap 4: Lead Qualification Trigger
## Intelligent Lead Qualification with Claude Agents

**Purpose:** Automatically trigger Claude agent qualification when leads complete enrichment, handle QUALIFIED/REJECTED/MARGINAL decisions, and route to appropriate next steps.

**Priority:** HIGH (Core intelligence layer)

---

## 📋 Zap Configuration

### Basic Info
- **Name:** Rise Local - Lead Qualification Trigger
- **Folder:** Rise Local / Phase 1
- **Status:** Active
- **Description:** Triggers Claude agent qualification and routes based on decision

---

## 🔧 Zap Steps

### Step 1: Webhooks by Zapier (Trigger)

**Trigger Type:** Catch Hook

**Webhook URL:** `https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/qualification`

**Expected Payload:** (From enrichment complete event)
```json
{
  "event": "lead_enriched",
  "lead_id": "abc-123-def-456",
  "business_name": "Austin Electric",
  "website_url": "https://austinelectric.com",
  "city": "Austin",
  "state": "TX",
  "google_rating": 4.3,
  "enrichment_data": {
    "tech_stack": ["WordPress", "Google Analytics"],
    "has_crm": false,
    "has_booking": false,
    "cms_detected": "WordPress",
    "visual_score": 42,
    "performance_score": 38,
    "mobile_responsive": false
  }
}
```

**Alternative Trigger:** Supabase webhook when `leads.status = 'enriched'`

---

### Step 2: HTTP GET - Fetch Full Lead Data

**Method:** GET

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

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
select=*
id=eq.{{Step 1: lead_id}}
```

**Output:**
```json
[
  {
    "id": "abc-123-def-456",
    "business_name": "Austin Electric",
    "website_url": "https://austinelectric.com",
    "address": "123 Main St",
    "city": "Austin",
    "state": "TX",
    "zip_code": "78701",
    "phone": "(512) 555-0100",
    "google_rating": 4.3,
    "google_reviews_count": 87,
    "tech_stack": ["WordPress", "Google Analytics", "Stripe"],
    "has_crm": false,
    "has_booking": false,
    "visual_score": 42,
    "performance_score": 38,
    "mobile_responsive": false,
    "license_status": "Active",
    "bbb_rating": "A+",
    "reputation_gap": 0.2
  }
]
```

---

### Step 3: Code by Zapier - Prepare Qualification Context

**Language:** Python 3.9

**Input:**
- `lead`: `{{Step 2: first item from array}}`

**Code:**
```python
import json

lead = input_data.get('lead', {})

# Extract enrichment data
enrichment = {
    'tech_stack': lead.get('tech_stack', []),
    'has_crm': lead.get('has_crm', False),
    'has_booking': lead.get('has_booking', False),
    'visual_score': lead.get('visual_score', 0),
    'performance_score': lead.get('performance_score', 0),
    'mobile_responsive': lead.get('mobile_responsive', False),
    'license_status': lead.get('license_status', 'Unknown'),
    'bbb_rating': lead.get('bbb_rating'),
    'reputation_gap': lead.get('reputation_gap', 0)
}

# Calculate initial pain signals
pain_signals = []

if enrichment['visual_score'] < 50:
    pain_signals.append('Poor website design')

if enrichment['performance_score'] < 40:
    pain_signals.append('Slow website performance')

if not enrichment['mobile_responsive']:
    pain_signals.append('Not mobile responsive')

if not enrichment['has_crm']:
    pain_signals.append('No CRM detected')

if not enrichment['has_booking']:
    pain_signals.append('No online booking system')

if enrichment['license_status'] == 'Expired':
    pain_signals.append('Expired license')

if enrichment['reputation_gap'] > 1.0:
    pain_signals.append(f'Reputation gap: BBB much lower than Google')

# Prepare context for Claude agent
context = {
    'lead_id': lead.get('id'),
    'business_name': lead.get('business_name'),
    'website_url': lead.get('website_url'),
    'location': f"{lead.get('city')}, {lead.get('state')}",
    'google_rating': lead.get('google_rating'),
    'google_reviews': lead.get('google_reviews_count'),
    'enrichment_data': enrichment,
    'pain_signals': pain_signals,
    'pain_signal_count': len(pain_signals)
}

# Calculate preliminary pain score (0-100)
pain_score = 0
if enrichment['visual_score'] < 50:
    pain_score += 20
if enrichment['performance_score'] < 40:
    pain_score += 15
if not enrichment['mobile_responsive']:
    pain_score += 10
if not enrichment['has_crm']:
    pain_score += 15
if not enrichment['has_booking']:
    pain_score += 10
if enrichment['license_status'] == 'Expired':
    pain_score += 10
if enrichment['reputation_gap'] > 1.5:
    pain_score += 20

context['preliminary_pain_score'] = pain_score

# Determine if Claude agent is needed
if pain_score <= 30:
    context['auto_decision'] = 'REJECTED'
    context['needs_claude'] = False
elif pain_score >= 60:
    context['auto_decision'] = 'QUALIFIED'
    context['needs_claude'] = False
else:
    context['auto_decision'] = 'MARGINAL'
    context['needs_claude'] = True  # Requires Claude council review

return context
```

**Output:**
```json
{
  "lead_id": "abc-123-def-456",
  "business_name": "Austin Electric",
  "pain_signals": ["Poor website design", "Slow performance", "Not mobile responsive", "No CRM"],
  "pain_signal_count": 4,
  "preliminary_pain_score": 60,
  "auto_decision": "QUALIFIED",
  "needs_claude": false
}
```

---

### Step 4: Paths by Zapier - Route Based on Decision

**Path A: Auto-Qualified (pain_score ≥ 60)**
- Continue if: `{{Step 3: auto_decision}}` equals `QUALIFIED`

**Path B: Auto-Rejected (pain_score ≤ 30)**
- Continue if: `{{Step 3: auto_decision}}` equals `REJECTED`

**Path C: Marginal - Needs Claude (31-59)**
- Continue if: `{{Step 3: auto_decision}}` equals `MARGINAL`

---

## 🛤️ Path A: Auto-Qualified

### Step 5A: Update Lead Status to Qualified

**Action:** HTTP PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

**Query:** `id=eq.{{Step 3: lead_id}}`

**Body:**
```json
{
  "status": "qualified",
  "pain_score": {{Step 3: preliminary_pain_score}},
  "qualification_method": "auto_rule_based",
  "qualified_at": "{{NOW}}",
  "phase_1_completed_at": "{{NOW}}"
}
```

---

### Step 6A: Create Agent Decision Record

**Action:** Create Record in Tables

**Table:** agent_decisions

**Fields:**
- `id` → Generate UUID
- `lead_id` → `{{Step 3: lead_id}}`
- `decision_type` → `qualification`
- `agent_name` → `zapier_qualifier`
- `agent_type` → `zapier_agent`
- `decision` → `qualified`
- `confidence` → `0.95` (high confidence for clear signals)
- `reasoning` → `Auto-qualified with {{Step 3: pain_signal_count}} pain signals: {{Step 3: pain_signals joined by comma}}`
- `metadata` → JSON:
  ```json
  {
    "pain_score": {{Step 3: preliminary_pain_score}},
    "pain_signals": {{Step 3: pain_signals}},
    "qualification_method": "auto_rule_based"
  }
  ```
- `created_at` → NOW()

---

### Step 7A: Trigger Contact Enrichment (Waterfall)

**Action:** HTTP POST

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/enrichment_queue`

**Body:**
```json
{
  "lead_id": "{{Step 3: lead_id}}",
  "queue_type": "waterfall",
  "status": "pending",
  "business_name": "{{Step 3: business_name}}",
  "website_url": "{{Step 3: website_url}}",
  "city": "{{Step 3: location}}",
  "created_at": "{{NOW}}"
}
```

---

### Step 8A: Send Slack Notification

**Action:** Send Channel Message in Slack

**Channel:** #rise-pipeline

**Message:**
```
✅ Lead Auto-Qualified

Business: {{Step 3: business_name}}
Location: {{Step 3: location}}
Pain Score: {{Step 3: preliminary_pain_score}}/100
Pain Signals: {{Step 3: pain_signal_count}}

Top Issues:
{{Step 3: pain_signals joined by newline with bullet points}}

Next: Contact enrichment waterfall triggered
View: https://dashboard.riselocal.com/leads/{{Step 3: lead_id}}
```

---

## 🛤️ Path B: Auto-Rejected

### Step 5B: Update Lead Status to Rejected

**Action:** HTTP PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

**Query:** `id=eq.{{Step 3: lead_id}}`

**Body:**
```json
{
  "status": "rejected",
  "pain_score": {{Step 3: preliminary_pain_score}},
  "qualification_method": "auto_rule_based",
  "rejected_at": "{{NOW}}",
  "rejection_reason": "Insufficient pain signals (score: {{Step 3: preliminary_pain_score}})"
}
```

---

### Step 6B: Create Agent Decision Record

**Action:** Create Record in Tables

**Table:** agent_decisions

**Fields:**
- `decision` → `rejected`
- `confidence` → `0.90`
- `reasoning` → `Auto-rejected: Only {{Step 3: pain_signal_count}} pain signals detected. Score: {{Step 3: preliminary_pain_score}}/100 (threshold: 31+)`

---

### Step 7B: Audit Log Entry

**Action:** Create Record in Tables

**Table:** audit_log

**Fields:**
- `actor` → `zapier_qualifier`
- `actor_type` → `zapier_agent`
- `action` → `lead_rejected`
- `resource_type` → `lead`
- `resource_id` → `{{Step 3: lead_id}}`
- `metadata` → JSON with pain_score, signals
- `severity` → `info`

---

## 🛤️ Path C: Marginal - Claude Agent Review

### Step 5C: Create Agent Job for Claude

**Action:** Create Record in Tables

**Table:** agent_jobs

**Fields:**
- `id` → Generate UUID
- `job_type` → `qualification`
- `status` → `queued`
- `initiated_by` → `zapier_qualifier`
- `initiated_by_type` → `zapier_agent`
- `parameters` → JSON:
  ```json
  {
    "lead_id": "{{Step 3: lead_id}}",
    "business_name": "{{Step 3: business_name}}",
    "preliminary_pain_score": {{Step 3: preliminary_pain_score}},
    "context": {{Step 3: entire context object}},
    "requires_council": true
  }
  ```
- `created_at` → NOW()

---

### Step 6C: HTTP POST - Invoke Claude Agent

**Method:** POST

**URL:** `{{process.env.CLAUDE_AGENT_API_URL}}/api/agents/claude/invoke`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.CLAUDE_AGENT_SERVICE_TOKEN}}",
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "agent": "qualification_validator",
  "mode": "council",
  "job_id": "{{Step 5C: id}}",
  "lead_id": "{{Step 3: lead_id}}",
  "context": {{Step 3: entire context object}},
  "tools_enabled": [
    "search_tdlr_license",
    "search_bbb_reputation",
    "analyze_pagespeed",
    "capture_screenshot_and_analyze",
    "extract_owner_info",
    "verify_address"
  ]
}
```

**Timeout:** 120 seconds (Claude may call multiple MCP tools)

**Output:**
```json
{
  "job_id": "job-uuid-here",
  "agent_session_id": "session-xyz-789",
  "status": "running",
  "message": "Claude qualification agent started",
  "estimated_completion": "2025-12-22T10:10:00Z"
}
```

---

### Step 7C: Delay for Agent Execution

**Action:** Delay by Zapier

**Wait Time:** 90 seconds

**Purpose:** Give Claude agent time to:
1. Call 6 MCP tools in parallel
2. Analyze all results
3. Run LLMCouncil 4-agent vote
4. Write decision to agent_decisions table

---

### Step 8C: HTTP GET - Poll for Claude Decision

**Method:** GET

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/agent_decisions`

**Query:**
```
select=*
lead_id=eq.{{Step 3: lead_id}}
decision_type=eq.qualification
agent_name=like.claude_%
order=created_at.desc
limit=1
```

**Output:**
```json
[
  {
    "id": "decision-uuid",
    "lead_id": "abc-123-def-456",
    "decision_type": "qualification",
    "agent_name": "claude_qualifier",
    "decision": "qualified",
    "confidence": 0.87,
    "reasoning": "Strong pain signals detected: outdated website (2015 design), no mobile optimization, slow performance (38/100). Active TDLR license confirmed. BBB rating A+ indicates established business. Lead Analyst scored 82/100, Email Strategist confirmed high engagement potential. Quality Reviewer flagged no issues. Risk Assessor approved. Consensus: 4/4 QUALIFIED.",
    "metadata": {
      "council_votes": {
        "lead_analyst": {"vote": "qualified", "score": 82},
        "email_strategist": {"vote": "qualified", "engagement_potential": "high"},
        "quality_reviewer": {"vote": "qualified", "data_complete": true},
        "risk_assessor": {"vote": "qualified", "red_flags": []}
      },
      "pain_score": 68,
      "category": "DIY_CEILING",
      "top_pain_points": [
        "Outdated website design (2015 era)",
        "No mobile optimization",
        "Slow page load (4.2s)"
      ]
    }
  }
]
```

---

### Step 9C: Filter - Check if Decision Found

**Continue Only If:** `{{Step 8C: id}}` exists

**Alternative:** If decision not found after 90s:
- Retry Step 8C after another 30s
- Max retries: 3
- If still no decision → mark job as failed, send alert

---

### Step 10C: Update Agent Job Status

**Action:** Update Record in Tables

**Table:** agent_jobs

**Find By:** `id` equals `{{Step 5C: id}}`

**Update:**
- `status` → `completed`
- `completed_at` → NOW()
- `results` → JSON:
  ```json
  {
    "decision": "{{Step 8C: decision}}",
    "confidence": {{Step 8C: confidence}},
    "pain_score": {{Step 8C: metadata.pain_score}},
    "category": "{{Step 8C: metadata.category}}"
  }
  ```

---

### Step 11C: Paths by Zapier - Route Claude Decision

**Path C1: Claude Says QUALIFIED**
- Continue if: `{{Step 8C: decision}}` equals `qualified`
- Actions: Same as Path A Steps 5A-8A (update status, trigger waterfall)

**Path C2: Claude Says REJECTED**
- Continue if: `{{Step 8C: decision}}` equals `rejected`
- Actions: Same as Path B Steps 5B-7B (update status, audit log)

**Path C3: Claude Says MARGINAL (Rare)**
- Continue if: `{{Step 8C: decision}}` equals `marginal`
- Actions: Flag for human review, send high-priority Slack alert

---

### Step 12C: Send Detailed Slack Notification

**Channel:** #rise-pipeline

**Message:**
```
🤖 Claude Agent Decision: {{Step 8C: decision uppercase}}

Business: {{Step 3: business_name}}
Pain Score: {{Step 8C: metadata.pain_score}}/100
Category: {{Step 8C: metadata.category}}
Confidence: {{Step 8C: confidence × 100}}%

Council Breakdown:
- Lead Analyst: {{Step 8C: metadata.council_votes.lead_analyst.vote}} ({{Step 8C: metadata.council_votes.lead_analyst.score}}/100)
- Email Strategist: {{Step 8C: metadata.council_votes.email_strategist.vote}}
- Quality Reviewer: {{Step 8C: metadata.council_votes.quality_reviewer.vote}}
- Risk Assessor: {{Step 8C: metadata.council_votes.risk_assessor.vote}}

Reasoning:
{{Step 8C: reasoning}}

Top Pain Points:
{{Step 8C: metadata.top_pain_points joined by newline with bullet points}}

View full analysis: https://dashboard.riselocal.com/leads/{{Step 3: lead_id}}/decisions
```

---

## 🧪 Testing Procedure

### Test 1: Auto-Qualified Lead

```bash
# 1. Create test lead with high pain signals
curl -X POST "{{SUPABASE_URL}}/rest/v1/leads" \
  -H "apikey: {{SUPABASE_SERVICE_KEY}}" \
  -d '{
    "business_name": "Test Electric Co",
    "status": "enriched",
    "visual_score": 35,
    "performance_score": 28,
    "mobile_responsive": false,
    "has_crm": false,
    "has_booking": false
  }'

# 2. Trigger webhook manually
curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/qualification" \
  -d '{"event": "lead_enriched", "lead_id": "test-lead-id"}'

# 3. Wait 5 seconds

# 4. Verify:
# - Lead status = "qualified" in Supabase
# - agent_decisions record created
# - enrichment_queue has waterfall entry
# - Slack notification sent
```

---

### Test 2: Auto-Rejected Lead

```bash
# 1. Create test lead with low pain signals
curl -X POST "{{SUPABASE_URL}}/rest/v1/leads" \
  -d '{
    "business_name": "Perfect Electric",
    "status": "enriched",
    "visual_score": 85,
    "performance_score": 92,
    "mobile_responsive": true,
    "has_crm": true,
    "has_booking": true
  }'

# 2. Trigger webhook

# 3. Verify:
# - Lead status = "rejected"
# - agent_decisions shows rejection reasoning
# - No waterfall queue entry
```

---

### Test 3: Marginal Lead → Claude Review

```bash
# 1. Create marginal lead (pain_score = 50)
curl -X POST "{{SUPABASE_URL}}/rest/v1/leads" \
  -d '{
    "business_name": "Marginal Electric",
    "status": "enriched",
    "visual_score": 55,
    "performance_score": 60,
    "mobile_responsive": true,
    "has_crm": false
  }'

# 2. Trigger webhook

# 3. Verify:
# - agent_jobs record created (job_type='qualification')
# - Claude agent API called (check logs)
# - After 90s: agent_decisions created with Claude reasoning
# - Lead status updated based on Claude decision
# - Detailed Slack notification with council votes
```

---

### Test 4: Claude Agent Timeout

```bash
# 1. Simulate slow Claude response (mock API delay > 120s)
# 2. Trigger qualification for marginal lead
# 3. Verify:
# - Zap retries polling 3 times
# - After 3 retries: agent_jobs status = 'failed'
# - Alert sent to #rise-errors channel
# - Lead remains in 'processing' status for manual review
```

---

## 📊 Success Metrics

- **Qualification Rate:** 60% qualified (target), track trend
- **Auto-Decision Rate:** 70% (auto-qualified + auto-rejected, no Claude needed)
- **Claude Accuracy:** 90%+ (measured by human override rate)
- **Avg Processing Time:**
  - Auto: <5 seconds
  - Claude: <120 seconds (including MCP tool calls)
- **Error Rate:** <2% (failed API calls, timeouts)

---

## 💰 Cost Analysis

**Per Lead:**
- Auto-qualified/rejected: $0.001 (Zapier tasks only)
- Claude review (30% of leads):
  - Claude API: $0.05 (council with 4 agents)
  - MCP tools: $0.10 (6 tool calls average)
  - Total: $0.15

**Monthly (3,000 leads):**
- 2,100 auto-decisions: $2.10
- 900 Claude reviews: $135
- **Total: $137.10/month**

---

## 🐛 Troubleshooting

### Issue 1: Claude Agent Not Responding

**Symptom:** Step 8C returns empty array, no decision found

**Debug:**
1. Check Claude agent API logs
2. Verify MCP server is running (health check)
3. Check agent_jobs table for error_message

**Fix:**
- Increase delay in Step 7C to 120 seconds
- Add retry logic with exponential backoff
- Implement fallback: Use preliminary pain score if Claude fails

---

### Issue 2: Incorrect Auto-Qualification

**Symptom:** Leads auto-qualified but should be rejected (or vice versa)

**Debug:**
- Review pain scoring logic in Step 3
- Check if thresholds (30, 60) are appropriate

**Fix:**
```python
# Adjust thresholds in Step 3:
if pain_score <= 40:  # Increased from 30
    context['auto_decision'] = 'REJECTED'
elif pain_score >= 70:  # Increased from 60
    context['auto_decision'] = 'QUALIFIED'
```

---

### Issue 3: Duplicate Decisions Created

**Symptom:** Multiple agent_decisions records for same lead

**Debug:**
- Check if Zap triggered multiple times
- Verify webhook deduplication

**Fix:**
- Add unique constraint in agent_decisions: (lead_id, decision_type, agent_name)
- In Step 6A/6B, use "Find or Create" instead of "Create"

---

## 🔧 Environment Variables

```bash
SUPABASE_URL=https://jitawzicdwgbhatvjblh.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
CLAUDE_AGENT_API_URL=http://localhost:8080  # or production URL
CLAUDE_AGENT_SERVICE_TOKEN=your-jwt-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## 📁 Related Files

- Supabase Edge Function: `/supabase/functions/qualify-lead/index.ts` (future)
- Claude Agent: `/agents/qualification_validator.py`
- MCP Server: `/mcp_server/server.py`
- Python Models: `/rise_pipeline/agent_models.py`

---

**Created:** December 22, 2025
**Status:** Ready to implement
**Estimated Setup Time:** 45 minutes
**Priority:** HIGH
**Monthly Cost:** $137.10 (Claude API + tools)

