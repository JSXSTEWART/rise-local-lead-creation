# Rise Local MCP Server
## Model Context Protocol Server for Agent Orchestration

This MCP server exposes the 6 Rise Local intelligence microservices as tools that can be used by both **Zapier AI agents** and **Claude agents**.

---

## 🎯 Purpose

The MCP server acts as a **unified gateway** that allows AI agents to access lead intelligence gathering services:

1. **TDLR License Search** (Port 8001) - Electrical contractor license verification
2. **BBB Reputation** (Port 8002) - Better Business Bureau data + reputation gap
3. **PageSpeed Analysis** (Port 8003) - Website performance + Core Web Vitals
4. **Screenshot & Visual Analysis** (Port 8004) - Design quality + tech stack detection
5. **Owner Extraction** (Port 8005) - Extract owner info from website (for TDLR waterfall)
6. **Address Verification** (Port 8006) - Residential vs commercial classification

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /home/user/rise-local-lead-creation/mcp_server
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
# Service URLs (defaults to localhost, override for production)
export TDLR_SCRAPER_URL=http://localhost:8001
export BBB_SCRAPER_URL=http://localhost:8002
export PAGESPEED_API_URL=http://localhost:8003
export SCREENSHOT_SERVICE_URL=http://localhost:8004
export OWNER_EXTRACTOR_URL=http://localhost:8005
export ADDRESS_VERIFIER_URL=http://localhost:8006

# Logging
export LOG_LEVEL=INFO
```

### 3. Start MCP Server

**Option A: Direct Python**
```bash
python server.py
```

**Option B: Docker Compose (Recommended)**
```bash
cd /home/user/rise-local-lead-creation
docker compose up -d mcp-server
```

**Option C: Docker Standalone**
```bash
cd /home/user/rise-local-lead-creation/mcp_server
docker build -t rise-local-mcp .
docker run --name mcp-server \
  --network riselocal \
  -e TDLR_SCRAPER_URL=http://tdlr-scraper:8001 \
  -e BBB_SCRAPER_URL=http://bbb-scraper:8002 \
  -e PAGESPEED_API_URL=http://pagespeed-api:8003 \
  -e SCREENSHOT_SERVICE_URL=http://screenshot-service:8004 \
  -e OWNER_EXTRACTOR_URL=http://owner-extractor:8005 \
  -e ADDRESS_VERIFIER_URL=http://address-verifier:8006 \
  rise-local-mcp
```

---

## 🔧 Available Tools

### 1. `search_tdlr_license`

Search Texas TDLR database for electrical contractor licenses using waterfall method.

**Input:**
```json
{
  "license_number": "TECL123456",
  "owner_first_name": "John",
  "owner_last_name": "Smith",
  "business_name": "Austin Electric",
  "city": "Austin",
  "lead_id": "uuid-here"
}
```

**Output:**
```json
{
  "license_status": "Active",
  "owner_name": "John Smith",
  "license_number": "TECL123456",
  "license_type": "Master Electrician",
  "violations": 0,
  "license_expiry": "2026-12-31"
}
```

---

### 2. `search_bbb_reputation`

Search Better Business Bureau for reputation data and calculate gap vs Google rating.

**Input:**
```json
{
  "business_name": "Austin Electric",
  "city": "Austin",
  "state": "TX",
  "google_rating": 4.5,
  "lead_id": "uuid-here"
}
```

**Output:**
```json
{
  "bbb_rating": "A+",
  "bbb_accredited": true,
  "complaints_total": 2,
  "complaints_3yr": 1,
  "complaints_resolved": 1,
  "reputation_gap": 0.5,
  "years_in_business": 15
}
```

---

### 3. `analyze_pagespeed`

Analyze website performance using Google PageSpeed Insights.

**Input:**
```json
{
  "url": "https://austinelectric.com",
  "strategy": "mobile",
  "lead_id": "uuid-here"
}
```

**Output:**
```json
{
  "performance_score": 85,
  "mobile_score": 90,
  "seo_score": 95,
  "accessibility_score": 88,
  "largest_contentful_paint": 1.2,
  "cumulative_layout_shift": 0.05,
  "has_https": true
}
```

---

### 4. `capture_screenshot_and_analyze`

Capture screenshots and analyze visual quality using Gemini Vision.

**Input:**
```json
{
  "url": "https://austinelectric.com",
  "include_mobile": true,
  "lead_id": "uuid-here"
}
```

**Output:**
```json
{
  "visual_score": 75,
  "design_era": "Modern",
  "has_hero_image": true,
  "has_clear_cta": true,
  "mobile_responsive": true,
  "tracking": {
    "has_gtm": true,
    "has_ga4": true,
    "has_chat_widget": false,
    "cms_detected": "WordPress"
  }
}
```

---

### 5. `extract_owner_info`

Extract owner name, email, phone, and license number from website.

**Input:**
```json
{
  "url": "https://austinelectric.com",
  "lead_id": "uuid-here"
}
```

**Output:**
```json
{
  "owner_first_name": "John",
  "owner_last_name": "Smith",
  "owner_full_name": "John Smith",
  "license_number": "TECL123456",
  "email": "john@austinelectric.com",
  "phone": "(512) 555-1234",
  "confidence": "high"
}
```

---

### 6. `verify_address`

Verify if business address is residential or commercial.

**Input:**
```json
{
  "address": "123 Main St",
  "city": "Austin",
  "state": "TX",
  "zip_code": "78701",
  "lead_id": "uuid-here"
}
```

**Output:**
```json
{
  "is_residential": true,
  "address_type": "residential",
  "verified": true,
  "formatted_address": "123 Main St, Austin, TX 78701"
}
```

---

### 7. `health_check`

Check health status of all 6 microservices.

**Input:**
```json
{}
```

**Output:**
```json
{
  "overall_status": "healthy",
  "services": [
    {
      "service": "tdlr",
      "status": "healthy",
      "response_time_ms": 45.3
    },
    {
      "service": "bbb",
      "status": "healthy",
      "response_time_ms": 123.7
    }
  ],
  "timestamp": "2025-12-22T16:00:00Z"
}
```

---

## 🤖 Using with Claude Agents

### Option 1: Claude Desktop (MCP)

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rise-local": {
      "command": "python",
      "args": ["/home/user/rise-local-lead-creation/mcp_server/server.py"],
      "env": {
        "TDLR_SCRAPER_URL": "http://localhost:8001",
        "BBB_SCRAPER_URL": "http://localhost:8002",
        "PAGESPEED_API_URL": "http://localhost:8003",
        "SCREENSHOT_SERVICE_URL": "http://localhost:8004",
        "OWNER_EXTRACTOR_URL": "http://localhost:8005",
        "ADDRESS_VERIFIER_URL": "http://localhost:8006"
      }
    }
  }
}
```

