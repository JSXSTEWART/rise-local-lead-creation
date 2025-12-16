"""
Google PageSpeed Insights API Integration
Phase 2B: Technical Scores for Rise Local Lead System

Measures website performance, mobile-friendliness, and SEO basics.
FREE API - no key required for basic usage.

Usage:
    from pagespeed_api import PageSpeedAPI

    api = PageSpeedAPI()
    result = await api.analyze("https://example.com")
    print(result)
"""

import asyncio
import httpx
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google PageSpeed Insights API (free, no key required)
PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


@dataclass
class PageSpeedResult:
    """Result from PageSpeed Insights API"""
    performance_score: int  # 0-100
    mobile_score: int  # 0-100 (mobile-friendliness)
    seo_score: int  # 0-100
    accessibility_score: int  # 0-100
    largest_contentful_paint: float  # seconds
    cumulative_layout_shift: float
    first_input_delay: float  # milliseconds
    has_https: bool
    has_viewport_meta: bool
    url: str
    analysis_date: str = ""
    strategy: str = "mobile"  # mobile or desktop
    error: Optional[str] = None

    def __post_init__(self):
        if not self.analysis_date:
            self.analysis_date = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class PageSpeedAPI:
    """
    Google PageSpeed Insights API client.

    FREE API - measures Core Web Vitals, SEO, and accessibility.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 60):
        """
        Initialize PageSpeed API client.

        Args:
            api_key: Optional API key (not required but increases rate limits)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()

    async def analyze(
        self,
        url: str,
        strategy: str = "mobile",
        categories: Optional[list] = None
    ) -> PageSpeedResult:
        """
        Analyze a website using PageSpeed Insights.

        Args:
            url: Website URL to analyze
            strategy: "mobile" or "desktop"
            categories: List of categories to analyze (default: all)
                       Options: performance, accessibility, best-practices, seo

        Returns:
            PageSpeedResult with scores and metrics
        """
        logger.info(f"Analyzing URL: {url} (strategy: {strategy})")

        if categories is None:
            categories = ["performance", "accessibility", "seo"]

        try:
            # Build request parameters
            params = {
                "url": url,
                "strategy": strategy,
                "category": categories
            }

            if self.api_key:
                params["key"] = self.api_key

            # Make API request
            response = await self._client.get(
                PAGESPEED_API_URL,
                params=params
            )

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except:
                    pass

                return PageSpeedResult(
                    performance_score=0,
                    mobile_score=0,
                    seo_score=0,
                    accessibility_score=0,
                    largest_contentful_paint=0,
                    cumulative_layout_shift=0,
                    first_input_delay=0,
                    has_https=url.startswith("https"),
                    has_viewport_meta=False,
                    url=url,
                    strategy=strategy,
                    error=error_msg
                )

            data = response.json()
            return self._parse_response(data, url, strategy)

        except httpx.TimeoutException:
            logger.error(f"Timeout analyzing {url}")
            return PageSpeedResult(
                performance_score=0,
                mobile_score=0,
                seo_score=0,
                accessibility_score=0,
                largest_contentful_paint=0,
                cumulative_layout_shift=0,
                first_input_delay=0,
                has_https=url.startswith("https"),
                has_viewport_meta=False,
                url=url,
                strategy=strategy,
                error="Request timeout"
            )
        except Exception as e:
            logger.error(f"Error analyzing {url}: {str(e)}")
            return PageSpeedResult(
                performance_score=0,
                mobile_score=0,
                seo_score=0,
                accessibility_score=0,
                largest_contentful_paint=0,
                cumulative_layout_shift=0,
                first_input_delay=0,
                has_https=url.startswith("https"),
                has_viewport_meta=False,
                url=url,
                strategy=strategy,
                error=str(e)
            )

    def _parse_response(self, data: dict, url: str, strategy: str) -> PageSpeedResult:
        """Parse PageSpeed API response"""

        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})

        # Extract category scores (0-1 scale, convert to 0-100)
        def get_score(category: str) -> int:
            cat_data = categories.get(category, {})
            score = cat_data.get("score", 0)
            return int(score * 100) if score else 0

        performance_score = get_score("performance")
        seo_score = get_score("seo")
        accessibility_score = get_score("accessibility")

        # Mobile score is same as performance for mobile strategy
        # For desktop, we need to estimate mobile-friendliness
        if strategy == "mobile":
            mobile_score = performance_score
        else:
            # Check viewport meta audit
            viewport_audit = audits.get("viewport", {})
            has_viewport = viewport_audit.get("score", 0) == 1
            mobile_score = 80 if has_viewport else 40

        # Extract Core Web Vitals
        lcp_audit = audits.get("largest-contentful-paint", {})
        lcp_value = lcp_audit.get("numericValue", 0) / 1000  # Convert ms to seconds

        cls_audit = audits.get("cumulative-layout-shift", {})
        cls_value = cls_audit.get("numericValue", 0)

        fid_audit = audits.get("max-potential-fid", {})
        fid_value = fid_audit.get("numericValue", 0)  # Already in ms

        # Check HTTPS
        is_https = audits.get("is-on-https", {}).get("score", 0) == 1

        # Check viewport meta
        viewport_audit = audits.get("viewport", {})
        has_viewport = viewport_audit.get("score", 0) == 1

        return PageSpeedResult(
            performance_score=performance_score,
            mobile_score=mobile_score,
            seo_score=seo_score,
            accessibility_score=accessibility_score,
            largest_contentful_paint=round(lcp_value, 2),
            cumulative_layout_shift=round(cls_value, 3),
            first_input_delay=round(fid_value, 0),
            has_https=is_https,
            has_viewport_meta=has_viewport,
            url=url,
            strategy=strategy
        )

    async def analyze_both_strategies(self, url: str) -> dict:
        """
        Analyze URL for both mobile and desktop.

        Returns dict with 'mobile' and 'desktop' PageSpeedResults.
        """
        mobile_result, desktop_result = await asyncio.gather(
            self.analyze(url, strategy="mobile"),
            self.analyze(url, strategy="desktop")
        )

        return {
            "mobile": mobile_result.to_dict(),
            "desktop": desktop_result.to_dict()
        }


async def main():
    """Test the API"""

    api = PageSpeedAPI()

    try:
        # Test with a sample URL
        result = await api.analyze("https://www.google.com", strategy="mobile")

        print("\n=== PageSpeed Analysis ===")
        print(f"URL: {result.url}")
        print(f"Strategy: {result.strategy}")
        print(f"Performance Score: {result.performance_score}/100")
        print(f"Mobile Score: {result.mobile_score}/100")
        print(f"SEO Score: {result.seo_score}/100")
        print(f"Accessibility Score: {result.accessibility_score}/100")
        print(f"LCP: {result.largest_contentful_paint}s")
        print(f"CLS: {result.cumulative_layout_shift}")
        print(f"FID: {result.first_input_delay}ms")
        print(f"HTTPS: {result.has_https}")
        print(f"Viewport Meta: {result.has_viewport_meta}")

        if result.error:
            print(f"Error: {result.error}")

    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
