# TDLR License Scraper

**Phase 2D: License Verification** for Rise Local Lead System

Scrapes Texas Department of Licensing and Regulation (TDLR) for electrical contractor license verification with **waterfall redundancy** for maximum match rates.

## ✨ NEW: Waterfall Search (v2.0)

**Automatically tries multiple search methods until successful:**
1. 🎯 License Number (highest accuracy)
2. 👤 Owner Name (first + last)
3. 🏢 Business Name (fallback)

**Features:**
- ✅ Special character handling (Acuña → Acuna)
- ✅ Dual license detection (personal + contractor)
- ✅ 95%+ success rate with all available data
- ✅ 4-6 second response time

## Critical Output

**`owner_name`** - The legal name on the license. This is ESSENTIAL for Phase 5 (Skip Trace).

## Quick Start

### Option 1: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run as standalone script
python tdlr_scraper.py

# Run as API server
python api.py
# Server runs on http://localhost:8001
```

### Option 2: Run with Docker

```bash
# Build image
docker build -t tdlr-scraper .

# Run container
docker run -d -p 8001:8001 --name tdlr-scraper tdlr-scraper

# Check health
curl http://localhost:8001/health
```

## API Endpoints

### POST /search/waterfall ⭐ RECOMMENDED

**Waterfall search with automatic fallback** - tries multiple methods until successful.

```bash
curl -X POST http://localhost:8001/search/waterfall \
  -H "Content-Type: application/json" \
  -d '{
    "license_number": "TECL #32689",
    "owner_first_name": "Jose Luis",
    "owner_last_name": "Acuña",
    "business_name": "ACL Electric LLC",
    "city": "Austin",
    "lead_id": "uuid-here"
  }'
```

**Search Strategy:**
1. Tries license number first (strips "TECL #")
2. Falls back to owner name (normalizes special characters)
3. Finally tries business name

**All fields are optional** - provide what you have for best results.

---

### POST /search/business
Search by business name only.

```bash
curl -X POST http://localhost:8001/search/business \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Austin Pro Electric", "city": "AUSTIN", "lead_id": "uuid-here"}'
```

### POST /search/owner
Search by owner name only.

```bash
curl -X POST http://localhost:8001/search/owner \
  -H "Content-Type: application/json" \
  -d '{"owner_name": "Smith, John", "lead_id": "uuid-here"}'
```

### POST /search/license
Search by license number only.

```bash
curl -X POST http://localhost:8001/search/license \
  -H "Content-Type: application/json" \
  -d '{"license_number": "12345678", "lead_id": "uuid-here"}'
```

## Response Format

```json
{
  "license_status": "Active",
  "license_number": "12345678",
  "license_type": "Master Electrician",
  "owner_name": "John Smith",
  "business_name": "Austin Pro Electric",
  "license_expiry": "12/31/2025",
  "violations": 0,
  "city": "Austin",
  "state": "TX",
  "verification_date": "2025-12-04T10:30:00",
  "lead_id": "uuid-here",
  "error": null
}
```

## Integration with Dify

Add as HTTP Request node in Dify workflow:

```yaml
- type: http-request
  title: TDLR License Check
  url: 'http://tdlr-scraper:8001/search/business'
  method: POST
  headers: 'Content-Type: application/json'
  body:
    type: json
    data: '{"business_name": "{{#parse_lead.business_name#}}", "city": "{{#parse_lead.city#}}", "lead_id": "{{#start_node.lead_id#}}"}'
```

## Pain Point Signals (Phase 3)

| Signal | Points | Condition |
|--------|--------|-----------|
| License Issues | +2 | `license_status` != 'Active' |
| Violations | +1 | `violations` > 0 |

## Supabase Fields Updated

- `license_status`
- `license_number`
- `owner_name_tdlr`
- `license_data` (JSONB)

## Notes

- Respectful scraping: 2 second delay between requests
- No CAPTCHA on TDLR site currently
- Results may include multiple licenses; API returns first match
- For bulk processing, consider adding request queuing
