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


class HeyReachClient:
    """HeyReach LinkedIn automation API"""

    BASE_URL = "https://api.heyreach.io/api/v1"

    def __init__(self):
        self.headers = {
            "X-API-KEY": HEYREACH_API_KEY,
            "Content-Type": "application/json"
        }

    async def add_lead_to_campaign(
        self,
        linkedin_url: str,
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        email: str = "",
        custom_variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Add a lead to a HeyReach LinkedIn campaign.

        Args:
            linkedin_url: LinkedIn profile URL (required)
            first_name: Contact's first name
            last_name: Contact's last name
            company_name: Company name
            email: Email address
            custom_variables: Custom variables for personalization

        Returns:
            Dict with success status and response
        """
        if not HEYREACH_API_KEY or not HEYREACH_CAMPAIGN_ID:
            return {"success": False, "error": "HeyReach not configured"}

        if not linkedin_url:
            return {"success": False, "error": "LinkedIn URL required"}

        lead_data = {
            "linkedinUrl": linkedin_url
        }

        if first_name:
            lead_data["firstName"] = first_name
        if last_name:
            lead_data["lastName"] = last_name
        if company_name:
            lead_data["companyName"] = company_name
        if email:
            lead_data["email"] = email
        if custom_variables:
            lead_data["customVariables"] = custom_variables

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.BASE_URL}/campaigns/{HEYREACH_CAMPAIGN_ID}/leads",
                    headers=self.headers,
                    json={"leads": [lead_data]}
                )

                if resp.status_code in [200, 201]:
                    return {"success": True, "response": resp.json()}
                return {"success": False, "error": resp.text}

            except Exception as e:
                print(f"  HeyReach error: {e}")
                return {"success": False, "error": str(e)}

    async def add_leads_batch(
        self,
        leads: list
    ) -> Dict[str, Any]:
        """
        Add multiple leads to campaign.

        Args:
            leads: List of lead dicts with linkedinUrl and optional fields

        Returns:
            Dict with success status and response
        """
        if not HEYREACH_API_KEY or not HEYREACH_CAMPAIGN_ID:
            return {"success": False, "error": "HeyReach not configured"}

        # Format leads for API
        formatted_leads = []
        for lead in leads:
            lead_data = {"linkedinUrl": lead.get("linkedin_url", "")}
            if lead.get("first_name"):
                lead_data["firstName"] = lead["first_name"]
            if lead.get("last_name"):
                lead_data["lastName"] = lead["last_name"]
            if lead.get("company_name"):
                lead_data["companyName"] = lead["company_name"]
            if lead.get("email"):
                lead_data["email"] = lead["email"]
            if lead.get("custom_variables"):
                lead_data["customVariables"] = lead["custom_variables"]
            if lead_data["linkedinUrl"]:
                formatted_leads.append(lead_data)

        if not formatted_leads:
            return {"success": False, "error": "No valid leads with LinkedIn URLs"}

        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.BASE_URL}/campaigns/{HEYREACH_CAMPAIGN_ID}/leads",
                    headers=self.headers,
                    json={"leads": formatted_leads}
                )

                if resp.status_code in [200, 201]:
                    return {"success": True, "response": resp.json(), "count": len(formatted_leads)}
                return {"success": False, "error": resp.text}

            except Exception as e:
                print(f"  HeyReach batch error: {e}")
                return {"success": False, "error": str(e)}

    async def get_campaign_stats(self) -> Dict[str, Any]:
        """Get campaign statistics."""
        if not HEYREACH_API_KEY or not HEYREACH_CAMPAIGN_ID:
            return {"error": "HeyReach not configured"}

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/campaigns/{HEYREACH_CAMPAIGN_ID}",
                    headers=self.headers
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Failed to get campaign stats"}
