"""
Website Owner Extractor Service
Phase 2D-Enhanced: Extract owner name and license from website

Two-Stage Pipeline:
1. Google Cloud Vision API - OCR text extraction from screenshots
2. Google Gemini 1.5 Flash - Intelligent parsing of extracted text

This data can then be used to lookup TDLR license with actual owner name.
"""

import asyncio
import base64
import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime
import logging

try:
    from playwright.async_api import async_playwright, Browser
except ImportError:
    raise ImportError("playwright not installed. Run: pip install playwright && playwright install chromium")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logging.warning("httpx not installed")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logging.warning("beautifulsoup4 not installed")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("google-generativeai not installed")

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Explicitly set level for this logger


@dataclass
class OwnerExtractionResult:
    """Result from owner extraction"""
    owner_first_name: Optional[str] = None
    owner_last_name: Optional[str] = None
    owner_full_name: Optional[str] = None
    license_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    confidence: str = "low"  # low, medium, high
    extraction_method: str = "vision"  # vision, dom, both, about_page, homepage_fallback, both_pages
    pages_analyzed: list = None  # List of pages analyzed: ["about", "homepage"]
    url: str = ""
    analysis_date: str = ""
    error: Optional[str] = None

    def __post_init__(self):
        if not self.analysis_date:
            self.analysis_date = datetime.now().isoformat()
        if self.pages_analyzed is None:
            self.pages_analyzed = []

    def to_dict(self) -> dict:
        return asdict(self)


