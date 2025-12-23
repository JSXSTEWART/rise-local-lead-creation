"""
Main Pipeline Orchestrator for Rise Local Lead Processing

This is the entry point that coordinates all pipeline stages:
1. Fetch lead from Supabase
2. Enrich with tech stack (Clay)
3. Gather intelligence (Screenshot, PageSpeed, Yext, TDLR, BBB) in parallel
4. Calculate pain score
5. If qualified: enrich contacts, generate email, deliver to Instantly/GHL
6. Update lead status in Supabase
"""
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Optional

# Support both package-relative and top-level imports. When this module is
# imported as part of the ``rise_pipeline`` package (e.g. via
# ``from rise_pipeline import pipeline``) the relative imports work. When
# imported as a top-level script (e.g. ``import pipeline`` from within
# the same directory), the relative imports will fail. In that case we
# fall back to importing the modules from the current working directory.
try:
    from .models import (
        Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
        DirectoryPresence, LicenseInfo, ReputationData,
        PainScore, ContactInfo, GeneratedEmail,
        PipelineResult, LeadStatus, QualificationStatus
    )  # type: ignore
except ImportError:
    from models import (
        Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
        DirectoryPresence, LicenseInfo, ReputationData,
        PainScore, ContactInfo, GeneratedEmail,
        PipelineResult, LeadStatus, QualificationStatus
    )  # type: ignore

try:
    from .services import (
        SupabaseClient, ClayClient, IntelligenceServices,
        InstantlyClient, GHLClient, FullEnrichClient, HeyReachClient,
        QuickChartClient, RAGService, HallucinationDetector, LLMCouncil
    )  # type: ignore
except ImportError:
    from services import (
        SupabaseClient, ClayClient, IntelligenceServices,
        InstantlyClient, GHLClient, FullEnrichClient, HeyReachClient,
        QuickChartClient, RAGService, HallucinationDetector, LLMCouncil
    )  # type: ignore

try:
    from .scoring import calculate_pain_score  # type: ignore
except ImportError:
    from scoring import calculate_pain_score  # type: ignore

try:
    from .email_generator import generate_email, select_ab_variant  # type: ignore
