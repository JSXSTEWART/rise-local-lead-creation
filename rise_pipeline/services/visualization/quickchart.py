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


class QuickChartClient:
    """QuickChart.io for generating chart images"""

    BASE_URL = "https://quickchart.io/chart"

    async def generate_chart(
        self,
        chart_config: Dict[str, Any],
        width: int = 500,
        height: int = 300,
        format: str = "png",
        background_color: str = "white"
    ) -> Optional[str]:
        """
        Generate a chart image URL from Chart.js config.

        Returns the image URL or None on failure.
        """
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            try:
                resp = await client.post(
                    self.BASE_URL,
                    json={
                        "chart": chart_config,
                        "width": width,
                        "height": height,
                        "format": format,
                        "backgroundColor": background_color
                    }
                )
                if resp.status_code == 200:
                    # POST returns the image directly, use GET URL for shareable link
                    return self._build_url(chart_config, width, height, background_color)
            except Exception as e:
                print(f"  QuickChart error: {e}")
        return None

    def _build_url(
        self,
        chart_config: Dict[str, Any],
        width: int,
        height: int,
        background_color: str
    ) -> str:
        """Build a shareable chart URL."""
        import urllib.parse
        config_str = json.dumps(chart_config)
        encoded = urllib.parse.quote(config_str)
        return f"{self.BASE_URL}?c={encoded}&w={width}&h={height}&bkg={background_color}"

    async def pain_score_gauge(self, score: int, business_name: str) -> Optional[str]:
        """Generate a pain score gauge chart."""
        config = {
            "type": "gauge",
            "data": {
                "datasets": [{
                    "value": score,
                    "minValue": 0,
                    "maxValue": 100,
                    "data": [30, 50, 70, 100],
                    "backgroundColor": ["#4ade80", "#facc15", "#fb923c", "#ef4444"]
                }]
            },
            "options": {
                "title": {
                    "display": True,
                    "text": f"Pain Score: {business_name}"
                }
            }
        }
        return await self.generate_chart(config, width=400, height=300)

    async def score_comparison_bar(
        self,
        labels: list,
        scores: list,
        title: str = "Score Comparison"
    ) -> Optional[str]:
        """Generate a bar chart comparing scores."""
        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Score",
                    "data": scores,
                    "backgroundColor": [
                        "#3b82f6", "#8b5cf6", "#ec4899", "#f97316", "#22c55e"
                    ]
                }]
            },
            "options": {
                "title": {"display": True, "text": title},
                "scales": {"yAxes": [{"ticks": {"beginAtZero": True, "max": 100}}]}
            }
        }
        return await self.generate_chart(config, width=600, height=400)

    async def pipeline_funnel(
        self,
        stages: list,
        counts: list,
        title: str = "Pipeline Funnel"
    ) -> Optional[str]:
        """Generate a funnel chart for pipeline stages."""
        config = {
            "type": "horizontalBar",
            "data": {
                "labels": stages,
                "datasets": [{
                    "data": counts,
                    "backgroundColor": [
                        "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#d946ef"
                    ]
                }]
            },
            "options": {
                "title": {"display": True, "text": title},
                "legend": {"display": False},
                "scales": {"xAxes": [{"ticks": {"beginAtZero": True}}]}
            }
        }
        return await self.generate_chart(config, width=500, height=300)

    async def tech_stack_radar(
        self,
        categories: list,
        scores: list,
        title: str = "Tech Stack Analysis"
    ) -> Optional[str]:
        """Generate a radar chart for tech stack analysis."""
        config = {
            "type": "radar",
            "data": {
                "labels": categories,
                "datasets": [{
                    "label": "Score",
                    "data": scores,
                    "backgroundColor": "rgba(59, 130, 246, 0.2)",
                    "borderColor": "#3b82f6",
                    "pointBackgroundColor": "#3b82f6"
                }]
            },
            "options": {
                "title": {"display": True, "text": title},
                "scale": {"ticks": {"beginAtZero": True, "max": 100}}
            }
        }
        return await self.generate_chart(config, width=500, height=500)
