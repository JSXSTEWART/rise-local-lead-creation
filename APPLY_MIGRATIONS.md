# Apply Database Migrations - Step-by-Step Guide

**Status:** ⚠️ Migrations NOT YET APPLIED
**Verification:** Run `python3 scripts/verify_migrations.py` to check status

---

## 🎯 Quick Start (Choose One Method)

### Method 1: Interactive HTML Viewer (Easiest) ⭐

1. **Open the migration viewer:**
   ```bash
   open scripts/migrations_viewer.html
   # Or: xdg-open scripts/migrations_viewer.html
   # Or: Use your browser to open the file
   ```

2. **Click "Copy SQL" button**

3. **Go to Supabase Dashboard:**
   https://supabase.com/dashboard/project/bvnllbpqstcrynehjvan/editor

4. **Paste and Run** (Ctrl+V → Ctrl+Enter)

5. **Verify** with the button or run:
   ```bash
   python3 scripts/verify_migrations.py
   ```

---

### Method 2: Command Line Copy-Paste

1. **Copy the SQL:**
   ```bash
   cat supabase/migrations/000_combined_migrations.sql
   ```

2. **Select all output** (Click + drag, or Ctrl+A)

3. **Copy to clipboard** (Ctrl+C or Cmd+C)

4. **Go to Supabase:**
   https://supabase.com/dashboard/project/bvnllbpqstcrynehjvan/editor

5. **SQL Editor → New Query → Paste → Run**

---

### Method 3: Direct File Upload (If Available)

Some Supabase projects support file upload:

1. Go to SQL Editor
2. Look for "Upload SQL file" option
3. Select: `supabase/migrations/000_combined_migrations.sql`
4. Click "Run"

---

## 📋 Detailed Step-by-Step

### Step 1: Verify Current Status

```bash
cd /home/user/rise-local-lead-creation
python3 scripts/verify_migrations.py
```

**Expected output:**
```
⚠️  INCOMPLETE - Some tables are missing

Missing:
  ❌ agent_jobs
  ❌ agent_decisions
  ❌ audit_log
  ❌ rate_limits
```

---

### Step 2: Access Supabase Dashboard

**Dashboard URL:**
https://supabase.com/dashboard/project/bvnllbpqstcrynehjvan

**Direct SQL Editor:**
https://supabase.com/dashboard/project/bvnllbpqstcrynehjvan/editor

**Login credentials:**
- Use your Supabase account email/password
- Project ID: `bvnllbpqstcrynehjvan`

---

### Step 3: Navigate to SQL Editor

1. **Click "SQL Editor"** in left sidebar
2. **Click "New Query"** button (top right)
3. You'll see an empty SQL editor

---

### Step 4: Get Migration SQL

**Option A: Use HTML viewer (recommended)**
```bash
open scripts/migrations_viewer.html
# Click "Copy SQL" button
```

**Option B: Terminal**
```bash
# Display and copy manually
cat supabase/migrations/000_combined_migrations.sql

# Or copy to clipboard (if xclip installed)
cat supabase/migrations/000_combined_migrations.sql | xclip -selection clipboard
```

**Option C: Python script**
```bash
python3 scripts/apply_migrations.py
# Follow the instructions printed
```

---

### Step 5: Paste SQL into Editor

1. **Click inside the SQL editor** (big text area)
2. **Paste** (Ctrl+V on Linux/Windows, Cmd+V on Mac)
3. You should see 307 lines of SQL

**What you'll see:**
- CREATE TABLE statements
- CREATE INDEX statements
- CREATE FUNCTION statements
- Comments and documentation

---

### Step 6: Run Migration

1. **Click the "Run" button** (or press Ctrl+Enter)
2. **Wait** 2-5 seconds for execution
3. **Look for success message** at bottom:
   - "Success. No rows returned" ✅
   - Or "Success. Rows returned: 0" ✅

**If you see errors:**
- Red error message will appear
- Common issues:
  - Already applied (safe to ignore)
  - Permission denied (need service role key)
  - Syntax error (check copy-paste)

---

### Step 7: Verify Tables Created

**In Supabase Dashboard:**

1. Go to "Table Editor" (left sidebar)
2. Look for new tables:
   - `agent_jobs`
   - `agent_decisions`
   - `audit_log`
   - `rate_limits`

**Or run verification query:**

In SQL Editor, run:
```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('agent_jobs', 'agent_decisions', 'audit_log', 'rate_limits')
ORDER BY tablename;
```

**Expected result:** 4 rows

---

### Step 8: Verify from Terminal

```bash
python3 scripts/verify_migrations.py
```

**Expected output:**
```
🎉 SUCCESS! All migrations applied

Tables created:
  ✅ agent_jobs
  ✅ agent_decisions
  ✅ audit_log
  ✅ rate_limits

✅ Your database is ready!
```

---

## 🧪 Test Your Setup

