"""
Configuration and environment variables for Rise Local Pipeline
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Look for .env in current dir, then parent dir
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent / ".env"

load_dotenv(env_path)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jitawzicdwgbhatvjblh.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Clay
CLAY_API_KEY = os.getenv("CLAY_API_KEY", "")
CLAY_BUILTWITH_TABLE_ID = os.getenv("CLAY_BUILTWITH_TABLE_ID", "")
CLAY_CONTACT_TABLE_ID = os.getenv("CLAY_CONTACT_TABLE_ID", "")

# Local Services
TDLR_SCRAPER_URL = os.getenv("TDLR_SCRAPER_URL", "http://localhost:8001")
BBB_SCRAPER_URL = os.getenv("BBB_SCRAPER_URL", "http://localhost:8002")
PAGESPEED_API_URL = os.getenv("PAGESPEED_API_URL", "http://localhost:8003")
SCREENSHOT_SERVICE_URL = os.getenv("SCREENSHOT_SERVICE_URL", "http://localhost:8004")
OWNER_EXTRACTOR_URL = os.getenv("OWNER_EXTRACTOR_URL", "http://localhost:8005")
ADDRESS_VERIFIER_URL = os.getenv("ADDRESS_VERIFIER_URL", "http://localhost:8006")

# Yext
YEXT_API_KEY = os.getenv("YEXT_API_KEY", "")
YEXT_ACCOUNT_ID = os.getenv("YEXT_ACCOUNT_ID", "939444")

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Instantly
INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY", "")
INSTANTLY_CAMPAIGN_ID = os.getenv("INSTANTLY_CAMPAIGN_ID", "")

# GoHighLevel
GHL_API_KEY = os.getenv("GHL_API_KEY", "")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "")

# FullEnrich
FULLENRICH_API_KEY = os.getenv("FULLENRICH_API_KEY", "")
FULLENRICH_WEBHOOK_URL = os.getenv("FULLENRICH_WEBHOOK_URL", "")

# HeyReach
HEYREACH_API_KEY = os.getenv("HEYREACH_API_KEY", "")
HEYREACH_CAMPAIGN_ID = os.getenv("HEYREACH_CAMPAIGN_ID", "")

# OpenAI (for embeddings)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# RAG Settings
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
RAG_EMBEDDING_DIMENSIONS = 1536
RAG_MATCH_THRESHOLD = 0.7
RAG_MATCH_COUNT = 5

# Cleanlab TLM (Hallucination Detection)
CLEANLAB_API_KEY = os.getenv("CLEANLAB_TLM_API_KEY", "")
HALLUCINATION_THRESHOLD = float(os.getenv("HALLUCINATION_THRESHOLD", "0.7"))

# Pipeline Settings
PAIN_SCORE_REJECT_THRESHOLD = 3  # <= this = rejected
PAIN_SCORE_MARGINAL_THRESHOLD = 5  # <= this = marginal, > this = qualified
EMAIL_CONFIDENCE_THRESHOLD = 0.6
EMAIL_MAX_WORDS = 200
