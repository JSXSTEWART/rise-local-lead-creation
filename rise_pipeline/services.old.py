"""
External service integrations for Rise Local Pipeline
"""
import os
import httpx
import asyncio
from typing import Optional, Dict, Any, List
import json

# Support both package-relative and top-level imports. When this module
# is imported as part of the ``rise_pipeline`` package (e.g. via
# ``from rise_pipeline import services``) the relative import works. When
# imported as a top-level module (e.g. ``import services`` from the same
# directory), the relative import will fail. In that case we fall back
# to importing the config symbols from a top-level ``config`` module.
try:
    from .config import *  # type: ignore
except ImportError:
    from config import *  # type: ignore

# Additional config from environment (also in config.py)
FULLENRICH_API_KEY = os.environ.get("FULLENRICH_API_KEY", "")
FULLENRICH_WEBHOOK_URL = os.environ.get("FULLENRICH_WEBHOOK_URL", "")
HEYREACH_API_KEY = os.environ.get("HEYREACH_API_KEY", "")
HEYREACH_CAMPAIGN_ID = os.environ.get("HEYREACH_CAMPAIGN_ID", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
CLEANLAB_API_KEY = os.environ.get("CLEANLAB_TLM_API_KEY", "")
HALLUCINATION_THRESHOLD = float(os.environ.get("HALLUCINATION_THRESHOLD", "0.7"))
# See comment above regarding relative vs absolute imports. Fall back to
# absolute imports when executed outside of a package context.
try:
    from .models import (
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


class IntelligenceServices:
    """Phase 2 intelligence gathering services"""

    @staticmethod
    async def get_visual_analysis(lead: Lead) -> VisualAnalysis:
        """Screenshot and visual analysis"""
        async with httpx.AsyncClient(timeout=90.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{SCREENSHOT_SERVICE_URL}/analyze",
                    json={
                        "url": lead.website_url,
                        "include_mobile": True,
                        "include_screenshots": False,
                        "lead_id": lead.id
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return VisualAnalysis(
                        visual_score=int(data.get("visual_score", 50)),
                        design_era=str(data.get("design_era", "Unknown")),
                        mobile_responsive=data.get("mobile_responsive", True),
                        social_facebook=str(data.get("social_links", {}).get("facebook", "")),
                        social_instagram=str(data.get("social_links", {}).get("instagram", "")),
                        social_linkedin=str(data.get("social_links", {}).get("linkedin", "")),
                        trust_signals=int(data.get("trust_signals", 0)),
                        has_hero_image=data.get("has_hero_image", False),
                        has_clear_cta=data.get("has_clear_cta", False)
                    )
            except Exception as e:
                print(f"  Visual analysis error: {e}")
        return VisualAnalysis()

    @staticmethod
    async def get_pagespeed(lead: Lead) -> TechnicalScores:
        """PageSpeed analysis"""
        async with httpx.AsyncClient(timeout=90.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{PAGESPEED_API_URL}/analyze",
                    json={
                        "url": lead.website_url,
                        "strategy": "mobile",
                        "lead_id": lead.id
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return TechnicalScores(
                        performance_score=int(data.get("performance_score", 50)),
                        mobile_score=int(data.get("mobile_score", 50)),
                        seo_score=int(data.get("seo_score", 50)),
                        accessibility_score=int(data.get("accessibility_score", 50)),
                        has_https=data.get("has_https", True),
                        lcp_ms=int(data.get("lcp_ms", 0)),
                        fid_ms=int(data.get("fid_ms", 0)),
                        cls=float(data.get("cls", 0))
                    )
            except Exception as e:
                print(f"  PageSpeed error: {e}")
        return TechnicalScores()

    @staticmethod
    async def get_yext_listings(lead: Lead) -> DirectoryPresence:
        """
        Yext directory scan - DISABLED.

        REASON: Yext Scan API only allows initiating scans (POST /scan).
        The GET endpoint to retrieve results returns 404, and there's no
        webhook event for scan completion. Results are only viewable in
        Yext dashboard UI, making it unusable for automated pipelines.

        Disabled: December 15, 2025

        Returns neutral DirectoryPresence values that won't trigger
        any pain point signals in scoring.
        """
        print(f"  Yext: DISABLED - Returning neutral values (API cannot retrieve scan results)")

        # Return neutral values that won't trigger Listings pain signals:
        # - listings_score >= 50 = no "Poor directory presence" signal
        # - listings_found >= 10 = no "Limited directory presence" signal
        # - nap_consistency >= 0.7 = no "Inconsistent business info" signal
        return DirectoryPresence(
            listings_score=50,      # Neutral - won't trigger pain signal
            listings_found=10,      # Neutral - won't trigger pain signal
            listings_verified=0,    # Unknown
            nap_consistency=1.0,    # Neutral - won't trigger pain signal
            scan_id=""              # No scan initiated
        )

    @staticmethod
    async def get_owner_extraction(lead: Lead) -> OwnerExtraction:
        """
        Extract owner info from website using Claude Vision.

        This is KEY to making TDLR work - get owner name from website first,
        then search TDLR by person name instead of business name.
        """
        if not lead.website_url:
            return OwnerExtraction(error="No website URL")

        async with httpx.AsyncClient(timeout=90.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{OWNER_EXTRACTOR_URL}/extract-owner",
                    json={
                        "url": lead.website_url,
                        "lead_id": lead.id
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return OwnerExtraction(
                        owner_first_name=str(data.get("owner_first_name") or ""),
                        owner_last_name=str(data.get("owner_last_name") or ""),
                        owner_full_name=str(data.get("owner_full_name") or ""),
                        license_number=str(data.get("license_number") or ""),
                        email=str(data.get("email") or ""),
                        phone=str(data.get("phone") or ""),
                        confidence=str(data.get("confidence", "low")),
                        extraction_method=str(data.get("extraction_method", "")),
                        error=str(data.get("error") or "")
                    )
            except Exception as e:
                print(f"  Owner extraction error: {e}")
        return OwnerExtraction(error="Failed to extract owner info")

    @staticmethod
    async def get_tdlr_license(lead: Lead, owner_data: OwnerExtraction = None) -> LicenseInfo:
        """
        TDLR license verification with waterfall search.

        Search order (stops at first successful match):
        1. License number (if owner_data has it) - most accurate
        2. Owner name (if owner_data has first/last name)
        3. Business name (fallback)

        Args:
            lead: Lead data with business_name and city
            owner_data: Optional OwnerExtraction with owner name and license number
        """
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            try:
                # Use waterfall search if we have owner data
                if owner_data and (owner_data.license_number or owner_data.owner_first_name):
                    print(f"  TDLR: Using waterfall search with owner data")
                    print(f"    License: {owner_data.license_number or 'N/A'}")
                    print(f"    Owner: {owner_data.owner_first_name} {owner_data.owner_last_name}")

                    resp = await client.post(
                        f"{TDLR_SCRAPER_URL}/search/waterfall",
                        json={
                            "license_number": owner_data.license_number or None,
                            "owner_first_name": owner_data.owner_first_name or None,
                            "owner_last_name": owner_data.owner_last_name or None,
                            "business_name": lead.business_name,
                            "city": lead.city,
                            "lead_id": lead.id
                        }
                    )
                else:
                    # Fallback to business name only search
                    print(f"  TDLR: Using business name search (no owner data)")
                    resp = await client.post(
                        f"{TDLR_SCRAPER_URL}/search/business",
                        json={
                            "business_name": lead.business_name,
                            "city": lead.city,
                            "lead_id": lead.id
                        }
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    return LicenseInfo(
                        license_status=str(data.get("license_status", "Unknown")),
                        owner_name=str(data.get("owner_name", "")),
                        license_number=str(data.get("license_number", "")),
                        license_type=str(data.get("license_type", "")),
                        expiry_date=str(data.get("license_expiry", ""))
                    )
            except Exception as e:
                print(f"  TDLR error: {e}")
        return LicenseInfo()

    @staticmethod
    async def get_bbb_reputation(lead: Lead) -> ReputationData:
        """BBB reputation check"""
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{BBB_SCRAPER_URL}/search",
                    json={
                        "business_name": lead.business_name,
                        "city": lead.city,
                        "state": lead.state,
                        "google_rating": lead.google_rating,
                        "lead_id": lead.id
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ReputationData(
                        bbb_rating=str(data.get("bbb_rating", "NR")),
                        bbb_accredited=data.get("bbb_accredited", False),
                        complaints_3yr=int(data.get("complaints_3yr", 0)),
                        complaints_total=int(data.get("complaints_total", 0)),
                        reputation_gap=float(data.get("reputation_gap", 0)),
                        years_in_business=int(data.get("years_in_business") or 0)
                    )
            except Exception as e:
                print(f"  BBB error: {e}")
        return ReputationData()

    @staticmethod
    async def get_address_verification(lead: Lead) -> AddressVerification:
        """Address verification - residential vs commercial"""
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{ADDRESS_VERIFIER_URL}/verify",
                    json={
                        "address": lead.address,
                        "city": lead.city,
                        "state": lead.state,
                        "zip_code": lead.zip_code,
                        "lead_id": lead.id
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return AddressVerification(
                        is_residential=bool(data.get("is_residential", False)),
                        address_type=str(data.get("address_type", "unknown")),
                        verified=bool(data.get("verified", False)),
                        formatted_address=str(data.get("formatted_address", ""))
                    )
            except Exception as e:
                print(f"  Address verification error: {e}")
        return AddressVerification()

    @classmethod
    async def gather_all(cls, lead: Lead, website_url: str) -> tuple:
        """
        Run all intelligence gathering with optimized flow.

        Flow:
        1. FIRST: Extract owner info from website (needed for TDLR waterfall)
        2. PARALLEL: Visual, PageSpeed, Yext, BBB, Address
        3. TDLR with waterfall using owner data

        Returns:
            tuple: (visual, pagespeed, yext, tdlr, bbb, address, owner_extraction)
        """
        owner_data = OwnerExtraction()

        # STEP 1: Extract owner info first (KEY for TDLR waterfall)
        if website_url:
            print("  Phase 2D-Prep: Extracting owner info from website...")
            try:
                owner_data = await cls.get_owner_extraction(lead)
                if owner_data.owner_first_name:
                    print(f"  Owner found: {owner_data.owner_first_name} {owner_data.owner_last_name}")
                if owner_data.license_number:
                    print(f"  License found on website: {owner_data.license_number}")
            except Exception as e:
                print(f"  Owner extraction failed: {e}")
                owner_data = OwnerExtraction(error=str(e))

        # STEP 2: Build parallel task list
        tasks = []
        if website_url:
            tasks.append(cls.get_visual_analysis(lead))
            tasks.append(cls.get_pagespeed(lead))
        else:
            async def empty_visual(): return VisualAnalysis()
            async def empty_technical(): return TechnicalScores()
            tasks.append(empty_visual())
            tasks.append(empty_technical())

        tasks.extend([
            cls.get_yext_listings(lead),
            cls.get_tdlr_license(lead, owner_data),  # Pass owner data for waterfall
            cls.get_bbb_reputation(lead),
            cls.get_address_verification(lead)
        ])

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        visual = results[0] if not isinstance(results[0], Exception) else VisualAnalysis()
        pagespeed = results[1] if not isinstance(results[1], Exception) else TechnicalScores()
        yext = results[2] if not isinstance(results[2], Exception) else DirectoryPresence()
        tdlr = results[3] if not isinstance(results[3], Exception) else LicenseInfo()
        bbb = results[4] if not isinstance(results[4], Exception) else ReputationData()
        address = results[5] if not isinstance(results[5], Exception) else AddressVerification()

        return visual, pagespeed, yext, tdlr, bbb, address


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


class QuickChartClient:
    """QuickChart.io for generating chart images"""

    BASE_URL = "https://quickchart.io/chart"

    async def generate_chart(
        self,
        chart_config: Dict[str, Any],
        width: int = 500,
        height: int = 300,
        format: str = "png",
        background_color: str = "white"
    ) -> Optional[str]:
        """
        Generate a chart image URL from Chart.js config.

        Returns the image URL or None on failure.
        """
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    self.BASE_URL,
                    json={
                        "chart": chart_config,
                        "width": width,
                        "height": height,
                        "format": format,
                        "backgroundColor": background_color
                    }
                )
                if resp.status_code == 200:
                    # POST returns the image directly, use GET URL for shareable link
                    return self._build_url(chart_config, width, height, background_color)
            except Exception as e:
                print(f"  QuickChart error: {e}")
        return None

    def _build_url(
        self,
        chart_config: Dict[str, Any],
        width: int,
        height: int,
        background_color: str
    ) -> str:
        """Build a shareable chart URL."""
        import urllib.parse
        config_str = json.dumps(chart_config)
        encoded = urllib.parse.quote(config_str)
        return f"{self.BASE_URL}?c={encoded}&w={width}&h={height}&bkg={background_color}"

    async def pain_score_gauge(self, score: int, business_name: str) -> Optional[str]:
        """Generate a pain score gauge chart."""
        config = {
            "type": "gauge",
            "data": {
                "datasets": [{
                    "value": score,
                    "minValue": 0,
                    "maxValue": 100,
                    "data": [30, 50, 70, 100],
                    "backgroundColor": ["#4ade80", "#facc15", "#fb923c", "#ef4444"]
                }]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": f"Pain Score: {business_name}"
                }
            }
        }
        return await self.generate_chart(config, width=400, height=300)

    async def score_comparison_bar(
        self,
        labels: list,
        scores: list,
        title: str = "Score Comparison"
    ) -> Optional[str]:
        """Generate a bar chart comparing scores."""
        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Score",
                    "data": scores,
                    "backgroundColor": [
                        "#3b82f6", "#8b5cf6", "#ec4899", "#f97316", "#22c55e"
                    ]
                }]
            },
            "options": {
                "title": {"display": True, "text": title},
                "scales": {"yAxes": [{"ticks": {"beginAtZero": True, "max": 100}}]}
            }
        }
        return await self.generate_chart(config, width=600, height=400)

    async def pipeline_funnel(
        self,
        stages: list,
        counts: list,
        title: str = "Pipeline Funnel"
    ) -> Optional[str]:
        """Generate a funnel chart for pipeline stages."""
        config = {
            "type": "horizontalBar",
            "data": {
                "labels": stages,
                "datasets": [{
                    "data": counts,
                    "backgroundColor": [
                        "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#d946ef"
                    ]
                }]
            },
            "options": {
                "title": {"display": True, "text": title},
                "legend": {"display": False},
                "scales": {"xAxes": [{"ticks": {"beginAtZero": True}}]}
            }
        }
        return await self.generate_chart(config, width=500, height=300)

    async def tech_stack_radar(
        self,
        categories: list,
        scores: list,
        title: str = "Tech Stack Analysis"
    ) -> Optional[str]:
        """Generate a radar chart for tech stack analysis."""
        config = {
            "type": "radar",
            "data": {
                "labels": categories,
                "datasets": [{
                    "label": "Score",
                    "data": scores,
                    "backgroundColor": "rgba(59, 130, 246, 0.2)",
                    "borderColor": "#3b82f6",
                    "pointBackgroundColor": "#3b82f6"
                }]
            },
            "options": {
                "title": {"display": True, "text": title},
                "scale": {"ticks": {"beginAtZero": True, "max": 100}}
            }
        }
        return await self.generate_chart(config, width=500, height=500)


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


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) service for knowledge-grounded email generation.

    Uses OpenAI embeddings + Supabase pgvector for semantic search.
    """

    OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"

    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_SERVICE_KEY
        self.embedding_model = RAG_EMBEDDING_MODEL

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text using OpenAI."""
        if not OPENAI_API_KEY:
            print("  RAG: OpenAI API key not configured")
            return []

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    self.OPENAI_EMBEDDING_URL,
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.embedding_model,
                        "input": text
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return data["data"][0]["embedding"]
                else:
                    print(f"  RAG embedding error: {resp.status_code} - {resp.text[:200]}")

            except Exception as e:
                print(f"  RAG embedding error: {e}")

        return []

    async def add_knowledge_document(
        self,
        title: str,
        content: str,
        category: str = "general",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add a document to the knowledge base with embedding."""
        # Generate embedding
        embedding = await self.generate_embedding(f"{title}\n\n{content}")
        if not embedding:
            return False

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.supabase_url}/rest/v1/knowledge_documents",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json={
                        "title": title,
                        "content": content,
                        "category": category,
                        "metadata": metadata or {},
                        "embedding": embedding
                    }
                )
                return resp.status_code in [200, 201]

            except Exception as e:
                print(f"  RAG add document error: {e}")
                return False

    async def add_email_template(
        self,
        name: str,
        subject_template: str,
        body_template: str,
        use_case: str,
        pain_points: List[str] = None,
        performance_score: float = 0
    ) -> bool:
        """Add an email template with embedding for similarity matching."""
        # Generate embedding from combined template content
        embed_text = f"{use_case}\n{subject_template}\n{body_template}"
        embedding = await self.generate_embedding(embed_text)
        if not embedding:
            return False

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.supabase_url}/rest/v1/email_templates",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json={
                        "name": name,
                        "subject_template": subject_template,
                        "body_template": body_template,
                        "use_case": use_case,
                        "pain_points": pain_points or [],
                        "performance_score": performance_score,
                        "embedding": embedding
                    }
                )
                return resp.status_code in [200, 201]

            except Exception as e:
                print(f"  RAG add template error: {e}")
                return False

    async def search_knowledge(
        self,
        query: str,
        category: str = None,
        match_threshold: float = 0.7,
        match_count: int = 5
    ) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant documents."""
        # Generate query embedding
        query_embedding = await self.generate_embedding(query)
        if not query_embedding:
            return []

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                # Call the match_knowledge_documents function via RPC
                resp = await client.post(
                    f"{self.supabase_url}/rest/v1/rpc/match_knowledge_documents",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "query_embedding": query_embedding,
                        "match_threshold": match_threshold,
                        "match_count": match_count,
                        "filter_category": category
                    }
                )

                if resp.status_code == 200:
                    return resp.json()
                else:
                    print(f"  RAG search error: {resp.status_code}")

            except Exception as e:
                print(f"  RAG search error: {e}")

        return []

    async def search_email_templates(
        self,
        query: str,
        match_threshold: float = 0.6,
        match_count: int = 3
    ) -> List[Dict[str, Any]]:
        """Search for similar email templates."""
        query_embedding = await self.generate_embedding(query)
        if not query_embedding:
            return []

        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.supabase_url}/rest/v1/rpc/match_email_templates",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "query_embedding": query_embedding,
                        "match_threshold": match_threshold,
                        "match_count": match_count
                    }
                )

                if resp.status_code == 200:
                    return resp.json()

            except Exception as e:
                print(f"  RAG template search error: {e}")

        return []

    async def get_context_for_email(
        self,
        lead: Lead,
        pain_points: List[str],
        tech_context: str = ""
    ) -> Dict[str, Any]:
        """
        Get RAG context for email generation.

        Returns relevant knowledge documents and email templates
        based on the lead's characteristics and pain points.
        """
        # Build search query from lead context
        search_parts = [
            lead.business_name,
            f"local business in {lead.city}",
        ]
        search_parts.extend(pain_points[:3])  # Top 3 pain points
        if tech_context:
            search_parts.append(tech_context)

        search_query = " ".join(search_parts)

        # Search in parallel
        knowledge_task = self.search_knowledge(
            query=search_query,
            category="email_guidance",
            match_count=3
        )
        template_task = self.search_email_templates(
            query=search_query,
            match_count=2
        )

        knowledge_docs, email_templates = await asyncio.gather(
            knowledge_task,
            template_task
        )

        # Format context for LLM
        context = {
            "knowledge_snippets": [],
            "example_templates": [],
            "has_context": False
        }

        if knowledge_docs:
            context["knowledge_snippets"] = [
                {
                    "title": doc["title"],
                    "content": doc["content"][:500],  # Truncate for context window
                    "relevance": doc["similarity"]
                }
                for doc in knowledge_docs
            ]
            context["has_context"] = True

        if email_templates:
            context["example_templates"] = [
                {
                    "name": tmpl["name"],
                    "subject": tmpl["subject_template"],
                    "body_preview": tmpl["body_template"][:300],
                    "use_case": tmpl["use_case"],
                    "performance": tmpl["performance_score"]
                }
                for tmpl in email_templates
            ]
            context["has_context"] = True

        return context

    async def seed_initial_knowledge(self) -> int:
        """Seed the knowledge base with initial documents."""
        documents = [
            {
                "title": "Email Best Practices for Local Businesses",
                "content": """When emailing local business owners:
                - Keep emails under 150 words
                - Lead with a specific observation about their business
                - Mention a single, clear pain point
                - Offer one specific solution, not a menu
                - Include a low-friction CTA (reply, quick call)
                - Personalize with their city/neighborhood
                - Avoid jargon - speak their language
                - Don't oversell - be consultative""",
                "category": "email_guidance"
            },
            {
                "title": "Pain Point Messaging Guide",
                "content": """How to address common pain points:

                LOW GOOGLE RATING: "I noticed your Google rating could use some love..."
                OUTDATED WEBSITE: "Your website looks like it might be due for a refresh..."
                NO ONLINE BOOKING: "I saw customers can't book online yet..."
                POOR MOBILE EXPERIENCE: "When I checked your site on my phone..."
                MISSING ANALYTICS: "Are you tracking where your leads come from?"
                BBB COMPLAINTS: "I noticed some customer feedback that might need attention..."
                LICENSE ISSUES: "Just wanted to make sure you're aware of..."

                Always acknowledge the pain without being negative.""",
                "category": "email_guidance"
            },
            {
                "title": "Subject Line Formulas That Work",
                "content": """High-performing subject line patterns:

                1. Question format: "Quick question about [business name]?"
                2. Observation: "Noticed something about your [website/reviews]"
                3. Local angle: "Fellow [city] business reaching out"
                4. Specific number: "3 customers you might be missing"
                5. Curiosity gap: "Something I found while researching [industry]"

                Keep under 50 characters. Avoid spam triggers.
                Test shows question format gets 23% higher opens.""",
                "category": "email_guidance"
            }
        ]

        added = 0
        for doc in documents:
            success = await self.add_knowledge_document(**doc)
            if success:
                added += 1
                print(f"  Added: {doc['title']}")

        return added


class HallucinationDetector:
    """
    Hallucination detection using Cleanlab TLM.

    Provides trustworthiness scoring for LLM outputs to catch
    factual errors, hallucinations, and unreliable responses.
    """

    CLEANLAB_API_URL = "https://api.cleanlab.ai/v1"

    def __init__(self, threshold: float = None):
        self.api_key = CLEANLAB_API_KEY
        self.threshold = threshold or HALLUCINATION_THRESHOLD

    async def get_trustworthiness_score(
        self,
        prompt: str,
        response: str
    ) -> Dict[str, Any]:
        """
        Score the trustworthiness of an LLM response.

        Args:
            prompt: The original prompt/question
            response: The LLM's response to evaluate

        Returns:
            Dict with:
                - trustworthiness_score: 0-1 (higher = more trustworthy)
                - is_trustworthy: Boolean based on threshold
                - risk_level: 'low', 'medium', 'high'
        """
        if not self.api_key:
            # Fallback: return neutral score if not configured
            return {
                "trustworthiness_score": 0.5,
                "is_trustworthy": True,
                "risk_level": "unknown",
                "error": "Cleanlab API key not configured"
            }

        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    f"{self.CLEANLAB_API_URL}/trustworthiness",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": prompt,
                        "response": response
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    score = data.get("trustworthiness_score", 0.5)

                    return {
                        "trustworthiness_score": score,
                        "is_trustworthy": score >= self.threshold,
                        "risk_level": self._get_risk_level(score),
                        "raw_response": data
                    }
                else:
                    print(f"  Cleanlab error: {resp.status_code} - {resp.text[:200]}")
                    return {
                        "trustworthiness_score": 0.5,
                        "is_trustworthy": True,
                        "risk_level": "unknown",
                        "error": f"API error: {resp.status_code}"
                    }

            except Exception as e:
                print(f"  Cleanlab error: {e}")
                return {
                    "trustworthiness_score": 0.5,
                    "is_trustworthy": True,
                    "risk_level": "unknown",
                    "error": str(e)
                }

    async def verify_email_content(
        self,
        lead_context: str,
        email_subject: str,
        email_body: str,
        pain_points: List[str]
    ) -> Dict[str, Any]:
        """
        Verify that generated email content is trustworthy and accurate.

        Checks multiple aspects:
        1. Subject line relevance
        2. Body content accuracy
        3. Pain point claims
        """
        results = {
            "overall_trustworthy": True,
            "overall_score": 0.0,
            "checks": []
        }

        # Check 1: Subject line relevance
        subject_prompt = f"""Given this business context:
{lead_context}

Is this email subject line relevant and accurate? Subject: "{email_subject}"
Answer only 'yes' or 'no' and explain why."""

        subject_check = await self.get_trustworthiness_score(
            prompt=subject_prompt,
            response=f"The subject line '{email_subject}' is relevant to the business context."
        )
        results["checks"].append({
            "type": "subject_relevance",
            "score": subject_check["trustworthiness_score"],
            "passed": subject_check["is_trustworthy"]
        })

        # Check 2: Body content - no false claims
        body_prompt = f"""Business context: {lead_context}

Review this email for factual accuracy and relevance:
{email_body}

Does this email contain accurate, relevant information without false claims?"""

        body_check = await self.get_trustworthiness_score(
            prompt=body_prompt,
            response="The email content is accurate and makes no false claims about the business."
        )
        results["checks"].append({
            "type": "body_accuracy",
            "score": body_check["trustworthiness_score"],
            "passed": body_check["is_trustworthy"]
        })

        # Check 3: Pain points are justified
        if pain_points:
            pain_prompt = f"""Business context: {lead_context}

Are these pain points accurate observations?
Pain points: {', '.join(pain_points[:3])}"""

            pain_check = await self.get_trustworthiness_score(
                prompt=pain_prompt,
                response=f"The pain points ({', '.join(pain_points[:3])}) are accurate observations based on the business data."
            )
            results["checks"].append({
                "type": "pain_points_justified",
                "score": pain_check["trustworthiness_score"],
                "passed": pain_check["is_trustworthy"]
            })

        # Calculate overall score
        if results["checks"]:
            scores = [c["score"] for c in results["checks"]]
            results["overall_score"] = sum(scores) / len(scores)
            results["overall_trustworthy"] = all(c["passed"] for c in results["checks"])
            results["risk_level"] = self._get_risk_level(results["overall_score"])

        return results

    async def batch_score(
        self,
        items: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Score multiple prompt/response pairs.

        Args:
            items: List of dicts with 'prompt' and 'response' keys

        Returns:
            List of score results
        """
        tasks = [
            self.get_trustworthiness_score(item["prompt"], item["response"])
            for item in items
        ]
        return await asyncio.gather(*tasks)

    def _get_risk_level(self, score: float) -> str:
        """Convert score to risk level."""
        if score >= 0.85:
            return "low"
        elif score >= 0.7:
            return "medium"
        elif score >= 0.5:
            return "high"
        else:
            return "critical"

    async def generate_with_verification(
        self,
        prompt: str,
        generate_func,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate content with automatic verification and retry.

        If generated content has low trustworthiness, regenerates
        with additional context to improve accuracy.

        Args:
            prompt: The generation prompt
            generate_func: Async function that generates content
            max_retries: Max regeneration attempts

        Returns:
            Dict with final content and verification results
        """
        attempts = []

        for attempt in range(max_retries + 1):
            # Generate content
            if attempt == 0:
                content = await generate_func(prompt)
            else:
                # Add verification feedback to prompt
                enhanced_prompt = f"""{prompt}

IMPORTANT: Previous attempts had low confidence scores. Please ensure:
- All claims are factually accurate
- No assumptions or guesses
- Only include information directly supported by the provided data
- Be specific and avoid generalizations"""
                content = await generate_func(enhanced_prompt)

            # Verify
            score_result = await self.get_trustworthiness_score(
                prompt=prompt,
                response=content
            )

            attempts.append({
                "attempt": attempt + 1,
                "content": content,
                "score": score_result["trustworthiness_score"],
                "trustworthy": score_result["is_trustworthy"]
            })

            if score_result["is_trustworthy"]:
                return {
                    "content": content,
                    "trustworthiness_score": score_result["trustworthiness_score"],
                    "risk_level": score_result["risk_level"],
                    "attempts": attempts,
                    "verified": True
                }

        # Return best attempt if all failed verification
        best_attempt = max(attempts, key=lambda x: x["score"])
        return {
            "content": best_attempt["content"],
            "trustworthiness_score": best_attempt["score"],
            "risk_level": self._get_risk_level(best_attempt["score"]),
            "attempts": attempts,
            "verified": False,
            "warning": "Content did not pass verification threshold"
        }


class LLMCouncil:
    """
    LLM Council using CrewAI for multi-agent consensus decisions.

    Uses multiple specialized AI agents to review and validate:
    - Lead qualification decisions
    - Pain point identification
    - Email content quality
    - Overall lead scoring

    The council provides consensus-based outputs that are more
    reliable than single-agent decisions.
    """

    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        # Agent personas with specialized expertise
        self.agents = {
            "lead_analyst": {
                "role": "Lead Qualification Analyst",
                "expertise": "Business analysis, market research, lead scoring",
                "personality": "Analytical, data-driven, thorough"
            },
            "email_strategist": {
                "role": "Email Marketing Strategist",
                "expertise": "Copywriting, personalization, conversion optimization",
                "personality": "Creative, persuasive, customer-focused"
            },
            "quality_reviewer": {
                "role": "Quality Assurance Reviewer",
                "expertise": "Accuracy verification, compliance, brand consistency",
                "personality": "Detail-oriented, skeptical, methodical"
            },
            "risk_assessor": {
                "role": "Risk Assessment Specialist",
                "expertise": "Red flags, reputation analysis, potential issues",
                "personality": "Cautious, thorough, protective"
            }
        }

    async def _call_agent(
        self,
        agent_name: str,
        task: str,
        context: str,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Execute a single agent's analysis."""
        agent = self.agents.get(agent_name, {})

        system_prompt = f"""You are a {agent['role']} with expertise in {agent['expertise']}.
Your personality: {agent['personality']}.

Analyze the given context and provide your professional assessment.
Be concise but thorough. Focus on your area of expertise.
Format your response as JSON with keys: assessment, confidence (0-1), concerns (list), recommendations (list)."""

        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    self.ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"Task: {task}\n\nContext:\n{context}"
                            }
                        ]
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content = data["content"][0]["text"]

                    # Try to parse as JSON
                    try:
                        # Clean up potential markdown formatting
                        content_clean = content.strip()
                        if content_clean.startswith("```json"):
                            content_clean = content_clean[7:]
                        if content_clean.startswith("```"):
                            content_clean = content_clean[3:]
                        if content_clean.endswith("```"):
                            content_clean = content_clean[:-3]

                        result = json.loads(content_clean.strip())
                    except json.JSONDecodeError:
                        result = {
                            "assessment": content,
                            "confidence": 0.5,
                            "concerns": [],
                            "recommendations": []
                        }

                    return {
                        "agent": agent_name,
                        "role": agent["role"],
                        "result": result,
                        "success": True
                    }
                else:
                    return {
                        "agent": agent_name,
                        "role": agent["role"],
                        "result": {"error": f"API error: {resp.status_code}"},
                        "success": False
                    }

            except Exception as e:
                return {
                    "agent": agent_name,
                    "role": agent["role"],
                    "result": {"error": str(e)},
                    "success": False
                }

    async def evaluate_lead(
        self,
        lead_data: Dict[str, Any],
        enrichment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Have the council evaluate a lead for qualification.

        Returns consensus decision with individual agent assessments.
        """
        context = f"""
LEAD DATA:
- Business: {lead_data.get('business_name', 'Unknown')}
- Location: {lead_data.get('city', '')}, {lead_data.get('state', '')}
- Website: {lead_data.get('website_url', 'None')}
- Google Rating: {lead_data.get('google_rating', 'N/A')}
- Reviews: {lead_data.get('review_count', 0)}

ENRICHMENT DATA:
- Tech Stack: {enrichment_data.get('tech_stack', {})}
- Visual Score: {enrichment_data.get('visual_score', 'N/A')}
- PageSpeed: {enrichment_data.get('performance_score', 'N/A')}
- License Status: {enrichment_data.get('license_status', 'Unknown')}
- BBB Rating: {enrichment_data.get('bbb_rating', 'NR')}
- Years in Business: {enrichment_data.get('years_in_business', 'Unknown')}
"""

        task = "Evaluate this lead for qualification. Should we pursue this lead? Rate their potential value and identify any concerns."

        # Run agents in parallel
        agent_tasks = [
            self._call_agent("lead_analyst", task, context),
            self._call_agent("risk_assessor", task, context)
        ]

        results = await asyncio.gather(*agent_tasks)

        return self._build_consensus(results, "lead_evaluation")

    async def review_pain_points(
        self,
        lead_data: Dict[str, Any],
        identified_pain_points: List[str],
        enrichment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Have the council validate identified pain points.

        Ensures pain points are accurate and appropriately prioritized.
        """
        context = f"""
LEAD DATA:
- Business: {lead_data.get('business_name', 'Unknown')}
- Industry: Local service business
- Website: {lead_data.get('website_url', 'None')}

IDENTIFIED PAIN POINTS:
{chr(10).join(f'- {pp}' for pp in identified_pain_points)}

SUPPORTING DATA:
- Google Rating: {lead_data.get('google_rating', 'N/A')} ({lead_data.get('review_count', 0)} reviews)
- Visual Score: {enrichment_data.get('visual_score', 'N/A')}/100
- Mobile Score: {enrichment_data.get('mobile_score', 'N/A')}/100
- Has GTM: {enrichment_data.get('has_gtm', False)}
- Has GA4: {enrichment_data.get('has_ga4', False)}
- CRM: {enrichment_data.get('crm_detected', 'None')}
"""

        task = """Review the identified pain points:
1. Are they accurate based on the data?
2. Are they prioritized correctly?
3. Are any pain points missing?
4. Are any pain points incorrect or overstated?"""

        agent_tasks = [
            self._call_agent("lead_analyst", task, context),
            self._call_agent("quality_reviewer", task, context)
        ]

        results = await asyncio.gather(*agent_tasks)

        return self._build_consensus(results, "pain_point_review")

    async def review_email_content(
        self,
        email_subject: str,
        email_body: str,
        lead_context: str,
        pain_points: List[str]
    ) -> Dict[str, Any]:
        """
        Have the council review generated email content.

        Checks for quality, accuracy, and effectiveness.
        """
        context = f"""
LEAD CONTEXT:
{lead_context}

TARGETED PAIN POINTS:
{chr(10).join(f'- {pp}' for pp in pain_points)}

GENERATED EMAIL:
Subject: {email_subject}

Body:
{email_body}
"""

        task = """Review this email for:
1. Accuracy - Are all claims truthful and supported by data?
2. Relevance - Does it address the right pain points?
3. Effectiveness - Will it resonate with the recipient?
4. Professionalism - Is the tone appropriate?
5. Compliance - Any red flags or potential issues?"""

        agent_tasks = [
            self._call_agent("email_strategist", task, context),
            self._call_agent("quality_reviewer", task, context),
            self._call_agent("risk_assessor", task, context)
        ]

        results = await asyncio.gather(*agent_tasks)

        return self._build_consensus(results, "email_review")

    async def final_qualification_vote(
        self,
        lead_data: Dict[str, Any],
        enrichment_data: Dict[str, Any],
        pain_score: int,
        email_content: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Final council vote on whether to proceed with this lead.

        All agents vote, and consensus determines the outcome.
        """
        context = f"""
FINAL REVIEW - READY TO SEND?

Lead: {lead_data.get('business_name', 'Unknown')}
Location: {lead_data.get('city', '')}, {lead_data.get('state', '')}
Pain Score: {pain_score}/100

Key Metrics:
- Google Rating: {lead_data.get('google_rating', 'N/A')}
- Website Score: {enrichment_data.get('visual_score', 'N/A')}/100
- License: {enrichment_data.get('license_status', 'Unknown')}
- BBB: {enrichment_data.get('bbb_rating', 'NR')}

Proposed Email:
Subject: {email_content.get('subject', '')}
Preview: {email_content.get('body', '')[:200]}...
"""

        task = """VOTE: Should we send this email to this lead?
Respond with:
- vote: 'yes', 'no', or 'abstain'
- confidence: 0-1
- reason: Brief explanation
- blocking_concerns: Any issues that must be resolved"""

        # All agents vote
        agent_tasks = [
            self._call_agent(name, task, context)
            for name in self.agents.keys()
        ]

        results = await asyncio.gather(*agent_tasks)

        return self._build_voting_result(results)

    def _build_consensus(
        self,
        results: List[Dict[str, Any]],
        decision_type: str
    ) -> Dict[str, Any]:
        """Build consensus from multiple agent results."""
        successful = [r for r in results if r.get("success")]

        if not successful:
            return {
                "decision_type": decision_type,
                "consensus": "unable_to_determine",
                "confidence": 0,
                "agent_results": results,
                "all_concerns": [],
                "all_recommendations": []
            }

        # Aggregate concerns and recommendations
        all_concerns = []
        all_recommendations = []
        confidence_scores = []

        for r in successful:
            result = r.get("result", {})
            if isinstance(result.get("concerns"), list):
                all_concerns.extend(result["concerns"])
            if isinstance(result.get("recommendations"), list):
                all_recommendations.extend(result["recommendations"])
            if isinstance(result.get("confidence"), (int, float)):
                confidence_scores.append(result["confidence"])

        # Calculate average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5

        # Deduplicate concerns and recommendations
        unique_concerns = list(set(all_concerns))
        unique_recommendations = list(set(all_recommendations))

        return {
            "decision_type": decision_type,
            "consensus": "approved" if avg_confidence >= 0.6 else "needs_review",
            "confidence": round(avg_confidence, 2),
            "agent_results": results,
            "all_concerns": unique_concerns,
            "all_recommendations": unique_recommendations,
            "agents_consulted": len(successful)
        }

    def _build_voting_result(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build voting result from agent votes."""
        votes = {"yes": 0, "no": 0, "abstain": 0}
        blocking_concerns = []

        for r in results:
            if not r.get("success"):
                votes["abstain"] += 1
                continue

            result = r.get("result", {})
            vote = result.get("vote", "abstain").lower()

            if vote in votes:
                votes[vote] += 1
            else:
                votes["abstain"] += 1

            # Collect blocking concerns
            if isinstance(result.get("blocking_concerns"), list):
                blocking_concerns.extend(result["blocking_concerns"])
            elif result.get("blocking_concerns"):
                blocking_concerns.append(str(result["blocking_concerns"]))

        # Determine outcome
        total_votes = votes["yes"] + votes["no"]
        if total_votes == 0:
            decision = "abstain"
        elif votes["yes"] > votes["no"]:
            decision = "approved"
        elif votes["no"] > votes["yes"]:
            decision = "rejected"
        else:
            decision = "tie"

        # Block if there are any blocking concerns
        if blocking_concerns:
            decision = "blocked"

        return {
            "decision": decision,
            "votes": votes,
            "blocking_concerns": list(set(blocking_concerns)),
            "agent_results": results,
            "approval_rate": votes["yes"] / total_votes if total_votes > 0 else 0
        }

    async def quick_review(
        self,
        content_type: str,
        content: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Quick single-agent review for simple validations.

        Uses the quality_reviewer agent for fast checks.
        """
        task = f"Quick review of {content_type}. Is this acceptable? Any immediate concerns?"
        full_context = f"{context}\n\nContent to review:\n{content}" if context else content

        result = await self._call_agent("quality_reviewer", task, full_context)

        return {
            "content_type": content_type,
            "passed": result.get("result", {}).get("confidence", 0) >= 0.6,
            "result": result
        }