class OwnerExtractorService:
    """
    Extracts owner information from websites using agentic multi-method approach:

    Primary Method: Jina Reader API (fast, reliable text extraction)
    Fallback Method: Playwright screenshots (for visual-only content)
    Parsing: Google Gemini 2.5 Flash (intelligent owner/TECL extraction)

    Strategy:
    1. Find homepage + about page URLs (via link discovery)
    2. Extract text using Jina Reader API (1-2 seconds, works on slow sites)
    3. Parse text with Gemini to find owner name + TECL license
    4. Waterfall fallback: about page → homepage → visual analysis
    5. DOM scraping for contact info (email/phone)
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 90000,
        google_api_key: Optional[str] = None
    ):
        self.headless = headless
        self.timeout = timeout
        self.google_api_key = google_api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        self._playwright = None
        self._browser: Optional[Browser] = None

        # Initialize HTTP client for Jina Reader
        self._http_client = httpx.AsyncClient(timeout=30.0) if HTTPX_AVAILABLE else None

        # Initialize Gemini for parsing
        if GEMINI_AVAILABLE and self.google_api_key:
            try:
                genai.configure(api_key=self.google_api_key)
                # Use gemini-2.5-flash for text parsing
                self._gemini_model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception as e:
                logger.warning(f"Gemini initialization failed: {str(e)}")
                self._gemini_model = None
        else:
            self._gemini_model = None
            logger.warning("Gemini API not available - owner extraction will be limited")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize browser"""
        logger.info("Starting Owner Extractor Service...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

    async def close(self):
        """Close browser and HTTP client"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        if self._http_client:
            await self._http_client.aclose()
        logger.info("Owner Extractor Service closed")

    async def extract_owner_info(self, url: str) -> OwnerExtractionResult:
        """
        Extract owner information from website using agentic multi-method approach.

        Primary: Jina Reader API for fast, reliable text extraction
        Fallback: Playwright screenshots for visual-only content

        Args:
            url: Website URL to analyze

        Returns:
            OwnerExtractionResult with extracted owner data
        """
        logger.info(f"🚀 Extracting owner info from: {url}")

        result = OwnerExtractionResult(url=url)

        try:
            # STEP 1: Find about page URL (fast HTML crawl)
            about_url = await self._find_about_page_url(url)

            # STEP 2: Extract text with Jina Reader (PRIMARY METHOD)
            extracted_texts = {}

            # Try about page first (if found)
            if about_url:
                logger.info("=== EXTRACTING TEXT FROM ABOUT PAGE (PRIMARY - Jina Reader) ===")
                about_text = await self._extract_text_with_jina(about_url)
                if about_text:
                    extracted_texts["about"] = about_text
                    result.pages_analyzed.append("about")

            # Always try homepage (for fallback or if no about page)
            logger.info("=== EXTRACTING TEXT FROM HOMEPAGE (Jina Reader) ===")
            homepage_text = await self._extract_text_with_jina(url)
            if homepage_text:
                extracted_texts["homepage"] = homepage_text
                if "homepage" not in result.pages_analyzed:
                    result.pages_analyzed.append("homepage")

            # STEP 3: Parse extracted text with Gemini (WATERFALL STRATEGY)
            if extracted_texts:
                # STEP 3A: Try about page first
                if "about" in extracted_texts:
                    logger.info("=== PARSING ABOUT PAGE TEXT (Gemini) ===")
                    about_extraction = await self._parse_with_gemini(
                        {"about": extracted_texts["about"]},
                        page_type="about"
                    )
                    if about_extraction:
                        logger.info(f"About page extraction: {about_extraction}")
                        result.owner_first_name = about_extraction.get("owner_first_name")
                        result.owner_last_name = about_extraction.get("owner_last_name")
                        result.owner_full_name = about_extraction.get("owner_full_name")
                        result.license_number = about_extraction.get("license_number")
                        result.confidence = about_extraction.get("confidence", "low")
                        result.extraction_method = "jina_about"

                # STEP 3B: Homepage fallback (if data missing)
                needs_homepage_fallback = (
                    not result.owner_full_name or
                    not result.license_number
                )

                if needs_homepage_fallback and "homepage" in extracted_texts:
                    logger.info("=== PARSING HOMEPAGE TEXT (Gemini - fallback) ===")
                    homepage_extraction = await self._parse_with_gemini(
                        {"homepage": extracted_texts["homepage"]},
                        page_type="homepage"
                    )
                    if homepage_extraction:
                        logger.info(f"Homepage extraction: {homepage_extraction}")

                        # Merge results - fill in missing fields only
                        if not result.owner_first_name:
                            result.owner_first_name = homepage_extraction.get("owner_first_name")
                        if not result.owner_last_name:
                            result.owner_last_name = homepage_extraction.get("owner_last_name")
                        if not result.owner_full_name:
                            result.owner_full_name = homepage_extraction.get("owner_full_name")
                        if not result.license_number:
                            result.license_number = homepage_extraction.get("license_number")

                        # Update extraction method
                        if result.extraction_method == "jina_about":
                            result.extraction_method = "jina_both"
                        else:
                            result.extraction_method = "jina_homepage"

                        # Adjust confidence
                        if result.owner_full_name and result.license_number:
                            result.confidence = "high" if result.extraction_method == "jina_about" else "medium"
                        else:
                            result.confidence = "low"

            else:
                logger.warning("❌ Jina Reader failed to extract text from any page")
                result.error = "Text extraction failed"
                result.extraction_method = "failed"

            # STEP 4: DOM scraping for contact info (DISABLED - causes timeouts on slow sites)
            # TODO: Re-enable once we have a faster method for contact extraction
            # dom_data = await self._scrape_contact_from_dom(url)
            # if dom_data:
            #     if not result.email and dom_data.get("email"):
            #         result.email = dom_data["email"]
            #     if not result.phone and dom_data.get("phone"):
            #         result.phone = dom_data["phone"]

        except Exception as e:
            logger.error(f"❌ Error extracting owner info from {url}: {str(e)}")
            result.error = str(e)

        logger.info(f"✅ Extraction complete: method={result.extraction_method}, confidence={result.confidence}")
        return result

    async def _capture_key_pages(self, base_url: str) -> Dict[str, bytes]:
        """
        Capture screenshots of BOTH homepage AND about page for comprehensive analysis.

        Homepage: Used by aesthetics analyzer + owner extractor fallback
        About page: Primary source for owner name + TECL license

        Returns dict with page_name -> screenshot_bytes
        """
        screenshots = {}
        page = await self._browser.new_page()

        try:
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            # STEP 1: Capture HOMEPAGE (full page with scroll)
            try:
                await page.goto(base_url, wait_until="networkidle", timeout=self.timeout)
                await asyncio.sleep(2)

                # Scroll to bottom to trigger lazy-loaded content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)  # Wait for lazy-load

                # Scroll back to top for clean screenshot
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)

                # Capture full page
                screenshots["homepage"] = await page.screenshot(type="png", full_page=True)
                logger.info(f"Captured homepage screenshot (full page with scroll)")
            except Exception as e:
                logger.warning(f"Could not capture homepage: {str(e)}")

            # STEP 2: Find and capture ABOUT page (primary source for owner info)
            about_keywords = [
                "about", "about-us", "aboutus", "about us",
                "team", "our-team", "ourteam", "our team", "meet-the-team", "meet the team",
                "company", "our-company", "the-company",
                "who-we-are", "who we are",
                "leadership", "management",
                "staff", "our-staff",
                "people", "our-people"
            ]

            about_links = await self._find_page_links(page, about_keywords)
            if about_links:
                # Capture the FIRST about page found (most likely to have owner info)
                try:
                    link = about_links[0]
                    logger.info(f"Found about page link: {link}")
                    await page.goto(link, wait_until="networkidle", timeout=self.timeout)
                    await asyncio.sleep(2)

                    # Scroll to bottom to trigger lazy-loaded content
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                    # Scroll back to top
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(1)

                    # Capture full page
                    screenshots["about"] = await page.screenshot(type="png", full_page=True)
                    logger.info(f"Captured about page screenshot (full page with scroll): {link}")
                except Exception as e:
                    logger.warning(f"Could not capture about page: {str(e)}")
            else:
                logger.warning(f"No about/team pages found on {base_url}")

        finally:
            await page.close()

        return screenshots

    async def _find_page_links(self, page, keywords: list) -> list:
        """Find links matching keywords (case-insensitive)"""
        try:
            links = await page.query_selector_all("a[href]")
            found = []

            for link in links:
                href = await link.get_attribute("href")
                text = await link.inner_text()

                if not href:
                    continue

                # Check if href or text contains any keyword
                href_lower = href.lower()
                text_lower = text.lower() if text else ""

                for keyword in keywords:
                    if keyword in href_lower or keyword in text_lower:
                        # Convert relative URL to absolute
                        if href.startswith("/"):
                            href = f"{page.url.rstrip('/')}{href}"
                        elif not href.startswith("http"):
                            href = f"{page.url.rstrip('/')}/{href}"

                        if href not in found:
                            found.append(href)
                        break

            return found
        except:
            return []

    async def _extract_text_with_jina(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        Extract text from URL using Jina Reader API (fast, reliable).

        Jina Reader converts any webpage to clean markdown text instantly.
        Works on slow sites, JavaScript-heavy sites, and handles most edge cases.

        Args:
            url: URL to extract text from
            max_retries: Maximum number of retry attempts for 503 errors

        Returns:
            Clean markdown text, or None if extraction fails
        """
        if not self._http_client:
            logger.warning("HTTP client not available for Jina Reader")
            return None

        import asyncio

        for attempt in range(max_retries):
            try:
                # Jina Reader API endpoint
                jina_url = f"https://r.jina.ai/{url}"

                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time}s delay")
                    await asyncio.sleep(wait_time)

                logger.info(f"Extracting text with Jina Reader: {url}")

                # Make request to Jina Reader
                response = await self._http_client.get(jina_url, follow_redirects=True)
                response.raise_for_status()

                # Get markdown text
                text = response.text.strip()

                # Validation
                if len(text) < 50:
                    logger.warning(f"Jina extraction too short ({len(text)} chars): {url}")
                    return None

                logger.info(f"Jina extracted {len(text)} characters from {url}")
                return text

            except Exception as e:
                # Check if it's a 503 (rate limit/temporary issue) - retry
                is_503 = "503" in str(e) or "Service Unavailable" in str(e)

                if is_503 and attempt < max_retries - 1:
                    logger.warning(f"Jina Reader 503 error for {url}, will retry...")
                    continue
                else:
                    logger.error(f"Jina Reader error for {url}: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return None

        return None

    async def _find_about_page_url(self, base_url: str) -> Optional[str]:
        """
        Find the about page URL by crawling homepage links.

        Uses BeautifulSoup to quickly parse homepage HTML and find about links.
        Much faster than Playwright for simple link discovery.

        Args:
            base_url: Homepage URL

        Returns:
            About page URL if found, None otherwise
        """
        if not self._http_client or not BS4_AVAILABLE:
            logger.warning("HTTP client or BeautifulSoup not available")
            return None

        try:
            logger.info(f"Searching for about page on {base_url}")

            # Fetch homepage HTML
            response = await self._http_client.get(base_url, follow_redirects=True)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # About page keywords
            about_keywords = [
                "about", "about-us", "aboutus", "about us",
                "team", "our-team", "ourteam", "our team",
                "company", "our-company",
                "who-we-are", "who we are",
                "leadership", "management",
                "staff", "people"
            ]

            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                text = link.get_text().lower().strip()

                # Check if link matches about keywords
                for keyword in about_keywords:
                    if keyword in href or keyword in text:
                        # Convert relative URL to absolute
                        if href.startswith('/'):
                            about_url = f"{base_url.rstrip('/')}{link['href']}"
                        elif not href.startswith('http'):
                            about_url = f"{base_url.rstrip('/')}/{link['href']}"
                        else:
                            about_url = link['href']

                        logger.info(f"Found about page: {about_url}")
                        return about_url

            logger.warning(f"No about page found on {base_url}")
            return None

        except Exception as e:
            logger.error(f"Error finding about page: {str(e)}")
            return None

    async def _extract_text_from_screenshots(self, screenshots: Dict[str, bytes]) -> Dict[str, str]:
        """
        Stage 1: Extract text from screenshots using Gemini Vision (OCR).

        Args:
            screenshots: Dict of page_name -> screenshot_bytes

        Returns:
            Dict of page_name -> extracted_text
        """
        if not self._gemini_model:
            logger.warning("Gemini API not available for OCR")
            return {}

        extracted_texts = {}

        for page_name, screenshot_bytes in screenshots.items():
            try:
                # Convert screenshot to base64 for Gemini
                import PIL.Image
                import io

                # Load image from bytes
                image = PIL.Image.open(io.BytesIO(screenshot_bytes))

                # OCR Prompt for Gemini
                ocr_prompt = """Extract ALL text from this image exactly as it appears.

Preserve the natural reading order (top to bottom, left to right).
Include ALL visible text: headings, paragraphs, buttons, labels, footer text, etc.
Do NOT summarize or interpret - just extract the raw text.
Separate sections with newlines to preserve structure.

Return ONLY the extracted text, no other commentary."""

                # Call Gemini for OCR
                response = self._gemini_model.generate_content(
                    [ocr_prompt, image],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        max_output_tokens=4096,  # Longer output for full page text
                    )
                )

                text = response.text.strip()

                # Optimization: Check if text is too short (< 50 chars)
                if len(text) < 50:
                    logger.info(f"Skipping {page_name} - insufficient text ({len(text)} chars)")
                    continue

                # Clean up excessive newlines
                text = re.sub(r'\n{3,}', '\n\n', text)

                extracted_texts[page_name] = text
                logger.info(f"Extracted {len(text)} characters from {page_name}")

            except Exception as e:
                logger.error(f"Gemini OCR error for {page_name}: {str(e)}")
                continue

        return extracted_texts

    async def _parse_with_gemini(self, extracted_texts: Dict[str, str], page_type: str = "about") -> Optional[dict]:
        """
        Stage 2: Parse extracted text using Gemini 2.5 Flash.

        Args:
            extracted_texts: Dict of page_name -> text_content
            page_type: Type of page being analyzed ("about" or "homepage")

        Returns:
            Dict with extracted owner information
        """
        if not self._gemini_model:
            return None

        response_text = ""  # Initialize outside try block for error logging
        try:
            # Combine all text from all pages
            combined_text = "\n\n---PAGE BREAK---\n\n".join([
                f"=== {page_name.upper()} ===\n{text}"
                for page_name, text in extracted_texts.items()
            ])

            # Customize prompt based on page type
            if page_type == "about":
                context_note = "This is an ABOUT US / TEAM page. Owner information should be clearly visible with job titles and possibly photos."
                confidence_guidance = """
**Confidence Levels:**
- "high": Explicitly states "Owner: John Smith" or "President: John Smith" AND license number found
- "medium": Name found with title OR license found separately
- "low": Uncertain or minimal information"""
            else:  # homepage
                context_note = "This is a HOMEPAGE. Owner information may be in the footer, header, or scattered throughout. Older/dated websites often show this info prominently."
                confidence_guidance = """
**Confidence Levels:**
- "high": Explicitly states "Owner: John Smith" AND license number found
- "medium": Name found OR license found (but not both)
- "low": Uncertain or minimal information"""

            # Gemini System Prompt (optimized for electrical contractors)
            prompt = f"""You are a data extraction specialist. Your job is to analyze text from an electrical contractor's website and extract specific business details.

**Context:** {context_note}

**Rules:**
1. **Owner Name:** Look for titles like President, Founder, Owner, Master Electrician, CEO, Principal. Extract the full name associated with these titles. If multiple names exist, prioritize "Owner" or "President".
2. **Electrical License Number:** Look for Texas electrical contractor license patterns:
   - TECL followed by 4-6 digits (e.g., "TECL 12345", "TECL# 123456", "TECL #123456")
   - "License #" or "Lic #" or "Lic#" followed by 4-6 digits
   - "Master Electrician License" followed by numbers
   - "EC" followed by numbers (Electrical Contractor)
   - Extract the FULL number including prefix (e.g., "TECL 123456" not just "123456")
3. **Output:** Return ONLY a valid JSON object. If a value is not found, return `null`.

**JSON Schema:**
{{{{
  "owner_first_name": "string or null",
  "owner_last_name": "string or null",
  "owner_full_name": "string or null (full name if found)",
  "license_number": "string or null (with prefix, e.g. 'TECL 123456')",
  "confidence_score": "low/medium/high"
}}}}

{confidence_guidance}

**Important:**
- Extract ONLY what you can clearly identify in the text
- Use null for any field you cannot find
- For names, extract both first_name and last_name separately if possible
- Do NOT confuse general business licenses with electrical contractor licenses
- Look for context around the name (job title, description) to confirm they are the owner
- TECL licenses are 6 digits - make sure to extract the full number

**Text to analyze:**

{{text}}

**Respond ONLY with the JSON object, no other text.**"""

            # Call Gemini API with temperature=0 for determinism
            logger.info("Calling Gemini API for parsing...")
            response = self._gemini_model.generate_content(
                prompt.format(text=combined_text),
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=1024,
                )
            )
            logger.info(f"Gemini API call completed. Response type: {type(response)}")

            # Parse JSON response
            response_text = response.text.strip()
            logger.info(f"Raw Gemini response (first 500 chars): {response_text[:500]}")

            # Extract JSON from response (handle markdown code blocks and extra text)
            if "```json" in response_text or "```" in response_text:
                # Find the JSON object within code blocks
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    response_text = response_text[json_start:json_end]
            else:
                # No code blocks, try to extract JSON object directly
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    response_text = response_text[json_start:json_end]

            # Final cleanup and parse
            response_text = response_text.strip()
            logger.info(f"Attempting to parse JSON: {response_text[:200]}...")  # Log first 200 chars
            result = json.loads(response_text)

            # Rename confidence_score to confidence for consistency
            if "confidence_score" in result:
                result["confidence"] = result.pop("confidence_score")

            logger.info(f"Gemini extraction result: {result}")

            return result

        except Exception as e:
            import traceback
            logger.error(f"Gemini parsing error: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if response_text:
                logger.error(f"Failed to parse text: {response_text[:500]}")  # Log first 500 chars
            return None

    async def _scrape_contact_from_dom(self, url: str) -> Optional[dict]:
        """Scrape email and phone from DOM as backup"""
        page = await self._browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)

            # Get page HTML
            html = await page.content()

            # Extract email with regex
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, html)

            # Extract phone with regex (US format)
            phone_pattern = r'\(?\\d{3}\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}'
            phones = re.findall(phone_pattern, html)

            return {
                "email": emails[0] if emails else None,
                "phone": phones[0] if phones else None
            }

        except Exception as e:
            logger.warning(f"DOM scraping error: {str(e)}")
            return None

        finally:
            await page.close()


async def main():
    """Test the service"""

    test_url = "http://powerproaustin.com/"

    async with OwnerExtractorService(headless=True) as service:
        result = await service.extract_owner_info(test_url)

        print("\n=== Owner Extraction Result ===")
        print(f"URL: {result.url}")
        print(f"Owner Name: {result.owner_full_name or f'{result.owner_first_name} {result.owner_last_name}'}")
        print(f"License #: {result.license_number}")
        print(f"Email: {result.email}")
        print(f"Phone: {result.phone}")
        print(f"Confidence: {result.confidence}")
        print(f"Method: {result.extraction_method}")

        if result.error:
            print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
