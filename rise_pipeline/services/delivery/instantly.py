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


class InstantlyClient:
    """Instantly.ai email sending"""

    async def add_lead(
        self,
        email: str,
        first_name: str,
        last_name: str,
        company_name: str,
        custom_variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Add lead to Instantly campaign"""
        if not INSTANTLY_API_KEY or not INSTANTLY_CAMPAIGN_ID:
            return {"success": False, "error": "Instantly not configured"}

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    "https://api.instantly.ai/api/v1/lead/add",
                    json={
                        "api_key": INSTANTLY_API_KEY,
                        "campaign_id": INSTANTLY_CAMPAIGN_ID,
                        "skip_if_in_workspace": True,
                        "leads": [{
                            "email": email,
                            "first_name": first_name,
                            "last_name": last_name,
                            "company_name": company_name,
                            "custom_variables": custom_variables or {}
                        }]
                    }
                )
                if resp.status_code == 200:
                    return {"success": True, "response": resp.json()}
                return {"success": False, "error": resp.text}
            except Exception as e:
                print(f"  Instantly error: {e}")
                return {"success": False, "error": str(e)}
