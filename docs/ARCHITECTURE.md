# Rise Local Lead Pipeline v2 - Implementation Document

**Version:** 2.0
**Last Updated:** December 14, 2024
**Status:** Active

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Key v2 Changes](#key-v2-changes)
3. [Services & Ports](#services--ports)
4. [API Keys Inventory](#api-keys-inventory)
5. [Pipeline Flow](#pipeline-flow)
6. [Phase Breakdown](#phase-breakdown)
7. [Testing Checklist](#testing-checklist)
8. [Common Issues & Solutions](#common-issues--solutions)

---

## Key v2 Changes

### Before (v1): Clay First, Expensive
```
Discovery → Clay BuiltWith → Custom Scrapers → Scoring → Clay Waterfall → Outreach
           ↑ PAID                                        ↑ PAID
           (ALL leads)                                   (ALL leads)
```

### After (v2): FREE Scrapers First, Clay Only for Qualified
```
Discovery → FREE Scrapers → Pre-Qualification → Clay (BuiltWith + Waterfall) → Outreach
            ↑ $0 COST       ↑ FILTER HERE      ↑ PAID (QUALIFIED ONLY)
            (ALL leads)     (reject bad leads) (ONE action, ONE import)
```

### Cost Savings
- **v1**: Clay enrichment on 1000 leads = ~$500-1000
- **v2**: Clay enrichment on ~200 qualified leads = ~$100-200 (80% savings!)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RISE LOCAL LEAD PIPELINE v2                          │
│                 "FREE Scrapers First, Clay Only for Qualified"          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ══════════════════════════════════════════════════════════════════════ │
│  STAGE 1: DISCOVERY (FREE)                                              │
│  ══════════════════════════════════════════════════════════════════════ │
│  └─> Google Places API → Supabase (raw leads with website, rating)      │
│                                                                          │
│  ══════════════════════════════════════════════════════════════════════ │
│  STAGE 2: FREE PRE-QUALIFICATION (LOCAL DOCKER - $0 COST)               │
│  ══════════════════════════════════════════════════════════════════════ │
│  ├─> Screenshot Service (8004) → visual_score, design_era               │
│  ├─> PageSpeed API (8003) → performance_score, mobile_score             │
│  ├─> Owner Extractor (8005) → owner_name, license_number                │
│  ├─> TDLR Scraper (8001) → license_status (waterfall search)            │
│  ├─> BBB Scraper (8002) → bbb_rating, complaints                        │
│  └─> Address Verifier (8006) → is_residential                           │
│                                                                          │
│  ══════════════════════════════════════════════════════════════════════ │
│  STAGE 3: PRE-QUALIFICATION SCORING (FREE)                              │
│  ══════════════════════════════════════════════════════════════════════ │
│  └─> Pain scoring based on FREE data only                               │
│      ├─> Score ≤ 3: REJECTED (stop here, save money)                    │
│      ├─> Score 4-5: MARGINAL (review manually)                          │
│      └─> Score ≥ 6: QUALIFIED (proceed to Clay)                         │
│                                                                          │
│  ══════════════════════════════════════════════════════════════════════ │
│  STAGE 4: CLAY ENRICHMENT - QUALIFIED LEADS ONLY (PAID)                 │
│  ══════════════════════════════════════════════════════════════════════ │
│  └─> ONE Clay Table with BOTH enrichments:                              │
│      ├─> BuiltWith Tech Stack (CMS, GTM, GA4, CRM, Booking)             │
│      └─> Contact Waterfall (Dropcontact → Hunter → Apollo)              │
│      = ONE manual import action in dashboard                            │
│                                                                          │
│  ══════════════════════════════════════════════════════════════════════ │
│  STAGE 5: FINAL SCORING + OUTREACH                                      │
│  ══════════════════════════════════════════════════════════════════════ │
│  ├─> Final pain score with tech data                                    │
│  ├─> AI email generation                                                │
│  └─> Instantly / GHL delivery                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Services & Ports

### Docker Services (custom_tools/)

| Service | Port | Container Name | Phase | Description |
|---------|------|----------------|-------|-------------|
| TDLR Scraper | 8001 | tdlr-scraper | 2D | Texas license verification (waterfall search) |
| BBB Scraper | 8002 | bbb-scraper | 2E | Better Business Bureau rating lookup |
| PageSpeed API | 8003 | pagespeed-api | 2B | Google PageSpeed Insights wrapper |
| Screenshot Service | 8004 | screenshot-service | 2A | Visual analysis with Gemini Vision |
| Owner Extractor | 8005 | owner-extractor | 2D-PREP | Extract owner name from website |
| Address Verifier | 8006 | address-verifier | 2F | Residential vs commercial check |

### Docker Commands

```bash
# Start all services
cd custom_tools
docker compose up -d

# Check status
docker ps

# View logs for specific service
docker logs tdlr-scraper -f
docker logs owner-extractor -f

# Rebuild after code changes
docker compose build screenshot-service
docker compose up -d screenshot-service

# Health check all services
curl http://localhost:8001/health  # TDLR
curl http://localhost:8002/health  # BBB
curl http://localhost:8003/health  # PageSpeed
curl http://localhost:8004/health  # Screenshot
curl http://localhost:8005/health  # Owner Extractor
curl http://localhost:8006/health  # Address Verifier
```

### External APIs

| Service | Purpose | Endpoint |
|---------|---------|----------|
| Supabase | Database | https://jitawzicdwgbhatvjblh.supabase.co |
| Clay | Tech + Contact enrichment | https://api.clay.com/v3/tables/ |
| Yext | Directory listings | https://api.yext.com/v2/ |
| Google Places | Lead discovery | Google Places API |
| Google PageSpeed | Performance scores | PageSpeed Insights API |
| Google Gemini | AI vision analysis | Gemini 2.0 Flash |
| Smarty | Address verification | us-street.api.smarty.com |

---

## API Keys Inventory

### Required Keys (Currently Configured)

| Key | Status | Used In | Notes |
|-----|--------|---------|-------|
| SUPABASE_SERVICE_KEY | ✅ Active | Database | Service role key |
| GOOGLE_PAGESPEED_API_KEY | ✅ Active | PageSpeed API | Also used for Places |
| GOOGLE_GEMINI_API_KEY | ✅ Active | Screenshot + Owner Extractor | Gemini 2.0 Flash |
| SMARTY_AUTH_ID | ✅ Active | Address Verifier | 250 free/month |
| SMARTY_AUTH_TOKEN | ✅ Active | Address Verifier | Paired with ID |
| YEXT_API_KEY | ✅ Active | Yext directory | Async-only results |
| CLAY_API_KEY | ✅ Active | Tech + Contact enrichment | See .env.example |
| ANTHROPIC_API_KEY | ✅ Active | Email generation | Claude API |
| INSTANTLY_API_KEY | ✅ Active | Email sending | Future use |

### Optional/Future Keys

| Key | Status | Purpose |
|-----|--------|---------|
| GHL_API_KEY | ⏳ Pending | GoHighLevel CRM sync |
| BATCHLEADS_API_KEY | ⏳ Pending | Skip trace |
| FULLENRICH_API_KEY | ⏳ Pending | Contact waterfall |
| HEYREACH_API_KEY | ⏳ Pending | LinkedIn outreach |

---

## Pipeline Flow

### NEW in v2: Owner Extraction → TDLR Waterfall

The key improvement in v2 is using the Owner Extractor to get owner name from the website BEFORE searching TDLR. This dramatically improves license match rates.

```
TDLR Search Order (Waterfall):
1. License Number (if found on website) → Most accurate
2. Owner Name (Last, First format) → High accuracy
3. Business Name → Fallback (often fails)
```

### Complete Flow Sequence

```python
# Phase 2: Intelligence Gathering Flow
async def gather_all(lead, website_url):

    # STEP 1: Extract owner info FIRST (KEY!)
    owner_data = await get_owner_extraction(lead)
    # Returns: owner_first_name, owner_last_name, license_number

    # STEP 2: Run remaining services in parallel
    visual, pagespeed, yext, tdlr, bbb, address = await asyncio.gather(
        get_visual_analysis(lead),           # Port 8004
        get_pagespeed(lead),                 # Port 8003
        get_yext_listings(lead),             # Yext API
        get_tdlr_license(lead, owner_data),  # Port 8001 (with waterfall!)
        get_bbb_reputation(lead),            # Port 8002
        get_address_verification(lead)       # Port 8006
    )

    return visual, pagespeed, yext, tdlr, bbb, address
```

---

## Phase Breakdown

### STAGE 1: Lead Discovery (FREE)
- **Input:** City, industry keywords
- **Process:** Google Places API search
- **Output:** Raw leads in Supabase `leads` table
- **Fields:** business_name, address, phone, website, google_rating, review_count
- **Cost:** FREE (within Google API limits)

---

### STAGE 2: FREE Pre-Qualification Scrapers

All these run BEFORE Clay to filter out bad leads and save money.

#### 2A: Visual Analysis
- **Service:** Screenshot Service (port 8004)
- **Input:** Website URL
- **Process:** Capture screenshot → Gemini Vision analysis
- **Output:**
  - `visual_score` (1-100)
  - `design_era` (Modern/Dated/Legacy/Template)
  - `has_hero_image`, `has_clear_cta`
  - `mobile_responsive`

### Phase 2B: Technical Performance
- **Service:** PageSpeed API (port 8003)
- **Input:** Website URL
- **Process:** Google PageSpeed Insights
- **Output:**
  - `performance_score` (0-100)
  - `mobile_score` (0-100)
  - `seo_score`, `accessibility_score`
  - Core Web Vitals: LCP, FID, CLS

### Phase 2C: Directory Presence
- **Service:** Yext API (external)
- **Status:** SKIPPED - Yext is async-only, no polling
- **Output:** `listings_score`, `listings_found` (placeholder)

### Phase 2D-PREP: Owner Extraction (NEW!)
- **Service:** Owner Extractor (port 8005)
- **Input:** Website URL
- **Process:** Screenshot → Claude Vision → Extract owner info
- **Output:**
  - `owner_first_name`, `owner_last_name`
  - `license_number` (if displayed on website)
  - `confidence` (low/medium/high)

### Phase 2D: License Verification
- **Service:** TDLR Scraper (port 8001)
- **Input:** Owner data from 2D-PREP + business name
- **Process:** Waterfall search (license → owner → business name)
- **Output:**
  - `license_status` (Active/Expired/Not Found)
  - `license_number`
  - `owner_name` (legal name from TDLR)
  - `license_type`

### Phase 2E: Reputation Check
- **Service:** BBB Scraper (port 8002)
- **Input:** Business name, city, state
- **Process:** BBB website search
- **Output:**
  - `bbb_rating` (A+, A, B, etc. or "NR")
  - `bbb_accredited` (boolean)
  - `complaints_total`, `complaints_3yr`
  - `years_in_business`

#### 2F: Address Verification
- **Service:** Address Verifier (port 8006)
- **Input:** Business address
- **Process:** Smarty API lookup
- **Output:**
  - `is_residential` (boolean)
  - `address_type` (residential/commercial/unknown)
  - `verified` (boolean)
- **Cost:** FREE (250/month Smarty free tier)

---

### STAGE 3: Pre-Qualification Scoring (FREE)

**THIS IS THE GATE - Decides who goes to Clay**

- **Input:** All Stage 2 FREE scraper data (NO tech stack yet)
- **Process:** Python scoring logic based on visual, performance, license, BBB, address
- **Output:**
  - `pre_qualification_score` (numeric)
  - `pre_qualification_status` (qualified/marginal/rejected)

**Auto-Disqualifiers (Instant Rejection):**
| Condition | Action | Rationale |
|-----------|--------|-----------|
| License expired/revoked/suspended | AUTO REJECT | Cannot legally operate |

**Pre-Qualification Signals (FREE data only):**

| Signal | Points | Source | Notes |
|--------|--------|--------|-------|
| Visual score < 40 | +3 | Screenshot | Very outdated |
| Visual score 40-59 | +2 | Screenshot | Average design |
| Design era = Legacy/Dated | +2 | Screenshot | Old look |
| Not mobile responsive | +2 | Screenshot | Major UX issue |
| No clear CTA | +1 | Screenshot | Missing conversion |
| Missing trust signals | +1 | Screenshot | No badges/certs |
| Performance < 50 | +2 | PageSpeed | Bottom 25% |
| Performance 50-64 | +1 | PageSpeed | Below median (65) |
| No HTTPS | +2 | PageSpeed | Security issue |
| Slow LCP > 4s | +1 | PageSpeed | Slow page load |
| Google rating < 4.0 | +1 | Google Places | Below average |
| < 100 reviews | +1 | Google Places | Less established |
| Residential address | +2 | Address Verifier | Small operation |
| BBB complaints > 3 | **-2** | BBB | Red flag |
| Recent BBB complaints | **-1** | BBB | Warning sign |

**Pre-Qualification Thresholds:**
- Score ≤ 2: **REJECTED** → Stop here, don't send to Clay
- Score 3-4: **MARGINAL** → Manual review
- Score ≥ 5: **QUALIFIED** → Send to Clay enrichment

**PageSpeed Thresholds (based on 57 lead analysis):**
- Average: 64.8 | Median: 65 | P25: 50 | P75: 74

---

### STAGE 4: Clay Enrichment (PAID - Qualified Only)

**ONE Clay table, ONE manual action, BOTH enrichments**

- **Input:** Only leads with `pre_qualification_status = 'qualified'`
- **Process:** Single Clay table with two enrichment columns:
  1. **BuiltWith Tech Stack** → CMS, GTM, GA4, CRM, booking system
  2. **Contact Waterfall** → Owner email, phone (Dropcontact → Hunter → Apollo)
- **Output:**
  - `tech_analysis` (JSONB) - Full tech stack
  - `tech_stack_ai_score` (0-10)
  - `website_type` - "DIY Builder", "Professional", etc.
  - `owner_email`, `owner_phone`, `owner_linkedin`
- **Cost:** ~$0.50-1.00 per lead (but only for qualified leads!)

**Dashboard Workflow:**
```
1. Click "Export to Clay" button (exports qualified leads)
2. Wait for Clay to process (few minutes)
3. Click "Import from Clay" button (imports enriched data)
4. Done - ONE action instead of TWO
```

---

### STAGE 5: Final Scoring + Outreach

- **Input:** Pre-qualification data + Clay tech/contact data
- **Process:**
  1. Final pain score with full tech stack analysis
  2. AI email generation using pain points
  3. Delivery via Instantly or GHL
- **Output:**
  - `final_pain_score`
  - `generated_email`
  - `outreach_status`

**Final Scoring Thresholds:**
- Score ≤ 3: REJECTED
- Score 4-5: MARGINAL
- Score ≥ 6: QUALIFIED for outreach

---

## Clay Table Setup (ONE Combined Table)

### Table Structure

Create ONE Clay table named `rise_local_qualified_leads` with these columns:

**Input Columns (from Google Sheets/Pipeline):**
| Column | Type | Description |
|--------|------|-------------|
| lead_id | Text | Supabase UUID |
| business_name | Text | Company name |
| website | URL | Website URL |
| owner_first_name | Text | From Owner Extractor |
| owner_last_name | Text | From Owner Extractor |
| city | Text | Business city |
| state | Text | TX |

**BuiltWith Enrichment Columns (auto-populated by Clay):**
| Column | Type | Clay Integration |
|--------|------|------------------|
| technologies_list | Text | BuiltWith → All Technologies |
| cms_platform | Text | BuiltWith → CMS |
| has_gtm | Boolean | BuiltWith → Contains "Google Tag Manager" |
| has_ga4 | Boolean | BuiltWith → Contains "Google Analytics 4" |
| crm_detected | Text | BuiltWith → CRM |
| booking_system | Text | BuiltWith → Scheduling |
| tech_count | Number | BuiltWith → Technology Count |

**Contact Waterfall Columns (auto-populated by Clay):**
| Column | Type | Clay Integration |
|--------|------|------------------|
| owner_email | Email | Waterfall: Dropcontact → Hunter → Apollo |
| owner_email_confidence | Number | Confidence score |
| owner_business_phone | Phone | Waterfall enrichment |
| owner_personal_email | Email | Personal email if found |
| owner_linkedin | URL | LinkedIn profile |
| enrichment_source | Text | Which service found the data |

### Clay Waterfall Setup

In Clay, create an enrichment column with this waterfall order:
1. **Dropcontact** - Best for EU/professional emails
2. **Hunter.io** - Good coverage, fast
3. **Apollo.io** - Large database, good for US

### Google Sheets Integration (Automated Sync)

Instead of manual CSV export/import, use Google Sheets as the bridge:

```
Pipeline → Google Sheet → Clay (auto-reads) → Clay enriches → Google Sheet (auto-writes) → Pipeline imports
```

**Setup Steps:**
1. Create Google Sheet with input columns
2. Share with service account
3. Configure Clay to read from Google Sheet
4. Configure Clay to write results back
5. Pipeline reads enriched data from Google Sheet

See: `SETUP_GUIDE_Google_Sheets_Clay_Automation.md` for detailed setup.

---

## Implementation TODO

### Already Done ✅
- [x] Owner Extractor service (port 8005)
- [x] TDLR Waterfall search (license → owner → business)
- [x] Screenshot Service with Gemini Vision
- [x] PageSpeed API wrapper
- [x] BBB Scraper
- [x] Address Verifier
- [x] Basic pain scoring logic

### Needs Implementation 🔨

#### 1. Pre-Qualification Scoring (Without Tech Data)
```python
# New function needed in scoring.py
def calculate_pre_qualification_score(
    lead: Lead,
    visual: VisualAnalysis,
    technical: TechnicalScores,
    license_info: LicenseInfo,
    reputation: ReputationData,
    address: AddressVerification
) -> PreQualificationScore:
    """Score lead using FREE data only - NO tech stack"""
    pass
```

#### 2. Dashboard Updates
- [ ] Add "Export Qualified to Clay" button
- [ ] Add "Import from Clay" button
- [ ] Remove separate BuiltWith/Waterfall buttons
- [ ] Add pre-qualification status column

#### 3. Google Sheets Automation
- [ ] Set up Google Cloud project
- [ ] Create service account
- [ ] Share Google Sheet with service account
- [ ] Test GoogleSheetsClient connection
- [ ] Configure Clay to read/write Google Sheet

#### 4. Combined Clay Table
- [ ] Create new Clay table with both enrichments
- [ ] Configure BuiltWith columns
- [ ] Configure Contact Waterfall columns
- [ ] Test end-to-end flow

#### 5. New Batch Processor
```bash
# New script needed
python run_prequalification_batch.py --limit 100
# Runs FREE scrapers only, sets pre_qualification_status
```

---

## Testing Checklist

### Pre-Test: Verify All Services Running

```bash
# Quick health check all services
curl -s http://localhost:8001/health | jq .
curl -s http://localhost:8002/health | jq .
curl -s http://localhost:8003/health | jq .
curl -s http://localhost:8004/health | jq .
curl -s http://localhost:8005/health | jq .
curl -s http://localhost:8006/health | jq .
```

Expected: `{"status": "healthy", "service": "service-name"}`

### Individual Service Tests

#### 1. Owner Extractor (Port 8005)
```bash
curl -X POST http://localhost:8005/extract-owner \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example-electric.com", "lead_id": "test-1"}'
```
**Expected:** `owner_first_name`, `owner_last_name`, `license_number` (if displayed)

#### 2. TDLR Scraper - Waterfall (Port 8001)
```bash
curl -X POST http://localhost:8001/search/waterfall \
  -H "Content-Type: application/json" \
  -d '{
    "license_number": "32689",
    "owner_first_name": "Michael",
    "owner_last_name": "Galvez",
    "business_name": "Big Shoulders Texas",
    "city": "Austin"
  }'
```
**Expected:** `license_status: "Active"`, `owner_name`, `license_number`

#### 3. Screenshot Service (Port 8004)
```bash
curl -X POST http://localhost:8004/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "include_mobile": true}'
```
**Expected:** `visual_score` (NOT 50), `design_era`, `mobile_responsive`

#### 4. PageSpeed API (Port 8003)
```bash
curl -X POST http://localhost:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "strategy": "mobile"}'
```
**Expected:** `performance_score`, `mobile_score`, `lcp_ms`, `cls`

#### 5. BBB Scraper (Port 8002)
```bash
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"business_name": "ACL Electric", "city": "Austin", "state": "TX"}'
```
**Expected:** `bbb_rating` or `"Not Found"`

#### 6. Address Verifier (Port 8006)
```bash
curl -X POST http://localhost:8006/verify \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St", "city": "Austin", "state": "TX", "zip_code": "78701"}'
```
**Expected:** `is_residential`, `address_type`, `verified`

### Integration Test (1 Lead)

```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
python run_phase_2_batch.py --lead-id <uuid> --batch-size 1
```

### Batch Test (10 Leads)

```bash
python run_phase_2_batch.py --limit 10 --batch-size 5
```

---

## Common Issues & Solutions

### Issue: visual_score always 50
**Cause:** Screenshot service timeout or wait strategy issue
**Solution:** Rebuild screenshot-service with `load` instead of `networkidle`
```bash
docker compose build screenshot-service
docker compose up -d screenshot-service
```

### Issue: TDLR returns "Not Found" for valid businesses
**Cause:** TDLR name/business searches are unreliable - only license number search is highly accurate
**Solution:** Prioritize extracting license numbers from websites
```
TDLR Waterfall Reliability:
1. License Number search → 95%+ accurate (GOLDEN PATH)
2. Owner Name search → ~50% accurate (formatting issues)
3. Business Name search → ~30% accurate (often fails)
```
**Key insight:** Focus on extracting TECL license numbers from websites. Many TX electricians display their license on their website (often in footer or About page).

### Issue: Owner Extractor fails
**Cause:** Claude API rate limit or no owner info on website
**Solution:** Check Gemini API key, some sites don't display owner

### Issue: Address Verifier returns "unknown"
**Cause:** Smarty API rate limit (250 free/month)
**Solution:** Check Smarty dashboard for remaining credits

### Issue: BBB returns "Not Found"
**Cause:** Business not registered with BBB (expected for many small businesses)
**Solution:** This is normal - not all businesses are BBB registered

---

## File Locations

```
Rise Local Lead Creation/
├── .env                          # All API keys
├── run_phase_2_batch.py          # Main batch processor
├── rise_pipeline/
│   ├── config.py                 # Service URLs and config
│   ├── services.py               # Service integrations (updated for waterfall)
│   ├── models.py                 # Data models
│   ├── scoring.py                # Pain point scoring logic
│   └── pipeline.py               # Full pipeline orchestration
├── custom_tools/
│   ├── docker-compose.yml        # All Docker services
│   ├── tdlr_scraper/             # Port 8001
│   ├── bbb_scraper/              # Port 8002
│   ├── pagespeed_api/            # Port 8003
│   ├── screenshot_service/       # Port 8004
│   ├── owner_extractor/          # Port 8005
│   └── address_verifier/         # Port 8006
└── LEAD_PIPELINE_V2_IMPLEMENTATION.md  # THIS FILE
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2024 | Initial pipeline with business name TDLR search |
| 2.0 | Dec 14, 2024 | Added Owner Extractor + TDLR Waterfall search |
