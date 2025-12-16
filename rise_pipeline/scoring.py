"""
Pain Point Scoring Logic for Rise Local Pipeline

Scoring thresholds:
- <= 3 points: REJECTED (not enough pain signals)
- 4-5 points: MARGINAL (needs review)
- >= 6 points: QUALIFIED (proceed to contact enrichment)

UPDATED: Now integrates AI-powered tech stack analysis from Claude Haiku
UPDATED 2025-12-15: Added FREE tracking detection for pre-qualification
"""
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from .models import (
    Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
    DirectoryPresence, LicenseInfo, ReputationData, AddressVerification,
    TrackingAnalysis, LeadCategory, CategoryAssignment,
    PainSignal, PainScore, QualificationStatus
)
from .config import PAIN_SCORE_REJECT_THRESHOLD, PAIN_SCORE_MARGINAL_THRESHOLD

# Pre-qualification thresholds (for FREE scraper data only)
PREQUALIFY_REJECT_THRESHOLD = 2  # <= 2 = rejected, don't send to Clay
PREQUALIFY_MARGINAL_THRESHOLD = 4  # 3-4 = marginal, manual review
# >= 5 = qualified, send to Clay

# DIY website builders that indicate self-built sites
DIY_CMS_PLATFORMS = ["wix", "squarespace", "weebly", "godaddy", "webflow", "duda", "jimdo"]


@dataclass
class PreQualificationScore:
    """Pre-qualification scoring result (FREE data only, no Clay)"""
    score: int
    signals: List[PainSignal]
    status: QualificationStatus
    top_signals: List[str]
    send_to_clay: bool  # True if qualified for Clay enrichment
    category_assignment: Optional[CategoryAssignment] = None  # Lead category


