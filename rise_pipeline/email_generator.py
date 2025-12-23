"""
Email Generation using Claude API for Rise Local Pipeline
"""
import json
import random
import httpx
from typing import Optional
# Support both package-relative and top-level imports. When this module
# is imported as part of the ``rise_pipeline`` package the relative imports
# will succeed. When this module is executed or imported as a top-level
# script (e.g. ``import email_generator`` from within the same directory),
# the relative imports will fail. In that case we fall back to importing
# the modules from the current working directory.
try:
    from .models import (
        Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
        DirectoryPresence, ReputationData, PainScore, GeneratedEmail
    )  # type: ignore
except ImportError:
    from models import (
        Lead, TechEnrichment, VisualAnalysis, TechnicalScores,
        DirectoryPresence, ReputationData, PainScore, GeneratedEmail
    )  # type: ignore

try:
    from .config import ANTHROPIC_API_KEY, EMAIL_CONFIDENCE_THRESHOLD, EMAIL_MAX_WORDS  # type: ignore
except ImportError:
    from config import ANTHROPIC_API_KEY, EMAIL_CONFIDENCE_THRESHOLD, EMAIL_MAX_WORDS  # type: ignore

try:
    from .scoring import format_pain_signals_for_email  # type: ignore
except ImportError:
    from scoring import format_pain_signals_for_email  # type: ignore


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# A/B test variants
AB_VARIANTS = ["authority", "curiosity", "pain_point"]


def build_email_prompt(
    lead: Lead,
    tech: TechEnrichment,
    visual: VisualAnalysis,
    technical: TechnicalScores,
    directory: DirectoryPresence,
    reputation: ReputationData,
    pain_score: PainScore,
    variant: str
) -> str:
    """Build the prompt for Claude to generate a personalized email."""

    pain_hooks = format_pain_signals_for_email(pain_score)
    pain_hooks_text = "\n".join(f"  - {hook}" for hook in pain_hooks)

    # Variant-specific instructions
    variant_instructions = {
        "authority": """
TONE: Position yourself as the expert who can solve their problems.
Focus on establishing credibility and showcasing expertise.
Lead with what you know about their business and industry.""",

        "curiosity": """
TONE: Create curiosity and intrigue about potential improvements.
Ask thought-provoking questions about their digital presence.
Hint at opportunities they might be missing.""",

        "pain_point": """
TONE: Directly address their specific pain points with empathy.
Show you understand their challenges before offering solutions.
Be consultative and helpful, not salesy."""
    }

    prompt = f"""You are a professional copywriter for Rise Local, a digital marketing agency specializing in helping home service businesses grow their online presence.

Generate a cold outreach email for this business:

BUSINESS INFORMATION:
- Business Name: {lead.business_name}
- Location: {lead.city}, {lead.state}
- Website: {lead.website_url or "No website found"}
- Google Rating: {lead.google_rating} stars ({lead.review_count} reviews)

IDENTIFIED PAIN POINTS (use 1-2 of these as personalization hooks):
{pain_hooks_text}

ADDITIONAL CONTEXT:
- Tech Stack Score: {tech.tech_score}/100
- Visual/Design Score: {visual.visual_score}/100
- Performance Score: {technical.performance_score}/100
- Directory Presence Score: {directory.listings_score}/100
- ICP Match Score: {pain_score.icp_score}/100

A/B VARIANT: {variant.upper()}
{variant_instructions.get(variant, variant_instructions["pain_point"])}

REQUIREMENTS:
1. Subject line: Short (5-8 words), personalized, creates curiosity
2. Preview text: 40-90 characters that complements the subject
3. Email body: Maximum {EMAIL_MAX_WORDS} words
4. Include ONE specific observation about their business
5. Include ONE clear value proposition
6. End with a soft CTA (question or offer, not hard sell)
7. Sign off as "Bryson" from Rise Local
8. Do NOT use generic phrases like "I noticed your website" without specifics
9. Do NOT include placeholder text like [NAME] or {{COMPANY}}

OUTPUT FORMAT (respond with valid JSON only):
{{
  "subject_line": "Your subject here",
  "preview_text": "Preview text here",
  "email_body": "Full email body here",
  "personalization_hooks": ["hook1", "hook2"],
  "confidence_score": 0.85
}}

Generate the email now:"""

    return prompt


