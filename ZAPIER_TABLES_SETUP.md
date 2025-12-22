# Zapier Tables Setup Guide
## Creating Agent Orchestration Tables

**Purpose:** Create 4 tables in Zapier Tables to support agent orchestration and workflow state management.

**Why Zapier Tables:**
- Fast workflow state storage (lower latency than Supabase for Zaps)
- Built-in Zapier integration (no API calls needed)
- Automatic webhooks on record changes
- Pay-per-use pricing ($0.10 per 1000 operations)

**Why Also Supabase:**
- Single source of truth for lead data
- Complex queries and joins
- Long-term storage and analytics
- Row-level security

---

## 📊 Table 1: agent_jobs

**Purpose:** Track all agent-initiated jobs (discovery, enrichment, qualification, delivery)

### Field Definitions

| Field Name | Type | Required | Default | Description |
|------------|------|----------|---------|-------------|
| id | UUID | Yes | Auto | Unique job identifier |
| job_type | Single Select | Yes | - | Options: discovery, enrichment, qualification, delivery, manual |
| status | Single Select | Yes | queued | Options: queued, running, completed, failed, cancelled |
| initiated_by | Text | No | - | User ID or agent name (e.g., 'user@example.com', 'zapier_coordinator') |
| initiated_by_type | Single Select | No | - | Options: human, zapier_agent, claude_agent |
| parameters | Long Text (JSON) | No | - | Job-specific parameters as JSON |
| results | Long Text (JSON) | No | - | Job outputs as JSON |
| error_message | Long Text | No | - | Error details if status=failed |
| retry_count | Number | No | 0 | Number of retry attempts |
| created_at | Date/Time | Yes | NOW() | When job was created |
| started_at | Date/Time | No | - | When job started running |
| completed_at | Date/Time | No | - | When job finished |
| updated_at | Date/Time | Yes | NOW() | Last update timestamp |

### Zapier Table Setup

1. Go to https://tables.zapier.com
2. Click "Create Table"
3. Name: `agent_jobs`
4. Add fields one by one using the table above
5. Set field types exactly as specified
6. For Single Select fields, add options as comma-separated list
7. Enable "Auto-update updated_at" if available

### Example Record

```json
{
  "id": "abc-123-def-456",
  "job_type": "discovery",
  "status": "completed",
  "initiated_by": "zapier_discovery_coordinator",
  "initiated_by_type": "zapier_agent",
  "parameters": "{\"metro_id\": \"austin\", \"radius\": 15, \"zip_code\": \"78701\"}",
  "results": "{\"leads_created\": 47, \"places_found\": 89, \"cost_cents\": 235}",
  "error_message": null,
  "retry_count": 0,
  "created_at": "2025-12-22T10:00:00Z",
  "started_at": "2025-12-22T10:00:05Z",
  "completed_at": "2025-12-22T10:15:32Z",
  "updated_at": "2025-12-22T10:15:32Z"
}
```

---

## 📊 Table 2: agent_decisions

**Purpose:** Track all agent decisions with reasoning and override capability

### Field Definitions

| Field Name | Type | Required | Default | Description |
|------------|------|----------|---------|-------------|
| id | UUID | Yes | Auto | Unique decision identifier |
| lead_id | Text (UUID) | Yes | - | UUID of lead being decided on |
| decision_type | Single Select | Yes | - | Options: qualification, scoring, routing, email_variant, category_assignment |
| agent_name | Text | Yes | - | Name of agent (e.g., 'claude_qualifier', 'zapier_router') |
| agent_type | Single Select | Yes | - | Options: zapier_agent, claude_agent, council |
| decision | Text | Yes | - | The actual decision (e.g., 'qualified', 'rejected', 'marginal') |
| confidence | Number (Decimal) | No | - | Confidence score 0.00 to 1.00 |
| reasoning | Long Text | No | - | Human-readable explanation |
| metadata | Long Text (JSON) | No | - | Additional context (council votes, pain signals) |
| overridden_by | Text | No | - | User ID who overrode this decision |
| override_reason | Long Text | No | - | Reason for override |
| overridden_at | Date/Time | No | - | When override occurred |
| created_at | Date/Time | Yes | NOW() | When decision was made |

### Zapier Table Setup

1. Create table: `agent_decisions`
2. Add fields from table above
3. For confidence field:
   - Type: Number
   - Format: Decimal (2 places)
   - Min: 0.00, Max: 1.00
4. Link to `agent_jobs` if possible (many decisions → one job)

### Example Record

