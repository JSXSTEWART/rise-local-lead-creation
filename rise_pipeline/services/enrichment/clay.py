"""
Service client for Rise Local Pipeline
"""
import os
import httpx
import asyncio
from typing import Optional, Dict, Any, List
import json

# Support both package-relative and top-level imports
try:
    from ...config import *  # type: ignore
except ImportError:
    try:
        from ..config import *  # type: ignore
    except ImportError:
        from config import *  # type: ignore

try:
    from ...models import (
        Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
        DirectoryPresence, LicenseInfo, ReputationData, ContactInfo, AddressVerification,
        OwnerExtraction
    )  # type: ignore
except ImportError:
    try:
        from ..models import (
            Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
            DirectoryPresence, LicenseInfo, ReputationData, ContactInfo, AddressVerification,
            OwnerExtraction
        )  # type: ignore
    except ImportError:
        from models import (
            Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
            DirectoryPresence, LicenseInfo, ReputationData, ContactInfo, AddressVerification,
            OwnerExtraction
        )  # type: ignore

# Additional config from environment (also in config.py)
FULLENRICH_API_KEY = os.environ.get("FULLENRICH_API_KEY", "")
FULLENRICH_WEBHOOK_URL = os.environ.get("FULLENRICH_WEBHOOK_URL", "")
HEYREACH_API_KEY = os.environ.get("HEYREACH_API_KEY", "")
HEYREACH_CAMPAIGN_ID = os.environ.get("HEYREACH_CAMPAIGN_ID", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
CLEANLAB_API_KEY = os.environ.get("CLEANLAB_TLM_API_KEY", "")
HALLUCINATION_THRESHOLD = float(os.environ.get("HALLUCINATION_THRESHOLD", "0.7"))


class ClayClient:
    """Clay API client for enrichment"""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {CLAY_API_KEY}",
            "Content-Type": "application/json"
        }

    async def enrich_tech_stack(self, website_url: str, business_name: str) -> TechEnrichment:
        """Get BuiltWith tech enrichment via Clay"""
        if not CLAY_BUILTWITH_TABLE_ID or not website_url:
            return TechEnrichment()

        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"https://api.clay.com/v3/tables/{CLAY_BUILTWITH_TABLE_ID}/rows",
                    headers=self.headers,
                    json={
                        "data": {
                            "business_name": business_name,
                            "website_url": website_url
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    row = data.get("data", data.get("row", data))
                    if isinstance(row, list) and row:
                        row = row[0]
                    return TechEnrichment(
                        has_gtm=self._to_bool(row.get("has_gtm", row.get("gtm_installed"))),
                        has_ga4=self._to_bool(row.get("has_ga4", row.get("ga4_installed"))),
                        has_ga_universal=self._to_bool(row.get("has_ga_universal")),
                        crm_detected=str(row.get("crm_detected", row.get("crm", ""))),
                        booking_system=str(row.get("booking_system", row.get("scheduling_tool", ""))),
                        cms_platform=str(row.get("cms_platform", row.get("cms", ""))),
                        email_marketing=str(row.get("email_marketing", "")),
                        chat_widget=str(row.get("chat_widget", "")),
                        tech_score=int(row.get("tech_score", 5)),
                        technologies=row.get("technologies", [])
                    )
            except Exception as e:
                print(f"  Clay tech enrichment error: {e}")
        return TechEnrichment()

    async def enrich_contacts(self, business_name: str, website_url: str, city: str, state: str) -> ContactInfo:
        """Get contact enrichment via Clay waterfall"""
        if not CLAY_CONTACT_TABLE_ID:
            return ContactInfo()

        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"https://api.clay.com/v3/tables/{CLAY_CONTACT_TABLE_ID}/rows",
                    headers=self.headers,
                    json={
                        "data": {
                            "business_name": business_name,
                            "website_url": website_url,
                            "city": city,
                            "state": state
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    row = data.get("data", data.get("row", data))
                    if isinstance(row, list) and row:
                        row = row[0]

                    return ContactInfo(
                        owner_email=str(row.get("owner_email", row.get("email", ""))),
                        owner_first_name=str(row.get("owner_first_name", "")),
                        owner_last_name=str(row.get("owner_last_name", "")),
                        owner_linkedin=str(row.get("linkedin_url", "")),
                        owner_phone_direct=str(row.get("direct_phone", "")),
                        email_verified=self._to_bool(row.get("email_verified")),
                        contact_source=str(row.get("source", "clay"))
                    )
            except Exception as e:
                print(f"  Clay contact enrichment error: {e}")

        return ContactInfo()

    @staticmethod
    def _to_bool(val) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes")