async def generate_email(
    lead: Lead,
    tech: TechEnrichment,
    visual: VisualAnalysis,
    technical: TechnicalScores,
    directory: DirectoryPresence,
    reputation: ReputationData,
    pain_score: PainScore,
    variant: Optional[str] = None,
    rag_context: Optional[dict] = None
) -> GeneratedEmail:
    """Generate personalized email using Claude API."""

    if not ANTHROPIC_API_KEY:
        return GeneratedEmail(
            valid=False,
            error="ANTHROPIC_API_KEY not configured"
        )

    # Select A/B variant
    selected_variant = variant or random.choice(AB_VARIANTS)

    # Build prompt
    prompt = build_email_prompt(
        lead=lead,
        tech=tech,
        visual=visual,
        technical=technical,
        directory=directory,
        reputation=reputation,
        pain_score=pain_score,
        variant=selected_variant
    )

    try:
        # Disable trust in environment proxies to avoid requiring optional
        # dependencies like socksio (see test integrations). When trust_env=False,
        # httpx will ignore HTTP_PROXY/HTTPS_PROXY environment variables that may
        # point to a SOCKS proxy. Without socksio installed this would otherwise
        # raise an error.
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )

            if response.status_code != 200:
                return GeneratedEmail(
                    valid=False,
                    error=f"Claude API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            content = result.get("content", [])

            if not content:
                return GeneratedEmail(
                    valid=False,
                    error="Empty response from Claude"
                )

            # Extract text from response
            text = content[0].get("text", "")

            # Parse JSON from response
            try:
                # Handle potential markdown code blocks
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()

                email_data = json.loads(text)
            except json.JSONDecodeError as e:
                return GeneratedEmail(
                    valid=False,
                    error=f"Failed to parse Claude response as JSON: {e}"
                )

            # Validate required fields
            required_fields = ["subject_line", "preview_text", "email_body"]
            for field in required_fields:
                if field not in email_data or not email_data[field]:
                    return GeneratedEmail(
                        valid=False,
                        error=f"Missing required field: {field}"
                    )

            # Count words
            word_count = len(email_data["email_body"].split())

            # Get confidence score
            confidence = email_data.get("confidence_score", 0.7)

            # Validate email quality
            email = GeneratedEmail(
                subject_line=email_data["subject_line"],
                preview_text=email_data["preview_text"],
                email_body=email_data["email_body"],
                personalization_hooks=email_data.get("personalization_hooks", []),
                confidence_score=confidence,
                word_count=word_count,
                valid=True
            )

            # Quality checks
            validation_errors = validate_email(email, lead)
            if validation_errors:
                email.valid = False
                email.error = "; ".join(validation_errors)
                email.confidence_score = min(email.confidence_score, 0.4)

            # Check confidence threshold
            if email.confidence_score < EMAIL_CONFIDENCE_THRESHOLD:
                email.valid = False
                if not email.error:
                    email.error = f"Confidence score {email.confidence_score} below threshold {EMAIL_CONFIDENCE_THRESHOLD}"

            return email

    except httpx.TimeoutException:
        return GeneratedEmail(
            valid=False,
            error="Claude API timeout"
        )
    except Exception as e:
        return GeneratedEmail(
            valid=False,
            error=f"Email generation failed: {str(e)}"
        )


def validate_email(email: GeneratedEmail, lead: Lead) -> list:
    """Validate generated email quality."""
    errors = []

    # Check for placeholder text
    placeholders = ["[NAME]", "[COMPANY]", "{{", "}}", "[CITY]", "[STATE]"]
    for placeholder in placeholders:
        if placeholder in email.email_body or placeholder in email.subject_line:
            errors.append(f"Contains placeholder text: {placeholder}")

    # Check word count
    if email.word_count > EMAIL_MAX_WORDS * 1.2:  # 20% tolerance
        errors.append(f"Email too long: {email.word_count} words (max {EMAIL_MAX_WORDS})")

    if email.word_count < 50:
        errors.append(f"Email too short: {email.word_count} words")

    # Check subject line length
    if len(email.subject_line) > 60:
        errors.append("Subject line too long (>60 chars)")

    if len(email.subject_line) < 10:
        errors.append("Subject line too short (<10 chars)")

    # Check for business name mention (personalization)
    business_words = lead.business_name.lower().split()
    body_lower = email.email_body.lower()

    # At least one significant word from business name should appear
    name_mentioned = any(
        word in body_lower
        for word in business_words
        if len(word) > 3 and word not in ["the", "and", "llc", "inc"]
    )

    if not name_mentioned and lead.city.lower() not in body_lower:
        errors.append("Email lacks personalization (no business name or city mention)")

    # Check for required sign-off
    if "bryson" not in body_lower and "rise local" not in body_lower:
        errors.append("Missing signature from Bryson/Rise Local")

    return errors


def select_ab_variant() -> str:
    """Select A/B test variant for email generation."""
    return random.choice(AB_VARIANTS)