```json
{
  "id": "def-456-ghi-789",
  "lead_id": "lead-abc-123",
  "decision_type": "qualification",
  "agent_name": "claude_qualifier",
  "agent_type": "claude_agent",
  "decision": "qualified",
  "confidence": 0.87,
  "reasoning": "Active TECL license, 4.5 BBB rating, modern responsive website with CRM integration. Strong pain signals: performance score 42/100, no online booking system. High intent business with budget.",
  "metadata": "{\"pain_score\": 72, \"icp_score\": 85, \"council_votes\": {\"lead_analyst\": \"approve\", \"risk_assessor\": \"approve\"}}",
  "overridden_by": null,
  "override_reason": null,
  "overridden_at": null,
  "created_at": "2025-12-22T10:16:00Z"
}
```

---

## 📊 Table 3: audit_log

**Purpose:** Comprehensive audit trail for compliance and debugging

### Field Definitions

| Field Name | Type | Required | Default | Description |
|------------|------|----------|---------|-------------|
| id | Auto-Increment | Yes | Auto | Unique log entry ID |
| timestamp | Date/Time | Yes | NOW() | When action occurred |
| actor | Text | Yes | - | User ID, agent name, or 'system' |
| actor_type | Single Select | Yes | - | Options: human, zapier_agent, claude_agent, system |
| action | Text | Yes | - | Action performed (e.g., 'discovery_started', 'lead_qualified') |
| resource_type | Text | No | - | Type of resource (e.g., 'lead', 'job', 'config') |
| resource_id | Text | No | - | UUID or identifier of resource |
| metadata | Long Text (JSON) | No | - | Full context of the action |
| ip_address | Text | No | - | IP address (for humans) |
| user_agent | Long Text | No | - | User agent string (for humans) |
| session_id | Text | No | - | Session identifier |
| severity | Single Select | No | info | Options: debug, info, warning, error, critical |

### Zapier Table Setup

1. Create table: `audit_log`
2. Add fields from table above
3. Configure as **append-only** (no edits/deletes after creation)
4. Set retention policy: 7 years (2555 days) for compliance

### Example Record

```json
{
  "id": 12345,
  "timestamp": "2025-12-22T10:00:00Z",
  "actor": "user@example.com",
  "actor_type": "human",
  "action": "discovery_started",
  "resource_type": "job",
  "resource_id": "abc-123-def-456",
  "metadata": "{\"metro\": \"austin\", \"radius\": 15, \"estimated_cost_cents\": 200}",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 ...",
  "session_id": "sess_xyz789",
  "severity": "info"
}
```

---

## 📊 Table 4: rate_limits

**Purpose:** Track API rate limits for external services and agent quotas

### Field Definitions

| Field Name | Type | Required | Default | Description |
|------------|------|----------|---------|-------------|
| id | UUID | Yes | Auto | Unique rate limit record ID |
| service_name | Text | Yes | - | Service or agent identifier (e.g., 'clay', 'agent:zapier_orchestrator') |
| window_start | Date/Time | Yes | - | Start of rate limit window |
| request_count | Number | Yes | 0 | Number of requests in this window |
| quota_limit | Number | Yes | - | Maximum requests allowed |
| reset_at | Date/Time | Yes | - | When window resets |
| metadata | Long Text (JSON) | No | - | Additional info (cost per request, plan details) |
| created_at | Date/Time | Yes | NOW() | When record created |
| updated_at | Date/Time | Yes | NOW() | Last update timestamp |

### Zapier Table Setup

1. Create table: `rate_limits`
2. Add fields from table above
3. Add unique constraint on: `service_name` + `window_start`
4. Enable auto-cleanup of old records (older than 7 days)

### Example Record

```json
{
  "id": "rate-abc-123",
  "service_name": "clay",
  "window_start": "2025-12-22T10:00:00Z",
  "request_count": 47,
  "quota_limit": 1000,
  "reset_at": "2025-12-22T11:00:00Z",
  "metadata": "{\"cost_per_request\": 0.01, \"plan\": \"professional\"}",
  "created_at": "2025-12-22T10:00:00Z",
  "updated_at": "2025-12-22T10:15:32Z"
}
```

---

## 🔄 Synchronization Strategy

### Zapier Tables ↔ Supabase Sync

**Why Sync:**
- Zapier Tables: Fast workflow state (low latency for Zaps)
- Supabase: Single source of truth (analytics, reporting, complex queries)

**Sync Pattern:**

```
┌─────────────────────────────────────────────────┐
│ 1. Zapier writes to Zapier Tables (fast)       │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ 2. Zapier webhook triggers on record change    │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│ 3. Zapier writes to Supabase (async, durable)  │
└─────────────────────────────────────────────────┘
```

**Implementation:**

```javascript
// Zap 1: agent_jobs → Supabase Sync
// Trigger: New Record in Tables (agent_jobs)
// Action: Create/Update Record in Supabase

{
  table: 'agent_jobs',
  data: {
    id: inputData.id,
    job_type: inputData.job_type,
    status: inputData.status,
    initiated_by: inputData.initiated_by,
    parameters: JSON.parse(inputData.parameters),
    results: JSON.parse(inputData.results),
    created_at: inputData.created_at,
    completed_at: inputData.completed_at
  }
}
```

