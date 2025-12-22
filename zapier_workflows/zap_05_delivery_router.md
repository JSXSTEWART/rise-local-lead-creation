# Zap 5: Delivery Channel Router
## Multi-Channel Outreach Orchestration

**Purpose:** Route qualified leads with contact info to appropriate delivery channels (Instantly, GHL, HeyReach), generate personalized emails with Claude, and track engagement.

**Priority:** HIGH (Revenue generation layer)

---

## 📋 Zap Configuration

### Basic Info
- **Name:** Rise Local - Delivery Channel Router
- **Folder:** Rise Local / Phase 1
- **Status:** Active
- **Description:** Orchestrates multi-channel outreach after contact enrichment completes

---

## 🔧 Zap Steps

### Step 1: Webhooks by Zapier (Trigger)

**Trigger Type:** Catch Hook

**Webhook URL:** `https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/delivery`

**Expected Payload:** (From waterfall enrichment complete)
```json
{
  "event": "contacts_enriched",
  "lead_id": "abc-123-def-456",
  "business_name": "Austin Electric",
  "contacts": [
    {
      "first_name": "John",
      "last_name": "Smith",
      "email": "john@austinelectric.com",
      "title": "Owner",
      "linkedin_url": "https://linkedin.com/in/johnsmith",
      "confidence": 0.92
    }
  ],
  "enrichment_source": "clay",
  "fallback_used": false
}
```

---

### Step 2: HTTP GET - Fetch Full Lead Data

**Method:** GET

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

**Query:**
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
    "city": "Austin",
    "state": "TX",
    "google_rating": 4.3,
    "pain_score": 68,
    "category": "DIY_CEILING",
    "visual_score": 42,
    "performance_score": 38,
    "top_pain_points": [
      "Outdated website design",
      "No mobile optimization",
      "Slow page load"
    ],
    "license_status": "Active",
    "contact_email": "john@austinelectric.com",
    "contact_first_name": "John",
    "contact_last_name": "Smith",
    "contact_linkedin": "https://linkedin.com/in/johnsmith"
  }
]
```

---

### Step 3: Code by Zapier - Classify Lead & Select Strategy

**Language:** Python 3.9

**Input:**
- `lead`: `{{Step 2: first item}}`
- `contacts`: `{{Step 1: contacts}}`

**Code:**
```python
import json

lead = input_data.get('lead', {})
contacts = json.loads(input_data.get('contacts', '[]'))

# Extract primary contact
primary_contact = contacts[0] if contacts else {}

# Determine lead category (if not already set)
category = lead.get('category')
if not category:
    # Classify based on pain signals
    visual_score = lead.get('visual_score', 50)
    has_crm = lead.get('has_crm', False)
    performance_score = lead.get('performance_score', 50)
    google_rating = lead.get('google_rating', 3.0)

    if visual_score < 30:
        category = 'THE_INVISIBLE'
    elif visual_score < 50 and not has_crm:
        category = 'DIY_CEILING'
    elif performance_score < 40:
        category = 'LEAKY_BUCKET'
    elif google_rating < 3.5:
        category = 'OVERWHELMED'
    else:
        category = 'READY_TO_DOMINATE'

# Select A/B test variant based on category
variant_map = {
    'THE_INVISIBLE': 'authority',      # "I help businesses like yours get found online"
    'DIY_CEILING': 'pain_point',       # "Your website might be costing you customers"
    'LEAKY_BUCKET': 'curiosity',       # "I noticed something interesting about your site"
    'OVERWHELMED': 'relief',           # "What if handling leads was effortless?"
    'READY_TO_DOMINATE': 'opportunity' # "Ready to dominate your local market?"
}

ab_variant = variant_map.get(category, 'pain_point')

# Determine available channels
has_email = bool(primary_contact.get('email'))
has_linkedin = bool(primary_contact.get('linkedin_url'))
has_phone = bool(lead.get('phone'))

channels = []
if has_email:
    channels.append('instantly')
if has_linkedin:
    channels.append('heyreach')
channels.append('ghl')  # Always sync to CRM

# Determine lead priority (for sequencing)
pain_score = lead.get('pain_score', 0)
if pain_score >= 80:
    priority = 'high'
    sequence_delay = 24  # hours
elif pain_score >= 60:
    priority = 'medium'
    sequence_delay = 48
else:
    priority = 'low'
    sequence_delay = 72