def calculate_pre_qualification_score(
    lead: Lead,
    visual: VisualAnalysis,
    technical: TechnicalScores,
    license_info: LicenseInfo,
    reputation: ReputationData,
    address: AddressVerification,
    tracking: Optional[TrackingAnalysis] = None
) -> PreQualificationScore:
    """
    Calculate pre-qualification score using ONLY FREE scraper data.

    This determines whether a lead should be sent to Clay for paid enrichment.
    Now includes FREE tracking detection from Screenshot Service HTML inspection.

    AUTO-DISQUALIFIERS (instant rejection):
    - License expired, revoked, or suspended

    Args:
        lead: Basic lead info (Google Places data)
        visual: Screenshot analysis (FREE - port 8004)
        technical: PageSpeed scores (FREE - port 8003)
        license_info: TDLR license data (FREE - port 8001)
        reputation: BBB data (FREE - port 8002)
        address: Address verification (FREE - port 8006)
        tracking: FREE tracking/tech detection from HTML (port 8004)

    Returns:
        PreQualificationScore with decision on whether to send to Clay
    """
    signals: List[PainSignal] = []

    # Use empty tracking if not provided
    if tracking is None:
        tracking = TrackingAnalysis()

    # =========================================================================
    # AUTO-DISQUALIFIERS (Instant Rejection)
    # =========================================================================

    # License expired/suspended = CAN'T DO BUSINESS, auto reject
    if license_info.license_status.lower() in ["expired", "revoked", "suspended"]:
        return PreQualificationScore(
            score=0,
            signals=[PainSignal(
                signal=f"AUTO-DISQUALIFIED: License {license_info.license_status.lower()}",
                points=0,
                category="Compliance"
            )],
            status=QualificationStatus.REJECTED,
            top_signals=[f"License {license_info.license_status.lower()} - cannot operate legally"],
            send_to_clay=False,
            category_assignment=None
        )

    # =========================================================================
    # VISUAL/DESIGN SIGNALS (FREE - Screenshot Service)
    # =========================================================================

    # Poor visual score - strong pain indicator
    if visual.visual_score < 40:
        signals.append(PainSignal(
            signal=f"Outdated website design (score: {visual.visual_score}/100)",
            points=3,
            category="Design"
        ))
    elif visual.visual_score < 60:
        signals.append(PainSignal(
            signal=f"Average website design ({visual.visual_score}/100)",
            points=2,
            category="Design"
        ))

    # Legacy design era
    if visual.design_era and visual.design_era.lower() in ["legacy", "dated", "2000s", "2010s"]:
        signals.append(PainSignal(
            signal=f"Legacy design era ({visual.design_era})",
            points=2,
            category="Design"
        ))

    # Not mobile responsive
    if not visual.mobile_responsive:
        signals.append(PainSignal(
            signal="Not mobile responsive",
            points=2,
            category="Design"
        ))

    # No clear CTA
    if not visual.has_clear_cta:
        signals.append(PainSignal(
            signal="No clear call-to-action",
            points=1,
            category="Design"
        ))

    # Low trust signals
    if visual.trust_signals < 2:
        signals.append(PainSignal(
            signal="Missing trust signals",
            points=1,
            category="Design"
        ))

    # =========================================================================
    # PERFORMANCE SIGNALS (FREE - PageSpeed API)
    # Thresholds based on analysis of 57 leads:
    #   Average: 64.8 | Median: 65 | P25: 50 | P75: 74
    # =========================================================================

    # No HTTPS - definite issue
    if not technical.has_https:
        signals.append(PainSignal(
            signal="No HTTPS security",
            points=2,
            category="Performance"
        ))

    # Slow LCP (> 4 seconds is definitely bad)
    if technical.lcp_ms > 4000:
        signals.append(PainSignal(
            signal=f"Slow page load ({technical.lcp_ms/1000:.1f}s)",
            points=1,
            category="Performance"
        ))

    # Performance score thresholds (based on data analysis)
    # < 50 = bottom 25% = definite pain
    # 50-64 = below median = some pain
    # >= 65 = above median = no points
    if technical.performance_score > 0:
        if technical.performance_score < 50:
            signals.append(PainSignal(
                signal=f"Poor website performance ({technical.performance_score}/100)",
                points=2,
                category="Performance"
            ))
        elif technical.performance_score < 65:
            signals.append(PainSignal(
                signal=f"Below-average performance ({technical.performance_score}/100)",
                points=1,
                category="Performance"
            ))

    # =========================================================================
    # REPUTATION SIGNALS (FREE - BBB Scraper + Google Places)
    # =========================================================================

    # BBB complaints are concerning
    if reputation.complaints_total > 3:
        signals.append(PainSignal(
            signal=f"BBB complaints ({reputation.complaints_total})",
            points=-2,  # NEGATIVE - bad sign, less likely to be good client
            category="Reputation"
        ))
    elif reputation.complaints_3yr > 0:
        signals.append(PainSignal(
            signal=f"Recent BBB complaints ({reputation.complaints_3yr})",
            points=-1,
            category="Reputation"
        ))

    # Low Google rating (if they have reviews)
    if lead.google_rating < 4.0 and lead.review_count > 5:
        signals.append(PainSignal(
            signal=f"Below-average rating ({lead.google_rating} stars)",
            points=1,
            category="Reputation"
        ))

    # Few reviews = less established (under 100 reviews)
    if lead.review_count < 100:
        signals.append(PainSignal(
            signal=f"Limited reviews ({lead.review_count})",
            points=1,
            category="Reputation"
        ))

    # =========================================================================
    # ADDRESS SIGNALS (FREE - Address Verifier)
    # =========================================================================

    # Residential address = smaller operation, good prospect
    if address.is_residential:
        signals.append(PainSignal(
            signal="Operating from residential address",
            points=2,  # Good pain signal - needs help professionalizing
            category="Business"
        ))

    # =========================================================================
    # TRACKING/TECH SIGNALS (FREE - HTML Detection from Screenshot Service)
    # These replace what we'd normally get from Clay/BuiltWith
    # =========================================================================

    # DIY Website Builder Detection (MAJOR pain signal)
    is_diy_site = False
    if tracking.cms_detected:
        cms_lower = tracking.cms_detected.lower()
        if cms_lower in DIY_CMS_PLATFORMS:
            is_diy_site = True
            signals.append(PainSignal(
                signal=f"DIY website ({tracking.cms_detected}) - hit growth ceiling",
                points=3,  # High value signal - these leads convert well
                category="Website"
            ))

    # No analytics tracking = flying blind
    if not tracking.has_gtm and not tracking.has_ga4 and not tracking.has_ga_universal:
        signals.append(PainSignal(
            signal="No analytics tracking (GTM/GA4/GA)",
            points=2,
            category="Website"
        ))
    elif not tracking.has_gtm:
        # Has some analytics but no GTM
        signals.append(PainSignal(
            signal="No Google Tag Manager",
            points=1,
            category="Website"
        ))

    # No booking system = missing leads
    if not tracking.has_booking:
        signals.append(PainSignal(
            signal="No online booking system detected",
            points=2,
            category="Website"
        ))

    # No chat widget = missing engagement
    if not tracking.has_chat_widget:
        signals.append(PainSignal(
            signal="No chat widget for visitor engagement",
            points=1,
            category="Website"
        ))

    # No CRM detected = no lead management
    if not tracking.has_crm:
        signals.append(PainSignal(
            signal="No CRM detected",
            points=1,
            category="Website"
        ))

    # No contact/lead capture form = leaky bucket
    if not tracking.has_contact_form and not tracking.has_lead_capture_form:
        signals.append(PainSignal(
            signal="No contact or lead capture form detected",
            points=2,
            category="Website"
        ))

    # =========================================================================
    # CALCULATE TOTALS AND ASSIGN CATEGORY
    # =========================================================================

    total_score = sum(s.points for s in signals)

    # Determine pre-qualification status
    if total_score <= PREQUALIFY_REJECT_THRESHOLD:
        status = QualificationStatus.REJECTED
        send_to_clay = False
    elif total_score <= PREQUALIFY_MARGINAL_THRESHOLD:
        status = QualificationStatus.MARGINAL
        send_to_clay = False  # Manual review first
    else:
        status = QualificationStatus.QUALIFIED
        send_to_clay = True  # Send to Clay for enrichment

    # Get top signals
    sorted_signals = sorted(signals, key=lambda s: s.points, reverse=True)
    top_signals = [s.signal for s in sorted_signals[:5] if s.points > 0]

    # =========================================================================
    # LEAD CATEGORY ASSIGNMENT (Based on FREE data signals)
    # =========================================================================
    category_assignment = _assign_lead_category(
        lead=lead,
        visual=visual,
        technical=technical,
        tracking=tracking,
        address=address,
        signals=signals,
        is_diy_site=is_diy_site
    )

    return PreQualificationScore(
        score=total_score,
        signals=signals,
        status=status,
        top_signals=top_signals,
        send_to_clay=send_to_clay,
        category_assignment=category_assignment
    )


