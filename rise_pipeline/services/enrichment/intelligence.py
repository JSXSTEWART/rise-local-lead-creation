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