return {
    'lead_id': lead.get('id'),
    'business_name': lead.get('business_name'),
    'category': category,
    'ab_variant': ab_variant,
    'pain_score': pain_score,
    'priority': priority,
    'sequence_delay': sequence_delay,
    'channels': channels,
    'has_email': has_email,
    'has_linkedin': has_linkedin,
    'contact_first_name': primary_contact.get('first_name'),
    'contact_email': primary_contact.get('email'),
    'contact_linkedin': primary_contact.get('linkedin_url'),
    'website_url': lead.get('website_url'),
    'city': lead.get('city'),
    'state': lead.get('state'),
    'top_pain_points': lead.get('top_pain_points', [])
}
```

**Output:**
```json
{
  "lead_id": "abc-123-def-456",
  "business_name": "Austin Electric",
  "category": "DIY_CEILING",
  "ab_variant": "pain_point",
  "pain_score": 68,
  "priority": "medium",
  "sequence_delay": 48,
  "channels": ["instantly", "heyreach", "ghl"],
  "has_email": true,
  "has_linkedin": true,
  "contact_first_name": "John",
  "contact_email": "john@austinelectric.com",
  "contact_linkedin": "https://linkedin.com/in/johnsmith"
}
```

---

### Step 4: Filter - Must Have Contact Method

**Continue Only If:**
- `{{Step 3: has_email}}` is `true`
- OR `{{Step 3: has_linkedin}}` is `true`

**If False:** End Zap, log to audit_log as "no_contact_info"

---

### Step 5: Create Agent Job for Email Generation

**Action:** Create Record in Tables

**Table:** agent_jobs

**Fields:**
- `id` → Generate UUID
- `job_type` → `delivery`
- `status` → `queued`
- `initiated_by` → `zapier_delivery_router`
- `initiated_by_type` → `zapier_agent`
- `parameters` → JSON:
  ```json
  {
    "lead_id": "{{Step 3: lead_id}}",
    "business_name": "{{Step 3: business_name}}",
    "category": "{{Step 3: category}}",
    "ab_variant": "{{Step 3: ab_variant}}",
    "contact_first_name": "{{Step 3: contact_first_name}}",
    "channels": {{Step 3: channels}}
  }
  ```
- `created_at` → NOW()

---

### Step 6: HTTP POST - Invoke Claude Email Strategist

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
  "agent": "email_strategist",
  "mode": "generate_personalized",
  "job_id": "{{Step 5: id}}",
  "lead_id": "{{Step 3: lead_id}}",
  "context": {
    "business_name": "{{Step 3: business_name}}",
    "contact_first_name": "{{Step 3: contact_first_name}}",
    "category": "{{Step 3: category}}",
    "ab_variant": "{{Step 3: ab_variant}}",
    "pain_score": {{Step 3: pain_score}},
    "top_pain_points": {{Step 3: top_pain_points}},
    "website_url": "{{Step 3: website_url}}",
    "location": "{{Step 3: city}}, {{Step 3: state}}"
  },
  "validation": {
    "use_hallucination_detector": true,
    "min_confidence": 0.7,
    "max_retries": 2
  }
}
```

**Timeout:** 90 seconds

**Output:**
```json
{
  "job_id": "job-uuid",
  "agent_session_id": "session-xyz",
  "status": "completed",
  "email": {
    "subject": "John, I noticed something about Austin Electric's website",
    "body": "Hi John,\n\nI was researching electrical contractors in Austin and came across Austin Electric...\n\n[Personalized content based on pain points]\n\nWould you be open to a quick 15-minute conversation about modernizing your online presence?\n\nBest,\n[Your Name]",
    "variant": "pain_point",
    "confidence": 0.89,
    "validated": true
  }
}
```

---

### Step 7: Filter - Check Email Generation Success

**Continue Only If:**
- `{{Step 6: status}}` equals `completed`
- AND `{{Step 6: email.validated}}` equals `true`

**If False:**
- Update agent_jobs.status = 'failed'
- Send alert to #rise-errors
- Use fallback template email

---

### Step 8: Create Agent Decision Record (Email Variant)

**Action:** Create Record in Tables

**Table:** agent_decisions

**Fields:**
- `id` → Generate UUID
- `lead_id` → `{{Step 3: lead_id}}`
- `decision_type` → `email_variant`
- `agent_name` → `claude_email_strategist`
- `agent_type` → `claude_agent`
- `decision` → `{{Step 3: ab_variant}}`
- `confidence` → `{{Step 6: email.confidence}}`
- `reasoning` → `Selected {{Step 3: ab_variant}} variant for {{Step 3: category}} lead. Generated personalized email with {{Step 3: top_pain_points count}} pain points addressed.`
- `metadata` → JSON:
  ```json
  {
    "category": "{{Step 3: category}}",
    "ab_variant": "{{Step 3: ab_variant}}",
    "email_subject": "{{Step 6: email.subject}}",
    "validation_confidence": {{Step 6: email.confidence}}
  }
  ```
