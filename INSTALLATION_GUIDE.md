# COMPREHENSIVE INSTALLATION GUIDE
## Rise Local Lead Creation Pipeline

**Complete Multi-Agent Analysis - All Files Crawled**
**Generated:** 2025-12-23
**Status:** ✅ NO SYNTAX ERRORS FOUND

---

## TABLE OF CONTENTS

1. [System Requirements](#system-requirements)
2. [Dependencies Overview](#dependencies-overview)
3. [Installation Order](#installation-order)
4. [Environment Configuration](#environment-configuration)
5. [Service Verification](#service-verification)
6. [Troubleshooting](#troubleshooting)

---

## SYSTEM REQUIREMENTS

### Operating System
- **Supported:** Linux (Ubuntu 20.04+), macOS (11+), Windows 10/11 with WSL2
- **Recommended:** Linux (Ubuntu 22.04 LTS)

### Hardware
- **CPU:** 2+ cores (4+ recommended for Docker services)
- **RAM:** 4GB minimum, 8GB+ recommended
- **Storage:** 10GB available (for Docker images and data)
- **Network:** Stable internet connection for API calls

### Core Software Requirements
- **Python:** 3.10+ (tested on 3.11.14)
- **Node.js:** 18+ (for Puppeteer testing scripts)
- **Docker:** 24.0+ with Docker Compose v2
- **Git:** 2.30+

---

## DEPENDENCIES OVERVIEW

### Python Packages (14 core + 4 optional)

#### **Core Dependencies (All Services)**
```
anthropic>=0.39.0          # Claude AI integration
httpx>=0.27.2              # Async HTTP client
pydantic>=2.9.2            # Data validation
python-dotenv>=1.0.1       # Environment management
gspread>=6.1.4             # Google Sheets API
google-auth>=2.36.0        # Google authentication
supabase>=2.10.0           # Supabase client
```

#### **Web Scraping Services**
```
playwright==1.48.0         # Browser automation
beautifulsoup4==4.12.3     # HTML parsing
```

#### **FastAPI Services**
```
fastapi==0.115.4           # API framework
uvicorn==0.32.0            # ASGI server
```

#### **AI/ML Services**
```
google-generativeai==0.8.3 # Gemini API
Pillow==11.0.0             # Image processing
```

#### **API Clients**
```
smartystreets-python-sdk==4.18.8  # Address verification
```

### Node.js/NPM Packages
```json
{
  "puppeteer": "^24.33.0"  // Browser testing only
}
```

### Docker Base Images
- `python:3.11-slim` (2 services)
- `mcr.microsoft.com/playwright/python:v1.40.0-jammy` (3 services)
- `mcr.microsoft.com/playwright/python:v1.41.0-jammy` (1 service)

### External Services (35+ API Keys Required)

#### **Critical (Required for Core Functionality)**
- Supabase (PostgreSQL database)
- Anthropic Claude API
- Google Cloud (Places API, PageSpeed API, Gemini API)
- Clay API (lead enrichment)

#### **Optional (Feature-Specific)**
- Smarty (address verification)
- OpenAI (embeddings for RAG)
- Instantly (email delivery)
- GoHighLevel (CRM)
- Yext, FullEnrich, HeyReach, etc.

---

## INSTALLATION ORDER

Follow these steps **in exact order** to avoid dependency issues.

### **PHASE 1: System Prerequisites**

#### Step 1.1: Install Python 3.10+
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# macOS (Homebrew)
brew install python@3.11

# Verify
python3.11 --version  # Should show 3.11.x
```

#### Step 1.2: Install Docker & Docker Compose
```bash
# Ubuntu/Debian
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker  # Refresh group membership

# macOS
brew install --cask docker

# Verify
docker --version          # Should show 24.0+
docker compose version    # Should show v2.x
```

#### Step 1.3: Install Node.js (Optional - Testing Only)
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# macOS
brew install node@18

# Verify
node --version  # Should show v18.x+
npm --version   # Should show 9.x+
```

#### Step 1.4: Install Git
```bash
# Ubuntu/Debian
sudo apt install -y git

# macOS
brew install git

# Verify
git --version
```

---

### **PHASE 2: Repository Setup**

#### Step 2.1: Clone Repository
```bash
cd /home/user  # Or your preferred directory
git clone https://github.com/JSXSTEWART/rise-local-lead-creation.git
cd rise-local-lead-creation
```

#### Step 2.2: Create Python Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify
which python  # Should show path to venv/bin/python
```

---

### **PHASE 3: Python Dependencies**

#### Step 3.1: Upgrade pip & setuptools
```bash
pip install --upgrade pip setuptools wheel
```

#### Step 3.2: Install Core Dependencies
```bash
# Install root requirements
pip install -r requirements.txt

# Install rise_pipeline requirements (same as root, but ensures consistency)
pip install -r rise_pipeline/requirements.txt
```

#### Step 3.3: Install Custom Tools Dependencies
```bash
# Each custom tool has its own requirements
pip install -r custom_tools/address_verifier/requirements.txt
pip install -r custom_tools/bbb_scraper/requirements.txt
pip install -r custom_tools/owner_extractor/requirements.txt
pip install -r custom_tools/pagespeed_api/requirements.txt
pip install -r custom_tools/screenshot_service/requirements.txt
pip install -r custom_tools/tdlr_scraper/requirements.txt
```

**OR install all at once:**
```bash
pip install \
  anthropic>=0.39.0 \
  httpx>=0.27.2 \
  pydantic>=2.9.2 \
  python-dotenv>=1.0.1 \
  gspread>=6.1.4 \
  google-auth>=2.36.0 \
  supabase>=2.10.0 \
  fastapi==0.115.4 \
  uvicorn==0.32.0 \
  playwright==1.48.0 \
  google-generativeai==0.8.3 \
  beautifulsoup4==4.12.3 \
  Pillow==11.0.0 \
  smartystreets-python-sdk==4.18.8
```

#### Step 3.4: Install Playwright Browsers
```bash
playwright install chromium
```

This downloads ~300MB of Chromium browser binaries.

---

### **PHASE 4: Node.js Dependencies (Optional)**

Only needed for running Puppeteer testing scripts.

```bash
cd marketing/landing_pages
npm install
cd ../..
```

---

### **PHASE 5: Docker Services Setup**

#### Step 5.1: Configure Docker Environment
```bash
# Copy environment template
cp custom_tools/.env.example custom_tools/.env

# Edit with your API keys
nano custom_tools/.env  # Or use your preferred editor
```

**Required Variables for Docker Services:**
```env
GOOGLE_PAGESPEED_API_KEY=your-key-here
GOOGLE_GEMINI_API_KEY=your-key-here
SMARTY_AUTH_ID=your-id-here
SMARTY_AUTH_TOKEN=your-token-here
```

#### Step 5.2: Build Docker Images
```bash
cd custom_tools
docker compose build

# Expected build time: 5-10 minutes
# Total image size: ~6GB (4 Playwright images + 2 slim images)
```

#### Step 5.3: Start All Services
```bash
docker compose up -d

# Verify all containers started
docker compose ps
```

Expected output:
```
NAME                          STATUS    PORTS
address-verifier              Up        0.0.0.0:8006->8006/tcp
bbb-scraper                   Up        0.0.0.0:8002->8002/tcp
owner-extractor               Up        0.0.0.0:8005->8005/tcp
pagespeed-api                 Up        0.0.0.0:8003->8003/tcp
screenshot-service            Up        0.0.0.0:8004->8004/tcp
tdlr-scraper                  Up        0.0.0.0:8001->8001/tcp
```

#### Step 5.4: Verify Service Health
```bash
# Test each service
curl http://localhost:8001/health  # TDLR Scraper
curl http://localhost:8002/health  # BBB Scraper
curl http://localhost:8003/health  # PageSpeed API
curl http://localhost:8004/health  # Screenshot Service
curl http://localhost:8005/health  # Owner Extractor
curl http://localhost:8006/health  # Address Verifier
```

All should return: `{"status":"healthy","service":"service-name"}`

---

### **PHASE 6: Database Setup (Supabase)**

#### Step 6.1: Create Supabase Project
1. Go to https://supabase.com
2. Create new project: `rise-local-lead-creation`
3. Wait for database provisioning (~2 minutes)
4. Copy Project URL and Service Role Key

#### Step 6.2: Enable pgvector Extension
```sql
-- In Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Step 6.3: Create Tables

**Table: leads**
```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name TEXT,
    address_full TEXT,
    address_street TEXT,
    address_city TEXT,
    address_state TEXT DEFAULT 'TX',
    address_zip TEXT,
    phone TEXT,
    website TEXT,
    google_rating NUMERIC,
    google_review_count INTEGER,
    place_id TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT NOW(),

    -- Pre-qualification data
    visual_score INTEGER,
    design_era TEXT,
    mobile_responsive BOOLEAN,
    performance_score INTEGER,
    mobile_score INTEGER,
    seo_score INTEGER,
    accessibility_score INTEGER,
    has_https BOOLEAN,
    lcp_ms INTEGER,
    fid_ms INTEGER,
    cls NUMERIC,
    license_status TEXT,
    owner_name TEXT,
    license_number TEXT,
    license_type TEXT,
    bbb_rating TEXT,
    bbb_accredited BOOLEAN,
    complaints_total INTEGER,
    complaints_3yr INTEGER,
    years_in_business INTEGER,
    is_residential BOOLEAN,
    address_type TEXT,

    -- Tech enrichment (Clay)
    has_gtm BOOLEAN,
    has_ga4 BOOLEAN,
    cms_platform TEXT,
    crm_platform TEXT,
    has_booking_system BOOLEAN,
    tech_stack_score INTEGER,
    has_chat_widget BOOLEAN,
    tech_analysis JSONB,
    tech_stack_ai_score INTEGER,
    website_type TEXT,
    tech_analysis_model TEXT,
    tech_analysis_at TIMESTAMP,

    -- Contact enrichment
    owner_email TEXT,
    owner_first_name TEXT,
    owner_last_name TEXT,
    owner_linkedin_url TEXT,
    owner_phone TEXT,
    verified_email BOOLEAN,
    owner_source TEXT,

    -- Scoring
    pre_qualification_score INTEGER,
    pre_qualification_status TEXT,
    pain_score INTEGER,
    icp_score INTEGER
);

-- Create indexes
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_created_at ON leads(created_at);
CREATE INDEX idx_leads_website ON leads(website);
```

**Table: knowledge_documents (RAG)**
```sql
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    metadata JSONB DEFAULT '{}',
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX ON knowledge_documents USING ivfflat (embedding vector_cosine_ops);
```

**Table: email_templates (RAG)**
```sql
CREATE TABLE email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    use_case TEXT NOT NULL,
    pain_points TEXT[] DEFAULT '{}',
    performance_score FLOAT DEFAULT 0,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON email_templates USING ivfflat (embedding vector_cosine_ops);
```

#### Step 6.4: Create RPC Functions

**Function: match_knowledge_documents**
```sql
CREATE OR REPLACE FUNCTION match_knowledge_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    category TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kd.id,
        kd.title,
        kd.content,
        kd.category,
        kd.metadata,
        1 - (kd.embedding <=> query_embedding) AS similarity
    FROM knowledge_documents kd
    WHERE
        (filter_category IS NULL OR kd.category = filter_category)
        AND 1 - (kd.embedding <=> query_embedding) > match_threshold
    ORDER BY kd.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

**Function: match_email_templates**
```sql
CREATE OR REPLACE FUNCTION match_email_templates(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.6,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    subject_template TEXT,
    body_template TEXT,
    use_case TEXT,
    pain_points TEXT[],
    performance_score FLOAT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        et.id,
        et.name,
        et.subject_template,
        et.body_template,
        et.use_case,
        et.pain_points,
        et.performance_score,
        1 - (et.embedding <=> query_embedding) AS similarity
    FROM email_templates et
    WHERE 1 - (et.embedding <=> query_embedding) > match_threshold
    ORDER BY et.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

### **PHASE 7: Environment Configuration**

#### Step 7.1: Copy Environment Template
```bash
cd /home/user/rise-local-lead-creation
cp .env.example .env
```

#### Step 7.2: Configure Required Variables

**Edit .env file:**
```bash
nano .env  # Or use your preferred editor
```

**Minimum Required Configuration:**
```env
# Database (CRITICAL)
SUPABASE_URL=https://jitawzicdwgbhatvjblh.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here

# AI Services (CRITICAL)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
GOOGLE_GEMINI_API_KEY=your-gemini-api-key

# Lead Enrichment (CRITICAL for Clay integration)
CLAY_API_KEY=your-clay-api-key
CLAY_BUILTWITH_TABLE_ID=your-table-id
CLAY_CONTACT_TABLE_ID=your-table-id

# Performance & Analysis (RECOMMENDED)
GOOGLE_PAGESPEED_API_KEY=your-pagespeed-key
SMARTY_AUTH_ID=your-smarty-id
SMARTY_AUTH_TOKEN=your-smarty-token

# Optional Services
OPENAI_API_KEY=sk-your-openai-key  # For RAG embeddings
INSTANTLY_API_KEY=your-instantly-key
GHL_API_KEY=your-ghl-key
YEXT_API_KEY=your-yext-key
```

**Optional Google Sheets Integration:**
```env
GOOGLE_SHEET_ID=your-sheet-id-here
GOOGLE_SHEETS_CREDENTIALS_PATH=.credentials/google-sheets-key.json
```

---

### **PHASE 8: Google Sheets Setup (Optional but Recommended)**

#### Step 8.1: Create Google Cloud Project
1. Go to https://console.cloud.google.com
2. Create project: `rise-local-pipeline`
3. Enable APIs:
   - Google Sheets API
   - Google Drive API

#### Step 8.2: Create Service Account
```bash
# In Google Cloud Console
1. IAM & Admin → Service Accounts
2. Create Service Account: pipeline-bot@rise-local-pipeline.iam.gserviceaccount.com
3. Grant role: Editor
4. Create JSON key
5. Download as google-sheets-key.json
```

#### Step 8.3: Store Credentials Securely
```bash
mkdir -p .credentials
mv ~/Downloads/google-sheets-key.json .credentials/
chmod 600 .credentials/google-sheets-key.json
```

#### Step 8.4: Create Google Sheet
```bash
# Run setup script
python setup_google_sheet.py
```

This creates a sheet with tabs:
- `qualified_leads` (v2 unified tab)
- `leads_for_tech_enrichment` (legacy)
- `leads_for_contact_enrichment` (legacy)

#### Step 8.5: Share Sheet with Service Account
1. Open Google Sheet
2. Click "Share"
3. Add: `pipeline-bot@rise-local-pipeline.iam.gserviceaccount.com`
4. Permission: Editor

---

### **PHASE 9: Verification & Testing**

#### Step 9.1: Test Python Installation
```bash
source venv/bin/activate
python -c "import anthropic, httpx, supabase; print('✅ Core imports successful')"
```

#### Step 9.2: Test Docker Services
```bash
cd custom_tools

# Test TDLR Scraper (Port 8001)
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"license_number": "TECL12345"}'

# Test BBB Scraper (Port 8002)
curl -X POST http://localhost:8002/scrape \
  -H "Content-Type: application/json" \
  -d '{"business_name": "ABC Electric", "city": "Austin", "state": "TX"}'

# Test PageSpeed (Port 8003)
curl -X POST http://localhost:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test Screenshot Service (Port 8004)
curl -X POST http://localhost:8004/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test Owner Extractor (Port 8005)
curl -X POST http://localhost:8005/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Test Address Verifier (Port 8006)
curl -X POST http://localhost:8006/verify \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701"}'
```

#### Step 9.3: Test Supabase Connection
```bash
python -c "
from rise_pipeline.services import SupabaseClient
import asyncio

async def test():
    client = SupabaseClient()
    # Test connection by querying leads table
    leads = await client.get_leads_by_status('new', limit=1)
    print(f'✅ Supabase connection successful. Found {len(leads)} leads.')

asyncio.run(test())
"
```

#### Step 9.4: Run Test Pipeline
```bash
# Test with a single professional lead
python test_professional_lead.py
```

Expected output:
```
✅ Lead created in Supabase
✅ Pre-qualification completed
✅ Scoring calculated
✅ Status updated
```

---

## SERVICE VERIFICATION

### Quick Health Check Script
```bash
#!/bin/bash
# Save as check_services.sh

echo "🔍 Checking Docker Services..."
for port in 8001 8002 8003 8004 8005 8006; do
    response=$(curl -s http://localhost:$port/health)
    if [[ $response == *"healthy"* ]]; then
        echo "✅ Port $port: healthy"
    else
        echo "❌ Port $port: FAILED"
    fi
done

echo ""
echo "🔍 Checking Python Environment..."
python -c "
try:
    import anthropic, httpx, supabase, playwright
    print('✅ Python dependencies installed')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
"

echo ""
echo "🔍 Checking Environment Variables..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'ANTHROPIC_API_KEY', 'CLAY_API_KEY']
missing = [var for var in required if not os.getenv(var)]

if missing:
    print(f'❌ Missing variables: {', '.join(missing)}')
else:
    print('✅ All critical environment variables set')
"
```

Run with:
```bash
chmod +x check_services.sh
./check_services.sh
```

---

## TROUBLESHOOTING

### Common Installation Issues

#### Issue 1: Docker Permission Denied
**Symptom:**
```
Got permission denied while trying to connect to the Docker daemon socket
```

**Solution:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

#### Issue 2: Playwright Install Fails
**Symptom:**
```
Error: Chromium not found
```

**Solution:**
```bash
# Install system dependencies first (Ubuntu)
sudo apt install -y libgbm1 libasound2

# Then install browsers
playwright install chromium
playwright install-deps chromium
```

#### Issue 3: Port Already in Use
**Symptom:**
```
Error: bind: address already in use
```

**Solution:**
```bash
# Find process using port (example: 8001)
sudo lsof -i :8001
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

#### Issue 4: Python Module Not Found
**Symptom:**
```
ModuleNotFoundError: No module named 'anthropic'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

#### Issue 5: Supabase Connection Timeout
**Symptom:**
```
httpx.ConnectTimeout: Connection timeout
```

**Solution:**
1. Check internet connection
2. Verify SUPABASE_URL is correct
3. Check firewall settings
4. Verify Supabase project is not paused

#### Issue 6: Google Sheets Authentication Failed
**Symptom:**
```
ValueError: No credentials found
```

**Solution:**
```bash
# Option 1: Application Default Credentials
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive

# Option 2: Service Account Key
export GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/google-sheets-key.json
```

#### Issue 7: Docker Compose Not Found
**Symptom:**
```
docker-compose: command not found
```

**Solution:**
```bash
# Use docker compose (v2 syntax)
docker compose up -d

# Or install docker-compose-v2
sudo apt install docker-compose-v2
```

---

## POST-INSTALLATION CHECKLIST

- [ ] Python 3.10+ installed and verified
- [ ] Docker and Docker Compose installed
- [ ] Virtual environment created and activated
- [ ] All Python dependencies installed
- [ ] Playwright browsers installed
- [ ] Docker services built and running (ports 8001-8006)
- [ ] All 6 Docker services show "healthy" status
- [ ] Supabase project created with tables and RPC functions
- [ ] .env file configured with all required API keys
- [ ] Supabase connection test passed
- [ ] Optional: Google Sheets set up and shared with service account
- [ ] Optional: Clay tables configured for enrichment
- [ ] Test pipeline executed successfully

---

## NEXT STEPS

After successful installation:

1. **Run Discovery Pipeline:**
   ```bash
   python rise_pipeline/pipeline.py --city "Austin" --state "TX" --industry "electrician"
   ```

2. **Run Pre-Qualification:**
   ```bash
   python run_prequalification_batch.py --all
   ```

3. **Run Phase 2 Intelligence:**
   ```bash
   python run_phase_2_batch.py --all --batch-size 5
   ```

4. **Access Dashboard:**
   ```bash
   # Serve dashboard locally
   cd dashboard
   python -m http.server 8080
   # Open http://localhost:8080
   ```

5. **Configure Clay Integration:**
   - See `docs/CLAY_WORKFLOW.md`
   - See `docs/SETUP_GOOGLE_SHEETS.md`

---

## SUPPORT & DOCUMENTATION

- **Architecture:** `docs/ARCHITECTURE.md`
- **Troubleshooting:** `docs/TROUBLESHOOTING.md`
- **Clay Workflow:** `docs/CLAY_WORKFLOW.md`
- **Google Sheets Setup:** `docs/SETUP_GOOGLE_SHEETS.md`
- **Dashboard Usage:** `docs/DASHBOARD_USAGE.md`
- **Project Status:** `CLAUDE_CONTEXT.md`

---

## APPENDIX: Complete Environment Variable Reference

```env
# ============================================
# CRITICAL - REQUIRED FOR CORE FUNCTIONALITY
# ============================================

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here

# AI Services
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
GOOGLE_GEMINI_API_KEY=your-gemini-api-key

# Lead Enrichment
CLAY_API_KEY=your-clay-api-key
CLAY_BUILTWITH_TABLE_ID=your-table-id
CLAY_CONTACT_TABLE_ID=your-table-id

# ============================================
# RECOMMENDED - FOR FULL FUNCTIONALITY
# ============================================

# Performance Analysis
GOOGLE_PAGESPEED_API_KEY=your-pagespeed-key

# Address Verification
SMARTY_AUTH_ID=your-smarty-id
SMARTY_AUTH_TOKEN=your-smarty-token

# Embeddings (RAG System)
OPENAI_API_KEY=sk-your-openai-key

# ============================================
# OPTIONAL - FEATURE-SPECIFIC
# ============================================

# Google Sheets Integration
GOOGLE_SHEET_ID=your-sheet-id
GOOGLE_SHEETS_CREDENTIALS_PATH=.credentials/google-sheets-key.json

# Directory Services
YEXT_API_KEY=your-yext-key
YEXT_ACCOUNT_ID=939444

# Email Delivery
INSTANTLY_API_KEY=your-instantly-key
INSTANTLY_CAMPAIGN_ID=your-campaign-id

# CRM Integration
GHL_API_KEY=your-ghl-key
GHL_LOCATION_ID=your-location-id

# LinkedIn Outreach
HEYREACH_API_KEY=your-heyreach-key
HEYREACH_CAMPAIGN_ID=your-campaign-id

# Contact Enrichment
FULLENRICH_API_KEY=your-fullenrich-key
FULLENRICH_WEBHOOK_URL=https://your-webhook-url

# AI Quality Control
CLEANLAB_TLM_API_KEY=your-cleanlab-key
HALLUCINATION_THRESHOLD=0.7

# Local Docker Services
TDLR_SCRAPER_URL=http://localhost:8001
BBB_SCRAPER_URL=http://localhost:8002
PAGESPEED_API_URL=http://localhost:8003
SCREENSHOT_SERVICE_URL=http://localhost:8004
OWNER_EXTRACTOR_URL=http://localhost:8005
ADDRESS_VERIFIER_URL=http://localhost:8006

# ============================================
# ADVANCED CONFIGURATION
# ============================================

# RAG Settings
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_MATCH_THRESHOLD=0.7
RAG_MATCH_COUNT=5

# Pipeline Settings
DEFAULT_STATE=TX
DEFAULT_INDUSTRY=electrician
BATCH_SIZE=10
MAX_CONCURRENT_REQUESTS=5
```

---

**Installation Guide Complete**
**Status:** Ready for deployment
**Last Updated:** 2025-12-23
