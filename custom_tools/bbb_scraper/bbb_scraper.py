"""
BBB Scraper for Rise Local Lead System
Phase 2E: Reputation Analysis

Scrapes Better Business Bureau for business reputation data.
Calculates reputation_gap between Google rating and BBB implied rating.

Usage:
    from bbb_scraper import BBBScraper

    async with BBBScraper() as scraper:
        result = await scraper.search_business("Austin Pro Electric", "Austin", "TX")
        print(result)
"""

import asyncio
import re
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
import logging

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    raise ImportError("playwright not installed. Run: pip install playwright && playwright install chromium")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BBB Search URL
BBB_SEARCH_URL = "https://www.bbb.org/search"


@dataclass
class BBBResult:
    """Result from BBB search"""
    bbb_rating: str  # A+, A, B, C, D, F, NR (Not Rated)
    bbb_accredited: bool
    complaints_total: int
    complaints_3yr: int  # Last 3 years
    complaints_resolved: int
    reputation_gap: float  # Google rating - BBB implied rating
    years_in_business: Optional[int] = None
    business_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    bbb_url: Optional[str] = None
    verification_date: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        if not self.verification_date:
            self.verification_date = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


# BBB rating to numeric score mapping
BBB_RATING_SCORES = {
    "A+": 4.5,
    "A": 4.0,
    "A-": 3.7,
    "B+": 3.5,
    "B": 3.0,
    "B-": 2.7,
    "C+": 2.5,
    "C": 2.0,
    "C-": 1.7,
    "D+": 1.5,
    "D": 1.0,
    "D-": 0.7,
    "F": 0.5,
    "NR": 2.5  # Not Rated - assume neutral
}


def calculate_reputation_gap(google_rating: float, bbb_rating: str) -> float:
    """
    Calculate the gap between Google rating and BBB implied rating.
    Positive gap = Google better than BBB suggests (potential red flag)
    Negative gap = BBB better than Google (less concern)
    """
    bbb_score = BBB_RATING_SCORES.get(bbb_rating.upper(), 2.5)
    return round(google_rating - bbb_score, 2)


