# Rise Local Lead Creation - Troubleshooting Guide

> Complete context for debugging and fixing pipeline issues

---

## Pipeline Architecture

### Pipeline Flow

```
Stage 1: Fetch Lead from Supabase
    ↓
Stage 2: Load Tech Enrichment (from Clay import)
    ↓
Stage 3: Parallel Intelligence Gathering
    ├── Screenshot Service (8004) → Visual Analysis
    ├── PageSpeed API (8003) → Technical Scores
    ├── Yext API → Directory Presence
    ├── TDLR Scraper (8001) → License Info
    ├── BBB Scraper (8002) → Reputation Data
    └── Address Verifier (8006) → Residential Check
    ↓ (ALL MUST COMPLETE BEFORE NEXT STAGE)
Stage 4: Calculate Pain Score
    ↓
Stage 5: Qualification Decision
    ├─→ REJECTED → Update DB → Exit
    ├─→ MARGINAL → Update DB → Exit
    └─→ QUALIFIED → Continue
        ↓
Stage 6: Load Contact Info (from Clay import)
        ↓
Stage 7: Generate Email (Claude API)
        ↓
Stage 8: Deliver (Instantly + HeyReach + GHL)
        ↓
Stage 9: Final DB Update
```

---

## Diagnostic Commands

### 1. Check Docker Service Status

```bash
cd custom_tools
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output:**
```
NAMES                 STATUS                  PORTS
screenshot-service    Up X hours (healthy)    0.0.0.0:8004->8004/tcp
tdlr-scraper         Up X hours (healthy)    0.0.0.0:8001->8001/tcp
owner-extractor      Up X hours (healthy)    0.0.0.0:8005->8005/tcp
pagespeed-api        Up X hours (healthy)    0.0.0.0:8003->8003/tcp
bbb-scraper          Up X hours (healthy)    0.0.0.0:8002->8002/tcp
address-verifier     Up X hours (healthy)    0.0.0.0:8006->8006/tcp
```

### 2. Test Each Service Individually

**TDLR Scraper (8001):**
```bash
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"license_number": "TECL12345", "owner_name": "Smith,John", "business_name": "ABC Electric"}'
```

**BBB Scraper (8002):**
```bash
curl -X POST http://localhost:8002/scrape \
  -H "Content-Type: application/json" \
  -d '{"business_name": "ABC Electric", "city": "Dallas", "state": "TX"}'
```

**PageSpeed API (8003):**
```bash
curl -X POST http://localhost:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Screenshot Service (8004):**
```bash
curl -X POST http://localhost:8004/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "use_ai": true}'
```

**Owner Extractor (8005):**
```bash
curl -X POST http://localhost:8005/extract \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://example.com/about"}'
```

**Address Verifier (8006):**
```bash
curl -X POST http://localhost:8006/verify \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St, Dallas, TX 75201"}'
```

### 3. Test Supabase Connectivity

```bash
# Read test
curl "$SUPABASE_URL/rest/v1/leads?select=id,business_name,status&limit=5" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY"
```

### 4. Run Pipeline with Debug Logging

**Single Lead Test:**
```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
python -m rise_pipeline.pipeline --lead-id <lead-uuid-here>
```

---

## Common Issues & Fixes

### Issue 1: `asyncio.gather()` Not Awaited Properly

**Symptom:** Stage 3 completes too fast, missing data in later stages

**Fix:**
```python
# ✅ CORRECT - Await the gather
results = await asyncio.gather(
    service1(),
    service2(),
    service3()
)
```

### Issue 2: Database Update Before Data Ready

**Symptom:** Status updated to "qualified" but pain_score is NULL

**Fix:** Ensure data is calculated BEFORE the update call.

### Issue 3: Timeout Too Short for Slow Services

**Symptom:** Services fail with "timeout" but actually just slow

**Fix:**
```python
client = httpx.AsyncClient(timeout=httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=5.0,
    pool=5.0
))
```

---

## Testing Checklist

### Before Making Changes
- [ ] Verify all Docker containers healthy
- [ ] Check .env file has all keys
- [ ] Run single-lead test to establish baseline

### After Making Changes
- [ ] Restart Docker containers if service code changed
- [ ] Run single-lead test with debug logging
- [ ] Verify data persists in Supabase
- [ ] Check processing time (should be <15s)

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `rise_pipeline/pipeline.py` | Main orchestrator |
| `rise_pipeline/services.py` | Service clients |
| `rise_pipeline/scoring.py` | Pain calculation |
| `rise_pipeline/models.py` | Data structures |
| `rise_pipeline/config.py` | Environment vars |

---

## Emergency Fixes

### If Pipeline Hangs

```bash
# Find Python processes
ps aux | grep python

# Kill hung pipeline
pkill -f "rise_pipeline.pipeline"

# Check Docker
docker ps
docker restart <container-name>
```
