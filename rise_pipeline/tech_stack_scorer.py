"""
Tech Stack Scoring using Claude Haiku

Analyzes technology lists from BuiltWith (via Clay) to identify:
- Professional vs DIY website builders
- Marketing automation maturity
- Analytics setup quality
- Overall tech sophistication

Uses Claude Haiku for AI-powered analysis.
"""

import os
import json
from typing import Dict, Any, List
try:
    import anthropic  # type: ignore
except ImportError:
    anthropic = None  # type: ignore

TECH_STACK_ANALYSIS_PROMPT = """You are a digital marketing technology analyst evaluating the tech stack of electrical contractor businesses.

Your goal: Identify businesses with POOR digital marketing setups who need professional help.

# What Makes a Stack "POOR" (High Pain Score)

## RED FLAGS (Major Pain Points):

1. **DIY Website Builders** (Automatic disqualification from "good")
   - Squarespace
   - Wix
   - GoDaddy Website Builder / GoDaddy Airo
   - Webs.com
   - Vistaprint Digital Marketing
   These are consumer-grade tools. Businesses using these don't have professional marketing.

2. **No Modern Analytics**
   - Missing Google Tag Manager (GTM)
   - Missing Google Analytics 4 (GA4)
   - Only has old Universal Analytics
   - No tracking at all

3. **No Marketing Automation**
   - Missing CRM (Salesforce, HubSpot, Pipedrive, GoHighLevel, etc.)
   - Missing email marketing (Mailchimp, ActiveCampaign, MailerLite, etc.)
   - Missing lead capture/forms

4. **No Booking System**
   - Missing Calendly, Acuity, ServiceTitan, Housecall Pro
   - No online scheduling

5. **Outdated/Bloated WordPress**
   - 50+ plugins (indicates poor management)
   - Old WordPress versions mentioned
   - Too many conflicting technologies

## GOOD SIGNS (Lower Pain Score):

1. **Professional Setup**
   - Custom-built site (lots of technologies but NOT DIY builders)
   - Modern hosting (AWS, Google Cloud, Cloudflare)
   - Professional CMS (WordPress with reasonable plugin count, custom)

2. **Modern Marketing Stack**
   - GTM + GA4
   - Active CRM
   - Email marketing platform
   - Lead forms/capture

3. **Service Business Tools**
   - ServiceTitan, Housecall Pro, Jobber
   - Online booking
   - Payment processing (Stripe, Square, Authorize.net)

# Scoring Guidelines

**Tech Score (0-10 scale):**
- **0-3 (CRITICAL NEED):** DIY builder OR no analytics OR ancient setup
- **4-5 (HIGH NEED):** Missing multiple core tools (GTM, CRM, booking)
- **6-7 (MODERATE):** Has basics but missing automation
- **8-10 (PROFESSIONAL):** Modern, complete marketing stack

**Pain Points to Extract:**
- "DIY website builder" (if Squarespace/Wix/GoDaddy)
- "No Google Tag Manager"
- "No Google Analytics 4"
- "No CRM detected"
- "No booking system"
- "No email marketing platform"
- "Outdated WordPress setup" (if 50+ plugins or old versions)
- "No lead capture forms"

# Response Format

Return ONLY valid JSON (no markdown, no explanation):

{{
  "has_gtm": false,
  "has_ga4": false,
  "has_modern_analytics": false,
  "has_crm": false,
  "has_email_marketing": false,
  "has_booking_system": false,
  "has_lead_capture": false,
  "website_type": "DIY Builder|Professional|Outdated WordPress|Custom|Unknown",
  "cms_platform": "Squarespace|Wix|GoDaddy|WordPress|Custom|None",
  "tech_score": 3,
  "pain_points": [
    "DIY website builder (Squarespace)",
    "No Google Tag Manager",
    "No CRM detected"
  ],
  "strengths": [
    "Has payment processing"
  ],
  "recommended_pitch": "Their Squarespace site is holding back their lead generation. No tracking, no CRM, no automation."
}}

# Now Analyze This Stack:

Business: {business_name}
Total Technologies: {tech_count}
Technologies: {technologies}

Return JSON only:"""


