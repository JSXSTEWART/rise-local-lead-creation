"""
TDLR License Scraper for Rise Local Lead System
Phase 2D: License Verification

Searches Texas Department of Licensing and Regulation (TDLR) for electrical contractor licenses.
Extracts owner_name which is CRITICAL for Phase 5 Skip Trace.

Usage:
    from tdlr_scraper import TDLRScraper

    async with TDLRScraper() as scraper:
        result = await scraper.search_by_business_name("Austin Pro Electric")
        print(result)
"""

import asyncio
import re
import unicodedata
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime
import logging

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    raise ImportError("playwright not installed. Run: pip install playwright && playwright install chromium")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TDLR License Search URL
TDLR_SEARCH_URL = "https://www.tdlr.texas.gov/LicenseSearch/"

# Electrician license type code
ELECTRICIAN_LICENSE_TYPE = "ELCTRC"


def normalize_name_for_tdlr(name: str) -> str:
    """
    Normalize name for TDLR search (removes accents and special characters).

    TDLR validation rejects special characters like ñ, á, é, etc.

    Examples:
        "Acuña" → "Acuna"
        "José" → "Jose"
        "García" → "Garcia"

    Args:
        name: Name with potential special characters

    Returns:
        ASCII-normalized name that TDLR will accept
    """
    if not name:
        return name

    # Normalize to NFD (decomposed form) then remove combining marks
    # This converts "ñ" to "n", "á" to "a", etc.
    nfd = unicodedata.normalize('NFD', name)
    ascii_name = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    # Remove any remaining non-ASCII characters
    ascii_name = ascii_name.encode('ascii', 'ignore').decode('ascii')

    return ascii_name


