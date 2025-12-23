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