- `created_at` → NOW()

---

### Step 9: Paths by Zapier - Route to Channels

**Path A: Has Email → Instantly**
- Continue if: `{{Step 3: has_email}}` is `true`

**Path B: Has LinkedIn → HeyReach**
- Continue if: `{{Step 3: has_linkedin}}` is `true`

**Path C: Always → GHL CRM Sync**
- Always runs

---

## 🛤️ Path A: Instantly (Email Delivery)

### Step 10A: HTTP POST - Add Contact to Instantly Campaign

**Method:** POST

**URL:** `https://api.instantly.ai/api/v1/lead/add`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.INSTANTLY_API_KEY}}",
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "api_key": "{{process.env.INSTANTLY_API_KEY}}",
  "campaign_id": "{{process.env.INSTANTLY_CAMPAIGN_ID}}",
  "email": "{{Step 3: contact_email}}",
  "first_name": "{{Step 3: contact_first_name}}",
  "company_name": "{{Step 3: business_name}}",
  "website": "{{Step 3: website_url}}",
  "custom_variables": {
    "business_name": "{{Step 3: business_name}}",
    "city": "{{Step 3: city}}",
    "pain_point_1": "{{Step 3: top_pain_points[0]}}",
    "pain_point_2": "{{Step 3: top_pain_points[1]}}",
    "pain_point_3": "{{Step 3: top_pain_points[2]}}"
  },
  "email_body": "{{Step 6: email.body}}",
  "email_subject": "{{Step 6: email.subject}}",
  "sequence_delay": {{Step 3: sequence_delay}}
}
```

**Output:**
```json
{
  "status": "success",
  "lead_id": "instantly-lead-id-123",
  "campaign_id": "camp-abc-456",
  "sequence_id": "seq-xyz-789",
  "estimated_send_date": "2025-12-24T10:00:00Z"
}
```

---

### Step 11A: Update Lead with Delivery Info

**Action:** HTTP PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

**Query:** `id=eq.{{Step 3: lead_id}}`

**Body:**
```json
{
  "status": "delivered",
  "delivery_channel": "instantly",
  "delivery_sequence_id": "{{Step 10A: sequence_id}}",
  "email_subject": "{{Step 6: email.subject}}",
  "email_variant": "{{Step 3: ab_variant}}",
  "delivered_at": "{{NOW}}",
  "estimated_send_date": "{{Step 10A: estimated_send_date}}"
}
```

---

## 🛤️ Path B: HeyReach (LinkedIn Outreach)

### Step 10B: HTTP POST - Add Contact to HeyReach Campaign

**Method:** POST

**URL:** `https://api.heyreach.io/api/v1/campaigns/{{process.env.HEYREACH_CAMPAIGN_ID}}/contacts`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.HEYREACH_API_KEY}}",
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "linkedin_url": "{{Step 3: contact_linkedin}}",
  "first_name": "{{Step 3: contact_first_name}}",
  "last_name": "{{Step 3: contact_last_name}}",
  "company": "{{Step 3: business_name}}",
  "custom_fields": {
    "pain_point": "{{Step 3: top_pain_points[0]}}",
    "city": "{{Step 3: city}}",
    "category": "{{Step 3: category}}"
  },
  "connection_message": "Hi {{Step 3: contact_first_name}}, I work with electrical contractors in {{Step 3: city}} and wanted to connect.",
  "follow_up_delay": 48,
  "priority": "{{Step 3: priority}}"
}
```

**Output:**
```json
{
  "status": "success",
  "contact_id": "heyreach-contact-123",
  "campaign_id": "camp-linkedin-456",
  "connection_request_sent": false,
  "scheduled_for": "2025-12-24T14:00:00Z"
}
```

---

### Step 11B: Create Agent Decision (LinkedIn Variant)

**Action:** Create Record in Tables

**Table:** agent_decisions

**Fields:**
- `decision_type` → `routing`
- `agent_name` → `zapier_delivery_router`
- `decision` → `route_heyreach`
- `confidence` → `0.95`
- `reasoning` → `LinkedIn profile found for {{Step 3: contact_first_name}}. Added to HeyReach campaign for B2B outreach.`
- `metadata` → JSON with contact_id, campaign_id

---

## 🛤️ Path C: GHL CRM Sync (Always)

### Step 10C: HTTP POST - Create/Update Contact in GHL

**Method:** POST

**URL:** `https://rest.gohighlevel.com/v1/contacts/`

