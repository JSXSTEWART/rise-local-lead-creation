# Rise Local Lead System - Custom Tools

Custom intelligence gathering tools for the Rise Local lead generation pipeline.
These tools must be running before the Dify workflow can execute Phase 2.

## Quick Start

```bash
# Start all services
docker compose up -d

# Check health
curl http://localhost:8001/health  # TDLR Scraper
curl http://localhost:8002/health  # BBB Scraper
curl http://localhost:8003/health  # PageSpeed API
curl http://localhost:8004/health  # Screenshot Service
```

## Services

| Service | Port | Phase | Purpose |
|---------|------|-------|---------|
| tdlr-scraper | 8001 | 2D | License Verification (extracts owner_name) |
| bbb-scraper | 8002 | 2E | Reputation Analysis |
| pagespeed-api | 8003 | 2B | Technical Scores |
| screenshot-service | 8004 | 2A | Visual Analysis |

## Environment Variables

Create a `.env` file (optional):

```env
# Optional: Increases PageSpeed API rate limits
GOOGLE_PAGESPEED_API_KEY=your-key-here

# Optional: Enables AI-powered visual analysis
GOOGLE_GEMINI_API_KEY=your-key-here
```

## API Documentation

### TDLR Scraper (Phase 2D)

**POST /search/business**
```json
{
  "business_name": "Austin Pro Electric",
  "city": "AUSTIN",
  "lead_id": "uuid-here"
}
```

**Response:**
```json
{
  "license_status": "Active",
  "license_number": "12345678",
  "license_type": "Master Electrician",
  "owner_name": "John Smith",
  "license_expiry": "12/31/2025"
}
```

### BBB Scraper (Phase 2E)

**POST /search**
```json
{
  "business_name": "Austin Pro Electric",
  "city": "Austin",
  "state": "TX",
  "google_rating": 4.2,
  "lead_id": "uuid-here"
}
```

**Response:**
```json
{
  "bbb_rating": "A+",
  "bbb_accredited": true,
  "complaints_3yr": 2,
  "reputation_gap": -0.3
}
```

### PageSpeed API (Phase 2B)

**POST /analyze**
```json
{
  "url": "https://example.com",
  "strategy": "mobile",
  "lead_id": "uuid-here"
}
```

**Response:**
```json
{
  "performance_score": 65,
  "mobile_score": 72,
  "seo_score": 85,
  "has_https": true
}
```

### Screenshot Service (Phase 2A)

**POST /analyze**
```json
{
  "url": "https://example.com",
  "include_mobile": true,
  "lead_id": "uuid-here"
}
```

**Response:**
```json
{
  "visual_score": 75,
  "design_era": "Modern",
  "mobile_responsive": true,
  "social_links": {
    "facebook": "https://facebook.com/example"
  }
}
```

## Dify Integration

These services integrate with Dify via HTTP Request nodes. See `dify_tool_configs/` for OpenAPI specifications.

## Pain Point Signals

Each service contributes to the 15-signal pain point scoring:

| Service | Signals |
|---------|---------|
| TDLR | License Issues (+2) |
| BBB | Poor BBB (+1), Many Complaints (+2) |
| PageSpeed | Slow Site (+2), Poor Mobile (+2), Bad SEO (+1) |
| Screenshot | Poor Design (+2), Dated (+1), No Social (+1), No Mobile (+2) |

## Testing Guide (Step-by-Step)

### Step 1: Populate Test Leads via Supabase Edge Function

First, create a list of ~20 real electricians in Dallas using the Google Places API:

```bash
# Get your Supabase project URL and anon key from the dashboard
# Get the Dallas-Fort Worth metro_area_id from metro_areas table

curl -X POST https://YOUR-PROJECT.supabase.co/functions/v1/discover-leads \
  -H "Authorization: Bearer YOUR-ANON-KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "metro_area_id": "DALLAS-METRO-UUID",
    "zip_code": "75201",
    "radius_miles": 15
  }'
```

**What this does:**
- Searches Google Places for "electrician OR electrical contractor" near Dallas 75201
- Applies ICP filters (rating 3.5-4.3, reviews 10-50)
- Saves qualified leads to the `leads` table with business_name, website, phone, address
- Returns stats: places_found, leads_created, API costs

**Verify leads were created:**
```sql
SELECT id, business_name, website, address_city, google_rating
FROM leads
WHERE address_city ILIKE '%dallas%' OR address_city ILIKE '%fort worth%'
LIMIT 20;
```

### Step 2: Start Docker Containers

```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation\custom_tools"
docker compose up -d --build
```

**Note:** First build takes ~5 minutes (downloads ~595MB Playwright image).

### Step 3: Verify All Services Are Healthy (Health Checks)