Once migrations are applied, test the qualification endpoint:

```bash
curl -X POST http://localhost:8080/api/agents/claude/invoke-sync \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "qualification_validator",
    "mode": "standard",
    "job_id": "test-migration-001",
    "lead_id": "lead-migration-001",
    "context": {
      "business_name": "Test Electric Company",
      "website": "https://example.com",
      "city": "Austin",
      "state": "TX",
      "preliminary_pain_score": 75,
      "pain_signals": [
        "Outdated website",
        "No online booking",
        "Poor mobile experience"
      ]
    }
  }'
```

**Expected Response:**
```json
{
  "decision": "qualified",
  "confidence": 0.85,
  "pain_score": 78,
  "category": "DIY_CEILING",
  "top_pain_points": [...],
  "reasoning": "...",
  "red_flags": []
}
```

**No more 500 errors!** ✅

---

## 🔍 What Gets Created

### Tables (4)

**1. agent_jobs**
- Tracks all agent-initiated jobs
- Fields: job_type, status, parameters, results
- 13 columns, 5 indexes

**2. agent_decisions**
- Stores all agent decisions
- Fields: decision, confidence, reasoning
- 12 columns, 6 indexes

**3. audit_log**
- Comprehensive audit trail
- Fields: actor, action, metadata
- Row-Level Security enabled
- 10 columns, 7 indexes

**4. rate_limits**
- API rate limiting
- Fields: service_name, request_count, quota
- 7 columns, 1 index

### Functions (3)

1. `update_updated_at_column()` - Auto-update timestamps
2. `check_rate_limit()` - Check API quotas
3. `increment_rate_limit()` - Increment counters
4. `reset_rate_limit()` - Reset limits

### Indexes (20+ total)

Optimized for:
- Fast job lookups
- Decision queries
- Audit log searches
- Rate limit checks

---

## 🛠️ Troubleshooting

### Error: "permission denied"

**Cause:** Using anon key instead of service role key

**Fix:**
1. Check `.env` file has `SUPABASE_SERVICE_KEY`
2. Verify it's the service role key (longer, starts with `eyJ...`)
3. Not the anon key (public key)

---

### Error: "relation already exists"

**Cause:** Migrations already applied (partially or fully)

**Fix:**
This is usually safe! Tables already exist.

**To verify:**
```bash
python3 scripts/verify_migrations.py
```

**To start fresh (DANGER - deletes data):**
```sql
-- Only if you want to reset
DROP TABLE IF EXISTS agent_jobs CASCADE;
DROP TABLE IF EXISTS agent_decisions CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS rate_limits CASCADE;

-- Then re-run migrations
```

---

### Error: "syntax error at or near..."

**Cause:** SQL not copied correctly

**Fix:**
1. Make sure you copied the **entire** file
2. Check for missing lines at start/end
3. Use the HTML viewer for reliable copy
4. Or download the SQL file directly

---

### Still getting 500 errors after migrations

**Check:**

1. **Tables exist:**
   ```bash
   python3 scripts/verify_migrations.py
   ```

2. **Agent server restarted:**
   ```bash
   kill $(cat agents/agent_server.pid)
   cd agents
   source venv/bin/activate
   set -a && source .env && set +a
   uvicorn api_server:app --host 0.0.0.0 --port 8080 &
   ```

3. **Check logs:**
   ```bash
   tail -50 agents/agent_server.log
   ```

---

## 📊 Migration Details

```
File: supabase/migrations/000_combined_migrations.sql
Size: 15,727 bytes
Lines: 307 lines
Tables: 4 tables
Indexes: 20+ indexes
Functions: 3 PostgreSQL functions
Triggers: 1 auto-update trigger
Policies: 3 Row-Level Security policies
```

---

## ✅ Success Checklist

After applying migrations, you should have:

- [x] 4 tables created in Supabase
- [x] Verification script shows all green ✅
- [x] Qualification endpoint returns 200 (not 500)
- [x] Decisions are logged to `agent_decisions` table
- [x] Jobs are tracked in `agent_jobs` table
- [x] API fully functional

---

## 🚀 Next Steps

1. **Apply migrations** (this guide)
2. **Test qualification endpoint**
3. **Process test leads** (10-20)
4. **Monitor accuracy**
5. **Configure Zapier workflows**
6. **Scale to production**

---

## 📞 Need Help?

**Verification:**
```bash
python3 scripts/verify_migrations.py
```

**Helper Script:**
```bash
python3 scripts/apply_migrations.py
```

**HTML Viewer:**
```bash
open scripts/migrations_viewer.html
```

**Documentation:**
- DEPLOYMENT_STATUS.md
- DEPLOYMENT_CHECKLIST.md
- TABLES_SCHEMA_IMPLEMENTATION.md

---

**Last Updated:** December 22, 2025
**Status:** Ready to apply
**Estimated Time:** 5 minutes
