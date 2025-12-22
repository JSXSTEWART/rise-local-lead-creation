"""
Claude Qualification Validator Agent
Intelligent lead qualification with MCP tool integration and LLMCouncil pattern
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal

from anthropic import Anthropic
import httpx


class QualificationValidator:
    """
    Claude agent for intelligent lead qualification.

    Features:
    - MCP tool integration for enrichment
    - LLMCouncil 4-agent consensus for marginal leads
    - Pain point analysis with scoring
    - Lead category classification
    - Confidence scoring and reasoning
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        model: str = "claude-opus-4-5-20251101"
    ):
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.mcp_server_url = mcp_server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")
        self.model = model

        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.http_client = httpx.AsyncClient(timeout=120.0)

        # MCP tool definitions
        self.tools = self._get_mcp_tools()

    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Define MCP tools for Claude to use"""
        return [
            {
                "name": "search_tdlr_license",
                "description": "Search Texas TDLR for electrical contractor license using waterfall method (license number, owner name, business name). Returns license status, owner name, violations, expiry date.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "license_number": {"type": "string", "description": "TECL license number if known"},
                        "owner_first_name": {"type": "string"},
                        "owner_last_name": {"type": "string"},
                        "business_name": {"type": "string"},
                        "city": {"type": "string"},
                        "lead_id": {"type": "string", "format": "uuid"}
                    },
                    "required": ["lead_id"]
                }
            },
            {
                "name": "search_bbb_reputation",
                "description": "Search Better Business Bureau for reputation data and calculate reputation gap vs Google rating. Returns BBB rating, accreditation status, complaint counts, reputation gap.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "business_name": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "google_rating": {"type": "number"},
                        "lead_id": {"type": "string"}
                    },
                    "required": ["business_name", "city", "state", "lead_id"]
                }
            },
            {
                "name": "analyze_pagespeed",
                "description": "Analyze website performance using Google PageSpeed Insights. Returns performance score, Core Web Vitals, mobile score, SEO score.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "strategy": {"enum": ["mobile", "desktop"], "default": "mobile"},
                        "lead_id": {"type": "string"}
                    },
                    "required": ["url", "lead_id"]
                }
            },
            {
                "name": "capture_screenshot_and_analyze",
                "description": "Capture website screenshots (desktop + mobile) and analyze visual quality, design era, tech stack using Gemini Vision. Returns visual score, design era, recommendations.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "include_mobile": {"type": "boolean", "default": True},
                        "lead_id": {"type": "string"}
                    },
                    "required": ["url", "lead_id"]
                }
            },
            {
                "name": "extract_owner_info",
                "description": "Extract owner name, email, phone, and license number from website using Claude Vision. Critical for TDLR waterfall lookup.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "lead_id": {"type": "string"}
                    },
                    "required": ["url", "lead_id"]
                }
            },
            {
                "name": "verify_address",
                "description": "Verify if business address is residential or commercial using Smarty API (USPS RDI). Returns address type, validation status.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip_code": {"type": "string"},
                        "lead_id": {"type": "string"}
                    },
                    "required": ["address", "city", "state", "lead_id"]
                }
            }
        ]

    async def _call_mcp_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP server tool"""
        try:
            response = await self.http_client.post(
                f"{self.mcp_server_url}/call_tool",
                json={"tool": tool_name, "arguments": tool_input},
                timeout=90.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"error": f"{tool_name} timeout", "status": "timeout"}
        except Exception as e:
            return {"error": str(e), "status": "error"}

    async def qualify_lead(
        self,
        lead_id: str,
        context: Dict[str, Any],
        mode: str = "standard"
    ) -> Dict[str, Any]:
        """
        Qualify a lead using Claude with MCP tool integration.

        Args:
            lead_id: UUID of the lead
            context: Lead context with enrichment data
            mode: "standard" for single agent, "council" for 4-agent consensus

        Returns:
            Decision dict with decision, confidence, reasoning, metadata
        """

        if mode == "council":
            return await self._qualify_with_council(lead_id, context)
        else:
            return await self._qualify_standard(lead_id, context)

    async def _qualify_standard(self, lead_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Standard qualification with single Claude agent"""

        # Build prompt
        prompt = self._build_qualification_prompt(context)

        # Call Claude with tools
        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            tools=self.tools,
            messages=messages
        )

        # Process tool calls
        tool_results = []
        if response.stop_reason == "tool_use":
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input

                    # Call MCP tool
                    result = await self._call_mcp_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": json.dumps(result)
                    })

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Get final decision
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=messages
            )

        # Extract decision from response
        decision_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                decision_text += block.text

        # Parse decision
        decision = self._parse_decision(decision_text, context)

        return decision

    async def _qualify_with_council(self, lead_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLMCouncil qualification with 4-agent consensus.

        Agents:
        1. Lead Analyst: Market opportunity scoring
        2. Email Strategist: Engagement potential assessment
        3. Quality Reviewer: Data completeness validation
        4. Risk Assessor: Red flag identification
        """

        # Define council agents
        agents = [
            {
                "name": "Lead Analyst",
                "role": "Evaluate market opportunity and business potential",
                "focus": "Market size, competition, growth potential, pain severity"
            },
            {
                "name": "Email Strategist",
                "role": "Assess email engagement potential",
                "focus": "Personalization opportunities, pain point messaging, response likelihood"
            },
            {
                "name": "Quality Reviewer",
                "role": "Validate data completeness and accuracy",
                "focus": "Missing data, data quality issues, enrichment gaps"
            },
            {
                "name": "Risk Assessor",
                "role": "Identify red flags and disqualification signals",
                "focus": "Franchise indicators, compliance issues, reputation problems"
            }
        ]

        # Get votes from each agent
        votes = []
        for agent in agents:
            vote = await self._get_agent_vote(lead_id, context, agent)
            votes.append(vote)

        # Calculate consensus
        qualified_votes = sum(1 for v in votes if v["vote"] == "qualified")
        rejected_votes = sum(1 for v in votes if v["vote"] == "rejected")

        # Decision logic: 3/4 or 4/4 for qualified, otherwise rejected
        if qualified_votes >= 3:
            final_decision = "qualified"
            confidence = qualified_votes / 4.0
        elif rejected_votes >= 3:
            final_decision = "rejected"
            confidence = rejected_votes / 4.0
        else:
            # 2-2 split, flag for human review
            final_decision = "marginal"
            confidence = 0.5

        # Build reasoning
        reasoning = self._build_council_reasoning(votes, final_decision)

        # Calculate final pain score (average from votes)
        pain_scores = [v.get("pain_score", context.get("preliminary_pain_score", 50)) for v in votes]
        avg_pain_score = int(sum(pain_scores) / len(pain_scores))

        return {
            "decision": final_decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "pain_score": avg_pain_score,
            "metadata": {
                "council_votes": {v["agent_name"]: v for v in votes},
                "qualified_votes": qualified_votes,
                "rejected_votes": rejected_votes
            }
        }

    async def _get_agent_vote(
        self,
        lead_id: str,
        context: Dict[str, Any],
        agent: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get vote from a single council agent"""

        prompt = f"""You are the {agent['name']} on a lead qualification council.

Your Role: {agent['role']}
Your Focus: {agent['focus']}

Lead Context:
{json.dumps(context, indent=2)}

Based on your specialized perspective, vote on whether this lead should be QUALIFIED or REJECTED.

Respond in this JSON format:
{{
    "vote": "qualified" or "rejected",
    "score": 0-100 (your assessment score),
    "reasoning": "Your specific analysis from your role's perspective",
    "key_factors": ["factor 1", "factor 2", "factor 3"]
}}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            # Parse JSON response
            vote_data = json.loads(response_text)
            vote_data["agent_name"] = agent["name"]
            vote_data["pain_score"] = vote_data.get("score", 50)

            return vote_data

        except Exception as e:
            # Fallback vote on error
            return {
                "agent_name": agent["name"],
                "vote": "rejected",
                "score": 0,
                "reasoning": f"Error: {str(e)}",
                "key_factors": [],
                "pain_score": 0
            }

    def _build_council_reasoning(self, votes: List[Dict], final_decision: str) -> str:
        """Build comprehensive reasoning from council votes"""

        reasoning_parts = []

        for vote in votes:
            status = "✓ QUALIFIED" if vote["vote"] == "qualified" else "✗ REJECTED"
            reasoning_parts.append(
                f"{vote['agent_name']}: {status} (Score: {vote.get('score', 0)}/100)\n"
                f"  Reasoning: {vote['reasoning']}"
            )

        qualified_count = sum(1 for v in votes if v["vote"] == "qualified")

        summary = f"\n\nCOUNCIL CONSENSUS: {qualified_count}/4 agents voted QUALIFIED → Final Decision: {final_decision.upper()}"

        return "\n\n".join(reasoning_parts) + summary

    def _build_qualification_prompt(self, context: Dict[str, Any]) -> str:
        """Build qualification prompt for Claude"""

        return f"""You are a lead qualification expert for Rise Local, specializing in electrical contractors.

Your task is to qualify this lead based on pain signals and business potential.

Lead Context:
{json.dumps(context, indent=2)}

Available Tools:
- search_tdlr_license: Verify contractor license status
- search_bbb_reputation: Check BBB rating and complaints
- analyze_pagespeed: Test website performance
- capture_screenshot_and_analyze: Evaluate website design
- extract_owner_info: Find owner contact information
- verify_address: Check if address is residential/commercial

Instructions:
1. Call relevant MCP tools to gather additional data (prioritize tools based on what's missing)
2. Analyze all pain signals:
   - Poor website (visual_score < 50) → HIGH PAIN
   - Slow performance (performance_score < 40) → MEDIUM PAIN
   - No mobile responsiveness → MEDIUM PAIN
   - No CRM detected → MEDIUM PAIN
   - Expired license → HIGH PAIN (disqualifying)
   - Reputation gap > 1.5 → HIGH PAIN
   - Residential address → LOW QUALITY (often home-based)

3. Calculate pain score (0-100):
   - 0-30: REJECTED (insufficient pain)
   - 31-59: MARGINAL (needs council review)
   - 60-100: QUALIFIED (clear opportunity)

4. Classify lead category:
   - THE_INVISIBLE: No website or minimal online presence
   - DIY_CEILING: Template website, no booking/CRM
   - LEAKY_BUCKET: Traffic but poor conversion
   - OVERWHELMED: Bad reviews, backlog issues
   - READY_TO_DOMINATE: Good foundation, needs scale

5. Make your decision:
   - QUALIFIED: High pain, good fit, likely to respond
   - REJECTED: Low pain, franchise, or red flags
   - MARGINAL: Uncertain, needs human review

Respond in this JSON format:
{{
    "decision": "qualified|rejected|marginal",
    "confidence": 0.0-1.0,
    "pain_score": 0-100,
    "category": "THE_INVISIBLE|DIY_CEILING|LEAKY_BUCKET|OVERWHELMED|READY_TO_DOMINATE",
    "top_pain_points": ["pain 1", "pain 2", "pain 3"],
    "reasoning": "Your detailed analysis explaining the decision",
    "red_flags": ["flag 1", "flag 2"] or []
}}
"""

    def _parse_decision(self, decision_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse decision from Claude's response"""

        try:
            # Try to extract JSON from response
            start = decision_text.find('{')
            end = decision_text.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = decision_text[start:end]
                decision = json.loads(json_str)

                # Validate required fields
                required = ["decision", "confidence", "pain_score", "reasoning"]
                if all(k in decision for k in required):
                    return decision

        except json.JSONDecodeError:
            pass

        # Fallback: Use preliminary pain score
        prelim_score = context.get("preliminary_pain_score", 50)

        return {
            "decision": "qualified" if prelim_score >= 60 else "rejected",
            "confidence": 0.7,
            "pain_score": prelim_score,
            "category": "DIY_CEILING",
            "top_pain_points": context.get("pain_signals", [])[:3],
            "reasoning": f"Fallback decision based on preliminary pain score: {prelim_score}. {decision_text[:200]}",
            "red_flags": []
        }

    async def save_decision(
        self,
        lead_id: str,
        decision: Dict[str, Any],
        agent_name: str = "claude_qualifier"
    ) -> str:
        """Save decision to agent_decisions table in Supabase"""

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not configured")

        decision_id = str(uuid4())

        record = {
            "id": decision_id,
            "lead_id": lead_id,
            "decision_type": "qualification",
            "agent_name": agent_name,
            "agent_type": "claude_agent",
            "decision": decision["decision"],
            "confidence": float(decision["confidence"]),
            "reasoning": decision["reasoning"],
            "metadata": {
                "pain_score": decision.get("pain_score"),
                "category": decision.get("category"),
                "top_pain_points": decision.get("top_pain_points", []),
                "red_flags": decision.get("red_flags", []),
                "council_votes": decision.get("metadata", {}).get("council_votes")
            },
            "created_at": datetime.utcnow().isoformat()
        }

        # POST to Supabase
        response = await self.http_client.post(
            f"{self.supabase_url}/rest/v1/agent_decisions",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json=record
        )

        response.raise_for_status()

        return decision_id

    async def update_lead_status(self, lead_id: str, decision: Dict[str, Any]):
        """Update lead status in Supabase based on decision"""

        if not self.supabase_url or not self.supabase_key:
            return

        status_map = {
            "qualified": "qualified",
            "rejected": "rejected",
            "marginal": "needs_review"
        }

        update_data = {
            "status": status_map.get(decision["decision"], "needs_review"),
            "pain_score": decision.get("pain_score"),
            "category": decision.get("category"),
            "qualification_method": "claude_agent",
            "qualified_at" if decision["decision"] == "qualified" else "rejected_at": datetime.utcnow().isoformat()
        }

        response = await self.http_client.patch(
            f"{self.supabase_url}/rest/v1/leads?id=eq.{lead_id}",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json"
            },
            json=update_data
        )

        response.raise_for_status()

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Example usage
async def main():
    """Example usage of QualificationValidator"""

    validator = QualificationValidator()

    # Example lead context
    context = {
        "lead_id": "abc-123-def-456",
        "business_name": "Austin Electric",
        "website_url": "https://austinelectric.com",
        "location": "Austin, TX",
        "google_rating": 4.3,
        "google_reviews": 87,
        "preliminary_pain_score": 55,
        "enrichment_data": {
            "tech_stack": ["WordPress", "Google Analytics"],
            "has_crm": False,
            "has_booking": False,
            "visual_score": 42,
            "performance_score": 38,
            "mobile_responsive": False,
            "license_status": "Unknown",
            "bbb_rating": None,
            "reputation_gap": 0
        },
        "pain_signals": [
            "Poor website design",
            "Slow performance",
            "Not mobile responsive",
            "No CRM detected",
            "No booking system"
        ]
    }

    # Standard qualification
    print("Running standard qualification...")
    decision = await validator.qualify_lead(
        lead_id=context["lead_id"],
        context=context,
        mode="standard"
    )

    print(f"\nDecision: {decision['decision']}")
    print(f"Confidence: {decision['confidence']}")
    print(f"Pain Score: {decision.get('pain_score')}")
    print(f"Reasoning: {decision['reasoning'][:200]}...")

    # Council qualification (for marginal leads)
    if decision["decision"] == "marginal" or decision.get("pain_score", 0) < 60:
        print("\n\n--- Running Council Review (Marginal Lead) ---\n")
        council_decision = await validator.qualify_lead(
            lead_id=context["lead_id"],
            context=context,
            mode="council"
        )

        print(f"\nCouncil Decision: {council_decision['decision']}")
        print(f"Council Confidence: {council_decision['confidence']}")
        print(f"Votes: {council_decision['metadata']['qualified_votes']}/4 qualified")
        print(f"\nFull Reasoning:\n{council_decision['reasoning']}")

    await validator.close()


if __name__ == "__main__":
    asyncio.run(main())