async def analyze_tech_stack(
    business_name: str,
    technologies: str,
    tech_count: int
) -> Dict[str, Any]:
    """
    Analyze a technology stack using Claude Haiku.

    Args:
        business_name: Name of the business
        technologies: Comma-separated list of technologies from BuiltWith
        tech_count: Total number of technologies detected

    Returns:
        dict with analysis results including pain points and tech_score
    """
    # Determine whether to use the Claude API or fall back to a heuristic
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Use Claude only if both the API key and the anthropic client are available
    if anthropic is not None and api_key:
        client = anthropic.Anthropic(api_key=api_key)

        # Format the prompt with actual data
        prompt = TECH_STACK_ANALYSIS_PROMPT.format(
            business_name=business_name,
            tech_count=tech_count,
            technologies=technologies[:3000]  # Limit to first 3000 chars to avoid token limits
        )

        try:
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                temperature=0,  # Deterministic for consistency
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse the JSON response
            response_text = message.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            analysis = json.loads(response_text)

            # Add metadata
            analysis["analyzed_at"] = message.id
            analysis["model"] = message.model
            analysis["tech_count_input"] = tech_count

            return analysis

        except json.JSONDecodeError as e:
            # If the AI returns invalid JSON, fall back to a neutral response
            print(f"  [ERROR] Failed to parse AI response as JSON: {e}")
            print(f"  Raw response: {response_text[:200]}...")
            return {
                "error": "JSON parse failed",
                "tech_score": 5,
                "pain_points": ["Unable to analyze tech stack"],
                "strengths": []
            }
        except Exception as e:
            # Unexpected API error; return a neutral response
            print(f"  [ERROR] Tech stack analysis failed: {e}")
            return {
                "error": str(e),
                "tech_score": 5,
                "pain_points": ["Analysis error"],
                "strengths": []
            }

    # ------------------------------------------------------------------
    # Heuristic-based analysis (offline fallback)
    # ------------------------------------------------------------------
    # Parse technologies into a list of lowercase keywords
    tech_list: List[str] = []
    if technologies:
        # Split on commas and strip whitespace
        tech_list = [t.strip() for t in technologies.split(",") if t.strip()]
    tech_list_lower = [t.lower() for t in tech_list]

    # Helper to search for any keyword in the technology list
    def contains_any(keywords: List[str]) -> bool:
        for kw in keywords:
            kw_l = kw.lower()
            for t in tech_list_lower:
                if kw_l in t:
                    return True
        return False

    # Detect presence of various tools
    has_gtm = contains_any(["google tag manager", "tag manager", "gtm"])
    # GA4 specifically; ensure we don't match universal analytics
    has_ga4 = contains_any(["ga4", "google analytics 4", "analytics ga4"])
    # Legacy universal analytics (not used currently but kept for completeness)
    has_ga_universal = contains_any(["universal analytics", "google analytics", "ga"])
    # Determine whether modern analytics stack is present
    has_modern_analytics = has_gtm and has_ga4

    # Common CRM platforms
    crm_keywords = [
        "salesforce", "hubspot", "pipe drive", "pipedrive", "go high level", "gohighlevel",
        "zoho", "keap", "infusionsoft", "monday.com", "monday", "freshsales",
        "insightly", "highlevel", "crm"
    ]
    has_crm = contains_any(crm_keywords)

    # Email marketing platforms
    email_keywords = [
        "mailchimp", "mail chimp", "activecampaign", "active campaign", "mailer lite",
        "constant contact", "sendgrid", "klaviyo", "aweber", "convertkit", "getresponse",
        "drip", "emma", "campaign monitor"
    ]
    has_email_marketing = contains_any(email_keywords)

    # Booking/scheduling systems
    booking_keywords = [
        "calendly", "acuity", "acuity scheduling", "servicetitan", "service titan",
        "housecall pro", "house call pro", "jobber", "square appointments", "mindbody",
        "scheduleonce", "setmore", "booksy", "resurva", "bookly", "go appointment"
    ]
    has_booking_system = contains_any(booking_keywords)

    # Lead capture forms and widgets
    lead_capture_keywords = [
        "contact form", "contact form 7", "gravity forms", "wpforms", "typeform",
        "wufoo", "jotform", "leadpages", "optinmonster", "mailchimp for wordpress",
        "formidable forms", "hubspot forms", "form", "lead capture"
    ]
    # Specific detection of lead capture forms; generic "form" is only used
    # if no specific match was found.
    def has_lead_capture_func() -> bool:
        # Check specific keywords first
        for kw in lead_capture_keywords:
            kw_l = kw.lower()
            if kw_l == "form":
                continue
            for t in tech_list_lower:
                if kw_l in t:
                    return True
        # Fall back to the generic term "form" if nothing else matched
        if contains_any(["form"]):
            return True
        return False
    has_lead_capture = has_lead_capture_func()

    # Determine CMS/platform
    cms_platform = "Custom"
    website_type = "Unknown"
    # Detect DIY builders
    if contains_any(["squarespace"]):
        cms_platform = "Squarespace"
        website_type = "DIY Builder"
    elif contains_any(["wix"]):
        cms_platform = "Wix"
        website_type = "DIY Builder"
    elif contains_any(["godaddy", "go daddy"]):
        cms_platform = "GoDaddy"
        website_type = "DIY Builder"
    # Recognise other DIY tools; treat as DIY but set cms_platform as Custom
    elif contains_any(["webflow", "weebly", "duda", "jimdo", "vistaprint"]):
        cms_platform = "Custom"
        website_type = "DIY Builder"
    # Detect WordPress
    elif contains_any(["wordpress"]):
        cms_platform = "WordPress"
        # If a large number of technologies suggests many plugins, mark as outdated
        if tech_count and tech_count >= 50:
            website_type = "Outdated WordPress"
        else:
            website_type = "Professional"
    else:
        # If no CMS detected but there are modern frameworks present,
        # assume a custom/professional build
        if contains_any(["react", "next.js", "nextjs", "gatsby", "vue", "nuxt", "angular"]):
            website_type = "Custom"
        else:
            website_type = "Professional" if tech_count >= 1 else "Unknown"

    # Estimate tech score (0–10 scale). Start at 10 and subtract points for
    # missing features and poor foundations. Clamp between 0 and 10.
    score = 10
    # DIY builder is a significant detractor
    if website_type == "DIY Builder":
        score -= 4
    elif website_type == "Outdated WordPress":
        score -= 3
    # Subtract for missing analytics tools
    if not has_gtm:
        score -= 2
    if not has_ga4:
        score -= 2
    # Subtract for missing CRM, booking, email
    if not has_crm:
        score -= 2
    if not has_booking_system:
        score -= 2
    if not has_email_marketing:
        score -= 1
    # Subtract for missing lead capture
    if not has_lead_capture:
        score -= 1
    # Ensure score is within 0-10
    if score < 0:
        score = 0
    if score > 10:
        score = 10
    tech_score = score

    # Compose pain points based on missing features
    pain_points: List[str] = []
    if website_type == "DIY Builder":
        pain_desc = cms_platform if cms_platform not in ["Custom", "Unknown"] else "DIY builder"
        pain_points.append(f"DIY website builder ({pain_desc})")
    if website_type == "Outdated WordPress":
        pain_points.append("Outdated WordPress setup")
    if not has_gtm:
        pain_points.append("No Google Tag Manager")
    if not has_ga4:
        pain_points.append("No Google Analytics 4")
    if not has_crm:
        pain_points.append("No CRM detected")
    if not has_booking_system:
        pain_points.append("No booking system")
    if not has_email_marketing:
        pain_points.append("No email marketing platform")
    if not has_lead_capture:
        pain_points.append("No lead capture forms")

    # Compose strengths for present features
    strengths: List[str] = []
    if website_type not in ["DIY Builder", "Outdated WordPress"]:
        strengths.append("Professional or custom website")
    if has_gtm:
        strengths.append("Has Google Tag Manager")
    if has_ga4:
        strengths.append("Has Google Analytics 4")
    if has_crm:
        strengths.append("Has CRM")
    if has_email_marketing:
        strengths.append("Has email marketing platform")
    if has_booking_system:
        strengths.append("Has booking system")
    if has_lead_capture:
        strengths.append("Has lead capture forms")

    # Build recommended pitch based on pain points
    if pain_points:
        if website_type == "DIY Builder":
            site_desc = cms_platform
            pitch_intro = f"Their {site_desc} site is holding back their lead generation."
        elif website_type == "Outdated WordPress":
            pitch_intro = "Their outdated WordPress setup is hurting their growth."
        else:
            pitch_intro = "Their website is missing critical tools."
        missing: List[str] = []
        for p in pain_points:
            if "DIY website builder" in p or "Outdated WordPress" in p:
                continue
            if p.startswith("No "):
                # Remove "No " prefix and any trailing " detected" for readability
                cleaned = p[3:]
                if cleaned.endswith(" detected"):
                    cleaned = cleaned[:-9].strip()
                missing.append(cleaned)
            else:
                missing.append(p)
            if len(missing) >= 3:
                break
        if missing:
            missing_text = ", ".join(missing)
            pitch_body = f" Lacking {missing_text}."
        else:
            pitch_body = ""
        recommended_pitch = f"{pitch_intro}{pitch_body}"
    else:
        recommended_pitch = "Looks like they have a solid marketing stack in place."

    from datetime import datetime
    analysis: Dict[str, Any] = {
        "has_gtm": has_gtm,
        "has_ga4": has_ga4,
        "has_modern_analytics": has_modern_analytics,
        "has_crm": has_crm,
        "has_email_marketing": has_email_marketing,
        "has_booking_system": has_booking_system,
        "has_lead_capture": has_lead_capture,
        "website_type": website_type,
        "cms_platform": cms_platform,
        "tech_score": tech_score,
        "pain_points": pain_points,
        "strengths": strengths,
        "recommended_pitch": recommended_pitch,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
        "model": "heuristic",
        "tech_count_input": tech_count
    }

    return analysis


