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


class FullEnrichClient:
    """FullEnrich waterfall contact enrichment API"""

    BASE_URL = "https://app.fullenrich.com/api/v1"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {FULLENRICH_API_KEY}",
            "Content-Type": "application/json"
        }

    async def enrich_contact(
        self,
        first_name: str,
        last_name: str,
        domain: str = "",
        company_name: str = "",
        linkedin_url: str = "",
        custom_data: Dict[str, str] = None
    ) -> ContactInfo:
        """
        Enrich a single contact via FullEnrich waterfall.

        Args:
            first_name: Contact's first name
            last_name: Contact's last name
            domain: Company domain (e.g., "example.com")
            company_name: Company name (alternative to domain)
            linkedin_url: LinkedIn profile URL (improves accuracy)
            custom_data: Custom metadata to pass through

        Returns:
            ContactInfo with enriched data
        """
        if not FULLENRICH_API_KEY:
            print("  FullEnrich API key not configured")
            return ContactInfo()

        # Build contact data
        contact_data = {
            "firstname": first_name.lower(),
            "lastname": last_name.lower(),
            "enrich_fields": ["contact.emails", "contact.phones"]
        }

        if domain:
            contact_data["domain"] = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        elif company_name:
            contact_data["company_name"] = company_name

        if linkedin_url:
            contact_data["linkedin_url"] = linkedin_url

        if custom_data:
            contact_data["custom"] = custom_data

        async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
            try:
                # Start enrichment
                resp = await client.post(
                    f"{self.BASE_URL}/contact/enrich/bulk",
                    headers=self.headers,
                    json={
                        "name": f"pipeline_{first_name}_{last_name}",
                        "datas": [contact_data],
                        "webhook_url": FULLENRICH_WEBHOOK_URL if FULLENRICH_WEBHOOK_URL else None
                    }
                )

                if resp.status_code != 200:
                    print(f"  FullEnrich start error: {resp.status_code} - {resp.text[:200]}")
                    return ContactInfo()

                enrichment_id = resp.json().get("enrichment_id")
                if not enrichment_id:
                    print("  FullEnrich: No enrichment_id returned")
                    return ContactInfo()

                print(f"  FullEnrich enrichment started: {enrichment_id}")

                # Poll for results (max 60 seconds)
                result = await self._poll_for_results(client, enrichment_id, max_wait=60)
                return result

            except Exception as e:
                print(f"  FullEnrich error: {e}")
                return ContactInfo()

    async def _poll_for_results(
        self,
        client: httpx.AsyncClient,
        enrichment_id: str,
        max_wait: int = 60
    ) -> ContactInfo:
        """Poll FullEnrich API for enrichment results."""
        poll_interval = 3  # seconds
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                resp = await client.get(
                    f"{self.BASE_URL}/contact/enrich/bulk/{enrichment_id}",
                    headers=self.headers
                )

                if resp.status_code != 200:
                    continue

                data = resp.json()
                status = data.get("status", "")

                if status == "completed":
                    # Parse results
                    results = data.get("results", [])
                    if results:
                        return self._parse_result(results[0])
                    return ContactInfo()

                elif status == "failed":
                    print(f"  FullEnrich enrichment failed")
                    return ContactInfo()

                # Still processing, continue polling
                print(f"  FullEnrich polling... ({elapsed}s)")

            except Exception as e:
                print(f"  FullEnrich poll error: {e}")

        print(f"  FullEnrich timeout after {max_wait}s")
        return ContactInfo()

    def _parse_result(self, result: Dict[str, Any]) -> ContactInfo:
        """Parse FullEnrich result into ContactInfo."""
        emails = result.get("emails", [])
        phones = result.get("phones", [])

        # Get best email (work email preferred)
        work_email = ""
        personal_email = ""
        for email_obj in emails:
            email = email_obj.get("email", "")
            email_type = email_obj.get("type", "")
            if email_type == "work" and not work_email:
                work_email = email
            elif email_type == "personal" and not personal_email:
                personal_email = email

        # Get best phone (mobile preferred)
        mobile_phone = ""
        for phone_obj in phones:
            phone = phone_obj.get("phone", "")
            phone_type = phone_obj.get("type", "")
            if phone_type == "mobile" and not mobile_phone:
                mobile_phone = phone

        return ContactInfo(
            owner_email=work_email or personal_email or (emails[0].get("email", "") if emails else ""),
            owner_first_name=result.get("firstname", ""),
            owner_last_name=result.get("lastname", ""),
            owner_linkedin=result.get("linkedin_url", ""),
            owner_phone_direct=mobile_phone or (phones[0].get("phone", "") if phones else ""),
            email_verified=True if work_email else False,
            contact_source="fullenrich"
        )

    async def enrich_batch(
        self,
        contacts: list,
        batch_name: str = "pipeline_batch"
    ) -> list:
        """
        Enrich multiple contacts in a single batch (max 100).

        Args:
            contacts: List of dicts with firstname, lastname, domain/company_name
            batch_name: Identifier for this batch

        Returns:
            List of ContactInfo objects
        """
        if not FULLENRICH_API_KEY or not contacts:
            return []

        # Prepare batch data
        datas = []
        for c in contacts[:100]:  # Max 100 per batch
            contact_data = {
                "firstname": c.get("firstname", "").lower(),
                "lastname": c.get("lastname", "").lower(),
                "enrich_fields": ["contact.emails", "contact.phones"]
            }
            if c.get("domain"):
                contact_data["domain"] = c["domain"]
            elif c.get("company_name"):
                contact_data["company_name"] = c["company_name"]
            if c.get("linkedin_url"):
                contact_data["linkedin_url"] = c["linkedin_url"]
            datas.append(contact_data)

        async with httpx.AsyncClient(timeout=300.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.BASE_URL}/contact/enrich/bulk",
                    headers=self.headers,
                    json={
                        "name": batch_name,
                        "datas": datas,
                        "webhook_url": FULLENRICH_WEBHOOK_URL if FULLENRICH_WEBHOOK_URL else None
                    }
                )

                if resp.status_code != 200:
                    print(f"  FullEnrich batch error: {resp.text[:200]}")
                    return []

                enrichment_id = resp.json().get("enrichment_id")
                print(f"  FullEnrich batch started: {enrichment_id} ({len(datas)} contacts)")

                # Poll for results (longer timeout for batch)
                return await self._poll_batch_results(client, enrichment_id, max_wait=180)

            except Exception as e:
                print(f"  FullEnrich batch error: {e}")
                return []

    async def _poll_batch_results(
        self,
        client: httpx.AsyncClient,
        enrichment_id: str,
        max_wait: int = 180
    ) -> list:
        """Poll for batch enrichment results."""
        poll_interval = 5
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                resp = await client.get(
                    f"{self.BASE_URL}/contact/enrich/bulk/{enrichment_id}",
                    headers=self.headers
                )

                if resp.status_code != 200:
                    continue

                data = resp.json()
                status = data.get("status", "")

                if status == "completed":
                    results = data.get("results", [])
                    return [self._parse_result(r) for r in results]
                elif status == "failed":
                    return []

            except Exception:
                pass

        return []

    async def check_credits(self) -> Dict[str, Any]:
        """Check remaining FullEnrich credits."""
        if not FULLENRICH_API_KEY:
            return {"error": "API key not configured"}

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/account/credits",
                    headers=self.headers
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Failed to check credits"}