except ImportError:
    from email_generator import generate_email, select_ab_variant  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiseLocalPipeline:
    """Main pipeline orchestrator."""

    def __init__(self, use_fullenrich: bool = True, use_rag: bool = True, use_council: bool = True):
        self.supabase = SupabaseClient()
        self.clay = ClayClient()
        self.fullenrich = FullEnrichClient()
        self.intelligence = IntelligenceServices()
        self.instantly = InstantlyClient()
        self.ghl = GHLClient()
        self.heyreach = HeyReachClient()
        self.charts = QuickChartClient()
        self.rag = RAGService()
        self.hallucination = HallucinationDetector()
        self.council = LLMCouncil()
        self.use_fullenrich = use_fullenrich  # Use FullEnrich for contacts (Clay as fallback)
        self.use_rag = use_rag  # Use RAG for knowledge-grounded email generation
        self.use_council = use_council  # Use LLM Council for consensus-based decisions

    async def process_lead(self, lead_id: str) -> PipelineResult:
        """
        Process a single lead through the entire pipeline.

        Returns PipelineResult with status and all collected data.
        """
        logger.info(f"Starting pipeline for lead: {lead_id}")

        try:
            # =================================================================
            # STAGE 1: Fetch Lead
            # =================================================================
            logger.info("Stage 1: Fetching lead from Supabase")

            lead = await self.supabase.get_lead(lead_id)
            if not lead:
                logger.error(f"Lead not found: {lead_id}")
                return PipelineResult(
                    lead_id=lead_id,
                    status=LeadStatus.FAILED,
                    error="Lead not found in database"
                )

            # Update status to processing
            await self.supabase.update_lead(lead_id, {"status": "processing"})

            logger.info(f"Processing: {lead.business_name} ({lead.city}, {lead.state})")

            # =================================================================
            # STAGE 2: Tech Stack Enrichment (from imported Clay data)
            # =================================================================
            logger.info("Stage 2: Loading tech enrichment from imported Clay data")

            # Get tech data that was imported via dashboard from Clay CSV
            tech = await self.supabase.get_tech_enrichment(lead_id)

            if tech.tech_score == 0 and not tech.has_gtm and not tech.has_ga4:
                logger.warning("  No tech enrichment data found - was Clay CSV imported?")
                logger.info("  Proceeding with default tech values...")

            logger.info(f"Tech score: {tech.tech_score}/100, GTM: {tech.has_gtm}, GA4: {tech.has_ga4}")

            # =================================================================
            # STAGE 3: Parallel Intelligence Gathering
            # =================================================================
            logger.info("Stage 3: Gathering intelligence (parallel)")

            visual, technical, directory, license_info, reputation, address = await self.intelligence.gather_all(
                lead=lead,
                website_url=lead.website_url
            )

            logger.info(f"Visual: {visual.visual_score}, Perf: {technical.performance_score}, Listings: {directory.listings_score}")
            logger.info(f"Address: {address.address_type} (residential={address.is_residential})")

            # =================================================================
            # STAGE 4: Pain Point Scoring
            # =================================================================
            logger.info("Stage 4: Calculating pain score")

            pain_score = calculate_pain_score(
                lead=lead,
                tech=tech,
                visual=visual,
                technical=technical,
                directory=directory,
                license_info=license_info,
                reputation=reputation
            )

            logger.info(f"Pain score: {pain_score.score}, Status: {pain_score.status.value}")
            logger.info(f"Top pain points: {pain_score.top_pain_points[:3]}")

            # =================================================================
            # STAGE 5: Qualification Decision
            # =================================================================

            if pain_score.status == QualificationStatus.REJECTED:
                logger.info("Lead REJECTED - insufficient pain signals")

                # Update Supabase with rejection
                await self._update_lead_rejected(lead_id, tech, visual, technical, directory, license_info, reputation, address, pain_score)

                return PipelineResult(
                    lead_id=lead_id,
                    status=LeadStatus.REJECTED,
                    qualification_status=QualificationStatus.REJECTED,
                    pain_score=pain_score.score,
                    icp_score=pain_score.icp_score,
                    tech_enrichment=tech,
                    visual_analysis=visual,
                    technical_scores=technical,
                    directory_presence=directory,
                    license_info=license_info,
                    reputation_data=reputation
                )

            if pain_score.status == QualificationStatus.MARGINAL:
                logger.info("Lead MARGINAL - needs manual review")

                await self._update_lead_needs_review(lead_id, tech, visual, technical, directory, license_info, reputation, address, pain_score)

                return PipelineResult(
                    lead_id=lead_id,
                    status=LeadStatus.NEEDS_REVIEW,
                    qualification_status=QualificationStatus.MARGINAL,
                    pain_score=pain_score.score,
                    icp_score=pain_score.icp_score,
                    tech_enrichment=tech,
                    visual_analysis=visual,
                    technical_scores=technical,
                    directory_presence=directory,
                    license_info=license_info,
                    reputation_data=reputation
                )

            # =================================================================
            # STAGE 6: Contact Enrichment (from imported Clay data)
            # =================================================================
            logger.info("Stage 6: Loading contact info from imported Clay data")

            # Get contact data that was imported via dashboard from Clay CSV
            contact = await self.supabase.get_contact_info(lead_id)

            # Also check if we got owner name from TDLR license
            if not contact.owner_first_name and license_info.owner_name:
                owner_parts = license_info.owner_name.split()
                contact.owner_first_name = owner_parts[0] if owner_parts else ""
                contact.owner_last_name = " ".join(owner_parts[1:]) if len(owner_parts) > 1 else ""

            if not contact.owner_email:
                logger.warning("  No contact email found - was Clay Contact CSV imported?")
                logger.info("  Will still generate email but cannot deliver...")

            logger.info(f"Contact found: {contact.owner_email or 'No email'}, Verified: {contact.email_verified}, Source: {contact.contact_source or 'Clay import'}")

            # =================================================================
            # STAGE 7: Email Generation (Claude + RAG)
            # =================================================================
            logger.info("Stage 7: Generating personalized email")

            # Get RAG context if enabled
            rag_context = None
            if self.use_rag:
                logger.info("  Retrieving RAG context...")
                tech_context = f"CMS: {tech.cms_platform}, CRM: {tech.crm_detected}" if tech.cms_platform or tech.crm_detected else ""
                rag_context = await self.rag.get_context_for_email(
                    lead=lead,
                    pain_points=pain_score.top_pain_points,
                    tech_context=tech_context
                )
                if rag_context.get("has_context"):
                    logger.info(f"  RAG: {len(rag_context.get('knowledge_snippets', []))} docs, {len(rag_context.get('example_templates', []))} templates")

            ab_variant = select_ab_variant()
            email = await generate_email(
                lead=lead,
                tech=tech,
                visual=visual,
                technical=technical,
                directory=directory,
                reputation=reputation,
                pain_score=pain_score,
                variant=ab_variant,
                rag_context=rag_context  # Pass RAG context to email generator
            )

            if email.valid:
                logger.info(f"Email generated: '{email.subject_line}' (confidence: {email.confidence_score})")
            else:
                logger.warning(f"Email generation failed: {email.error}")

            # =================================================================
            # STAGE 8: Delivery (Instantly + HeyReach + GHL)
            # =================================================================
            delivery_success = False
            heyreach_success = False

            if email.valid and contact.owner_email:
                logger.info("Stage 8: Delivering to Instantly, HeyReach, and GHL")

                # Deliver to Instantly (email)
                instantly_result = await self.instantly.add_lead(
                    email=contact.owner_email,
                    first_name=contact.owner_first_name,
                    last_name=contact.owner_last_name,
                    company_name=lead.business_name,
                    custom_variables={
                        "subject_line": email.subject_line,
                        "preview_text": email.preview_text,
                        "email_body": email.email_body,
                        "pain_score": str(pain_score.score),
                        "ab_variant": ab_variant
                    }
                )

                # Deliver to HeyReach (LinkedIn) if we have LinkedIn URL
                if contact.owner_linkedin:
                    heyreach_result = await self.heyreach.add_lead_to_campaign(
                        linkedin_url=contact.owner_linkedin,
                        first_name=contact.owner_first_name,
                        last_name=contact.owner_last_name,
                        company_name=lead.business_name,
                        email=contact.owner_email,
                        custom_variables={
                            "pain_score": str(pain_score.score),
                            "top_pain": pain_score.top_pain_points[0] if pain_score.top_pain_points else "",
                            "ab_variant": ab_variant
                        }
                    )
                    heyreach_success = heyreach_result.get("success", False)
                    logger.info(f"HeyReach: {heyreach_success}")

                # Create contact in GHL
                ghl_result = await self.ghl.create_contact(
                    email=contact.owner_email,
                    first_name=contact.owner_first_name,
                    last_name=contact.owner_last_name,
                    phone=contact.owner_phone_direct or lead.phone,
                    company_name=lead.business_name,
                    tags=["rise-pipeline", f"pain-{pain_score.score}", ab_variant]
                )

                delivery_success = instantly_result.get("success", False) or ghl_result.get("success", False)

                logger.info(f"Delivery: Instantly={instantly_result.get('success')}, GHL={ghl_result.get('success')}, HeyReach={heyreach_success}")
            else:
                logger.warning("Skipping delivery: No valid email or contact")

            # =================================================================
            # STAGE 9: Final Update
            # =================================================================
            logger.info("Stage 9: Updating lead record")

            final_status = LeadStatus.DELIVERED if delivery_success else LeadStatus.QUALIFIED

            await self._update_lead_final(
                lead_id=lead_id,
                status=final_status,
                tech=tech,
                visual=visual,
                technical=technical,
                directory=directory,
                license_info=license_info,
                reputation=reputation,
                address=address,
                pain_score=pain_score,
                contact=contact,
                email=email,
                ab_variant=ab_variant
            )

            logger.info(f"Pipeline complete for {lead.business_name}: {final_status.value}")

            return PipelineResult(
                lead_id=lead_id,
                status=final_status,
                qualification_status=QualificationStatus.QUALIFIED,
                pain_score=pain_score.score,
                icp_score=pain_score.icp_score,
                email_subject=email.subject_line if email.valid else "",
                ab_variant=ab_variant,
                owner_email=contact.owner_email,
                tech_enrichment=tech,
                visual_analysis=visual,
                technical_scores=technical,
                directory_presence=directory,
                license_info=license_info,
                reputation_data=reputation,
                contact_info=contact,
                generated_email=email
            )

        except Exception as e:
            logger.exception(f"Pipeline failed for {lead_id}: {e}")

            # Update status to failed
            await self.supabase.update_lead(lead_id, {
                "status": "failed",
                "error_message": str(e),
                "processed_at": datetime.utcnow().isoformat()
            })

            return PipelineResult(
                lead_id=lead_id,
                status=LeadStatus.FAILED,
                error=str(e)
            )

    async def _update_lead_rejected(self, lead_id: str, tech, visual, technical, directory, license_info, reputation, address, pain_score):
        """Update lead record for rejected leads."""
        await self.supabase.update_lead(lead_id, {
            "status": "rejected",
            "pain_point_score": pain_score.score,
            "qualification_status": "rejected",
            "qualification_reason": ", ".join(pain_score.top_pain_points[:3]) if pain_score.top_pain_points else None,
            "tech_stack_score": tech.tech_score,
            "visual_score": visual.visual_score,
            "performance_score": technical.performance_score,
            "yext_score": directory.listings_score,
            "pain_point_details": ", ".join(pain_score.top_pain_points) if pain_score.top_pain_points else None,
            "is_residential": address.is_residential,
            "address_type": address.address_type,
            "address_verified": address.verified,
            "formatted_address": address.formatted_address if address.formatted_address else None,
            "address_verified_at": datetime.utcnow().isoformat() if address.verified else None,
            "phase_3_completed_at": datetime.utcnow().isoformat()
        })

    async def _update_lead_needs_review(self, lead_id: str, tech, visual, technical, directory, license_info, reputation, address, pain_score):
        """Update lead record for marginal leads."""
        await self.supabase.update_lead(lead_id, {
            "status": "needs_review",
            "pain_point_score": pain_score.score,
            "qualification_status": "marginal",
            "qualification_reason": ", ".join(pain_score.top_pain_points[:3]) if pain_score.top_pain_points else None,
            "requires_manual_review": True,
            "manual_review_reason": "Marginal pain score - needs human evaluation",
            "tech_stack_score": tech.tech_score,
            "visual_score": visual.visual_score,
            "performance_score": technical.performance_score,
            "yext_score": directory.listings_score,
            "pain_point_details": ", ".join(pain_score.top_pain_points) if pain_score.top_pain_points else None,
            "is_residential": address.is_residential,
            "address_type": address.address_type,
            "address_verified": address.verified,
            "formatted_address": address.formatted_address if address.formatted_address else None,
            "address_verified_at": datetime.utcnow().isoformat() if address.verified else None,
            "phase_3_completed_at": datetime.utcnow().isoformat()
        })

    async def _update_lead_final(self, lead_id: str, status: LeadStatus, tech, visual, technical, directory, license_info, reputation, address, pain_score, contact, email, ab_variant: str):
        """Update lead record for qualified/delivered leads."""
        # Build social links JSON
        social_links = {}
        if visual.social_facebook:
            social_links["facebook"] = visual.social_facebook
        if visual.social_instagram:
            social_links["instagram"] = visual.social_instagram
        if visual.social_linkedin:
            social_links["linkedin"] = visual.social_linkedin

        await self.supabase.update_lead(lead_id, {
            "status": status.value,
            "pain_point_score": pain_score.score,
            "qualification_status": "qualified",
            "qualification_reason": ", ".join(pain_score.top_pain_points[:3]) if pain_score.top_pain_points else None,
            # Tech enrichment (Phase 1)
            "has_gtm": tech.has_gtm,
            "has_ga4": tech.has_ga4,
            "crm_platform": tech.crm_detected or None,
            "has_booking_system": bool(tech.booking_system),
            "cms_platform": tech.cms_platform or None,
            "tech_stack_score": tech.tech_score,
            "phase_1_completed_at": datetime.utcnow().isoformat(),
            # Visual analysis (Phase 2A)
            "visual_score": visual.visual_score,
            "design_era": visual.design_era or None,
            "mobile_responsive_visual": visual.mobile_responsive,
            "has_hero_image": visual.has_hero_image,
            "has_clear_cta": visual.has_clear_cta,
            "has_trust_signals": visual.trust_signals > 0,
            "social_links": social_links if social_links else None,
            "social_links_count": len(social_links),
            "phase_2a_completed_at": datetime.utcnow().isoformat(),
            # Technical scores (Phase 2B)
            "performance_score": technical.performance_score,
            "mobile_score": technical.mobile_score,
            "seo_score": technical.seo_score,
            "phase_2b_completed_at": datetime.utcnow().isoformat(),
            # Directory (Phase 2C)
            "yext_score": directory.listings_score,
            "yext_scan_id": directory.scan_id or None,  # Store for webhook matching
            "nap_consistency": directory.nap_consistency >= 0.8 if directory.nap_consistency else False,
            "phase_2c_completed_at": datetime.utcnow().isoformat(),
            # License (Phase 2D)
            "license_status": license_info.license_status or None,
            "license_number": license_info.license_number or None,
            "owner_name_from_license": license_info.owner_name or None,
            "phase_2d_completed_at": datetime.utcnow().isoformat(),
            # Reputation (Phase 2E)
            "bbb_rating": reputation.bbb_rating or None,
            "bbb_accredited": reputation.bbb_accredited,
            "bbb_years_in_business": reputation.years_in_business or None,
            "reputation_gap": reputation.reputation_gap or None,
            "phase_2e_completed_at": datetime.utcnow().isoformat(),
            # Address Verification (Phase 2F)
            "is_residential": address.is_residential,
            "address_type": address.address_type,
            "address_verified": address.verified,
            "formatted_address": address.formatted_address if address.formatted_address else None,
            "address_verified_at": datetime.utcnow().isoformat() if address.verified else None,
            "phase_2f_completed_at": datetime.utcnow().isoformat(),
            # Pain score (Phase 3)
            "pain_point_details": ", ".join(pain_score.top_pain_points) if pain_score.top_pain_points else None,
            "phase_3_completed_at": datetime.utcnow().isoformat(),
            # Contact (Phase 4)
            "owner_email": contact.owner_email or None,
            "owner_first_name": contact.owner_first_name or None,
            "owner_last_name": contact.owner_last_name or None,
            "owner_linkedin_url": contact.owner_linkedin or None,
            "verified_email": contact.email_verified,
            "owner_source": contact.contact_source or None,
            "phase_4_completed_at": datetime.utcnow().isoformat() if contact.owner_email else None,
            # Email (Phase 6)
            "email_subject": email.subject_line if email.valid else None,
            "email_body": email.email_body if email.valid else None,
            "owner_email_confidence": int(email.confidence_score * 100) if email.valid else None,
            "ab_test_group": ab_variant,
            "phase_6_completed_at": datetime.utcnow().isoformat() if email.valid else None
        })


