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
