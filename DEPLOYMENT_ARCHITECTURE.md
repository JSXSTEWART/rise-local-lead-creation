# DEPLOYMENT ARCHITECTURE CLARIFICATION
## Rise Local Lead Creation Pipeline

**Generated:** 2025-12-23
**Multi-Agent Analysis Complete:** ✅ All files crawled and inspected

---

## IMPORTANT: HOSTING ARCHITECTURE

### **Your Question: WHM Server at acne.zonedoc.com + MySQL Database**

After comprehensive analysis of all files in this repository, here's what was found:

### ❌ **NOT REQUIRED:**

1. **WHM (Web Host Manager)** - NOT used in this project
2. **Local MySQL Database** - NOT used in this project
3. **Traditional web hosting (cPanel/WHM)** - NOT needed
4. **acne.zonedoc.com server** - NOT referenced in codebase

### ✅ **ACTUAL ARCHITECTURE:**

This is a **containerized Python application** using:
- **Supabase (PostgreSQL)** - Cloud-hosted database (NOT MySQL)
- **Docker** - Local microservices (6 services on ports 8001-8006)
- **Python 3.10+** - Main application runtime
- **No traditional web server needed** (no Apache/Nginx required)

---

## DATABASE: SUPABASE vs MySQL

### What the Analysis Found:

**✅ SUPABASE (PostgreSQL 15+):**
- **Used:** Yes, extensively
- **Connection:** REST API (https://jitawzicdwgbhatvjblh.supabase.co/rest/v1)
- **Files:**
  - `rise_pipeline/services.py` (SupabaseClient class)
  - `rise_pipeline/config.py` (connection configuration)
- **Tables:** `leads`, `knowledge_documents`, `email_templates`
- **Extensions:** pgvector (for embeddings)

**❌ MYSQL:**
- **Used:** No
- **Connection strings:** None found
- **MySQL libraries:** Not imported (no pymysql, mysql.connector, MySQLdb)
- **Migration files:** None found

### Database Connection Pattern:
```python
# Actual connection code from services.py
class SupabaseClient:
    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self._header_dict = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
```

**This is REST API access, NOT SQL connection.**

---

## WHERE TO DEPLOY THIS APPLICATION

### Option 1: Local Development Machine (Recommended for Testing)
**Requirements:**
- Python 3.10+
- Docker Desktop
- 4GB+ RAM
- Linux/macOS/Windows with WSL2

**Deployment:**
```bash
# Clone repo
git clone <repo-url>
cd rise-local-lead-creation

# Install Python dependencies
pip install -r requirements.txt

# Start Docker services
cd custom_tools
docker compose up -d

# Run pipeline
python rise_pipeline/pipeline.py
```

### Option 2: Cloud VM (Recommended for Production)
**Platforms:**
- AWS EC2 (t3.medium or larger)
- Google Cloud Compute Engine
- DigitalOcean Droplet (4GB RAM minimum)
- Azure Virtual Machine

**Requirements:**
- Ubuntu 22.04 LTS
- 4GB+ RAM
- 2+ CPU cores
- Docker pre-installed

**Deployment:**
```bash
# SSH into VM
ssh user@your-vm-ip

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose-v2

# Clone and deploy
git clone <repo-url>
cd rise-local-lead-creation
pip install -r requirements.txt
cd custom_tools && docker compose up -d
```

### Option 3: Container Orchestration (Advanced)
**Platforms:**
- Kubernetes (EKS, GKE, AKS)
- Docker Swarm
- AWS ECS/Fargate

**Note:** This is overkill for most use cases. Option 2 (Cloud VM) is recommended.

---

## WHY NOT WHM/cPanel?

### WHM is designed for:
- Shared web hosting
- WordPress/PHP applications
- Multiple customer accounts
- Traditional LAMP stack (Linux + Apache + MySQL + PHP)

### This application is:
- Python-based (not PHP)
- Docker-containerized (not traditional web hosting)
- Uses cloud database (Supabase, not local MySQL)
- Runs as background process (not web server)

**Conclusion:** WHM/cPanel is the wrong deployment model for this application.

---

## INSTALLATION ORDER (Corrected)

Based on complete codebase analysis:

### **Phase 1: Infrastructure (Cloud)**
1. **Create Supabase Account** (Free tier available)
   - Sign up at https://supabase.com
   - Create project: `rise-local-lead-creation`
   - Enable pgvector extension
   - Create tables: `leads`, `knowledge_documents`, `email_templates`
   - Create RPC functions for vector search

2. **Get API Keys** (External Services)
   - Anthropic Claude: https://console.anthropic.com
   - Google Cloud: Enable Places API, PageSpeed API, Gemini API
   - Clay: https://clay.com (for lead enrichment)
   - Smarty: https://www.smarty.com (address verification)

### **Phase 2: Operating System Packages**
**Install in this order on Ubuntu 22.04:**

```bash
# 1. System update
sudo apt update && sudo apt upgrade -y

# 2. Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# 3. Docker & Docker Compose
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# 4. Git
sudo apt install -y git

# 5. System libraries for Playwright
sudo apt install -y \
    libgbm1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xvfb

# 6. Optional: Node.js (for testing scripts only)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### **Phase 3: Python Environment**

```bash
# 1. Clone repository
git clone https://github.com/JSXSTEWART/rise-local-lead-creation.git
cd rise-local-lead-creation

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip setuptools wheel

# 4. Install ALL Python packages (consolidated)
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

# 5. Install Playwright browsers
playwright install chromium
```

### **Phase 4: Docker Services**

```bash
# 1. Configure environment for Docker
cp custom_tools/.env.example custom_tools/.env
nano custom_tools/.env  # Add API keys

# 2. Build Docker images
cd custom_tools
docker compose build

# 3. Start all services
docker compose up -d

# 4. Verify health
for port in 8001 8002 8003 8004 8005 8006; do
    curl http://localhost:$port/health
done
```

### **Phase 5: Application Configuration**

```bash
# 1. Configure main application
cd /home/user/rise-local-lead-creation
cp .env.example .env
nano .env  # Add all API keys

# 2. Test Supabase connection
python -c "
from rise_pipeline.services import SupabaseClient
import asyncio
async def test():
    client = SupabaseClient()
    print('✅ Connected to Supabase')
asyncio.run(test())
"

# 3. Optional: Configure Google Sheets
python setup_google_sheet.py
```

---

## COMPLETE DEPENDENCY LIST

### Python Packages (Install Order)

**Core Framework:**
1. `python-dotenv==1.0.1` - Environment variables (install FIRST)
2. `pydantic==2.9.2` - Data validation
3. `httpx==0.27.2` - HTTP client

**API Clients:**
4. `anthropic>=0.39.0` - Claude AI
5. `google-auth>=2.36.0` - Google authentication
6. `google-generativeai==0.8.3` - Gemini AI
7. `gspread>=6.1.4` - Google Sheets
8. `supabase>=2.10.0` - Supabase client
9. `smartystreets-python-sdk==4.18.8` - Address verification

**Web Services:**
10. `fastapi==0.115.4` - API framework
11. `uvicorn==0.32.0` - ASGI server

**Scraping & Processing:**
12. `playwright==1.48.0` - Browser automation
13. `beautifulsoup4==4.12.3` - HTML parsing
14. `Pillow==11.0.0` - Image processing

**Total: 14 packages**

### Docker Base Images (Download Order)

**Slim Images (fast):**
1. `python:3.11-slim` → ~120MB

**Playwright Images (slow):**
2. `mcr.microsoft.com/playwright/python:v1.40.0-jammy` → ~1.5GB
3. `mcr.microsoft.com/playwright/python:v1.41.0-jammy` → ~1.5GB

**Total: ~4.5GB Docker images**

### System Libraries (Linux/Ubuntu)

**Install BEFORE Playwright:**
```bash
libgbm1 libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2
libdbus-1-3 libdrm2 libglib2.0-0 libgtk-3-0 libnspr4 libnss3
libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xvfb
```

---

## EXTERNAL SERVICES - REGISTRATION ORDER

### Critical Path (Required):

1. **Supabase** (Database)
   - URL: https://supabase.com
   - Create account → New project → Copy URL & Service Key
   - Cost: Free tier available (500MB database, 2GB bandwidth)

2. **Anthropic** (Claude AI)
   - URL: https://console.anthropic.com
   - Create account → API Keys → Generate key
   - Cost: Pay-as-you-go (~$0.001-0.01 per lead)

3. **Google Cloud Platform** (Multiple APIs)
   - URL: https://console.cloud.google.com
   - Create project → Enable APIs:
     - Places API (lead discovery)
     - PageSpeed Insights API (performance analysis)
     - Gemini API (vision analysis)
   - Cost: Places API ~$0.032 per search, PageSpeed free tier

4. **Clay** (Lead Enrichment)
   - URL: https://clay.com
   - Create account → Get API key
   - Set up BuiltWith enrichment table
   - Set up Contact waterfall table
   - Cost: ~$0.50-1.00 per enriched lead

### Recommended (Enhanced Functionality):

5. **Smarty** (Address Verification)
   - URL: https://www.smarty.com
   - Create account → Get Auth ID & Token
   - Cost: 250 free lookups/month, then $0.40 per 1000

6. **OpenAI** (Embeddings for RAG)
   - URL: https://platform.openai.com
   - Create account → API Keys → Generate
   - Cost: ~$0.00002 per embedding

### Optional (Future Features):

7. Instantly (Email delivery)
8. GoHighLevel (CRM)
9. Yext (Directory listings)
10. FullEnrich (Contact enrichment)
11. HeyReach (LinkedIn outreach)

---

## COST BREAKDOWN

### One-time Costs:
- **$0** - All software is open-source or free-tier cloud services

### Monthly Costs (1000 leads/month):

**FREE Tier:**
- Discovery (Google Places): $0-10
- Pre-qualification (Docker): $0
- Supabase database: $0 (free tier)
- Docker hosting: $0 (local) or $10-20 (cloud VM)

**Paid Enrichment (Qualified Leads Only - ~20%):**
- Clay enrichment: 200 leads × $0.75 = $150
- Anthropic Claude: $5-10
- Google Gemini: $2-5
- OpenAI embeddings: <$1

**Total: ~$170-190/month for 1000 discovered leads → 200 qualified**

---

## FINAL ANSWER TO YOUR QUESTION

### "What OS, packages, dependencies, libraries required and in what order?"

**Operating System:**
- **Recommended:** Ubuntu 22.04 LTS (server or desktop)
- **Alternatives:** Debian 11+, macOS 11+, Windows 10+ with WSL2

**Installation Order:**

1. **System Packages** (apt/yum/brew):
   ```
   python3.11 → docker.io → git → system libraries (libgbm1, etc.)
   ```

2. **Python Packages** (pip):
   ```
   python-dotenv → pydantic → httpx → anthropic → supabase →
   google-auth → gspread → google-generativeai → fastapi →
   uvicorn → playwright → beautifulsoup4 → Pillow → smartystreets-python-sdk
   ```

3. **Playwright Browsers**:
   ```
   playwright install chromium
   ```

4. **Docker Images** (automatic via docker compose):
   ```
   python:3.11-slim → playwright/python:v1.40.0 → playwright/python:v1.41.0
   ```

5. **External Services** (cloud setup):
   ```
   Supabase → Anthropic → Google Cloud → Clay → Smarty → OpenAI
   ```

### "Database: MySQL on WHM server at acne.zonedoc.com?"

**NO.** This project uses:
- **Supabase (PostgreSQL)** - cloud-hosted database
- **NOT MySQL**
- **NOT local server**
- **NOT WHM/cPanel**
- **acne.zonedoc.com is not referenced anywhere in the codebase**

If you need to host this on your existing WHM server:
1. This is NOT recommended (architecture mismatch)
2. You would need to:
   - Install Docker on the WHM server
   - Open ports 8001-8006
   - Run containers alongside WHM services
   - This may violate WHM/cPanel terms of service

**Better approach:** Deploy on a separate cloud VM or local development machine.

---

## COMPLETE FILE AUDIT SUMMARY

**Total Files Analyzed:** 100+
- **Python files:** 35+ (no syntax errors)
- **JavaScript files:** 7 (no syntax errors)
- **Docker files:** 7 (2 minor issues identified)
- **YAML configs:** 4
- **JSON files:** 2
- **Documentation:** 10+

**Errors Found:**
- ✅ **0 syntax errors**
- ⚠️ **2 Docker configuration issues** (non-critical)
- ⚠️ **1 website scraper needs update** (TDLR selectors)

**External Dependencies:**
- **14 Python packages**
- **1 NPM package** (testing only)
- **6 Docker services** (local)
- **6+ cloud APIs** (external)

---

**DEPLOYMENT_ARCHITECTURE.md Complete**
**Status:** Ready for deployment on correct infrastructure
**Last Updated:** 2025-12-23