**Headers:**
```json
{
  "Authorization": "Bearer {{process.env.GHL_API_KEY}}",
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "email": "{{Step 3: contact_email}}",
  "firstName": "{{Step 3: contact_first_name}}",
  "lastName": "{{Step 3: contact_last_name}}",
  "companyName": "{{Step 3: business_name}}",
  "website": "{{Step 3: website_url}}",
  "city": "{{Step 3: city}}",
  "state": "{{Step 3: state}}",
  "tags": [
    "rise_local",
    "qualified",
    "{{Step 3: category}}",
    "pain_score_{{Step 3: pain_score}}",
    "{{Step 3: ab_variant}}_variant"
  ],
  "customFields": {
    "lead_id": "{{Step 3: lead_id}}",
    "pain_score": {{Step 3: pain_score}},
    "category": "{{Step 3: category}}",
    "pain_point_1": "{{Step 3: top_pain_points[0]}}",
    "pain_point_2": "{{Step 3: top_pain_points[1]}}",
    "pain_point_3": "{{Step 3: top_pain_points[2]}}",
    "qualification_date": "{{NOW}}",
    "delivery_channels": "{{Step 3: channels joined by comma}}"
  }
}
```

**Output:**
```json
{
  "contact": {
    "id": "ghl-contact-id-123",
    "email": "john@austinelectric.com",
    "tags": ["rise_local", "qualified", "DIY_CEILING"]
  }
}
```

---

### Step 11C: Update Lead with GHL Contact ID

**Action:** HTTP PATCH

**URL:** `{{process.env.SUPABASE_URL}}/rest/v1/leads`

**Query:** `id=eq.{{Step 3: lead_id}}`

**Body:**
```json
{
  "ghl_contact_id": "{{Step 10C: contact.id}}",
  "synced_to_crm": true,
  "crm_sync_at": "{{NOW}}"
}
```

---

## 📧 Final Steps (All Paths Converge)

### Step 12: Update Agent Job to Completed

**Action:** Update Record in Tables

**Table:** agent_jobs

**Find By:** `id` equals `{{Step 5: id}}`

**Update:**
- `status` → `completed`
- `completed_at` → NOW()
- `results` → JSON:
  ```json
  {
    "email_generated": true,
    "email_confidence": {{Step 6: email.confidence}},
    "channels_delivered": {{Step 3: channels}},
    "instantly_sequence_id": "{{Step 10A: sequence_id}}",
    "heyreach_contact_id": "{{Step 10B: contact_id}}",
    "ghl_contact_id": "{{Step 10C: contact.id}}"
  }
  ```

---

### Step 13: Create Audit Log Entry

**Action:** Create Record in Tables

**Table:** audit_log

**Fields:**
- `timestamp` → NOW()
- `actor` → `zapier_delivery_router`
- `actor_type` → `zapier_agent`
- `action` → `lead_delivered`
- `resource_type` → `lead`
- `resource_id` → `{{Step 3: lead_id}}`
- `metadata` → JSON:
  ```json
  {
    "business_name": "{{Step 3: business_name}}",
    "channels": {{Step 3: channels}},
    "ab_variant": "{{Step 3: ab_variant}}",
    "pain_score": {{Step 3: pain_score}},
    "category": "{{Step 3: category}}"
  }
  ```
- `severity` → `info`

---

### Step 14: Send Slack Notification

**Action:** Send Channel Message in Slack

**Channel:** #rise-pipeline

**Message:**
```
🚀 Lead Delivered to Outreach

Business: {{Step 3: business_name}}
Contact: {{Step 3: contact_first_name}}
Category: {{Step 3: category}}
Pain Score: {{Step 3: pain_score}}/100

Email Strategy:
- Variant: {{Step 3: ab_variant}}
- Subject: {{Step 6: email.subject}}
- Confidence: {{Step 6: email.confidence × 100}}%

Delivery Channels:
{{Step 3: channels joined by newline with checkmarks}}

Tracking:
- Instantly Sequence: {{Step 10A: sequence_id}}
- HeyReach Contact: {{Step 10B: contact_id}}
- GHL Contact: {{Step 10C: contact.id}}

View in CRM: https://app.gohighlevel.com/contacts/{{Step 10C: contact.id}}
```

---

## 🔄 Follow-Up Zap (Separate Workflow)

**Name:** Rise Local - Engagement Monitor

**Purpose:** Monitor opens, clicks, replies from Instantly and HeyReach

### Trigger: Instantly Webhook (Open/Click/Reply)