**Conflict Resolution:**
- **Zapier Tables timestamp wins** for real-time workflow state
- **Supabase timestamp wins** for long-term analytics
- Acceptable eventual consistency lag: 30 seconds

---

## 🧪 Testing Your Tables

### Test Script (Python)

```python
import requests
import json
from datetime import datetime

ZAPIER_TABLE_WEBHOOK = "https://hooks.zapier.com/hooks/catch/YOUR_WEBHOOK_ID/"

# Test 1: Create agent job
def test_create_job():
    job = {
        "id": "test-job-001",
        "job_type": "discovery",
        "status": "queued",
        "initiated_by": "test_user",
        "initiated_by_type": "human",
        "parameters": json.dumps({"metro": "austin", "radius": 15}),
        "created_at": datetime.utcnow().isoformat()
    }

    response = requests.post(ZAPIER_TABLE_WEBHOOK, json=job)
    print(f"Create job: {response.status_code}")

# Test 2: Create agent decision
def test_create_decision():
    decision = {
        "id": "test-decision-001",
        "lead_id": "lead-test-123",
        "decision_type": "qualification",
        "agent_name": "test_agent",
        "agent_type": "claude_agent",
        "decision": "qualified",
        "confidence": 0.95,
        "reasoning": "Test decision for validation",
        "created_at": datetime.utcnow().isoformat()
    }

    response = requests.post(ZAPIER_TABLE_WEBHOOK, json=decision)
    print(f"Create decision: {response.status_code}")

# Test 3: Create audit log entry
def test_create_audit_log():
    log = {
        "timestamp": datetime.utcnow().isoformat(),
        "actor": "test_user",
        "actor_type": "human",
        "action": "test_action",
        "resource_type": "test",
        "resource_id": "test-001",
        "severity": "info"
    }

    response = requests.post(ZAPIER_TABLE_WEBHOOK, json=log)
    print(f"Create audit log: {response.status_code}")

# Run tests
test_create_job()
test_create_decision()
test_create_audit_log()
```

---

## 💰 Pricing Estimate

**Zapier Tables Pricing:**
- $0.10 per 1,000 operations (read/write)
- Free tier: 1,000 operations/month

**Estimated Usage:**
- 100 leads/day processed
- 4 tables × 2 operations (write to Tables + sync to Supabase) = 8 ops/lead
- 100 × 8 = 800 operations/day
- 800 × 30 = 24,000 operations/month
- **Cost:** $2.40/month for Zapier Tables

**Supabase Comparison:**
- Supabase direct: ~5ms latency for Zaps (network round-trip)
- Zapier Tables: <1ms latency (Zapier-native)
- **Performance gain:** 5x faster workflow execution

---

## 🔐 Security & Compliance

### Row-Level Security (Supabase)

Already implemented in migration files:
- `audit_log`: Append-only, read-only for non-admins
- `agent_decisions`: Filterable by user role
- `agent_jobs`: Scoped to user's region (if multi-tenant)

### Zapier Tables Security

- **Authentication:** Webhook URLs with secret tokens
- **Encryption:** Data encrypted at rest
- **Access Control:** Team-based permissions
- **Audit:** Built-in activity log

---

## ✅ Setup Checklist

**Supabase (Primary Database):**
- [ ] Run migration 001: `agent_jobs` table
- [ ] Run migration 002: `agent_decisions` table
- [ ] Run migration 003: `audit_log` table
- [ ] Run migration 004: `rate_limits` table
- [ ] Enable RLS policies on `audit_log`
- [ ] Test queries with sample data

**Zapier Tables (Workflow State):**
- [ ] Create `agent_jobs` table with fields
- [ ] Create `agent_decisions` table with fields
- [ ] Create `audit_log` table with fields
- [ ] Create `rate_limits` table with fields
- [ ] Set up webhook triggers for each table
- [ ] Create sync Zaps (Tables → Supabase)

**Testing:**
- [ ] Insert test record in each table
- [ ] Verify sync from Zapier Tables → Supabase
- [ ] Test rate limit check function
- [ ] Validate audit log append-only behavior
- [ ] Check query performance on large datasets

---

## 📚 Next Steps

1. **Week 3:** Run Supabase migrations
2. **Week 3:** Create Zapier Tables
3. **Week 3:** Build sync Zaps
4. **Week 4:** Integrate with Claude agents
5. **Week 4:** Test end-to-end workflows

---

**Created:** December 22, 2025
**Status:** Ready for implementation
**Estimated Setup Time:** 2-3 hours
