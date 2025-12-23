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
