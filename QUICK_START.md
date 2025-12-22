# Rise Local - Quick Start Guide
## Get Up and Running in 5 Minutes

---

## 🚀 What's New

✅ **Security Fixed:** Hardcoded API keys removed, authentication required
✅ **MCP Server Deployed:** Agent orchestration gateway for Zapier + Claude
✅ **Service Accounts:** JWT tokens for agent authentication

---

## 📦 Prerequisites

- Docker & Docker Compose installed
- Python 3.11+
- Environment variables configured

---

## ⚡ Quick Start (5 Steps)

### Step 1: Set Environment Variables

```bash
cd /home/user/rise-local-lead-creation

# Create .env file
cat > .env <<EOF
# Supabase
SUPABASE_URL=https://jitawzicdwgbhatvjblh.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Google APIs
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
GOOGLE_PAGESPEED_API_KEY=your-pagespeed-api-key

# Smarty (Address Verification)
SMARTY_AUTH_ID=your-smarty-auth-id
SMARTY_AUTH_TOKEN=your-smarty-auth-token

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET=your-jwt-secret-here
ADMIN_SECRET=your-admin-secret-here
EOF
```

### Step 2: Start All Services

```bash
# Start all microservices + MCP server
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f mcp-server
```

**Expected output:**
```
✓ tdlr-scraper       Up (healthy)
✓ bbb-scraper        Up (healthy)
✓ pagespeed-api      Up (healthy)
✓ screenshot-service Up (healthy)
✓ owner-extractor    Up (healthy)
✓ address-verifier   Up (healthy)
✓ mcp-server         Up (healthy)
```

### Step 3: Test MCP Server

```bash
cd mcp_server
python test_mcp.py
```

**Expected output:**
```
╔══════════════════════════════════════════════╗
║  Rise Local MCP Server - Tool Test Suite    ║
╚══════════════════════════════════════════════╝

✓ PASS  Health Check
✓ PASS  Owner Extraction
✓ PASS  TDLR License Search
✓ PASS  BBB Reputation Search
✓ PASS  PageSpeed Analysis
✓ PASS  Screenshot Analysis
✓ PASS  Address Verification

Results: 7/7 tests passed
```

### Step 4: Create User Account

```bash
# Start config API server
cd api
python config_server.py &

# Create user in Supabase Dashboard:
# 1. Go to https://supabase.com/dashboard/project/YOUR_PROJECT/auth/users
# 2. Click "Add user"
# 3. Email: your.email@example.com
# 4. Password: YourSecurePassword123!
# 5. Confirm email
```

### Step 5: Access Dashboard

```bash
# Open browser to:
http://localhost:3000/login.html

# Login with credentials from Step 4
# Dashboard will load with secure authentication
```

---

## 🧪 Testing Guide

### Test 1: MCP Health Check

```bash
cd /home/user/rise-local-lead-creation/mcp_server

python -c "
import asyncio
from server import RiseLocalMCP

async def test():
    mcp = RiseLocalMCP()
    health = await mcp.health_check()
    print('Health:', health['overall_status'])
    print('Services:', len(health['services']))
    await mcp.close()

asyncio.run(test())
"
```

### Test 2: Individual Service

```bash
# Test TDLR scraper directly
curl http://localhost:8001/health

# Test through MCP server
cd mcp_server
python -c "
import asyncio
from server import RiseLocalMCP

async def test():
    mcp = RiseLocalMCP()
    result = await mcp.search_tdlr_license(
        business_name='Test Electric',
        city='Austin',
        lead_id='test-001'
    )
    print('Result:', result)
    await mcp.close()

asyncio.run(test())
"
```

### Test 3: Dashboard Authentication

```bash
# 1. Open: http://localhost:3000/login.html
# 2. Enter credentials
# 3. Should redirect to dashboard on success
# 4. Check browser console for: "Logged in as: your.email@example.com"
```

---

## 🔧 Common Issues & Fixes

### Issue 1: Services Not Starting

```bash
# Check Docker
docker compose ps

# View logs
docker compose logs tdlr-scraper
docker compose logs mcp-server

# Restart specific service
docker compose restart tdlr-scraper

# Restart all
docker compose down && docker compose up -d
```

### Issue 2: MCP Test Failures

```bash
# Ensure all services running
docker compose ps | grep healthy

# Check network connectivity
docker compose exec mcp-server ping tdlr-scraper
docker compose exec mcp-server curl http://tdlr-scraper:8001/health

# View MCP logs
docker compose logs mcp-server
```

### Issue 3: Dashboard Login Fails

```bash
# Check config API running
ps aux | grep config_server.py

# Start if not running
cd /home/user/rise-local-lead-creation/api
python config_server.py &

# Check Supabase connection
curl http://localhost:8080/api/config/supabase

# Verify user exists in Supabase Dashboard
```

### Issue 4: Missing Environment Variables

```bash
# Check .env file exists
cat /home/user/rise-local-lead-creation/.env

# Verify variables loaded
docker compose config | grep GOOGLE_GEMINI_API_KEY

# Reload if needed
docker compose down
docker compose up -d
```

---

## 📊 Service Endpoints

| Service | Port | Health Check | Purpose |
|---------|------|--------------|---------|
| Config API | 8080 | - | Secure credentials |
| TDLR Scraper | 8001 | `/health` | License verification |
| BBB Scraper | 8002 | `/health` | Reputation data |
| PageSpeed API | 8003 | `/health` | Performance metrics |
| Screenshot Service | 8004 | `/health` | Visual analysis |
| Owner Extractor | 8005 | `/health` | Owner info extraction |
| Address Verifier | 8006 | `/health` | Residential check |
| MCP Server | 8000 | stdio | Agent gateway |
| Dashboard | 3000 | - | User interface |

---

## 🎯 Next Actions

**Immediate:**
- [ ] Test all 7 MCP tools
- [ ] Create first user account
- [ ] Login to dashboard
- [ ] Generate service account tokens

**This Week:**
- [ ] Create Zapier Tables schema
- [ ] Build HTTP wrapper for MCP
- [ ] Create first Zap workflow
- [ ] Test Claude agent integration

**Next Week:**
- [ ] Build Qualification Validator agent
- [ ] Integrate LLMCouncil with MCP
- [ ] Deploy Zapier Interfaces
- [ ] Production security hardening

---

## 📚 Documentation

- **Security:** `/home/user/rise-local-lead-creation/SECURITY_IMPLEMENTATION.md`
- **MCP Server:** `/home/user/rise-local-lead-creation/MCP_IMPLEMENTATION.md`
- **MCP Usage:** `/home/user/rise-local-lead-creation/mcp_server/README.md`
- **Full Plan:** `/home/user/.claude/plans/wild-weaving-sonnet.md`

---

## 🆘 Need Help?

1. **Check logs:** `docker compose logs [service-name]`
2. **Health check:** `docker compose ps`
3. **Restart:** `docker compose restart [service-name]`
4. **Full reset:** `docker compose down -v && docker compose up -d`

---

**Status:** Phase 1, Week 1-2 Complete ✅
**Next:** Phase 1, Week 3 - Zapier Integration