async def process_batch(lead_ids: list, concurrency: int = 3) -> list:
    """Process multiple leads with controlled concurrency."""
    pipeline = RiseLocalPipeline()
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(lead_id: str):
        async with semaphore:
            return await pipeline.process_lead(lead_id)

    tasks = [process_with_semaphore(lid) for lid in lead_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [
        r if isinstance(r, PipelineResult)
        else PipelineResult(lead_id="unknown", status=LeadStatus.FAILED, error=str(r))
        for r in results
    ]


async def fetch_and_process_new_leads(limit: int = 10) -> list:
    """Fetch new leads from Supabase and process them."""
    pipeline = RiseLocalPipeline()

    # Query for new leads
    response = await pipeline.supabase.client.get(
        f"{pipeline.supabase.base_url}/leads",
        headers=pipeline.supabase._headers(),
        params={
            "status": "eq.new",
            "limit": str(limit),
            "order": "created_at.asc"
        }
    )

    if response.status_code != 200:
        logger.error(f"Failed to fetch leads: {response.text}")
        return []

    leads = response.json()
    lead_ids = [lead["id"] for lead in leads]

    logger.info(f"Found {len(lead_ids)} new leads to process")

    return await process_batch(lead_ids)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Rise Local Lead Processing Pipeline")
    parser.add_argument("--lead-id", help="Process a specific lead by ID")
    parser.add_argument("--batch", help="Process comma-separated lead IDs")
    parser.add_argument("--fetch-new", type=int, default=0, help="Fetch and process N new leads")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent processing")

    args = parser.parse_args()

    if args.lead_id:
        # Process single lead
        pipeline = RiseLocalPipeline()
        result = asyncio.run(pipeline.process_lead(args.lead_id))
        print(f"\nResult: {result.status.value}")
        if result.error:
            print(f"Error: {result.error}")
        if result.pain_score:
            print(f"Pain Score: {result.pain_score}")
        if result.email_subject:
            print(f"Email Subject: {result.email_subject}")

    elif args.batch:
        # Process batch
        lead_ids = [lid.strip() for lid in args.batch.split(",")]
        results = asyncio.run(process_batch(lead_ids, args.concurrency))

        print(f"\nProcessed {len(results)} leads:")
        for r in results:
            status_emoji = "✓" if r.status in [LeadStatus.QUALIFIED, LeadStatus.DELIVERED] else "✗"
            print(f"  {status_emoji} {r.lead_id}: {r.status.value}")

    elif args.fetch_new > 0:
        # Fetch and process new leads
        results = asyncio.run(fetch_and_process_new_leads(args.fetch_new))

        qualified = sum(1 for r in results if r.status in [LeadStatus.QUALIFIED, LeadStatus.DELIVERED])
        rejected = sum(1 for r in results if r.status == LeadStatus.REJECTED)
        review = sum(1 for r in results if r.status == LeadStatus.NEEDS_REVIEW)
        failed = sum(1 for r in results if r.status == LeadStatus.FAILED)

        print(f"\nBatch Summary:")
        print(f"  Qualified/Delivered: {qualified}")
        print(f"  Rejected: {rejected}")
        print(f"  Needs Review: {review}")
        print(f"  Failed: {failed}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
