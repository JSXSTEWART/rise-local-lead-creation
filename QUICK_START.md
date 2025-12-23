# Rise Local Lead Creation - Quick Start Guide

**Status:** ✅ Production Ready
**Last Updated:** December 22, 2025

---

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git
- GitHub account

---

## 1. Local Setup (5 minutes)

### Environment Configuration

Your `.env` files are already configured with production credentials:

```bash
# Verify main .env exists
ls -la /home/user/rise-local-lead-creation/.env

# Verify agents .env exists
ls -la /home/user/rise-local-lead-creation/agents/.env
```

### Start Services

```bash
cd /home/user/rise-local-lead-creation

# Start all services (MCP + Claude Agent + 6 microservices)
docker compose up -d

# Verify services are running
docker compose ps
```

### Test Endpoints

```bash
# Test MCP Server
curl http://localhost:8000/health

# Test Claude Agent
curl http://localhost:8080/health

# View API Documentation
open http://localhost:8080/docs
```

---

## 2. Test Claude Agent

```bash
cd /home/user/rise-local-lead-creation/agents

# Run comprehensive test
python test_qualification.py

# Or run with pytest
pytest test_qualification.py -v
```

---

## 3. GitHub Setup

### Add Secrets for CI/CD

1. Go to: https://github.com/JSXSTEWART/rise-local-lead-creation/settings/secrets/actions
2. Add 5 secrets (see `SETUP_SECRETS.md` for values)
3. Trigger CI workflow to verify

---

## 4. Full Documentation

- [Setup Secrets Guide](SETUP_SECRETS.md)
- [Security Implementation](SECURITY_IMPLEMENTATION.md)
- [MCP Server Guide](MCP_IMPLEMENTATION.md)
- [Database Schema](TABLES_SCHEMA_IMPLEMENTATION.md)
- [Zapier Workflows](zapier_workflows/MASTER_IMPLEMENTATION_GUIDE.md)

---

**Ready to scale!** 🚀
