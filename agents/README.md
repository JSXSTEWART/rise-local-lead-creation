# Claude Qualification Agent
## Intelligent Lead Qualification with MCP Integration

**Powered by:** Claude Opus 4.5 + Anthropic SDK + MCP Protocol

---

## 🎯 Overview

The Claude Qualification Agent is an intelligent system that qualifies electrical contractor leads using:

- **6 MCP Tools** for comprehensive enrichment
- **LLMCouncil Pattern** for marginal leads (4-agent consensus)
- **Pain Point Analysis** with 0-100 scoring
- **Lead Category Classification** (5 categories)
- **Confidence Scoring** with detailed reasoning

**Key Features:**
- ✅ Auto-qualification for clear cases (70% of leads)
- ✅ Council review for marginal leads (30% of leads)
- ✅ FastAPI server for Zapier integration
- ✅ Async/sync endpoints
- ✅ Supabase integration for decision storage
- ✅ Production-ready with health checks

---

## 📁 Project Structure

```
agents/
├── qualification_validator.py  # Core agent logic with MCP tools
├── api_server.py               # FastAPI server
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── Dockerfile                  # Container configuration
├── test_qualification.py       # Test suite
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /home/user/rise-local-lead-creation/agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
MCP_SERVER_URL=http://localhost:8000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

### 3. Start MCP Server (Prerequisite)

The qualification agent requires the MCP server to be running:

```bash
# In another terminal
cd /home/user/rise-local-lead-creation/mcp_server
python server.py

# Verify it's running
curl http://localhost:8000/health
```

### 4. Run Agent API Server

```bash
# Start the FastAPI server
python api_server.py

# Server starts on http://localhost:8080
# Docs available at http://localhost:8080/docs
```

---

## 📖 Usage

### Standard Qualification

```python
from qualification_validator import QualificationValidator

validator = QualificationValidator()

# Prepare lead context
context = {
    "lead_id": "abc-123",
    "business_name": "Austin Electric",
    "website_url": "https://austinelectric.com",
    "location": "Austin, TX",
    "google_rating": 4.3,
    "preliminary_pain_score": 65,
    "enrichment_data": {
        "visual_score": 42,
        "performance_score": 38,
        "mobile_responsive": False,
        "has_crm": False,
        "has_booking": False
    },
    "pain_signals": [
        "Poor website design",
        "Slow performance",
        "Not mobile responsive",
        "No CRM detected"
    ]
}

# Run qualification
decision = await validator.qualify_lead(
    lead_id=context["lead_id"],
    context=context,
    mode="standard"
)

print(f"Decision: {decision['decision']}")
print(f"Confidence: {decision['confidence']}")
print(f"Pain Score: {decision['pain_score']}")
print(f"Reasoning: {decision['reasoning']}")
```

### Council Mode (Marginal Leads)

```python
# For marginal leads (pain_score 31-59), use council mode
council_decision = await validator.qualify_lead(
    lead_id=context["lead_id"],
    context=context,
    mode="council"  # 4-agent consensus
)

print(f"Council Decision: {council_decision['decision']}")
print(f"Votes: {council_decision['metadata']['qualified_votes']}/4")
print(f"\nCouncil Reasoning:\n{council_decision['reasoning']}")
```

### API Integration (Zapier)

**Async Endpoint (Production):**
```bash
curl -X POST http://localhost:8080/api/agents/claude/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "qualification_validator",
    "mode": "standard",
    "job_id": "job-uuid-123",
    "lead_id": "lead-uuid-456",
    "context": {
      "business_name": "Test Electric",
      "preliminary_pain_score": 65,
      ...
    }
  }'
```

Response:
```json
{
  "job_id": "job-uuid-123",
  "agent_session_id": "session-xyz",
  "status": "running",
  "message": "Claude qualification agent started in standard mode",
  "estimated_completion": "2025-12-22T10:05:00Z"
}
```

**Sync Endpoint (Testing):**
```bash
curl -X POST http://localhost:8080/api/agents/claude/invoke-sync \
  -H "Content-Type: application/json" \
  -d '{...same payload...}'
```

Response includes full decision immediately.

---

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest test_qualification.py -v

# Run specific test
pytest test_qualification.py::TestQualificationValidator::test_high_pain_qualification -v

# Run with coverage
pytest test_qualification.py --cov=. --cov-report=html
```

### Manual Testing

```bash
# Run manual test script
python test_qualification.py

# This runs 4 tests:
# 1. High pain lead (should qualify)
# 2. Low pain lead (should reject)
# 3. Marginal lead (council review)
# 4. API health check
```

### Test with Real Leads

