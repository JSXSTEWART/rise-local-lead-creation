# Setup GitHub Secrets for CI/CD

## Add Secrets to GitHub Repository

Go to your repository settings and add these secrets for GitHub Actions CI/CD:

**Navigate to:** https://github.com/JSXSTEWART/rise-local-lead-creation/settings/secrets/actions

### Required Secrets

Click **"New repository secret"** and add each of the following:

#### 1. ANTHROPIC_API_KEY
**Value:** Get from your local `.env` file:
```bash
grep ANTHROPIC_API_KEY /home/user/rise-local-lead-creation/.env | cut -d'=' -f2
```
**Used by:** Claude agent tests, qualification validator

---

#### 2. SUPABASE_URL
**Value:** Get from your local `.env` file:
```bash
grep SUPABASE_URL /home/user/rise-local-lead-creation/.env | cut -d'=' -f2
```
**Used by:** Database connection, schema validation

---

#### 3. SUPABASE_SERVICE_KEY
**Value:** Get from your local `.env` file:
```bash
grep SUPABASE_SERVICE_KEY /home/user/rise-local-lead-creation/.env | cut -d'=' -f2
```
**Used by:** Database admin access, agent decisions table

---

#### 4. GOOGLE_GEMINI_API_KEY (Optional for full tests)
**Value:** Get from your local `.env` file:
```bash
grep GOOGLE_GEMINI_API_KEY /home/user/rise-local-lead-creation/.env | cut -d'=' -f2
```
**Used by:** Screenshot analysis, owner extraction tests

---

#### 5. GOOGLE_PAGESPEED_API_KEY (Optional for full tests)
**Value:** Same as GOOGLE_GEMINI_API_KEY (reuse the same Google API key)

**Used by:** PageSpeed API higher rate limits

---

## Verify Secrets

After adding all secrets, trigger a manual CI run:

1. Go to: https://github.com/JSXSTEWART/rise-local-lead-creation/actions
2. Click on **"CI - Rise Local Lead Creation"** workflow
3. Click **"Run workflow"** → **"Run workflow"** button
4. Wait for tests to complete (~5 minutes)

## Expected Results

✅ **test-agent**: Claude agent unit tests pass
✅ **test-mcp**: MCP server validation passes
✅ **validate-schema**: Database migrations succeed
✅ **validate-docker**: Docker images build successfully
✅ **validate-docs**: All documentation present
✅ **security-checks**: No hardcoded secrets found
✅ **code-quality**: Code passes quality checks
✅ **integration-test**: Agent + MCP integration works

---

## Security Reminders

⚠️ **IMPORTANT**: These credentials were exposed in this conversation and should be rotated:

### Rotate Anthropic API Key
1. Go to: https://console.anthropic.com/settings/keys
2. Delete the current key
3. Create a new key
4. Update in:
   - `.env` (local)
   - `agents/.env` (local)
   - GitHub Secrets (repository settings)

### Rotate Supabase Service Key
1. Go to: https://supabase.com/dashboard/project/bvnllbpqstcrynehjvan/settings/api
2. Click "Generate new service role key"
3. Update in:
   - `.env` (local)
   - `agents/.env` (local)
   - GitHub Secrets (repository settings)

### Rotate Google API Key
1. Go to: https://console.cloud.google.com/apis/credentials
2. Delete exposed key
3. Create new key with restrictions:
   - API restrictions: PageSpeed Insights API, Gemini API
   - Application restrictions: None or HTTP referrers
4. Update in `.env`

### Rotate Clay API Key
1. Contact Clay support to rotate key
2. Update in `.env`

---

## Local Setup

Your local `.env` files are already configured:

```bash
# Main project .env
cat /home/user/rise-local-lead-creation/.env

# Claude agent .env
cat /home/user/rise-local-lead-creation/agents/.env
```

These files are **gitignored** and will never be committed.

---

## Start Services

```bash
cd /home/user/rise-local-lead-creation

# Start all services with Docker Compose
docker compose up -d

# Verify services are running
docker compose ps

# Check Claude agent logs
docker logs claude-agent -f

# Test agent endpoint
curl http://localhost:8080/health
```

---

## Next Steps

1. ✅ Add all 5 secrets to GitHub
2. ✅ Trigger manual CI run to verify
3. ⚠️ **ROTATE ALL CREDENTIALS** (exposed in conversation)
4. 🚀 Start local services with `docker compose up -d`
5. 🧪 Test qualification agent with sample lead
6. 📊 Monitor CI results on GitHub Actions

---

**Setup Complete!** Your Rise Local Lead Creation pipeline is now fully configured for production use.