def _assign_lead_category(
    lead: Lead,
    visual: VisualAnalysis,
    technical: TechnicalScores,
    tracking: TrackingAnalysis,
    address: AddressVerification,
    signals: List[PainSignal],
    is_diy_site: bool
) -> CategoryAssignment:
    """
    Assign lead to one of 5 categories based on FREE data signals.

    Categories:
    1. THE_INVISIBLE - No/minimal online presence
    2. THE_DIY_CEILING - Built own site with Wix/Squarespace, hit growth limit
    3. THE_LEAKY_BUCKET - Has traffic/presence but poor conversion systems
    4. THE_OVERWHELMED - Growing fast (high reviews), needs systems to scale
    5. READY_TO_DOMINATE - Has basics in place, wants to level up

    This is used for personalized email copy and landing page routing.
    """

    # Count signal categories for decision logic
    website_signals = [s for s in signals if s.category == "Website"]
    design_signals = [s for s in signals if s.category == "Design"]
    has_website = bool(lead.website_url and lead.website_url.strip())

    # =========================================================================
    # Category 1: THE INVISIBLE
    # No website or extremely poor online presence
    # =========================================================================
    if not has_website:
        return CategoryAssignment(
            category=LeadCategory.THE_INVISIBLE,
            reason="No website detected - operating completely offline",
            confidence="high"
        )

    # Very low visual score + no analytics = essentially invisible online
    if visual.visual_score < 30 and not tracking.has_ga4 and not tracking.has_gtm:
        return CategoryAssignment(
            category=LeadCategory.THE_INVISIBLE,
            reason=f"Minimal online presence (visual score: {visual.visual_score}, no tracking)",
            confidence="high"
        )

    # =========================================================================
    # Category 2: THE DIY CEILING
    # Built their own site with DIY tools, but hit limitations
    # =========================================================================
    if is_diy_site:
        # Confirmed DIY platform
        cms = tracking.cms_detected or "DIY Builder"
        return CategoryAssignment(
            category=LeadCategory.THE_DIY_CEILING,
            reason=f"Self-built {cms} website - hit growth ceiling",
            confidence="high"
        )

    # Not detected as DIY but has hallmarks of self-built site
    # (low design quality + no professional systems)
    if (visual.visual_score < 50 and
        not tracking.has_crm and
        not tracking.has_booking and
        not tracking.has_gtm):
        return CategoryAssignment(
            category=LeadCategory.THE_DIY_CEILING,
            reason="DIY-quality website lacking professional marketing systems",
            confidence="medium"
        )

    # =========================================================================
    # Category 3: THE LEAKY BUCKET
    # Has presence but poor conversion - missing lead capture/booking
    # =========================================================================

    # Has some analytics (knows about traffic) but no capture mechanisms
    has_analytics = tracking.has_gtm or tracking.has_ga4 or tracking.has_ga_universal
    has_capture = tracking.has_booking or tracking.has_contact_form or tracking.has_lead_capture_form or tracking.has_chat_widget

    if has_analytics and not has_capture:
        return CategoryAssignment(
            category=LeadCategory.THE_LEAKY_BUCKET,
            reason="Has analytics but no lead capture systems - losing potential customers",
            confidence="high"
        )

    # Decent design but no conversion systems
    if visual.visual_score >= 50 and not tracking.has_booking and not tracking.has_crm:
        return CategoryAssignment(
            category=LeadCategory.THE_LEAKY_BUCKET,
            reason="Professional-looking site but no booking or CRM systems",
            confidence="medium"
        )

    # =========================================================================
    # Category 4: THE OVERWHELMED
    # High review count (busy) but lacking systems to manage growth
    # These are often the BEST prospects - they have demand, need help scaling
    # =========================================================================

    # High review count indicates established, busy business
    if lead.review_count >= 50:
        # Busy but lacking systems
        missing_systems = []
        if not tracking.has_crm:
            missing_systems.append("CRM")
        if not tracking.has_booking:
            missing_systems.append("booking")
        if not tracking.has_email_marketing:
            missing_systems.append("email marketing")

        if len(missing_systems) >= 2:
            return CategoryAssignment(
                category=LeadCategory.THE_OVERWHELMED,
                reason=f"{lead.review_count} reviews but missing {', '.join(missing_systems)} systems",
                confidence="high"
            )

    # Growing business (moderate reviews) from residential address
    # = growing but not yet professionalized
    if lead.review_count >= 20 and address.is_residential:
        return CategoryAssignment(
            category=LeadCategory.THE_OVERWHELMED,
            reason=f"Growing business ({lead.review_count} reviews) operating from home - needs to scale",
            confidence="medium"
        )

    # =========================================================================
    # Category 5: READY TO DOMINATE
    # Has basics in place, positioned for growth
    # These get additional enrichment (review analysis) to find pitch angles
    # =========================================================================

    # Has analytics AND some capture mechanism AND decent design
    if (has_analytics and
        has_capture and
        visual.visual_score >= 60):
        return CategoryAssignment(
            category=LeadCategory.READY_TO_DOMINATE,
            reason="Solid foundation in place - ready to scale with advanced marketing",
            confidence="high"
        )

    # Good rating with decent presence
    if (lead.google_rating >= 4.5 and
        lead.review_count >= 30 and
        visual.visual_score >= 50):
        return CategoryAssignment(
            category=LeadCategory.READY_TO_DOMINATE,
            reason=f"Strong reputation ({lead.google_rating} stars, {lead.review_count} reviews) - positioned to dominate",
            confidence="medium"
        )

    # =========================================================================
    # DEFAULT: Uncategorized
    # Doesn't fit clear category - needs manual review
    # =========================================================================
    return CategoryAssignment(
        category=LeadCategory.UNCATEGORIZED,
        reason="Mixed signals - requires manual category assignment",
        confidence="low"
    )