```bash
# Test with a real lead from Supabase
python -c "
import asyncio
from qualification_validator import QualificationValidator
import httpx

async def test():
    validator = QualificationValidator()

    # Fetch a real lead
    async with httpx.AsyncClient() as client:
        response = await client.get(
            '${SUPABASE_URL}/rest/v1/leads?status=eq.enriched&limit=1',
            headers={'apikey': '${SUPABASE_SERVICE_KEY}'}
        )
        lead = response.json()[0]

    # Qualify it
    decision = await validator.qualify_lead(
        lead_id=lead['id'],
        context=lead,
        mode='standard'
    )

    print(f'Decision: {decision}')
    await validator.close()

asyncio.run(test())
"
```

---

## 🔧 MCP Tools Available

The agent can call these 6 tools automatically:

| Tool | Purpose | Response Time |
|------|---------|---------------|
| `search_tdlr_license` | Verify TX contractor license | ~5s |
| `search_bbb_reputation` | Check BBB rating & complaints | ~8s |
| `analyze_pagespeed` | Test website performance | ~10s |
| `capture_screenshot_and_analyze` | Visual design analysis | ~15s |
| `extract_owner_info` | Extract owner contact from site | ~12s |
| `verify_address` | Check residential vs commercial | ~3s |

**Tool Selection:**
Claude autonomously decides which tools to call based on:
- Missing data in context
- Uncertainty about pain signals
- Need for verification

**Example tool usage in decision:**
```
Reasoning: "Called analyze_pagespeed and found performance score of
28/100 (very slow). Called search_tdlr_license and verified Active
license. Called capture_screenshot_and_analyze and detected outdated
2015 design. Based on these findings, pain score: 75. Decision: QUALIFIED."
```

---

## 📊 Decision Output Schema

```typescript
{
  decision: "qualified" | "rejected" | "marginal",
  confidence: 0.0 - 1.0,
  pain_score: 0 - 100,
  category?: "THE_INVISIBLE" | "DIY_CEILING" | "LEAKY_BUCKET" | "OVERWHELMED" | "READY_TO_DOMINATE",
  top_pain_points: string[],
  reasoning: string,  // Detailed explanation
  red_flags?: string[],
  metadata?: {
    council_votes?: {
      "Lead Analyst": {vote: "qualified", score: 82, reasoning: "..."},
      "Email Strategist": {vote: "qualified", ...},
      "Quality Reviewer": {vote: "qualified", ...},
      "Risk Assessor": {vote: "rejected", ...}
    },
    qualified_votes?: number,
    rejected_votes?: number
  }
}
```

---

## 🎯 Lead Categories

The agent classifies leads into 5 categories:

1. **THE_INVISIBLE** (Highest Pain)
   - No website or minimal online presence
   - Signals: No website, outdated site, not found on Google
   - Email variant: Authority ("I help businesses get found online")

2. **DIY_CEILING** (High Pain)
   - Template website, hit a growth wall
   - Signals: WordPress template, no CRM, no booking
   - Email variant: Pain Point ("Your website might be costing you customers")

3. **LEAKY_BUCKET** (Medium Pain)
   - Traffic but poor conversion
   - Signals: Bad performance, no call tracking, poor mobile
   - Email variant: Curiosity ("I noticed something about your site")

4. **OVERWHELMED** (Medium Pain)
   - Backlog issues, poor reviews
   - Signals: Low Google rating, complaints, expired license
   - Email variant: Relief ("What if handling leads was effortless?")

5. **READY_TO_DOMINATE** (Low-Medium Pain)
   - Good foundation, needs scale
   - Signals: Modern site but missing advanced features
   - Email variant: Opportunity ("Ready to dominate your market?")

---

## 🏗️ Architecture

### Standard Mode Flow

```
1. Receive context from Zapier
2. Claude analyzes preliminary pain score
3. If needed, call MCP tools for additional data
4. Calculate final pain score (0-100)
5. Classify lead category
6. Make decision: QUALIFIED / REJECTED / MARGINAL
7. Write to agent_decisions table
8. Update lead status
9. Return decision to Zapier
```

**Time:** ~30-60 seconds

### Council Mode Flow

```
1. Receive marginal lead (pain_score 31-59)
2. Spawn 4 specialized agents:
   - Lead Analyst (market opportunity)
   - Email Strategist (engagement potential)
   - Quality Reviewer (data completeness)
   - Risk Assessor (red flags)
3. Each agent independently analyzes and votes
4. Calculate consensus (3/4 or 4/4 for qualified)
5. Build comprehensive reasoning
6. Write decision with full vote breakdown
7. Return to Zapier
```