class BBBScraper:
    """
    Scrapes Better Business Bureau for reputation data.

    Extracts ratings, complaints, and accreditation status.
    """

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize browser"""
        logger.info("Starting BBB scraper...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self._page = await self._browser.new_page()
        await self._page.set_viewport_size({"width": 1920, "height": 1080})
        await self._page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("BBB scraper closed")

    async def search_business(
        self,
        business_name: str,
        city: str,
        state: str = "TX",
        google_rating: float = 0.0
    ) -> BBBResult:
        """
        Search BBB for a business.

        Args:
            business_name: Name of the business
            city: City name
            state: State code (default: TX)
            google_rating: Google rating for reputation gap calculation

        Returns:
            BBBResult with reputation data
        """
        logger.info(f"Searching BBB for: {business_name} in {city}, {state}")

        try:
            # Build search URL
            search_query = f"{business_name} {city} {state}"
            search_url = f"{BBB_SEARCH_URL}?find_country=USA&find_text={search_query.replace(' ', '%20')}&find_type=Category"

            # Navigate to search
            await self._page.goto(search_url, wait_until="networkidle", timeout=self.timeout)

            # Wait for results to load
            await asyncio.sleep(2)

            # Look for search results
            results = await self._page.query_selector_all('[data-testid="search-result"], .search-result, .result-item')

            if not results:
                # Try alternative selectors
                results = await self._page.query_selector_all('a[href*="/us/"][href*="/profile/"]')

            if not results:
                logger.info(f"No BBB listing found for: {business_name}")
                return BBBResult(
                    bbb_rating="NR",
                    bbb_accredited=False,
                    complaints_total=0,
                    complaints_3yr=0,
                    complaints_resolved=0,
                    reputation_gap=calculate_reputation_gap(google_rating, "NR"),
                    business_name=business_name,
                    city=city,
                    state=state,
                    error="No BBB listing found"
                )

            # Click first result to get details
            first_result = results[0]
            profile_link = await first_result.get_attribute("href")

            if profile_link:
                if not profile_link.startswith("http"):
                    profile_link = f"https://www.bbb.org{profile_link}"
                await self._page.goto(profile_link, wait_until="networkidle", timeout=self.timeout)
            else:
                await first_result.click()
                await asyncio.sleep(2)
                await self._page.wait_for_load_state("networkidle", timeout=self.timeout)

            # Parse business profile
            return await self._parse_profile(business_name, city, state, google_rating)

        except Exception as e:
            logger.error(f"Error searching BBB: {str(e)}")
            return BBBResult(
                bbb_rating="NR",
                bbb_accredited=False,
                complaints_total=0,
                complaints_3yr=0,
                complaints_resolved=0,
                reputation_gap=calculate_reputation_gap(google_rating, "NR"),
                business_name=business_name,
                city=city,
                state=state,
                error=str(e)
            )

    async def _parse_profile(
        self,
        business_name: str,
        city: str,
        state: str,
        google_rating: float
    ) -> BBBResult:
        """Parse BBB business profile page"""

        result = BBBResult(
            bbb_rating="NR",
            bbb_accredited=False,
            complaints_total=0,
            complaints_3yr=0,
            complaints_resolved=0,
            reputation_gap=0.0,
            business_name=business_name,
            city=city,
            state=state,
            bbb_url=self._page.url
        )

        page_text = await self._page.inner_text("body")

        # Extract BBB Rating
        # Look for rating badge or text
        rating_patterns = [
            r'BBB\s*Rating[:\s]*([A-F][+-]?)',
            r'Rating[:\s]*([A-F][+-]?)',
            r'grade["\s:]*([A-F][+-]?)',
            r'bbb-rating["\s:]*([A-F][+-]?)'
        ]

        for pattern in rating_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                result.bbb_rating = match.group(1).upper()
                break

        # Check if rating element exists with specific class
        rating_element = await self._page.query_selector('[class*="rating"], [class*="grade"], .bbb-rating')
        if rating_element:
            rating_text = await rating_element.inner_text()
            rating_match = re.search(r'([A-F][+-]?)', rating_text)
            if rating_match:
                result.bbb_rating = rating_match.group(1).upper()

        # Check accreditation status
        accreditation_indicators = [
            "BBB Accredited",
            "Accredited Business",
            "accredited-seal",
            "is accredited"
        ]

        for indicator in accreditation_indicators:
            if indicator.lower() in page_text.lower():
                result.bbb_accredited = True
                break

        # Also check for accreditation badge
        accred_badge = await self._page.query_selector('[class*="accredited"], [alt*="Accredited"]')
        if accred_badge:
            result.bbb_accredited = True

        # Extract complaints
        complaint_patterns = [
            r'(\d+)\s*(?:total\s*)?complaints?\s*(?:in\s*last\s*3\s*years?|closed)',
            r'Complaints?\s*(?:Closed|Filed)?[:\s]*(\d+)',
            r'(\d+)\s*complaints?\s*closed'
        ]

        for pattern in complaint_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                if "3 year" in pattern.lower() or "last 3" in page_text.lower():
                    result.complaints_3yr = count
                else:
                    result.complaints_total = count
                break

        # If we found 3yr complaints but not total, estimate total
        if result.complaints_3yr > 0 and result.complaints_total == 0:
            result.complaints_total = result.complaints_3yr

        # Extract resolved complaints
        resolved_match = re.search(r'(\d+)\s*(?:complaints?\s*)?resolved', page_text, re.IGNORECASE)
        if resolved_match:
            result.complaints_resolved = int(resolved_match.group(1))

        # Extract years in business
        years_patterns = [
            r'(?:In\s*Business|Years?\s*in\s*Business)[:\s]*(\d+)\s*years?',
            r'(\d+)\s*years?\s*in\s*business',
            r'Business\s*Started[:\s]*(\d{4})'
        ]

        for pattern in years_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                if len(value) == 4:  # Year started
                    result.years_in_business = datetime.now().year - int(value)
                else:
                    result.years_in_business = int(value)
                break

        # Calculate reputation gap
        result.reputation_gap = calculate_reputation_gap(google_rating, result.bbb_rating)

        return result


async def main():
    """Test the scraper"""

    async with BBBScraper(headless=True) as scraper:
        result = await scraper.search_business(
            business_name="Austin Electric",
            city="Austin",
            state="TX",
            google_rating=4.2
        )

        print("\n=== BBB Search Results ===")
        print(f"BBB Rating: {result.bbb_rating}")
        print(f"Accredited: {result.bbb_accredited}")
        print(f"Complaints (3yr): {result.complaints_3yr}")
        print(f"Complaints (total): {result.complaints_total}")
        print(f"Years in Business: {result.years_in_business}")
        print(f"Reputation Gap: {result.reputation_gap}")
        print(f"BBB URL: {result.bbb_url}")

        if result.error:
            print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