**Webhook URL:** Configure in Instantly dashboard

**Payload:**
```json
{
  "event": "email_opened",
  "lead_id": "instantly-lead-id-123",
  "email": "john@austinelectric.com",
  "opened_at": "2025-12-24T15:30:00Z",
  "campaign_id": "camp-abc-456",
  "sequence_step": 1
}
```

**Actions:**
1. Find lead in Supabase by email
2. Update engagement metrics (opened_at, clicks_count)
3. If reply: Trigger sentiment analysis (Claude agent)
4. Route based on sentiment: interested, needs_info, rejected
5. Update GHL contact with engagement status

---

## 🧪 Testing Procedure

### Test 1: Email-Only Lead

```bash
# 1. Create qualified lead with email only
curl -X POST "{{SUPABASE_URL}}/rest/v1/leads" \
  -d '{
    "status": "qualified",
    "business_name": "Test Electric",
    "contact_email": "test@example.com",
    "contact_first_name": "Test",
    "category": "DIY_CEILING",
    "pain_score": 70
  }'

# 2. Trigger webhook
curl -X POST "https://hooks.zapier.com/hooks/catch/YOUR_HOOK_ID/delivery" \
  -d '{"event": "contacts_enriched", "lead_id": "test-lead-id"}'

# 3. Verify:
# - Claude email generated (check agent_jobs)
# - Contact added to Instantly
# - Contact created in GHL
# - Lead status = "delivered"
# - Slack notification sent
```

---

### Test 2: LinkedIn + Email Lead

```bash
# Test dual-channel delivery
# Verify both Instantly AND HeyReach receive contact
```

---

### Test 3: Email Generation Failure

```bash
# Simulate Claude API failure (timeout or low confidence)
# Verify:
# - Fallback template email used
# - Alert sent to #rise-errors
# - agent_jobs.status = 'failed'
# - Manual review triggered
```

---

## 📊 Success Metrics

- **Delivery Success Rate:** 95%+ (leads with valid contact info)
- **Email Generation Confidence:** 0.85 average
- **Multi-Channel Engagement:** 40% higher response vs email-only
- **Time to Delivery:** <5 minutes from qualification
- **GHL Sync Rate:** 100% (all qualified leads)

---

## 💰 Cost Analysis

**Per Lead:**
- Claude email generation: $0.05
- Instantly API: $0.001
- HeyReach API: $0.002
- GHL API: $0.001
- Zapier tasks: $0.005
- **Total: $0.059 per lead**

**Monthly (1,800 qualified leads):**
- **Total: $106.20/month**

---

## 🐛 Troubleshooting

### Issue 1: Instantly Rate Limit

**Symptom:** Step 10A fails with 429 error

**Fix:**
- Add rate limit check before Step 10A
- Queue leads if limit reached
- Retry after 1 hour
- Store in rate_limits table

---

### Issue 2: Low Email Confidence

**Symptom:** Claude generates email with confidence < 0.7

**Fix:**
```python
# In Step 6, retry with additional context:
if confidence < 0.7:
    retry_with_rag_context()
    if still < 0.7:
        use_fallback_template()
```

---

### Issue 3: Duplicate Contacts in CRM

**Symptom:** GHL creates multiple contacts for same lead

**Fix:**
- Change Step 10C to use "Find or Create" API
- Match on email address (unique identifier)
- Update existing contact instead of creating new

---

## 🔧 Environment Variables

```bash
CLAUDE_AGENT_API_URL=http://localhost:8080
CLAUDE_AGENT_SERVICE_TOKEN=your-jwt-token
INSTANTLY_API_KEY=your-instantly-key
INSTANTLY_CAMPAIGN_ID=your-campaign-id
HEYREACH_API_KEY=your-heyreach-key
HEYREACH_CAMPAIGN_ID=your-campaign-id
GHL_API_KEY=your-ghl-key
SLACK_WEBHOOK_URL=your-slack-webhook
SUPABASE_URL=https://jitawzicdwgbhatvjblh.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

---

## 📁 Related Files

- Claude Email Strategist: `/agents/email_strategist.py`
- Email Templates: `/templates/email_variants/`
- GHL Integration: `/integrations/ghl_client.py`
- Engagement Monitor Zap: `/zapier_workflows/zap_06_engagement_monitor.md`

---

**Created:** December 22, 2025
**Status:** Ready to implement
**Estimated Setup Time:** 2 hours
**Priority:** HIGH
**Monthly Cost:** $106.20 (per 1,800 leads)
**ROI:** Avg $500 close per lead, 10% close rate = $90,000 monthly revenue