Then in Claude Desktop:
```
"Qualify this lead: Austin Electric, website: austinelectric.com"
```

Claude will automatically use the MCP tools to:
1. Extract owner info
2. Search TDLR license
3. Check BBB reputation
4. Analyze website performance
5. Verify address

### Option 2: Claude API (Python SDK)

```python
from anthropic import Anthropic
import subprocess
import json

client = Anthropic(api_key="your-api-key")

# Define tools from MCP server
tools = [
    {
        "name": "search_tdlr_license",
        "description": "Search Texas TDLR for electrical contractor license",
        "input_schema": {
            "type": "object",
            "properties": {
                "business_name": {"type": "string"},
                "city": {"type": "string"},
                "lead_id": {"type": "string"}
            },
            "required": ["lead_id"]
        }
    },
    # ... other tools
]

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=4096,
    tools=tools,
    messages=[
        {
            "role": "user",
            "content": "Qualify lead abc123: Austin Electric in Austin, TX"
        }
    ]
)

# Handle tool calls
for block in response.content:
    if block.type == "tool_use":
        # Call MCP server via subprocess or HTTP
        result = call_mcp_tool(block.name, block.input)
        # Continue conversation with tool result
```

---

## 🔌 Using with Zapier

### Option 1: Webhooks by Zapier

Since MCP uses stdio, create an HTTP wrapper:

```python
# http_wrapper.py
from fastapi import FastAPI
import subprocess
import json

app = FastAPI()

@app.post("/mcp/call_tool")
async def call_tool(request: dict):
    tool_name = request["tool"]
    arguments = request["arguments"]

    # Call MCP server via subprocess
    result = subprocess.run(
        ["python", "server.py"],
        input=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }),
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)

# Run: uvicorn http_wrapper:app --port 8000
```

Then in Zapier:

```javascript
// Zapier Code by Zapier
const response = await fetch('http://localhost:8000/mcp/call_tool', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    tool: 'search_tdlr_license',
    arguments: {
      business_name: inputData.business_name,
      city: inputData.city,
      lead_id: inputData.lead_id
    }
  })
});

return await response.json();
```

### Option 2: MCP Client by Zapier (Future)

When Zapier adds native MCP support:

```javascript
// Zapier MCP Client Action
const result = await mcp.callTool('rise-local', 'search_tdlr_license', {
  business_name: inputData.business_name,
  city: inputData.city,
  lead_id: inputData.lead_id
});

return result;
```

---

## 🧪 Testing

### Test Individual Tools

```python
import asyncio
from server import RiseLocalMCP

async def test_tools():
    mcp = RiseLocalMCP()

    # Test TDLR search
    result = await mcp.search_tdlr_license(
        business_name="Austin Electric",
        city="Austin",
        lead_id="test-123"
    )
    print("TDLR Result:", result)

    # Test health check
    health = await mcp.health_check()
    print("Health:", health)

    await mcp.close()

asyncio.run(test_tools())
```

