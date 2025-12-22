# Agent Tables - Quick Reference
## Essential Commands & Examples

---

## 🚀 One-Command Setup

```bash
# Run in Supabase SQL Editor
# Copy/paste from: supabase/migrations/000_combined_migrations.sql
```

---

## 📊 Table Overview

| Table | Purpose | Key Fields | Indexes |
|-------|---------|------------|---------|
| **agent_jobs** | Track jobs | job_type, status, results | status, created_at |
| **agent_decisions** | Track decisions | decision, confidence, reasoning | lead_id, agent_name |
| **audit_log** | Audit trail | action, actor, metadata | timestamp, actor |
| **rate_limits** | Rate limiting | service_name, quota_limit | service_name |

---

## 💻 Common SQL Queries

### Get Active Jobs
```sql
SELECT * FROM agent_jobs
WHERE status IN ('queued', 'running')
ORDER BY created_at DESC;
```

### Get Recent Decisions for Lead
```sql
SELECT * FROM agent_decisions
WHERE lead_id = 'YOUR_LEAD_UUID'
ORDER BY created_at DESC;
```

### Check Rate Limit
```sql
SELECT * FROM check_rate_limit('clay', 1000, 60);
-- Returns: {allowed: true, remaining: 953, reset_at: '2025-12-22T11:00:00Z'}
```

### Audit Trail for User
```sql
SELECT timestamp, action, resource_type, resource_id
FROM audit_log
WHERE actor = 'user@example.com'
ORDER BY timestamp DESC
LIMIT 100;
```

---

## 🐍 Python Examples

### Create Agent Job
```python
from rise_pipeline.agent_models import create_agent_job

job = create_agent_job(
    job_type='discovery',
    initiated_by='zapier_coordinator',
    initiated_by_type='zapier_agent',
    parameters={'metro': 'austin', 'radius': 15}
)
```

### Create Agent Decision
```python
from rise_pipeline.agent_models import create_agent_decision
from uuid import uuid4

decision = create_agent_decision(
    lead_id=uuid4(),
    decision_type='qualification',
    agent_name='claude_qualifier',
    agent_type='claude_agent',
    decision='qualified',
    confidence=0.87,
    reasoning='Active license, strong pain signals',
    metadata={'pain_score': 72, 'icp_score': 85}
)
```

### Log Audit Event
```python
from rise_pipeline.agent_models import create_audit_log

log = create_audit_log(
    actor='user@example.com',
    actor_type='human',
    action='discovery_started',
    resource_type='job',
    resource_id='job-uuid-here',
    metadata={'metro': 'austin'},
    severity='info'
)
```

### Check Rate Limit
```python
from rise_pipeline.agent_models import RateLimit

rate_limit = RateLimit(
    service_name='clay',
    window_start=datetime.utcnow(),
    request_count=47,
    quota_limit=1000,
    reset_at=datetime.utcnow() + timedelta(hours=1)
)

if rate_limit.is_exceeded():
    print(f"Rate limit exceeded! Wait until {rate_limit.reset_at}")
else:
    print(f"OK to proceed. {rate_limit.remaining()} requests remaining")
```

---

## 📋 Zapier Table Fields

### agent_jobs
```
id (UUID), job_type (Select), status (Select), initiated_by (Text),
parameters (Long Text/JSON), results (Long Text/JSON),
created_at (DateTime), completed_at (DateTime)
```

### agent_decisions
```
id (UUID), lead_id (Text/UUID), decision_type (Select),
agent_name (Text), decision (Text), confidence (Number 0-1),
reasoning (Long Text), overridden_by (Text), created_at (DateTime)
```

### audit_log
```
id (Auto-increment), timestamp (DateTime), actor (Text),
action (Text), resource_type (Text), resource_id (Text),
metadata (Long Text/JSON), severity (Select)
```

### rate_limits
```
id (UUID), service_name (Text), window_start (DateTime),
request_count (Number), quota_limit (Number), reset_at (DateTime)
```

---

## 🔍 Monitoring Queries

### Job Success Rate (Last 24h)
```sql
SELECT
    job_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status='completed') as completed,
    COUNT(*) FILTER (WHERE status='failed') as failed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status='completed') / COUNT(*), 2) as success_rate
FROM agent_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY job_type;
```

### Agent Override Rate
```sql
SELECT
    agent_name,
    COUNT(*) as total_decisions,
    COUNT(*) FILTER (WHERE overridden_by IS NOT NULL) as overrides,
    ROUND(100.0 * COUNT(*) FILTER (WHERE overridden_by IS NOT NULL) / COUNT(*), 2) as override_rate
FROM agent_decisions
GROUP BY agent_name
ORDER BY override_rate DESC;
```

### Rate Limit Usage
```sql
SELECT
    service_name,
    request_count,
    quota_limit,
    ROUND(100.0 * request_count / quota_limit, 2) as usage_percent,
    reset_at
FROM rate_limits
WHERE window_start >= date_trunc('hour', NOW())
ORDER BY usage_percent DESC;
```

---

## 🚨 Emergency Commands

### Reset Rate Limit
```sql
SELECT reset_rate_limit('clay');
```

### Clear Old Audit Logs
```sql
SELECT delete_old_audit_logs();
```

### Cancel Running Jobs
```sql
UPDATE agent_jobs
SET status = 'cancelled', updated_at = NOW()
WHERE status = 'running' AND created_at < NOW() - INTERVAL '1 hour';
```

---

## 📁 File Locations

| File | Location |
|------|----------|
| Migrations | `/supabase/migrations/*.sql` |
| Combined SQL | `/supabase/migrations/000_combined_migrations.sql` |
| Init Script | `/supabase/init_tables.py` |
| Python Models | `/rise_pipeline/agent_models.py` |
| Setup Guide | `/ZAPIER_TABLES_SETUP.md` |
| Full Docs | `/TABLES_SCHEMA_IMPLEMENTATION.md` |

---

## ⚡ Quick Tests

```bash
# Test 1: Verify tables exist
cd /home/user/rise-local-lead-creation/supabase
python init_tables.py

# Test 2: Query tables
psql $DATABASE_URL -c "SELECT COUNT(*) FROM agent_jobs;"

# Test 3: Create test record
python -c "
from rise_pipeline.agent_models import create_agent_job
job = create_agent_job('discovery', 'test', 'human', {})
print(f'Created: {job.id}')
"
```

---

**Quick Reference v1.0** | December 22, 2025