def calculate_pain_score_with_ai_tech(
    lead: Lead,
    tech_analysis: Dict[str, Any],  # From tech_stack_scorer.analyze_tech_stack()
    visual: VisualAnalysis,
    technical: TechnicalScores,
    directory: DirectoryPresence,
    license_info: LicenseInfo,
    reputation: ReputationData
) -> PainScore:
    """
    Calculate pain score using AI-powered tech stack analysis.

    This is the NEW scoring function that uses Claude Haiku's analysis
    instead of basic boolean tech fields.

    Args:
        lead: Basic lead info
        tech_analysis: Dict from tech_stack_scorer.analyze_tech_stack() containing:
            - has_gtm, has_ga4, has_crm, etc. (booleans)
            - website_type (DIY Builder, Professional, Outdated WordPress, etc.)
            - cms_platform (Wix, Squarespace, WordPress, etc.)
            - tech_score (0-10)
            - pain_points (list of strings)
            - strengths (list of strings)
            - recommended_pitch (string)
        visual: Visual analysis from screenshot service
        technical: PageSpeed scores
        directory: Yext directory presence
        license_info: TDLR license data
        reputation: BBB reputation data

    Returns:
        PainScore with unified signals from all sources
    """
    signals: List[PainSignal] = []

    # =========================================================================
    # TECH STACK SIGNALS (AI-POWERED) - Category: Website
    # =========================================================================

    # DIY Website Builder = MAJOR pain point
    website_type = tech_analysis.get("website_type", "Unknown")
    if "DIY" in website_type:
        cms = tech_analysis.get("cms_platform", "Unknown")
        signals.append(PainSignal(
            signal=f"DIY website builder ({cms}) - not professional",
            points=4,  # Major red flag
            category="Website"
        ))

    # Outdated WordPress
    elif "Outdated" in website_type:
        signals.append(PainSignal(
            signal="Outdated WordPress setup needs modernization",
            points=2,
            category="Website"
        ))

    # No website
    if not lead.website_url or lead.website_url.strip() == "":
        signals.append(PainSignal(
            signal="No website detected",
            points=3,
            category="Website"
        ))

    # No GTM
    if not tech_analysis.get("has_gtm", False):
        signals.append(PainSignal(
            signal="No Google Tag Manager",
            points=2,
            category="Website"
        ))

    # No GA4
    if not tech_analysis.get("has_ga4", False):
        signals.append(PainSignal(
            signal="No Google Analytics 4",
            points=2,
            category="Website"
        ))

    # No CRM
    if not tech_analysis.get("has_crm", False):
        signals.append(PainSignal(
            signal="No CRM detected",
            points=2,
            category="Website"
        ))

    # No booking system
    if not tech_analysis.get("has_booking_system", False):
        signals.append(PainSignal(
            signal="No online booking system",
            points=2,
            category="Website"
        ))

    # No email marketing
    if not tech_analysis.get("has_email_marketing", False):
        signals.append(PainSignal(
            signal="No email marketing platform",
            points=1,
            category="Website"
        ))

    # No lead capture
    if not tech_analysis.get("has_lead_capture", False):
        signals.append(PainSignal(
            signal="No lead capture forms",
            points=1,
            category="Website"
        ))

    # Low tech score (AI's overall assessment)
    tech_score = tech_analysis.get("tech_score", 5)
    if tech_score <= 3:
        signals.append(PainSignal(
            signal=f"Critical technology gaps (AI score: {tech_score}/10)",
            points=2,
            category="Website"
        ))
    elif tech_score <= 5:
        signals.append(PainSignal(
            signal=f"Below-average technology stack (AI score: {tech_score}/10)",
            points=1,
            category="Website"
        ))

    # =========================================================================
    # VISUAL/DESIGN SIGNALS (Category: Design)
    # =========================================================================

    # Poor visual score
    if visual.visual_score < 40:
        signals.append(PainSignal(
            signal=f"Outdated website design (score: {visual.visual_score}/100)",
            points=2,
            category="Design"
        ))
    elif visual.visual_score < 60:
        signals.append(PainSignal(
            signal=f"Average website design needs improvement ({visual.visual_score}/100)",
            points=1,
            category="Design"
        ))

    # Old design era
    if visual.design_era and visual.design_era.lower() in ["2000s", "2010s", "early 2010s"]:
        signals.append(PainSignal(
            signal=f"Website design appears from {visual.design_era}",
            points=1,
            category="Design"
        ))

    # Not mobile responsive
    if not visual.mobile_responsive:
        signals.append(PainSignal(
            signal="Website not mobile-friendly",
            points=2,
            category="Design"
        ))

    # No hero image
    if not visual.has_hero_image:
        signals.append(PainSignal(
            signal="No compelling hero image",
            points=1,
            category="Design"
        ))

    # No clear CTA
    if not visual.has_clear_cta:
        signals.append(PainSignal(
            signal="No clear call-to-action",
            points=1,
            category="Design"
        ))

    # Low trust signals
    if visual.trust_signals < 2:
        signals.append(PainSignal(
            signal="Missing trust signals (badges, certifications, reviews)",
            points=1,
            category="Design"
        ))

    # =========================================================================
    # PERFORMANCE SIGNALS (Category: Performance)
    # =========================================================================

    # Poor overall performance
    if technical.performance_score < 50:
        signals.append(PainSignal(
            signal=f"Poor website performance ({technical.performance_score}/100)",
            points=2,
            category="Performance"
        ))

    # Poor mobile score
    if technical.mobile_score < 50:
        signals.append(PainSignal(
            signal=f"Poor mobile performance ({technical.mobile_score}/100)",
            points=1,
            category="Performance"
        ))

    # Poor SEO score
    if technical.seo_score < 50:
        signals.append(PainSignal(
            signal=f"SEO issues detected ({technical.seo_score}/100)",
            points=1,
            category="Performance"
        ))

    # No HTTPS
    if not technical.has_https:
        signals.append(PainSignal(
            signal="Website lacks HTTPS security",
            points=2,
            category="Performance"
        ))

    # Slow LCP (Largest Contentful Paint > 4s)
    if technical.lcp_ms > 4000:
        signals.append(PainSignal(
            signal=f"Slow page load time ({technical.lcp_ms/1000:.1f}s LCP)",
            points=1,
            category="Performance"
        ))

    # High CLS (Cumulative Layout Shift > 0.25)
    if technical.cls > 0.25:
        signals.append(PainSignal(
            signal=f"Poor visual stability (CLS: {technical.cls:.2f})",
            points=1,
            category="Performance"
        ))

    # =========================================================================
    # DIRECTORY/LISTINGS SIGNALS (Category: Listings)
    # =========================================================================

    # Low listings score
    if directory.listings_score < 50:
        signals.append(PainSignal(
            signal=f"Poor directory presence ({directory.listings_score}/100)",
            points=2,
            category="Listings"
        ))

    # Few listings found
    if directory.listings_found < 10:
        signals.append(PainSignal(
            signal=f"Limited online directory presence ({directory.listings_found} listings)",
            points=1,
            category="Listings"
        ))

    # NAP inconsistency
    if directory.nap_consistency < 0.7:
        signals.append(PainSignal(
            signal=f"Inconsistent business info across directories ({directory.nap_consistency*100:.0f}% consistency)",
            points=2,
            category="Listings"
        ))

    # =========================================================================
    # REPUTATION SIGNALS (Category: Reputation)
    # =========================================================================

    # Low Google rating
    if lead.google_rating < 4.0 and lead.review_count > 5:
        signals.append(PainSignal(
            signal=f"Below-average Google rating ({lead.google_rating} stars)",
            points=1,
            category="Reputation"
        ))

    # Few Google reviews
    if lead.review_count < 20:
        signals.append(PainSignal(
            signal=f"Limited Google reviews ({lead.review_count} reviews)",
            points=1,
            category="Reputation"
        ))

    # Not BBB accredited
    if not reputation.bbb_accredited:
        signals.append(PainSignal(
            signal="Not BBB accredited",
            points=1,
            category="Reputation"
        ))

    # BBB complaints
    if reputation.complaints_3yr > 0:
        signals.append(PainSignal(
            signal=f"BBB complaints in last 3 years ({reputation.complaints_3yr})",
            points=1,
            category="Reputation"
        ))

    # Reputation gap
    if reputation.reputation_gap > 1.5:
        signals.append(PainSignal(
            signal="Reputation inconsistency between platforms",
            points=1,
            category="Reputation"
        ))

    # =========================================================================
    # LICENSE/COMPLIANCE SIGNALS (Category: Compliance)
    # =========================================================================

    # License issues
    if license_info.license_status.lower() in ["expired", "revoked", "suspended"]:
        signals.append(PainSignal(
            signal=f"License status: {license_info.license_status}",
            points=2,
            category="Compliance"
        ))
    elif license_info.license_status.lower() in ["unknown", "not found", ""]:
        signals.append(PainSignal(
            signal="License status could not be verified",
            points=1,
            category="Compliance"
        ))

    # =========================================================================
    # SOCIAL MEDIA SIGNALS (Category: Social)
    # =========================================================================

    social_count = sum([
        1 if visual.social_facebook else 0,
        1 if visual.social_instagram else 0,
        1 if visual.social_linkedin else 0
    ])

    if social_count == 0:
        signals.append(PainSignal(
            signal="No social media presence detected",
            points=1,
            category="Social"
        ))
    elif social_count == 1:
        signals.append(PainSignal(
            signal="Limited social media presence",
            points=1,
            category="Social"
        ))

    # =========================================================================
    # CALCULATE TOTALS
    # =========================================================================

    total_score = sum(s.points for s in signals)

    # Determine qualification status
    if total_score <= PAIN_SCORE_REJECT_THRESHOLD:
        status = QualificationStatus.REJECTED
        proceed = False
    elif total_score <= PAIN_SCORE_MARGINAL_THRESHOLD:
        status = QualificationStatus.MARGINAL
        proceed = False  # Needs manual review
    else:
        status = QualificationStatus.QUALIFIED
        proceed = True

    # Get top pain points (highest point signals)
    sorted_signals = sorted(signals, key=lambda s: s.points, reverse=True)
    top_pain_points = [s.signal for s in sorted_signals[:5]]

    # Calculate ICP score (inverse of pain - how well they match ideal customer)
    # High pain = good prospect
    icp_score = min(100, total_score * 10)

    return PainScore(
        score=total_score,
        signals=signals,
        status=status,
        top_pain_points=top_pain_points,
        icp_score=icp_score,
        proceed=proceed
    )