### Test with Sample Lead

```bash
# Create test script
cat > test_lead_qualification.py <<'EOF'
import asyncio
from server import RiseLocalMCP

async def qualify_lead():
    mcp = RiseLocalMCP()

    lead = {
        "lead_id": "test-abc123",
        "business_name": "Austin Electric",
        "website": "https://example.com",
        "city": "Austin",
        "state": "TX",
        "address": "123 Main St",
        "zip_code": "78701",
        "google_rating": 4.5
    }

    print("=== Lead Qualification Pipeline ===\n")

    # Step 1: Extract owner info
    print("1. Extracting owner info...")
    owner = await mcp.extract_owner_info(lead["website"], lead["lead_id"])
    print(f"   Owner: {owner.get('owner_full_name', 'Not found')}\n")

    # Step 2: Search TDLR with owner name
    print("2. Searching TDLR license...")
    license = await mcp.search_tdlr_license(
        owner_first_name=owner.get("owner_first_name"),
        owner_last_name=owner.get("owner_last_name"),
        business_name=lead["business_name"],
        city=lead["city"],
        lead_id=lead["lead_id"]
    )
    print(f"   License: {license.get('license_status', 'Unknown')}\n")

    # Step 3: Check BBB reputation
    print("3. Checking BBB reputation...")
    bbb = await mcp.search_bbb_reputation(
        lead["business_name"],
        lead["city"],
        lead["state"],
        lead["google_rating"],
        lead["lead_id"]
    )
    print(f"   BBB Rating: {bbb.get('bbb_rating', 'NR')}, Gap: {bbb.get('reputation_gap', 0)}\n")

    # Step 4: Analyze website performance
    print("4. Analyzing website performance...")
    pagespeed = await mcp.analyze_pagespeed(lead["website"], "mobile", lead["lead_id"])
    print(f"   Performance: {pagespeed.get('performance_score', 0)}, Mobile: {pagespeed.get('mobile_score', 0)}\n")

    # Step 5: Visual analysis
    print("5. Analyzing visual quality...")
    visual = await mcp.capture_screenshot_and_analyze(lead["website"], True, lead["lead_id"])
    print(f"   Visual Score: {visual.get('visual_score', 0)}, Era: {visual.get('design_era', 'Unknown')}\n")

    # Step 6: Verify address
    print("6. Verifying address...")
    address = await mcp.verify_address(
        lead["address"],
        lead["city"],
        lead["state"],
        lead["zip_code"],
        lead["lead_id"]
    )
    print(f"   Address Type: {address.get('address_type', 'unknown')}\n")

    print("=== Qualification Complete ===")

    await mcp.close()

asyncio.run(qualify_lead())
EOF

python test_lead_qualification.py
```

---

## 📊 Monitoring & Logging

The MCP server logs all tool calls and responses:

```
2025-12-22 16:00:00 - rise-local-mcp - INFO - Tool call: search_tdlr_license with args: {"business_name": "Austin Electric", ...}
2025-12-22 16:00:05 - rise-local-mcp - INFO - TDLR search completed: Active
2025-12-22 16:00:05 - rise-local-mcp - INFO - Tool search_tdlr_license completed successfully
```

**View logs in Docker:**
```bash
docker compose logs -f mcp-server
```

**Set log level:**
```bash
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

---

## 🔒 Security Considerations

1. **No Authentication:** MCP server currently has no authentication. Add JWT validation for production.
2. **Rate Limiting:** Not implemented. Add rate limiting per agent/service account.
3. **Network Isolation:** Deploy on private VPC, not public internet.
4. **Secret Management:** Service URLs should come from AWS Secrets Manager in production.

---

## 🐛 Troubleshooting

### MCP server won't start

```bash
# Check if dependencies installed
pip list | grep mcp

# Check if microservices are running
curl http://localhost:8001/health
curl http://localhost:8002/health
# ... etc

# Check Docker network
docker network inspect riselocal
```

### Tool calls timeout

```bash
# Increase timeout in server.py
# Line 36: httpx.AsyncClient(timeout=90.0)  # Increase this value

# Or check microservice logs
docker compose logs screenshot-service
```

### Services unreachable

```bash
# Verify network connectivity
docker compose exec mcp-server ping tdlr-scraper
docker compose exec mcp-server curl http://tdlr-scraper:8001/health
```

---

## 📚 Additional Resources

- **MCP Protocol:** https://modelcontextprotocol.io/
- **Claude Agent SDK:** https://docs.anthropic.com/claude/docs/agent-sdk
- **Zapier MCP Integration:** (Coming soon)

---

**Created by:** Claude Sonnet 4.5 (Rise Local Agent)
**Version:** 1.0.0
**Last Updated:** December 22, 2025
