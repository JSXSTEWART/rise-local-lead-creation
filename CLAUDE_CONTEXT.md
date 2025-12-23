# Rise Local Lead Creation - Claude Code Context

**Last Updated:** December 16, 2025
**Status:** Ready to push to GitHub

---

## Current State

### Git Repository
- **Initialized:** Yes
- **Branch:** `master`
- **Initial Commit:** `3ad60f2` - "Initial commit: Rise Local Lead Creation Pipeline"
- **Files Committed:** 87 files, 24,803 lines
- **Remote:** Not yet configured

### What Was Cleaned Up
1. Updated `.gitignore` with comprehensive patterns
2. Removed deprecated files (`nul`, old context files)
3. Created `.env.example` templates (root + custom_tools)
4. Organized documentation into `docs/` folder
5. Created proper `README.md`
6. Added root `requirements.txt`
7. Sanitized docs to remove hardcoded API keys

### Files Excluded from Git (via .gitignore)
- `.env` (actual API keys)
- `.credentials/` folder
- `.mcp.json`
- `dify/docker/volumes/` (database data)
- `test_lead.csv`
- `node_modules/`
- `__pycache__/`

---

## Next Step: Push to GitHub

### Option 1: Using GitHub CLI (Recommended)

First, install GitHub CLI (run in **Administrator PowerShell**):
```powershell
winget install --id GitHub.cli -e
```

Then authenticate and create repo:
```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
gh auth login
gh repo create rise-local-lead-creation --private --source=. --remote=origin --push
```

### Option 2: Manual GitHub Setup

1. Go to https://github.com/new
2. Create repo named `rise-local-lead-creation`
3. Do NOT add README, .gitignore, or license (we have them)
4. Copy the repo URL, then run:

```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
git remote add origin https://github.com/YOUR_USERNAME/rise-local-lead-creation.git
git branch -M main
git push -u origin main
```

---

## Project Structure (After Cleanup)

```
rise-local-lead-creation/
├── .env.example           # Environment template
├── .gitignore             # Comprehensive ignore patterns
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
├── rise_pipeline/         # Core pipeline code
│   ├── pipeline.py        # Main orchestrator
│   ├── services.py        # Service integrations
│   ├── scoring.py         # Pain point scoring
│   ├── models.py          # Data models
│   └── config.py          # Configuration
├── custom_tools/          # Docker services
│   ├── tdlr_scraper/      # Port 8001
│   ├── bbb_scraper/       # Port 8002
│   ├── pagespeed_api/     # Port 8003
│   ├── screenshot_service/ # Port 8004
│   ├── owner_extractor/   # Port 8005
│   ├── address_verifier/  # Port 8006
│   └── docker-compose.yml
├── dashboard/             # Web dashboard
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md
│   ├── TROUBLESHOOTING.md
│   ├── DASHBOARD_USAGE.md
│   └── CLAY_WORKFLOW.md
├── marketing/             # Marketing assets
└── presentation_tools/    # Presentation generators
```

---

## Quick Commands

### Check Git Status
```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
git status
git log --oneline -1
```

### Start Docker Services
```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation\custom_tools"
docker compose up -d
```

### Run Pipeline
```bash
cd "C:\Users\Owner\OneDrive\Desktop\Rise Local Lead Creation"
python run_prequalification_batch.py --all
python run_phase_2_batch.py --all --batch-size 5
```

---

## Resume Instructions for Claude

When resuming this project, tell Claude:

> "Read CLAUDE_CONTEXT.md in the Rise Local Lead Creation folder. I need to push to GitHub."

Claude will then help you complete the GitHub push.
