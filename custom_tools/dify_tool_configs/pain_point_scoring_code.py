"""
Pain Point Scoring Code Node for Dify Workflow
Phase 3: Qualification Gate

This code is designed to be used in a Dify Code Node.
It implements all 15 pain point signals from the specification.

Copy this code directly into a Dify Code Node.
"""

def main(
    # Phase 1: Tech Enrichment signals
    has_gtm: str,
    has_ga4: str,
    has_ga_universal: str,
    crm_detected: str,
    booking_system: str,
    cms_platform: str,
    # Phase 2A: Visual Analysis signals
    visual_score: str,
    design_era: str,
    social_facebook: str,
    social_instagram: str,
    social_linkedin: str,
    mobile_responsive: str,
    # Phase 2B: Technical Scores signals
    performance_score: str,
    mobile_score: str,
    seo_score: str,
    # Phase 2C: Directory Presence signals
    listings_score: str,
    nap_consistency: str,
    # Phase 2D: License Verification signals
    license_status: str,
    # Phase 2E: Reputation Analysis signals
    bbb_rating: str,
    complaints_3yr: str
) -> dict:
    """
    Calculate comprehensive pain point score from all Phase 1-2 data.

    Scoring Logic:
    - pain_score <= 3  -> REJECTED (stop processing)
    - pain_score 4-5   -> MARGINAL (continue with flag)
    - pain_score >= 6  -> QUALIFIED (full processing)

    Returns dict with:
    - pain_score: Total points (0-25+)
    - pain_signals: List of triggered signals
    - qualification_status: REJECTED | MARGINAL | QUALIFIED
    - top_pain_points: Top 3 pain points for email personalization
    - icp_score: 0-100 overall fit score
    """

    pain_score = 0
    pain_signals = []

    # Helper functions
    def to_bool(val: str) -> bool:
        return str(val).lower() in ('true', '1', 'yes')

    def to_int(val: str, default: int = 0) -> int:
        try:
            return int(float(val)) if val else default
        except:
            return default

    def to_float(val: str, default: float = 0.0) -> float:
        try:
            return float(val) if val else default
        except:
            return default

    # ==================== PHASE 1: TECH ENRICHMENT ====================

    # Signal: No GTM (+2)
    if not to_bool(has_gtm):
        pain_score += 2
        pain_signals.append({
            "signal": "No GTM",
            "points": 2,
            "category": "tech",
            "description": "No Google Tag Manager detected"
        })

    # Signal: No GA4 (+1)
    if not to_bool(has_ga4):
        pain_score += 1
        pain_signals.append({
            "signal": "No GA4",
            "points": 1,
            "category": "tech",
            "description": "No Google Analytics 4 detected"
        })

    # Signal: Legacy GA Only (+2)
    if to_bool(has_ga_universal) and not to_bool(has_ga4):
        pain_score += 2
        pain_signals.append({
            "signal": "Legacy GA Only",
            "points": 2,
            "category": "tech",
            "description": "Using outdated Universal Analytics"
        })

    # Signal: No CRM (+2)
    if not crm_detected or crm_detected.lower() in ('null', 'none', ''):
        pain_score += 2
        pain_signals.append({
            "signal": "No CRM",
            "points": 2,
            "category": "tech",
            "description": "No CRM platform detected"
        })

    # Signal: No Booking (+2)
    if not booking_system or booking_system.lower() in ('null', 'none', ''):
        pain_score += 2
        pain_signals.append({
            "signal": "No Booking",
            "points": 2,
            "category": "tech",
            "description": "No online booking system"
        })

    # Signal: Dated CMS (+1)
    dated_cms = ['wix', 'godaddy', 'weebly', 'squarespace']
    if cms_platform and cms_platform.lower() in dated_cms:
        pain_score += 1
        pain_signals.append({
            "signal": "Dated CMS",
            "points": 1,
            "category": "tech",
            "description": f"Using {cms_platform} (limited customization)"
        })

    # ==================== PHASE 2A: VISUAL ANALYSIS ====================

    visual = to_int(visual_score, 50)

    # Signal: Poor Design (+2)
    if visual < 40:
        pain_score += 2
        pain_signals.append({
            "signal": "Poor Design",
            "points": 2,
            "category": "visual",
            "description": f"Visual score {visual}/100 indicates poor design"
        })

    # Signal: Dated Design (+1)
    if design_era and design_era.lower() in ('dated', 'legacy'):
        pain_score += 1
        pain_signals.append({
            "signal": "Dated Design",
            "points": 1,
            "category": "visual",
            "description": f"Website design appears {design_era.lower()}"
        })

    # Signal: No Social (+1)
    has_any_social = any([
        social_facebook and social_facebook.lower() not in ('null', 'none', ''),
        social_instagram and social_instagram.lower() not in ('null', 'none', ''),
        social_linkedin and social_linkedin.lower() not in ('null', 'none', '')
    ])
    if not has_any_social:
        pain_score += 1
        pain_signals.append({
            "signal": "No Social",
            "points": 1,
            "category": "visual",
            "description": "No social media links found"
        })

    # Signal: No Mobile (+2)
    if not to_bool(mobile_responsive):
        pain_score += 2
        pain_signals.append({
            "signal": "No Mobile",
            "points": 2,
            "category": "visual",
            "description": "Website not mobile responsive"
        })

    # ==================== PHASE 2B: TECHNICAL SCORES ====================

    perf = to_int(performance_score, 50)
    mobile = to_int(mobile_score, 50)
    seo = to_int(seo_score, 50)

    # Signal: Slow Site (+2)
    if perf < 50:
        pain_score += 2
        pain_signals.append({
            "signal": "Slow Site",
            "points": 2,
            "category": "technical",
            "description": f"Performance score {perf}/100 indicates slow loading"
        })

    # Signal: Poor Mobile (+2)
    if mobile < 50:
        pain_score += 2
        pain_signals.append({
            "signal": "Poor Mobile",
            "points": 2,
            "category": "technical",
            "description": f"Mobile score {mobile}/100 indicates mobile issues"
        })

    # Signal: Bad SEO (+1)
    if seo < 50:
        pain_score += 1
        pain_signals.append({
            "signal": "Bad SEO",
            "points": 1,
            "category": "technical",
            "description": f"SEO score {seo}/100 indicates optimization needed"
        })

    # ==================== PHASE 2C: DIRECTORY PRESENCE ====================

    listings = to_int(listings_score, 50)
    nap = to_float(nap_consistency, 1.0)

    # Signal: Poor Presence (+2)
    if listings < 40:
        pain_score += 2
        pain_signals.append({
            "signal": "Poor Presence",
            "points": 2,
            "category": "directory",
            "description": f"Directory listings score {listings}/100"
        })

    # Signal: NAP Issues (+1)
    if nap < 0.8:
        pain_score += 1
        pain_signals.append({
            "signal": "NAP Issues",
            "points": 1,
            "category": "directory",
            "description": f"Name/Address/Phone consistency at {int(nap*100)}%"
        })

    # ==================== PHASE 2D: LICENSE VERIFICATION ====================

    # Signal: License Issues (+2)
    if license_status and license_status.lower() not in ('active', ''):
        pain_score += 2
        pain_signals.append({
            "signal": "License Issues",
            "points": 2,
            "category": "license",
            "description": f"License status: {license_status}"
        })

    # ==================== PHASE 2E: REPUTATION ANALYSIS ====================

    complaints = to_int(complaints_3yr, 0)

    # Signal: Poor BBB (+1)
    poor_bbb_ratings = ['c', 'c+', 'c-', 'd', 'd+', 'd-', 'f']
    if bbb_rating and bbb_rating.lower() in poor_bbb_ratings:
        pain_score += 1
        pain_signals.append({
            "signal": "Poor BBB",
            "points": 1,
            "category": "reputation",
            "description": f"BBB rating: {bbb_rating}"
        })

    # Signal: Many Complaints (+2)
    if complaints > 5:
        pain_score += 2
        pain_signals.append({
            "signal": "Many Complaints",
            "points": 2,
            "category": "reputation",
            "description": f"{complaints} BBB complaints in last 3 years"
        })

    # ==================== QUALIFICATION ROUTING ====================

    if pain_score <= 3:
        qualification_status = "REJECTED"
    elif pain_score <= 5:
        qualification_status = "MARGINAL"
    else:
        qualification_status = "QUALIFIED"

    # Calculate ICP score (inverse of pain score, normalized to 0-100)
    # Max pain score ~25, so: icp_score = 100 - (pain_score * 4)
    icp_score = max(0, min(100, 100 - (pain_score * 4)))

    # Get top 3 pain points for email personalization (sorted by points)
    sorted_signals = sorted(pain_signals, key=lambda x: x['points'], reverse=True)
    top_pain_points = [s['description'] for s in sorted_signals[:3]]

    return {
        "pain_score": pain_score,
        "pain_signals": str([s['signal'] for s in pain_signals]),
        "pain_signals_full": str(pain_signals),
        "qualification_status": qualification_status,
        "top_pain_points": str(top_pain_points),
        "icp_score": icp_score,
        "proceed": "true" if qualification_status != "REJECTED" else "false",
        "signal_count": len(pain_signals)
    }


# Test function
if __name__ == "__main__":
    result = main(
        has_gtm="false",
        has_ga4="false",
        has_ga_universal="false",
        crm_detected="",
        booking_system="",
        cms_platform="Wix",
        visual_score="35",
        design_era="Dated",
        social_facebook="",
        social_instagram="",
        social_linkedin="",
        mobile_responsive="true",
        performance_score="45",
        mobile_score="55",
        seo_score="40",
        listings_score="50",
        nap_consistency="0.9",
        license_status="Active",
        bbb_rating="A",
        complaints_3yr="2"
    )

    print(f"Pain Score: {result['pain_score']}")
    print(f"Status: {result['qualification_status']}")
    print(f"ICP Score: {result['icp_score']}")
    print(f"Top Pain Points: {result['top_pain_points']}")
    print(f"Signals: {result['pain_signals']}")
