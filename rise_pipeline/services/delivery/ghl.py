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


class GHLClient:
    """GoHighLevel CRM integration"""

    async def create_contact(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone: str,
        company_name: str,
        tags: list = None
    ) -> Dict[str, Any]:
        """Create/update contact in GHL"""
        if not GHL_API_KEY or not GHL_LOCATION_ID:
            return {"success": False, "error": "GHL not configured"}

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    "https://services.leadconnectorhq.com/contacts/",
                    headers={
                        "Authorization": f"Bearer {GHL_API_KEY}",
                        "Content-Type": "application/json",
                        "Version": "2021-07-28"
                    },
                    json={
                        "locationId": GHL_LOCATION_ID,
                        "firstName": first_name,
                        "lastName": last_name,
                        "email": email,
                        "phone": phone,
                        "companyName": company_name,
                        "source": "Rise Local AI Pipeline",
                        "tags": tags or ["ai-generated", "pipeline-python"]
                    }
                )
                if resp.status_code in [200, 201]:
                    return {"success": True, "response": resp.json()}
                return {"success": False, "error": resp.text}
            except Exception as e:
                print(f"  GHL error: {e}")
                return {"success": False, "error": str(e)}