async def batch_analyze_tech_stacks(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze multiple tech stacks in batch.

    Args:
        leads: List of lead dicts with 'business_name', 'Technologiesfound', 'Numberoftotaltechnologies'

    Returns:
        List of analysis results (same order as input)
    """
    results = []

    for lead in leads:
        business_name = lead.get("business_name", "Unknown")
        technologies = lead.get("Technologiesfound", "")
        tech_count = int(lead.get("Numberoftotaltechnologies", 0))

        print(f"\n  Analyzing: {business_name} ({tech_count} technologies)")

        analysis = await analyze_tech_stack(business_name, technologies, tech_count)

        # Merge analysis with lead data
        result = {**lead, **analysis}
        results.append(result)

        print(f"    Tech Score: {analysis.get('tech_score', 'N/A')}/10")
        print(f"    Pain Points: {len(analysis.get('pain_points', []))}")

    return results


def calculate_pain_score_from_tech(analysis: Dict[str, Any]) -> int:
    """
    Calculate pain point score based on tech stack analysis.

    Returns:
        Pain score (0-10+) where higher = more pain = better lead
    """
    pain_score = 0

    # DIY website builder = MAJOR red flag (+4 points)
    website_type = analysis.get("website_type", "")
    if "DIY" in website_type or analysis.get("cms_platform") in ["Squarespace", "Wix", "GoDaddy"]:
        pain_score += 4

    # No GTM (+2)
    if not analysis.get("has_gtm", False):
        pain_score += 2

    # No GA4 (+2)
    if not analysis.get("has_ga4", False):
        pain_score += 2

    # No CRM (+2)
    if not analysis.get("has_crm", False):
        pain_score += 2

    # No booking system (+2)
    if not analysis.get("has_booking_system", False):
        pain_score += 2

    # No email marketing (+1)
    if not analysis.get("has_email_marketing", False):
        pain_score += 1

    # Low tech score amplifier
    tech_score = analysis.get("tech_score", 5)
    if tech_score <= 3:
        pain_score += 2  # Really bad setup
    elif tech_score <= 5:
        pain_score += 1  # Mediocre setup

    return pain_score


# Example usage
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    async def test():
        # Test with a sample from your Clay export
        result = await analyze_tech_stack(
            business_name="Hart Electrical Services, LLC",
            technologies="Google Cloud, Google, U.S. Server Location, Wix Pepyaka, Google Cloud CDN, SSL by Default, DNSSEC, Google Cloud Global Multi-Region",
            tech_count=8
        )

        print("\n=== Analysis Result ===")
        print(json.dumps(result, indent=2))

        pain_score = calculate_pain_score_from_tech(result)
        print(f"\nPain Score: {pain_score}")

    asyncio.run(test())
