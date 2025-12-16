# Rise Local Lead Creation Pipeline

An automated lead generation and qualification pipeline for local service businesses. The system discovers leads, enriches them with intelligence data, scores pain points, and generates personalized outreach.

## Features

- **Lead Discovery**: Automated discovery via Google Places API
- **Free Pre-Qualification**: Local Docker scrapers filter leads before paid enrichment
- **AI-Powered Analysis**: Visual analysis, tech stack scoring, and pain point detection
- **Cost Optimization**: 80% savings by enriching only qualified leads via Clay
- **Multi-Source Intelligence**:
  - Screenshot analysis with Gemini Vision
  - PageSpeed performance metrics
  - TDLR license verification (Texas)
  - BBB reputation data
  - Address verification (residential vs commercial)
- **Email Generation**: Claude-powered personalized outreach emails

## Architecture

```
Discovery → FREE Scrapers → Pre-Qualification → Clay Enrichment → Outreach
              ↑ $0 COST       ↑ FILTER HERE      ↑ QUALIFIED ONLY
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| TDLR Scraper | 8001 | Texas license verification |
| BBB Scraper | 8002 | Better Business Bureau lookup |
| PageSpeed API | 8003 | Google PageSpeed wrapper |
| Screenshot Service | 8004 | Visual analysis with Gemini |
| Owner Extractor | 8005 | Owner name extraction |
| Address Verifier | 8006 | Residential/commercial check |

## Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- API keys (see `.env.example`)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/rise-local-lead-creation.git
   cd rise-local-lead-creation
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   cp custom_tools/.env.example custom_tools/.env
   # Edit both files with your API keys
   ```

3. **Start Docker services**
   ```bash
   cd custom_tools
   docker compose up -d
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r rise_pipeline/requirements.txt
   ```

5. **Run the pipeline**
   ```bash
   # Process discovered leads
   python run_prequalification_batch.py --all

   # Run Phase 2 intelligence gathering
   python run_phase_2_batch.py --all --batch-size 5
   ```

## Project Structure

```
rise-local-lead-creation/
├── rise_pipeline/           # Core pipeline code
│   ├── pipeline.py          # Main orchestrator
│   ├── services.py          # Service integrations
│   ├── scoring.py           # Pain point scoring
│   ├── models.py            # Data models
│   └── config.py            # Configuration
├── custom_tools/            # Docker services
│   ├── tdlr_scraper/        # Port 8001
│   ├── bbb_scraper/         # Port 8002
│   ├── pagespeed_api/       # Port 8003
│   ├── screenshot_service/  # Port 8004
│   ├── owner_extractor/     # Port 8005
│   ├── address_verifier/    # Port 8006
│   └── docker-compose.yml
├── dashboard/               # Web dashboard
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # System design
│   ├── TROUBLESHOOTING.md   # Debug guide
│   ├── DASHBOARD_USAGE.md   # Dashboard guide
│   └── CLAY_WORKFLOW.md     # Clay integration
├── .env.example             # Environment template
└── README.md                # This file
```

## Configuration

### Required API Keys

| Service | Purpose | Get from |
|---------|---------|----------|
| Supabase | Database | [supabase.com](https://supabase.com) |
| Google PageSpeed | Performance | [Google Cloud Console](https://console.cloud.google.com) |
| Google Gemini | AI Vision | [AI Studio](https://makersuite.google.com) |
| Smarty | Address verification | [smarty.com](https://smarty.com) |
| Clay | Lead enrichment | [clay.com](https://clay.com) |
| Anthropic | Email generation | [console.anthropic.com](https://console.anthropic.com) |

See `.env.example` for all configuration options.

## Pipeline Stages

### Stage 1: Lead Discovery
- Google Places API search by city and industry
- Raw leads stored in Supabase

### Stage 2: FREE Pre-Qualification
- Visual analysis (design quality, mobile responsiveness)
- Technical performance (PageSpeed scores)
- License verification (TDLR for Texas)
- Reputation check (BBB rating, complaints)
- Address verification (residential vs commercial)

### Stage 3: Pain Scoring
- Score calculation based on free data
- Qualification decision:
  - Score ≤ 3: **REJECTED**
  - Score 4-5: **MARGINAL**
  - Score ≥ 6: **QUALIFIED**

### Stage 4: Clay Enrichment (Qualified Only)
- BuiltWith tech stack analysis
- Contact waterfall (Dropcontact → Hunter → Apollo)

### Stage 5: Outreach
- AI-generated personalized emails
- Delivery via Instantly/GHL

## Dashboard

Access the dashboard at `http://localhost:8080` to:
- View lead counts and qualification status
- Export CSVs for Clay enrichment
- Import enriched data back to the pipeline
- Monitor pipeline progress

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and flow
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Debug guide
- [Dashboard Usage](docs/DASHBOARD_USAGE.md) - Dashboard guide
- [Clay Workflow](docs/CLAY_WORKFLOW.md) - Clay integration steps

## Development

### Running Tests

```bash
cd rise_pipeline
python test_pipeline.py
python test_integrations.py
```

### Health Checks

```bash
curl http://localhost:8001/health  # TDLR
curl http://localhost:8002/health  # BBB
curl http://localhost:8003/health  # PageSpeed
curl http://localhost:8004/health  # Screenshot
curl http://localhost:8005/health  # Owner Extractor
curl http://localhost:8006/health  # Address Verifier
```

## License

Proprietary - Rise Local

## Support

For issues or questions, contact the Rise Local team.