**Time:** ~90-120 seconds

---

## 💰 Cost Analysis

**Per Lead (Standard Mode):**
- Input tokens: ~2,000 (context + prompt)
- Output tokens: ~1,000 (reasoning + decision)
- MCP tool calls: 2-3 on average
- **Cost: ~$0.05 per lead**

**Per Lead (Council Mode):**
- 4 agent calls: ~8,000 tokens total
- **Cost: ~$0.15 per lead**

**Monthly (3,000 leads):**
- 70% standard (2,100 leads): $105
- 30% council (900 leads): $135
- **Total: $240/month**

**ROI:**
- Manual qualification: 20 hours/week × $50/hr = $4,000/month
- Automated: $240/month
- **Savings: $3,760/month (94% reduction)**

---

## 🔒 Security

### Authentication

The API server supports JWT authentication:

```python
from fastapi import Header, HTTPException

async def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")

    token = authorization.replace("Bearer ", "")
    # Verify JWT token
    # ...

# Add to endpoint
@app.post("/api/agents/claude/invoke", dependencies=[Depends(verify_token)])
async def invoke_agent(...):
    ...
```

### Rate Limiting

Add rate limiting to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/agents/claude/invoke")
@limiter.limit("10/minute")
async def invoke_agent(...):
    ...
```

---

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t claude-qualification-agent .
```

### Run Container

```bash
docker run -d \
  --name claude-agent \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  -e MCP_SERVER_URL=http://mcp-server:8000 \
  -e SUPABASE_URL=${SUPABASE_URL} \
  -e SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY} \
  --network riselocal \
  claude-qualification-agent
```

### Add to Docker Compose

```yaml
services:
  claude-agent:
    build:
      context: ./agents
    ports:
      - "8080:8080"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MCP_SERVER_URL=http://mcp-server:8000
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
    depends_on:
      - mcp-server
    networks:
      - riselocal
    restart: unless-stopped
```

---

## 📈 Monitoring

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T10:00:00Z",
  "mcp_server": "healthy",
  "supabase": "healthy"
}
```

### Metrics to Track

1. **Decision Accuracy**
   ```sql
   SELECT
     agent_name,
     COUNT(*) as total,
     COUNT(*) FILTER (WHERE overridden_by IS NOT NULL) as overrides,
     ROUND(100.0 * COUNT(*) FILTER (WHERE overridden_by IS NOT NULL) / COUNT(*), 2) as override_rate
   FROM agent_decisions
   WHERE decision_type = 'qualification'
   GROUP BY agent_name;
   ```

2. **Processing Time**
   ```sql
   SELECT
     AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_seconds
   FROM agent_jobs
   WHERE job_type = 'qualification'
     AND status = 'completed';
   ```

3. **Qualification Rate**
   ```sql
   SELECT
     decision,
     COUNT(*) as count,
     ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
   FROM agent_decisions
   WHERE decision_type = 'qualification'
   GROUP BY decision;
   ```

---

## 🐛 Troubleshooting

### Issue 1: "ANTHROPIC_API_KEY not set"

**Solution:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
# Or add to .env file
```

### Issue 2: MCP Server Timeout

**Symptoms:** Tools fail with timeout errors

**Solution:**
```bash
# Check MCP server is running
curl http://localhost:8000/health

# Restart if needed
cd ../mcp_server
python server.py
```

### Issue 3: Low Confidence Scores

**Symptoms:** Most decisions have confidence < 0.7

**Solution:**
- Provide more context in lead data
- Ensure enrichment data is complete
- Use council mode for marginal leads

### Issue 4: Slow Response Times

**Symptoms:** Qualification takes > 2 minutes

**Solution:**
- Check MCP tool latency
- Reduce number of tools called (filter in prompt)
- Use standard mode instead of council for clear cases

---

## 📚 References

- [Anthropic API Docs](https://docs.anthropic.com/)
- [Claude Model Docs](https://docs.anthropic.com/claude/docs/models-overview)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [Supabase API Docs](https://supabase.com/docs/guides/api)

---

## 📝 Development

### Code Style

```bash
# Format code
black qualification_validator.py api_server.py test_qualification.py

# Type checking
mypy qualification_validator.py
```

### Adding New Council Agents

Edit `_qualify_with_council` in `qualification_validator.py`:

```python
agents = [
    {...existing agents...},
    {
        "name": "New Agent Name",
        "role": "Agent's specific role",
        "focus": "What this agent focuses on"
    }
]
```

---

**Version:** 1.0.0
**Last Updated:** December 22, 2025
**Status:** Production Ready ✅
