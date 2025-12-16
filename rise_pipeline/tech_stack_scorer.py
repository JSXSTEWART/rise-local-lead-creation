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
import anthropic

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
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured in environment")

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
        print(f"  [ERROR] Failed to parse AI response as JSON: {e}")
        print(f"  Raw response: {response_text[:200]}...")
        return {
            "error": "JSON parse failed",
            "tech_score": 5,  # Default neutral score
            "pain_points": ["Unable to analyze tech stack"],
            "strengths": []
        }
    except Exception as e:
        print(f"  [ERROR] Tech stack analysis failed: {e}")
        return {
            "error": str(e),
            "tech_score": 5,
            "pain_points": ["Analysis error"],
            "strengths": []
        }


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
