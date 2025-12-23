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


class SupabaseClient:
    """Supabase REST API client"""

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self._header_dict = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        # Explicitly disable trust in environment proxies to avoid requiring
        # optional dependencies like socksio. When trust_env=False,
        # httpx will ignore environment proxy settings such as HTTP_PROXY
        # or HTTPS_PROXY, which may point to a SOCKS proxy. Without
        # socksio installed, attempting to use a SOCKS proxy would
        # otherwise raise an error. See test_integrations for context.
        self.client = httpx.AsyncClient(timeout=30.0, trust_env=False)

    def _headers(self) -> dict:
        return self._header_dict

    async def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Fetch lead by ID"""
        async with httpx.AsyncClient(trust_env=False) as client:
            resp = await client.get(
                f"{self.base_url}/leads",
                headers=self._headers(),
                params={"id": f"eq.{lead_id}", "select": "*"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    row = data[0]
                    return Lead(
                        id=str(row.get("id", "")),
                        business_name=str(row.get("business_name", "")),
                        address=str(row.get("address_full") or row.get("address_street") or ""),
                        city=str(row.get("address_city", "")),
                        state=str(row.get("address_state", "TX")),
                        zip_code=str(row.get("address_zip", "")),
                        phone=str(row.get("phone") or ""),
                        website_url=str(row.get("website") or ""),
                        google_rating=float(row.get("google_rating") or 0),
                        review_count=int(row.get("google_review_count") or 0),
                        place_id=str(row.get("place_id") or ""),
                        status=str(row.get("status", "discovered"))
                    )
            return None

    async def update_lead(self, lead_id: str, data: Dict[str, Any]) -> bool:
        """Update lead record"""
        async with httpx.AsyncClient(trust_env=False) as client:
            resp = await client.patch(
                f"{self.base_url}/leads",
                headers={**self._headers(), "Prefer": "return=minimal"},
                params={"id": f"eq.{lead_id}"},
                json=data
            )
            if resp.status_code not in [200, 204]:
                print(f"  Supabase update error ({resp.status_code}): {resp.text}")
            return resp.status_code in [200, 204]

    async def fetch_new_leads(self, limit: int = 10, status: str = "new") -> List[Dict]:
        """Fetch leads by status for processing (default: 'new', can also use 'discovered')"""
        async with httpx.AsyncClient(trust_env=False) as client:
            resp = await client.get(
                f"{self.base_url}/leads",
                headers=self._headers(),
                params={
                    "status": f"eq.{status}",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": limit
                }
            )
            if resp.status_code == 200:
                return resp.json()
            return []

    async def get_tech_enrichment(self, lead_id: str) -> TechEnrichment:
        """Get tech enrichment data from lead record (imported from Clay CSV)"""
        async with httpx.AsyncClient(trust_env=False) as client:
            resp = await client.get(
                f"{self.base_url}/leads",
                headers=self._headers(),
                params={
                    "id": f"eq.{lead_id}",
                    "select": "has_gtm,has_ga4,cms_platform,crm_platform,has_booking_system,tech_stack_score,has_chat_widget"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    row = data[0]
                    return TechEnrichment(
                        has_gtm=bool(row.get("has_gtm", False)),
                        has_ga4=bool(row.get("has_ga4", False)),
                        cms_platform=str(row.get("cms_platform") or ""),
                        crm_detected=str(row.get("crm_platform") or ""),
                        booking_system="yes" if row.get("has_booking_system") else "",
                        chat_widget="yes" if row.get("has_chat_widget") else "",
                        tech_score=int(row.get("tech_stack_score") or 0)
                    )
            return TechEnrichment()

    async def get_contact_info(self, lead_id: str) -> ContactInfo:
        """Get contact info from lead record (imported from Clay CSV)"""
        async with httpx.AsyncClient(trust_env=False) as client:
            resp = await client.get(
                f"{self.base_url}/leads",
                headers=self._headers(),
                params={
                    "id": f"eq.{lead_id}",
                    "select": "owner_email,owner_first_name,owner_last_name,owner_linkedin_url,owner_phone,verified_email,owner_source"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    row = data[0]
                    return ContactInfo(
                        owner_email=str(row.get("owner_email") or ""),
                        owner_first_name=str(row.get("owner_first_name") or ""),
                        owner_last_name=str(row.get("owner_last_name") or ""),
                        owner_linkedin=str(row.get("owner_linkedin_url") or ""),
                        owner_phone_direct=str(row.get("owner_phone") or ""),
                        email_verified=bool(row.get("verified_email", False)),
                        contact_source=str(row.get("owner_source") or "clay_import")
                    )
            return ContactInfo()