def calculate_pain_score(
    lead: Lead,
    tech: TechEnrichment,
    visual: VisualAnalysis,
    technical: TechnicalScores,
    directory: DirectoryPresence,
    license_info: LicenseInfo,
    reputation: ReputationData
) -> PainScore:
    """
    Calculate pain score based on all enrichment data.
    Returns PainScore with signals, status, and qualification decision.
    """
    signals: List[PainSignal] = []

    # =========================================================================
    # WEBSITE & TECH SIGNALS (Category: Website)
    # =========================================================================

    # No website at all - major pain point
    if not lead.website_url or lead.website_url.strip() == "":
        signals.append(PainSignal(
            signal="No website detected",
            points=3,
            category="Website"
        ))
    else:
        # Has website - check quality signals

        # No Google Tag Manager
        if not tech.has_gtm:
            signals.append(PainSignal(
                signal="No Google Tag Manager",
                points=1,
                category="Website"
            ))

        # No Google Analytics (neither GA4 nor Universal)
        if not tech.has_ga4 and not tech.has_ga_universal:
            signals.append(PainSignal(
                signal="No Google Analytics tracking",
                points=1,
                category="Website"
            ))

        # Old/basic CMS or no CMS
        if not tech.cms_platform or tech.cms_platform.lower() in ["none", "unknown", ""]:
            signals.append(PainSignal(
                signal="No modern CMS detected",
                points=1,
                category="Website"
            ))

        # No booking system
        if not tech.booking_system or tech.booking_system.strip() == "":
            signals.append(PainSignal(
                signal="No online booking system",
                points=2,
                category="Website"
            ))

        # No chat widget
        if not tech.chat_widget or tech.chat_widget.strip() == "":
            signals.append(PainSignal(
                signal="No chat widget for lead capture",
                points=1,
                category="Website"
            ))

        # Low tech score overall
        if tech.tech_score < 30:
            signals.append(PainSignal(
                signal=f"Low technology adoption score ({tech.tech_score}/100)",
                points=1,
                category="Website"
            ))

    # =========================================================================
    # VISUAL/DESIGN SIGNALS (Category: Design)
    # =========================================================================

    # Poor visual score
    if visual.visual_score < 40:
        signals.append(PainSignal(
            signal=f"Outdated website design (score: {visual.visual_score}/100)",
            points=2,
            category="Design"
        ))
    elif visual.visual_score < 60:
        signals.append(PainSignal(
            signal=f"Average website design needs improvement ({visual.visual_score}/100)",
            points=1,
            category="Design"
        ))

    # Old design era
    if visual.design_era and visual.design_era.lower() in ["2000s", "2010s", "early 2010s"]:
        signals.append(PainSignal(
            signal=f"Website design appears from {visual.design_era}",
            points=1,
            category="Design"
        ))

    # Not mobile responsive
    if not visual.mobile_responsive:
        signals.append(PainSignal(
            signal="Website not mobile-friendly",
            points=2,
            category="Design"
        ))

    # No hero image
    if not visual.has_hero_image:
        signals.append(PainSignal(
            signal="No compelling hero image",
            points=1,
            category="Design"
        ))

    # No clear CTA
    if not visual.has_clear_cta:
        signals.append(PainSignal(
            signal="No clear call-to-action",
            points=1,
            category="Design"
        ))

    # Low trust signals
    if visual.trust_signals < 2:
        signals.append(PainSignal(
            signal="Missing trust signals (badges, certifications, reviews)",
            points=1,
            category="Design"
        ))

    # =========================================================================
    # PERFORMANCE SIGNALS (Category: Performance)
    # =========================================================================

    # Poor overall performance
    if technical.performance_score < 50:
        signals.append(PainSignal(
            signal=f"Poor website performance ({technical.performance_score}/100)",
            points=2,
            category="Performance"
        ))

    # Poor mobile score
    if technical.mobile_score < 50:
        signals.append(PainSignal(
            signal=f"Poor mobile performance ({technical.mobile_score}/100)",
            points=1,
            category="Performance"
        ))

    # Poor SEO score
    if technical.seo_score < 50:
        signals.append(PainSignal(
            signal=f"SEO issues detected ({technical.seo_score}/100)",
            points=1,
            category="Performance"
        ))

    # No HTTPS
    if not technical.has_https:
        signals.append(PainSignal(
            signal="Website lacks HTTPS security",
            points=2,
            category="Performance"
        ))

    # Slow LCP (Largest Contentful Paint > 4s)
    if technical.lcp_ms > 4000:
        signals.append(PainSignal(
            signal=f"Slow page load time ({technical.lcp_ms/1000:.1f}s LCP)",
            points=1,
            category="Performance"
        ))

    # High CLS (Cumulative Layout Shift > 0.25)
    if technical.cls > 0.25:
        signals.append(PainSignal(
            signal=f"Poor visual stability (CLS: {technical.cls:.2f})",
            points=1,
            category="Performance"
        ))

    # =========================================================================
    # DIRECTORY/LISTINGS SIGNALS (Category: Listings)
    # =========================================================================

    # Low listings score
    if directory.listings_score < 50:
        signals.append(PainSignal(
            signal=f"Poor directory presence ({directory.listings_score}/100)",
            points=2,
            category="Listings"
        ))

    # Few listings found
    if directory.listings_found < 10:
        signals.append(PainSignal(
            signal=f"Limited online directory presence ({directory.listings_found} listings)",
            points=1,
            category="Listings"
        ))

    # NAP inconsistency
    if directory.nap_consistency < 0.7:
        signals.append(PainSignal(
            signal=f"Inconsistent business info across directories ({directory.nap_consistency*100:.0f}% consistency)",
            points=2,
            category="Listings"
        ))

    # =========================================================================
    # REPUTATION SIGNALS (Category: Reputation)
    # =========================================================================

    # Low Google rating
    if lead.google_rating < 4.0 and lead.review_count > 5:
        signals.append(PainSignal(
            signal=f"Below-average Google rating ({lead.google_rating} stars)",
            points=1,
            category="Reputation"
        ))

    # Few Google reviews
    if lead.review_count < 20:
        signals.append(PainSignal(
            signal=f"Limited Google reviews ({lead.review_count} reviews)",
            points=1,
            category="Reputation"
        ))

    # Not BBB accredited
    if not reputation.bbb_accredited:
        signals.append(PainSignal(
            signal="Not BBB accredited",
            points=1,
            category="Reputation"
        ))

    # BBB complaints
    if reputation.complaints_3yr > 0:
        signals.append(PainSignal(
            signal=f"BBB complaints in last 3 years ({reputation.complaints_3yr})",
            points=1,
            category="Reputation"
        ))

    # Reputation gap (BBB rating vs Google rating mismatch)
    if reputation.reputation_gap > 1.5:
        signals.append(PainSignal(
            signal="Reputation inconsistency between platforms",
            points=1,
            category="Reputation"
        ))

    # =========================================================================
    # LICENSE/COMPLIANCE SIGNALS (Category: Compliance)
    # =========================================================================

    # License issues
    if license_info.license_status.lower() in ["expired", "revoked", "suspended"]:
        signals.append(PainSignal(
            signal=f"License status: {license_info.license_status}",
            points=2,
            category="Compliance"
        ))
    elif license_info.license_status.lower() in ["unknown", "not found", ""]:
        signals.append(PainSignal(
            signal="License status could not be verified",
            points=1,
            category="Compliance"
        ))

    # =========================================================================
    # SOCIAL MEDIA SIGNALS (Category: Social)
    # =========================================================================

    social_count = sum([
        1 if visual.social_facebook else 0,
        1 if visual.social_instagram else 0,
        1 if visual.social_linkedin else 0
    ])

    if social_count == 0:
        signals.append(PainSignal(
            signal="No social media presence detected",
            points=1,
            category="Social"
        ))
    elif social_count == 1:
        signals.append(PainSignal(
            signal="Limited social media presence",
            points=1,
            category="Social"
        ))

    # =========================================================================
    # CALCULATE TOTALS
    # =========================================================================

    total_score = sum(s.points for s in signals)

    # Determine qualification status
    if total_score <= PAIN_SCORE_REJECT_THRESHOLD:
        status = QualificationStatus.REJECTED
        proceed = False
    elif total_score <= PAIN_SCORE_MARGINAL_THRESHOLD:
        status = QualificationStatus.MARGINAL
        proceed = False  # Needs manual review
    else:
        status = QualificationStatus.QUALIFIED
        proceed = True

    # Get top pain points (highest point signals)
    sorted_signals = sorted(signals, key=lambda s: s.points, reverse=True)
    top_pain_points = [s.signal for s in sorted_signals[:5]]

    # Calculate ICP score (inverse of pain - how well they match ideal customer)
    # High pain = good prospect, so ICP score reflects that
    icp_score = min(100, total_score * 10)

    return PainScore(
        score=total_score,
        signals=signals,
        status=status,
        top_pain_points=top_pain_points,
        icp_score=icp_score,
        proceed=proceed
    )