```bash
curl http://localhost:8001/health  # TDLR: {"status":"healthy","service":"tdlr-scraper"}
curl http://localhost:8002/health  # BBB:  {"status":"healthy","service":"bbb-scraper"}
curl http://localhost:8003/health  # PageSpeed: {"status":"healthy","service":"pagespeed-api"}
curl http://localhost:8004/health  # Screenshot: {"status":"healthy","service":"screenshot-service"}
```

### Step 4: Quick Test Each Service (Sample Data)

#### A. Screenshot Service (WORKS - No API Key Needed)
```bash
curl -X POST http://localhost:8004/analyze -H "Content-Type: application/json" -d "{\"url\": \"https://www.example.com\", \"include_screenshots\": false}"
```
**Expected:** Returns `visual_score`, `design_era`, `mobile_responsive`, `social_links`
**Note:** Without Gemini API key, uses heuristic analysis (still functional).

#### B. PageSpeed API (Free Tier - Limited Quota)
```bash
curl -X POST http://localhost:8003/analyze -H "Content-Type: application/json" -d "{\"url\": \"https://www.example.com\"}"
```
**Expected:** Returns `performance_score`, `mobile_score`, `seo_score`
**Note:** Free tier has low quota. Add `GOOGLE_PAGESPEED_API_KEY` for higher limits.

#### C. BBB Scraper (Works - Scrapes BBB.org)
```bash
curl -X POST http://localhost:8002/search -H "Content-Type: application/json" -d "{\"business_name\": \"ABC Electric\", \"city\": \"Austin\", \"state\": \"TX\"}"
```
**Expected:** Returns `bbb_rating`, `bbb_accredited`, `complaints_3yr`, or `"No BBB listing found"`

#### D. TDLR Scraper (NEEDS UPDATE - Website Changed)
```bash
curl -X POST http://localhost:8001/search/business -H "Content-Type: application/json" -d "{\"business_name\": \"Austin Electric\"}"
```
**Known Issue:** Timeout on `#LicenseType` selector - TDLR.texas.gov website structure has changed.
**TODO:** Update selectors to match current TDLR website layout.

Other TDLR endpoints:
- `POST /search/license` - Search by license number
- `POST /search/owner` - Search by owner name

### Step 5: Test Custom Tools Against Real Leads

Now use the Dallas electricians from Step 1 to test each service:

```sql
-- Get a lead with a website to test
SELECT id, business_name, website, phone, address_city
FROM leads
WHERE website IS NOT NULL
LIMIT 1;
```

**Example: Test with a real lead's website (replace with actual data):**

```bash
# Screenshot Service - analyze their website design
curl -X POST http://localhost:8004/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://LEAD-WEBSITE-HERE.com", "include_screenshots": false, "lead_id": "LEAD-UUID"}'

# PageSpeed API - check their site performance
curl -X POST http://localhost:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://LEAD-WEBSITE-HERE.com", "lead_id": "LEAD-UUID"}'

# BBB Scraper - check their BBB reputation
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"business_name": "LEAD-BUSINESS-NAME", "city": "Dallas", "state": "TX", "lead_id": "LEAD-UUID"}'

# TDLR Scraper - verify their electrical license (needs fix)
curl -X POST http://localhost:8001/search/business \
  -H "Content-Type: application/json" \
  -d '{"business_name": "LEAD-BUSINESS-NAME", "lead_id": "LEAD-UUID"}'
```

**Loop through multiple leads (bash example):**
```bash
# Get 5 leads and test Screenshot Service on each
for url in $(psql -t -c "SELECT website FROM leads WHERE website IS NOT NULL LIMIT 5"); do
  echo "Testing: $url"
  curl -s -X POST http://localhost:8004/analyze \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$url\", \"include_screenshots\": false}"
  echo ""
done
```

### Step 6: Check Docker Logs (If Issues)

```bash
docker logs tdlr-scraper --tail 30
docker logs bbb-scraper --tail 30
docker logs pagespeed-api --tail 30
docker logs screenshot-service --tail 30
```

### Test Results Summary (Dec 2024)

| Service | Status | Notes |
|---------|--------|-------|
| Screenshot Service | ✅ Working | Heuristic mode works without Gemini key |
| PageSpeed API | ✅ Working | Free tier quota limited |
| BBB Scraper | ✅ Working | Returns structured data |
| TDLR Scraper | ⚠️ Needs Fix | Selectors outdated for current TDLR website |

---

## Troubleshooting

**Services won't start:**
```bash
# Check logs
docker compose logs tdlr-scraper

# Rebuild
docker compose build --no-cache
docker compose up -d
```

**Playwright issues:**
```bash
# Ensure browsers are installed
docker compose exec tdlr-scraper playwright install chromium
```

**High memory usage:**
The Playwright-based services (TDLR, BBB, Screenshot) use browser instances.
Consider running on a machine with at least 4GB RAM.