@dataclass
class LicenseResult:
    """Result from TDLR license search"""
    license_status: str  # Active, Expired, Suspended, Not Found
    license_number: Optional[str] = None
    license_type: Optional[str] = None  # Master Electrician, Journeyman, etc.
    owner_name: Optional[str] = None  # CRITICAL: Legal name on license
    business_name: Optional[str] = None
    license_expiry: Optional[str] = None
    violations: int = 0
    city: Optional[str] = None
    state: str = "TX"
    verification_date: str = ""
    raw_data: Optional[dict] = None
    error: Optional[str] = None

    def __post_init__(self):
        if not self.verification_date:
            self.verification_date = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class TDLRScraper:
    """
    Scrapes TDLR license database for electrical contractor verification.

    Provides owner_name extraction which is ESSENTIAL for Phase 5 Skip Trace.
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
        logger.info("Starting TDLR scraper...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self._page = await self._browser.new_page()
        await self._page.set_viewport_size({"width": 1920, "height": 1080})
        # Set a realistic user agent
        await self._page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("TDLR scraper closed")

    async def search_by_business_name(self, business_name: str, city: Optional[str] = None) -> LicenseResult:
        """
        Search TDLR for a business by name.

        Args:
            business_name: Name of the electrical contractor business
            city: Optional city filter (Texas cities only)

        Returns:
            LicenseResult with owner_name and license details
        """
        logger.info(f"Searching TDLR for business: {business_name}")

        try:
            # Navigate to search page
            await self._page.goto(TDLR_SEARCH_URL, wait_until="networkidle", timeout=self.timeout)

            # Wait for page to fully load - SelectStatus is the ID, tdlr_status is the name
            await self._page.wait_for_selector('#SelectStatus', timeout=self.timeout)

            # Select Electricians license type
            await self._page.select_option('#SelectStatus', ELECTRICIAN_LICENSE_TYPE)

            # Wait for endorsement dropdown to populate after license type selection
            await asyncio.sleep(1.5)

            # Enter business name (field name changed from #Name to pht_oth_name)
            name_field = await self._page.query_selector('[name="pht_oth_name"]')
            if name_field:
                await name_field.fill(business_name)

            # Name search type is now "Startswith" by default (no longer configurable dropdown)
            # The "Contains" option was removed from TDLR website

            # Set city filter if provided (field name changed from #City to phy_city)
            if city:
                city_field = await self._page.query_selector('[name="phy_city"]')
                if city_field:
                    # Try to find and select the city
                    try:
                        await self._page.select_option('[name="phy_city"]', city.upper())
                    except:
                        logger.warning(f"Could not select city: {city}")

            # Submit search - use the actual submit button ID
            search_button = await self._page.query_selector("#Submit1")
            if not search_button:
                search_button = await self._page.query_selector("input[type='submit'][value='Search']")

            if search_button:
                await search_button.click()
            else:
                # Fallback: submit form directly via JavaScript
                await self._page.evaluate("document.FormPHT.submit()")

            # Wait for results to load
            await asyncio.sleep(2)
            await self._page.wait_for_load_state("networkidle", timeout=self.timeout)

            # Parse results
            return await self._parse_results(business_name)

        except Exception as e:
            logger.error(f"Error searching TDLR: {str(e)}")
            return LicenseResult(
                license_status="Not Found",
                error=str(e),
                business_name=business_name
            )

    async def search_by_owner_name(self, owner_name: str, city: Optional[str] = None) -> LicenseResult:
        """
        Search TDLR for licenses by owner/individual name.

        Args:
            owner_name: Name of the license holder
            city: Optional city filter

        Returns:
            LicenseResult with license details
        """
        logger.info(f"Searching TDLR for owner: {owner_name}")

        # Same logic as business name search - TDLR searches both
        return await self.search_by_business_name(owner_name, city)

    async def search_with_waterfall(
        self,
        license_number: Optional[str] = None,
        owner_first_name: Optional[str] = None,
        owner_last_name: Optional[str] = None,
        business_name: Optional[str] = None,
        city: Optional[str] = None
    ) -> LicenseResult:
        """
        Waterfall search strategy with redundancy for maximum match rate.

        Search order (stops at first successful match):
        1. License number (most accurate)
        2. Owner name (Last, First format)
        3. Business name (fallback)

        Args:
            license_number: TDLR license number (e.g., "32689" or "TECL #32689")
            owner_first_name: Owner's first name
            owner_last_name: Owner's last name
            business_name: Business name
            city: Optional city filter

        Returns:
            LicenseResult from first successful search method
        """
        logger.info("=== WATERFALL SEARCH START ===")
        logger.info(f"License: {license_number}, Owner: {owner_first_name} {owner_last_name}, Business: {business_name}")

        attempts = []

        # ATTEMPT 1: License Number (Highest Accuracy)
        if license_number:
            # Clean license number - remove "TECL", "#", spaces
            clean_license = re.sub(r'[^\d]', '', license_number)
            if clean_license:
                logger.info(f"🔍 ATTEMPT 1: Searching by license number: {clean_license}")
                result = await self.search_by_license_number(clean_license)
                attempts.append(("license_number", clean_license, result))

                if result.license_status != "Not Found" and result.owner_name:
                    logger.info(f"✅ SUCCESS via license number: {result.owner_name}")
                    result.raw_data = result.raw_data or {}
                    result.raw_data['search_method'] = 'license_number'
                    result.raw_data['attempts'] = len(attempts)
                    return result
                else:
                    logger.warning(f"❌ License search failed or incomplete")

        # ATTEMPT 2: Owner Name (Last, First format)
        if owner_last_name and owner_first_name:
            # Normalize names to remove special characters (ñ → n, á → a, etc.)
            last_normalized = normalize_name_for_tdlr(owner_last_name)
            first_normalized = normalize_name_for_tdlr(owner_first_name)

            # Format: "Last,First" (NO SPACE after comma - TDLR requirement)
            owner_name_formatted = f"{last_normalized},{first_normalized}"
            logger.info(f"🔍 ATTEMPT 2: Searching by owner name: {owner_name_formatted}")
            logger.info(f"   Original: {owner_last_name}, {owner_first_name}")
            logger.info(f"   Normalized: {last_normalized},{first_normalized}")

            result = await self.search_by_owner_name(owner_name_formatted, city)
            attempts.append(("owner_name", owner_name_formatted, result))

            if result.license_status != "Not Found" and result.license_number:
                logger.info(f"✅ SUCCESS via owner name: License {result.license_number}")
                result.raw_data = result.raw_data or {}
                result.raw_data['search_method'] = 'owner_name'
                result.raw_data['attempts'] = len(attempts)
                return result
            else:
                logger.warning(f"❌ Owner name search failed")

        # ATTEMPT 3: Business Name (Fallback)
        if business_name:
            logger.info(f"🔍 ATTEMPT 3: Searching by business name: {business_name}")
            result = await self.search_by_business_name(business_name, city)
            attempts.append(("business_name", business_name, result))

            if result.license_status != "Not Found":
                logger.info(f"✅ SUCCESS via business name")
                result.raw_data = result.raw_data or {}
                result.raw_data['search_method'] = 'business_name'
                result.raw_data['attempts'] = len(attempts)
                return result
            else:
                logger.warning(f"❌ Business name search failed")

        # All attempts failed
        logger.error(f"❌ WATERFALL SEARCH FAILED: All {len(attempts)} attempts unsuccessful")
        return LicenseResult(
            license_status="Not Found",
            business_name=business_name,
            error=f"Not found after {len(attempts)} search attempts",
            raw_data={
                'search_method': 'waterfall_failed',
                'attempts': len(attempts),
                'tried': [a[0] for a in attempts]
            }
        )

    async def search_by_license_number(self, license_number: str) -> LicenseResult:
        """
        Search TDLR by license number (most accurate).

        Args:
            license_number: TDLR license number

        Returns:
            LicenseResult with license details
        """
        logger.info(f"Searching TDLR for license: {license_number}")

        try:
            await self._page.goto(TDLR_SEARCH_URL, wait_until="networkidle", timeout=self.timeout)
            await self._page.wait_for_selector('#SelectStatus', timeout=self.timeout)

            # Select Electricians license type to filter results
            await self._page.select_option('#SelectStatus', ELECTRICIAN_LICENSE_TYPE)
            await asyncio.sleep(1.5)

            # Enter license number
            license_field = await self._page.query_selector('[name="pht_lic"]')
            if license_field:
                await license_field.fill(license_number)

            # Submit search
            search_button = await self._page.query_selector("#Submit1")
            if search_button:
                await search_button.click()
            else:
                await self._page.evaluate("document.FormPHT.submit()")

            await asyncio.sleep(3)  # Increased wait time
            await self._page.wait_for_load_state("networkidle", timeout=self.timeout)

            # Always parse as detail view for license searches (TDLR shows detail page)
            return await self._parse_detail_view(license_number)

        except Exception as e:
            logger.error(f"Error searching by license: {str(e)}")
            return LicenseResult(
                license_status="Not Found",
                license_number=license_number,
                error=str(e)
            )

    async def _parse_results(self, search_term: str) -> LicenseResult:
        """Parse search results from TDLR page"""

        # Check for no results message
        no_results = await self._page.query_selector("text='No records found'")
        if no_results or await self._page.query_selector("text='no results'"):
            return LicenseResult(
                license_status="Not Found",
                business_name=search_term
            )

        # Look for results table
        results_table = await self._page.query_selector("table.results, #results, .searchResults, table")

        if not results_table:
            # Try to get page content for debugging
            content = await self._page.content()
            logger.warning("No results table found")

            # Check if there's a detail view instead of table
            return await self._parse_detail_view(search_term)

        # Parse first result from table
        rows = await results_table.query_selector_all("tr")

        if len(rows) < 2:  # Need at least header + 1 data row
            return LicenseResult(
                license_status="Not Found",
                business_name=search_term
            )

        # Get data from first result row (skip header)
        first_row = rows[1]
        cells = await first_row.query_selector_all("td")

        if not cells:
            return await self._parse_detail_view(search_term)

        # Extract data from cells (order may vary by TDLR's layout)
        cell_texts = []
        for cell in cells:
            text = await cell.inner_text()
            cell_texts.append(text.strip())

        # Parse based on typical TDLR result format
        # Usually: License#, Name, License Type, Status, Expiry, City
        result = LicenseResult(
            license_status="Unknown",
            business_name=search_term
        )

        for i, text in enumerate(cell_texts):
            text_lower = text.lower()

            # Try to identify field by content
            if re.match(r'^\d{8,}$', text):  # License number pattern
                result.license_number = text
            elif 'active' in text_lower:
                result.license_status = "Active"
            elif 'expired' in text_lower:
                result.license_status = "Expired"
            elif 'suspended' in text_lower:
                result.license_status = "Suspended"
            elif 'master' in text_lower or 'journeyman' in text_lower or 'electrical' in text_lower:
                result.license_type = text
            elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):  # Date pattern
                result.license_expiry = text
            elif any(city in text_lower for city in ['austin', 'dallas', 'houston', 'san antonio']):
                result.city = text

        # Try to extract owner name from name field
        # TDLR typically shows: "LAST, FIRST" or "BUSINESS NAME / OWNER NAME"
        if len(cell_texts) > 1:
            name_cell = cell_texts[1]  # Usually second column
            result.owner_name = self._extract_owner_name(name_cell)
            if not result.business_name or result.business_name == search_term:
                result.business_name = name_cell

        result.raw_data = {"cells": cell_texts}
        return result

    async def _parse_detail_view(self, search_term: str) -> LicenseResult:
        """Parse a detail view page instead of results table"""

        result = LicenseResult(
            license_status="Unknown",
            business_name=search_term
        )

        # Look for labeled fields on detail page
        page_text = await self._page.inner_text("body")

        logger.info(f"Parsing detail view, page text length: {len(page_text)}")
        logger.info(f"First 500 chars: {page_text[:500]}")

        # Extract fields using patterns - UPDATED for actual TDLR format
        patterns = {
            "license_number": r'License\s*#?[:.\s]*(\d{5,})',
            "license_status": r'License\s+Status[:.\s]*(Active|Expired|Suspended|Inactive)',
            "license_expiry": r'Expiration\s+Date[:.\s]*(\d{1,2}/\d{1,2}/\d{4})',
            "license_type": r'Type[:.\s]*([A-Z]{2,})',
            "city": r'County[:.\s]*([A-Z][A-Za-z\s]+)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                setattr(result, field, value)
                logger.info(f"Extracted {field}: {value}")

        # Extract business name (first line of Name and Location section)
        business_match = re.search(r'Name and Location\s+Other Information\s+([^\n]+)', page_text)
        if business_match:
            result.business_name = business_match.group(1).strip()
            logger.info(f"Extracted business_name: {result.business_name}")

        # Extract master electrician name (format: "Master: LAST, FIRST")
        master_match = re.search(r'Master:\s*([A-Z][A-Z\s,]+)', page_text)
        if master_match:
            master_name = master_match.group(1).strip()
            result.owner_name = self._extract_owner_name(master_name)
            logger.info(f"Extracted owner_name from Master: {result.owner_name}")

        # Check for contractor license information (dual license scenario)
        # Pattern: "This licensee is the designated master for:"
        #          "Electrical Contractor: ACL ELECTRIC LLC"
        #          "License #: 32689"
        contractor_match = re.search(
            r'designated\s+master\s+for:.*?Electrical\s+Contractor:\s*([^\n]+).*?License\s*#:\s*(\d+)',
            page_text,
            re.IGNORECASE | re.DOTALL
        )

        if contractor_match:
            contractor_business = contractor_match.group(1).strip()
            contractor_license = contractor_match.group(2).strip()

            logger.info(f"Found contractor license: {contractor_business} (License #{contractor_license})")

            # Store both licenses in raw_data for reference
            result.raw_data = result.raw_data or {}
            result.raw_data['personal_license'] = result.license_number
            result.raw_data['contractor_license'] = contractor_license
            result.raw_data['contractor_business'] = contractor_business

            # Update business name if found
            if contractor_business:
                result.business_name = contractor_business

        if result.license_number or result.owner_name:
            if result.license_status == "Unknown":
                if "active" in page_text.lower():
                    result.license_status = "Active"
        else:
            result.license_status = "Not Found"

        return result

    def _extract_owner_name(self, name_field: str) -> Optional[str]:
        """Extract owner name from TDLR name field"""

        if not name_field:
            return None

        # TDLR often shows names as "LAST, FIRST MIDDLE" or "BUSINESS / OWNER"
        name = name_field.strip()

        # If contains slash, owner might be after it
        if '/' in name:
            parts = name.split('/')
            name = parts[-1].strip()  # Take last part as owner

        # Convert "LAST, FIRST" to "FIRST LAST"
        if ',' in name:
            parts = name.split(',')
            if len(parts) == 2:
                last = parts[0].strip()
                first = parts[1].strip()
                name = f"{first} {last}"

        # Title case
        name = ' '.join(word.capitalize() for word in name.split())

        return name if name else None


async def main():
    """Test the scraper"""

    # Example usage
    async with TDLRScraper(headless=True) as scraper:
        # Test search by business name
        result = await scraper.search_by_business_name("Austin Electric")
        print("\n=== Search by Business Name ===")
        print(f"Status: {result.license_status}")
        print(f"Owner Name: {result.owner_name}")
        print(f"License #: {result.license_number}")
        print(f"License Type: {result.license_type}")
        print(f"Expiry: {result.license_expiry}")
        print(f"City: {result.city}")

        if result.error:
            print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