def get_pain_summary(pain_score: PainScore) -> str:
    """Generate a human-readable summary of pain points for email personalization."""
    if not pain_score.signals:
        return "No significant pain points identified."

    # Group by category
    categories = {}
    for signal in pain_score.signals:
        if signal.category not in categories:
            categories[signal.category] = []
        categories[signal.category].append(signal.signal)

    summary_parts = []
    for category, signals in categories.items():
        if signals:
            summary_parts.append(f"{category}: {', '.join(signals[:2])}")

    return "; ".join(summary_parts[:3])


def format_pain_signals_for_email(pain_score: PainScore) -> List[str]:
    """Format pain signals as personalization hooks for email generation."""
    hooks = []

    # Prioritize high-impact, actionable signals
    priority_signals = [
        "No website detected",
        "No online booking system",
        "Website not mobile-friendly",
        "Poor website performance",
        "Poor directory presence",
        "Outdated website design",
        "No Google Analytics tracking",
        "Website lacks HTTPS security"
    ]

    for signal in pain_score.signals:
        if any(priority in signal.signal for priority in priority_signals):
            hooks.append(signal.signal)

    # Add top pain points if we don't have enough hooks
    if len(hooks) < 3:
        for point in pain_score.top_pain_points:
            if point not in hooks:
                hooks.append(point)
            if len(hooks) >= 3:
                break

    return hooks[:5]


# =============================================================================
# LEAD CATEGORY UTILITIES
# =============================================================================

CATEGORY_DESCRIPTIONS = {
    LeadCategory.THE_INVISIBLE: {
        "name": "The Invisible",
        "tagline": "Hidden Gem Ready to Shine",
        "pain": "Operating completely offline or with minimal online presence",
        "pitch_angle": "You're missing out on customers who are searching online right now",
        "email_tone": "opportunity_discovery"
    },
    LeadCategory.THE_DIY_CEILING: {
        "name": "The DIY Ceiling",
        "tagline": "Outgrowing Your Website",
        "pain": "Self-built website has hit its limits - looks amateur, can't scale",
        "pitch_angle": "You've proven the business works - now let's get you a professional online presence",
        "email_tone": "upgrade_path"
    },
    LeadCategory.THE_LEAKY_BUCKET: {
        "name": "The Leaky Bucket",
        "tagline": "Stop Losing Leads",
        "pain": "Traffic is coming but leads are slipping through the cracks",
        "pitch_angle": "You're already getting visitors - let's make sure they become customers",
        "email_tone": "conversion_focus"
    },
    LeadCategory.THE_OVERWHELMED: {
        "name": "The Overwhelmed",
        "tagline": "Ready to Scale Smart",
        "pain": "Business is growing fast but systems can't keep up",
        "pitch_angle": "You've got the jobs - now let's build systems so growth doesn't break you",
        "email_tone": "systems_scale"
    },
    LeadCategory.READY_TO_DOMINATE: {
        "name": "Ready to Dominate",
        "tagline": "Level Up Your Market Position",
        "pain": "Solid foundation but ready for aggressive growth",
        "pitch_angle": "You've got the basics - let's turn you into the go-to electrician in your area",
        "email_tone": "market_domination"
    },
    LeadCategory.UNCATEGORIZED: {
        "name": "Uncategorized",
        "tagline": "Custom Approach Needed",
        "pain": "Mixed signals - needs personalized analysis",
        "pitch_angle": "Let's have a conversation about your specific situation",
        "email_tone": "discovery_call"
    }
}


def get_category_info(category: LeadCategory) -> Dict[str, str]:
    """Get description info for a lead category."""
    return CATEGORY_DESCRIPTIONS.get(category, CATEGORY_DESCRIPTIONS[LeadCategory.UNCATEGORIZED])
