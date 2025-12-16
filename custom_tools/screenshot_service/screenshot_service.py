"""
Screenshot Service for Rise Local Lead System
Phase 2A: Visual Analysis

Captures website screenshots and optionally analyzes with Gemini Vision.
Extracts visual quality score, design era, and social links.

Usage:
    from screenshot_service import ScreenshotService

    async with ScreenshotService() as service:
        result = await service.capture_and_analyze("https://example.com")
        print(result)
"""

import asyncio
import base64
import re
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime
from io import BytesIO
import logging

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    raise ImportError("playwright not installed. Run: pip install playwright && playwright install chromium")

try:
    import google.generativeai as genai
    from PIL import Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("google-generativeai not installed. Vision analysis will be disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrackingAnalysis:
    """Result from HTML tracking/tech detection - FREE enrichment"""
    # Analytics
    has_gtm: bool = False
    has_ga4: bool = False
    has_ga_universal: bool = False
    has_facebook_pixel: bool = False
    has_hotjar: bool = False

    # Chat Widgets
    has_chat_widget: bool = False
    chat_provider: Optional[str] = None  # intercom, drift, crisp, tawk, zendesk, livechat

    # Booking Systems
    has_booking: bool = False
    booking_provider: Optional[str] = None  # calendly, acuity, housecallpro, jobber, servicetitan

    # CRM/Marketing
    has_crm: bool = False
    crm_provider: Optional[str] = None  # hubspot, salesforce, zoho, pipedrive
    has_email_marketing: bool = False
    email_provider: Optional[str] = None  # mailchimp, klaviyo, activecampaign, constantcontact

    # CMS Detection (partial - not as reliable as BuiltWith)
    cms_detected: Optional[str] = None  # wordpress, wix, squarespace, shopify, godaddy, weebly

    # Lead Capture
    has_lead_capture_form: bool = False
    has_contact_form: bool = False


@dataclass
class VisualAnalysisResult:
    """Result from visual analysis"""
    visual_score: int  # 1-100 design quality rating
    design_era: str  # Modern, Dated, Legacy, Template
    has_hero_image: bool
    has_clear_cta: bool
    color_scheme: str  # Professional, Amateur, Template
    mobile_responsive: bool
    social_links: Dict[str, Optional[str]]  # facebook, instagram, linkedin, youtube
    trust_signals: int  # Count of badges, certifications visible
    screenshot_desktop_base64: Optional[str] = None
    screenshot_mobile_base64: Optional[str] = None
    url: str = ""
    analysis_date: str = ""
    error: Optional[str] = None

    # NEW: Tracking/Tech Analysis (FREE)
    tracking: Optional[TrackingAnalysis] = None

    def __post_init__(self):
        if not self.analysis_date:
            self.analysis_date = datetime.now().isoformat()
        if not self.social_links:
            self.social_links = {
                "facebook": None,
                "instagram": None,
                "linkedin": None,
                "youtube": None
            }

    def to_dict(self) -> dict:
        return asdict(self)


class ScreenshotService:
    """
    Captures website screenshots and performs visual analysis.

    Optionally uses Gemini Vision for AI-powered design evaluation.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        gemini_api_key: Optional[str] = None
    ):
        self.headless = headless
        self.timeout = timeout
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

        # Initialize Gemini if available
        if GEMINI_AVAILABLE and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
        else:
            self._gemini_model = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize browser"""
        logger.info("Starting Screenshot Service...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Screenshot Service closed")

    async def capture_screenshot(
        self,
        url: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = False
    ) -> bytes:
        """
        Capture a screenshot of a website.

        Args:
            url: Website URL
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            full_page: Capture full scrollable page

        Returns:
            Screenshot as PNG bytes
        """
        page = await self._browser.new_page()
        try:
            await page.set_viewport_size({
                "width": viewport_width,
                "height": viewport_height
            })
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            # Try to load page - use 'load' instead of 'networkidle' as many modern sites never fully idle
            try:
                await page.goto(url, wait_until="load", timeout=self.timeout)
            except Exception:
                # Fallback to domcontentloaded if load times out
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            await asyncio.sleep(3)  # Wait for JS rendering and animations

            screenshot = await page.screenshot(full_page=full_page, type="png")
            return screenshot

        finally:
            await page.close()

    async def capture_and_analyze(
        self,
        url: str,
        include_mobile: bool = True
    ) -> VisualAnalysisResult:
        """
        Capture screenshots and analyze website visually.

        Args:
            url: Website URL to analyze
            include_mobile: Also capture mobile viewport

        Returns:
            VisualAnalysisResult with scores and extracted data
        """
        logger.info(f"Capturing and analyzing: {url}")

        result = VisualAnalysisResult(
            visual_score=50,  # Default neutral score
            design_era="Unknown",
            has_hero_image=False,
            has_clear_cta=False,
            color_scheme="Unknown",
            mobile_responsive=False,
            social_links={
                "facebook": None,
                "instagram": None,
                "linkedin": None,
                "youtube": None
            },
            trust_signals=0,
            url=url
        )

        try:
            # Capture desktop screenshot
            desktop_screenshot = await self.capture_screenshot(
                url,
                viewport_width=1920,
                viewport_height=1080
            )
            result.screenshot_desktop_base64 = base64.b64encode(desktop_screenshot).decode()

            # Capture mobile screenshot
            if include_mobile:
                mobile_screenshot = await self.capture_screenshot(
                    url,
                    viewport_width=375,
                    viewport_height=812
                )
                result.screenshot_mobile_base64 = base64.b64encode(mobile_screenshot).decode()

            # Extract social links and tracking info from page
            page = await self._browser.new_page()
            try:
                try:
                    await page.goto(url, wait_until="load", timeout=self.timeout)
                except Exception:
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                await asyncio.sleep(2)  # Wait for JS to render

                result.social_links = await self._extract_social_links(page)
                result.mobile_responsive = await self._check_mobile_responsive(page)

                # NEW: Detect tracking/tech from HTML (FREE enrichment!)
                page_html = await page.content()
                result.tracking = self._detect_tracking(page_html)
                logger.info(f"Tracking detection complete: GTM={result.tracking.has_gtm}, "
                           f"GA4={result.tracking.has_ga4}, Chat={result.tracking.has_chat_widget}, "
                           f"Booking={result.tracking.has_booking}, CRM={result.tracking.has_crm}, "
                           f"CMS={result.tracking.cms_detected}")
            finally:
                await page.close()

            # Use Gemini Vision for analysis if available
            if self._gemini_model:
                vision_analysis = await self._analyze_with_gemini(desktop_screenshot)
                if vision_analysis:
                    result.visual_score = vision_analysis.get("visual_score", 50)
                    result.design_era = vision_analysis.get("design_era", "Unknown")
                    result.has_hero_image = vision_analysis.get("has_hero_image", False)
                    result.has_clear_cta = vision_analysis.get("has_clear_cta", False)
                    result.color_scheme = vision_analysis.get("color_scheme", "Unknown")
                    result.trust_signals = vision_analysis.get("trust_signals", 0)
            else:
                # Basic heuristic analysis without AI
                result = await self._basic_analysis(url, result)

        except Exception as e:
            logger.error(f"Error analyzing {url}: {str(e)}")
            result.error = str(e)

        return result

    async def _extract_social_links(self, page: Page) -> Dict[str, Optional[str]]:
        """Extract social media links from page"""
        social_links = {
            "facebook": None,
            "instagram": None,
            "linkedin": None,
            "youtube": None
        }

        try:
            # Get all links on page
            links = await page.query_selector_all("a[href]")

            for link in links:
                href = await link.get_attribute("href")
                if not href:
                    continue

                href_lower = href.lower()

                if "facebook.com" in href_lower and not social_links["facebook"]:
                    social_links["facebook"] = href
                elif "instagram.com" in href_lower and not social_links["instagram"]:
                    social_links["instagram"] = href
                elif "linkedin.com" in href_lower and not social_links["linkedin"]:
                    social_links["linkedin"] = href
                elif "youtube.com" in href_lower and not social_links["youtube"]:
                    social_links["youtube"] = href

        except Exception as e:
            logger.warning(f"Error extracting social links: {str(e)}")

        return social_links

    async def _check_mobile_responsive(self, page: Page) -> bool:
        """Check if site has mobile viewport meta tag"""
        try:
            viewport_meta = await page.query_selector('meta[name="viewport"]')
            return viewport_meta is not None
        except:
            return False

    def _detect_tracking(self, html: str) -> TrackingAnalysis:
        """
        Detect tracking pixels, analytics, chat widgets, booking systems, and CMS from HTML.
        This is FREE enrichment - no API costs!

        Args:
            html: Raw HTML content of the page

        Returns:
            TrackingAnalysis with all detected technologies
        """
        html_lower = html.lower()
        tracking = TrackingAnalysis()

        # =====================================================================
        # ANALYTICS DETECTION
        # =====================================================================

        # Google Tag Manager
        tracking.has_gtm = (
            "googletagmanager.com/gtm.js" in html_lower or
            "gtm-" in html_lower or
            "gtm.start" in html_lower
        )

        # Google Analytics 4
        tracking.has_ga4 = (
            "gtag/js?id=g-" in html_lower or
            "'g-" in html_lower or
            '"g-' in html_lower or
            "googletagmanager.com/gtag/js" in html_lower
        )

        # Google Analytics Universal (legacy)
        tracking.has_ga_universal = (
            "google-analytics.com/analytics.js" in html_lower or
            "ua-" in html_lower or
            "googleanalytics" in html_lower
        )

        # Facebook Pixel
        tracking.has_facebook_pixel = (
            "connect.facebook.net" in html_lower or
            "fbevents.js" in html_lower or
            "fbq(" in html_lower or
            "facebook-jssdk" in html_lower
        )

        # Hotjar
        tracking.has_hotjar = (
            "hotjar.com" in html_lower or
            "static.hotjar.com" in html_lower or
            "_hjSettings" in html_lower
        )

        # =====================================================================
        # CHAT WIDGET DETECTION
        # =====================================================================

        chat_providers = {
            "intercom": ["intercom.io", "intercomcdn.com", "intercom-"],
            "drift": ["drift.com", "js.driftt.com", "drift-"],
            "crisp": ["crisp.chat", "client.crisp.chat"],
            "tawk": ["tawk.to", "embed.tawk.to"],
            "zendesk": ["zendesk.com", "zdassets.com", "zopim"],
            "livechat": ["livechatinc.com", "cdn.livechatinc.com"],
            "hubspot_chat": ["js.hs-scripts.com", "hubspot.com/conversations"],
            "freshdesk": ["freshdesk.com", "freshchat"],
            "olark": ["olark.com"],
            "tidio": ["tidio.co", "tidiochat"],
        }

        for provider, signatures in chat_providers.items():
            if any(sig in html_lower for sig in signatures):
                tracking.has_chat_widget = True
                tracking.chat_provider = provider
                break

        # =====================================================================
        # BOOKING SYSTEM DETECTION
        # =====================================================================

        booking_providers = {
            "calendly": ["calendly.com", "assets.calendly.com"],
            "acuity": ["acuityscheduling.com", "squareup.com/appointments"],
            "housecall_pro": ["housecallpro.com", "hcp."],
            "jobber": ["jobber.com", "getjobber.com"],
            "servicetitan": ["servicetitan.com"],
            "setmore": ["setmore.com"],
            "square_appointments": ["squareup.com/appointments", "square.site"],
            "booksy": ["booksy.com"],
            "vagaro": ["vagaro.com"],
            "schedulicity": ["schedulicity.com"],
            "simplybook": ["simplybook.me"],
        }

        for provider, signatures in booking_providers.items():
            if any(sig in html_lower for sig in signatures):
                tracking.has_booking = True
                tracking.booking_provider = provider
                break

        # =====================================================================
        # CRM DETECTION
        # =====================================================================

        crm_providers = {
            "hubspot": ["js.hs-scripts.com", "hubspot.com", "hs-analytics", "hbspt."],
            "salesforce": ["salesforce.com", "force.com", "pardot.com"],
            "zoho": ["zoho.com", "zohocdn.com", "salesiq.zoho"],
            "pipedrive": ["pipedrive.com"],
            "activecampaign": ["activecampaign.com", "actcmpaign"],
            "keap": ["keap.com", "infusionsoft.com"],
            "gohighlevel": ["gohighlevel.com", "highlevel.com", "msgsndr.com"],
            "close": ["close.com", "close.io"],
        }

        for provider, signatures in crm_providers.items():
            if any(sig in html_lower for sig in signatures):
                tracking.has_crm = True
                tracking.crm_provider = provider
                break

        # =====================================================================
        # EMAIL MARKETING DETECTION
        # =====================================================================

        email_providers = {
            "mailchimp": ["mailchimp.com", "chimpstatic.com", "list-manage.com"],
            "klaviyo": ["klaviyo.com", "static.klaviyo.com"],
            "activecampaign": ["activecampaign.com"],
            "constantcontact": ["constantcontact.com", "ctctcdn.com"],
            "convertkit": ["convertkit.com", "ck.page"],
            "drip": ["getdrip.com"],
            "sendinblue": ["sendinblue.com", "sibautomation.com"],
            "aweber": ["aweber.com"],
            "mailerlite": ["mailerlite.com"],
        }

        for provider, signatures in email_providers.items():
            if any(sig in html_lower for sig in signatures):
                tracking.has_email_marketing = True
                tracking.email_provider = provider
                break

        # =====================================================================
        # CMS DETECTION (Partial - not as reliable as BuiltWith)
        # =====================================================================

        # WordPress - very detectable
        if "wp-content" in html_lower or "wp-includes" in html_lower or "wordpress" in html_lower:
            tracking.cms_detected = "WordPress"

        # Wix
        elif "wix.com" in html_lower or "wixsite.com" in html_lower or "static.wixstatic.com" in html_lower:
            tracking.cms_detected = "Wix"

        # Squarespace
        elif "squarespace.com" in html_lower or "static.squarespace" in html_lower or "sqsp" in html_lower:
            tracking.cms_detected = "Squarespace"

        # Shopify
        elif "shopify.com" in html_lower or "cdn.shopify" in html_lower or "myshopify" in html_lower:
            tracking.cms_detected = "Shopify"

        # GoDaddy Website Builder
        elif "godaddy.com" in html_lower or "secureserver.net" in html_lower or "godaddysites" in html_lower:
            tracking.cms_detected = "GoDaddy"

        # Weebly
        elif "weebly.com" in html_lower or "editmysite.com" in html_lower:
            tracking.cms_detected = "Weebly"

        # Webflow
        elif "webflow.com" in html_lower or "assets.website-files.com" in html_lower:
            tracking.cms_detected = "Webflow"

        # Duda
        elif "duda.co" in html_lower or "dudaone.com" in html_lower:
            tracking.cms_detected = "Duda"

        # Joomla
        elif "/media/jui/" in html_lower or "joomla" in html_lower:
            tracking.cms_detected = "Joomla"

        # Drupal
        elif "drupal" in html_lower or "/sites/default/files" in html_lower:
            tracking.cms_detected = "Drupal"

        # =====================================================================
        # LEAD CAPTURE FORM DETECTION
        # =====================================================================

        # Check for contact forms
        tracking.has_contact_form = (
            '<form' in html_lower and (
                'contact' in html_lower or
                'email' in html_lower or
                'message' in html_lower or
                'inquiry' in html_lower
            )
        )

        # Check for lead capture forms (pop-ups, embedded forms)
        lead_capture_signatures = [
            "leadcapture", "lead-capture", "optin", "opt-in",
            "subscribe", "newsletter", "signup", "sign-up",
            "getresponse", "leadpages", "unbounce", "instapage"
        ]
        tracking.has_lead_capture_form = any(sig in html_lower for sig in lead_capture_signatures)

        return tracking

    async def _analyze_with_gemini(self, screenshot_bytes: bytes) -> Optional[dict]:
        """Analyze screenshot with Gemini Vision"""

        if not self._gemini_model:
            return None

        try:
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(screenshot_bytes))

            prompt = """Analyze this website screenshot and provide a JSON response with these fields:

{
    "visual_score": <integer 1-100, overall design quality>,
    "design_era": <"Modern" | "Dated" | "Legacy" | "Template">,
    "has_hero_image": <boolean, prominent hero/banner image visible>,
    "has_clear_cta": <boolean, clear call-to-action button visible>,
    "color_scheme": <"Professional" | "Amateur" | "Template">,
    "trust_signals": <integer, count of visible trust badges, certifications, awards>
}

Scoring guide for visual_score:
- 80-100: Modern, professional, clean design with good UX
- 60-79: Decent design, some dated elements
- 40-59: Clearly dated or template-based design
- 20-39: Poor design, cluttered, hard to navigate
- 1-19: Very amateur, broken, or unusable

Respond ONLY with the JSON object, no other text."""

            response = await asyncio.to_thread(
                self._gemini_model.generate_content,
                [prompt, image]
            )

            # Parse JSON from response
            response_text = response.text.strip()

            # Try to extract JSON
            json_match = re.search(r'\{[^{}]+\}', response_text, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())

            return None

        except Exception as e:
            logger.error(f"Gemini analysis error: {str(e)}")
            return None

    async def _basic_analysis(self, url: str, result: VisualAnalysisResult) -> VisualAnalysisResult:
        """Basic heuristic analysis without AI"""

        # Simple heuristics based on what we can detect
        page = await self._browser.new_page()
        try:
            try:
                await page.goto(url, wait_until="load", timeout=self.timeout)
            except Exception:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            await asyncio.sleep(2)  # Wait for JS rendering

            # Check for hero image
            hero_selectors = [
                '.hero', '#hero', '[class*="hero"]',
                '.banner', '#banner', '[class*="banner"]',
                'header img', '.header-image'
            ]
            for selector in hero_selectors:
                element = await page.query_selector(selector)
                if element:
                    result.has_hero_image = True
                    break

            # Check for CTA buttons
            cta_selectors = [
                'a.btn', 'button.btn', '.cta',
                '[class*="button"]', 'a[class*="cta"]',
                'button[type="submit"]'
            ]
            for selector in cta_selectors:
                element = await page.query_selector(selector)
                if element:
                    result.has_clear_cta = True
                    break

            # Check for trust signals (badges, certifications)
            trust_selectors = [
                '[class*="trust"]', '[class*="badge"]',
                '[class*="certification"]', '[class*="award"]',
                '[alt*="certified"]', '[alt*="award"]'
            ]
            trust_count = 0
            for selector in trust_selectors:
                elements = await page.query_selector_all(selector)
                trust_count += len(elements)
            result.trust_signals = min(trust_count, 10)  # Cap at 10

            # Estimate visual score based on detected elements
            score = 50
            if result.has_hero_image:
                score += 10
            if result.has_clear_cta:
                score += 10
            if result.mobile_responsive:
                score += 10
            if any(result.social_links.values()):
                score += 5
            if result.trust_signals > 0:
                score += min(result.trust_signals * 2, 15)

            result.visual_score = min(score, 100)

            # Estimate design era based on common patterns
            page_html = await page.content()
            if any(x in page_html.lower() for x in ['tailwind', 'flex', 'grid', 'react', 'vue']):
                result.design_era = "Modern"
            elif any(x in page_html.lower() for x in ['bootstrap', 'jquery']):
                result.design_era = "Template"
            elif any(x in page_html.lower() for x in ['table', 'frames', 'marquee']):
                result.design_era = "Legacy"
            else:
                result.design_era = "Dated"

            result.color_scheme = "Professional" if result.visual_score >= 60 else "Amateur"

        finally:
            await page.close()

        return result


async def main():
    """Test the service"""

    # Test with a real electrician website or any website
    test_url = "https://www.google.com"

    async with ScreenshotService(headless=True) as service:
        result = await service.capture_and_analyze(test_url)

        print("\n" + "=" * 60)
        print("VISUAL ANALYSIS")
        print("=" * 60)
        print(f"URL: {result.url}")
        print(f"Visual Score: {result.visual_score}/100")
        print(f"Design Era: {result.design_era}")
        print(f"Has Hero Image: {result.has_hero_image}")
        print(f"Has Clear CTA: {result.has_clear_cta}")
        print(f"Color Scheme: {result.color_scheme}")
        print(f"Mobile Responsive: {result.mobile_responsive}")
        print(f"Trust Signals: {result.trust_signals}")
        print(f"Social Links: {result.social_links}")

        if result.tracking:
            print("\n" + "=" * 60)
            print("TRACKING/TECH DETECTION (FREE)")
            print("=" * 60)
            print(f"Analytics:")
            print(f"  - GTM: {result.tracking.has_gtm}")
            print(f"  - GA4: {result.tracking.has_ga4}")
            print(f"  - GA Universal: {result.tracking.has_ga_universal}")
            print(f"  - Facebook Pixel: {result.tracking.has_facebook_pixel}")
            print(f"  - Hotjar: {result.tracking.has_hotjar}")
            print(f"Chat Widget:")
            print(f"  - Has Chat: {result.tracking.has_chat_widget}")
            print(f"  - Provider: {result.tracking.chat_provider}")
            print(f"Booking System:")
            print(f"  - Has Booking: {result.tracking.has_booking}")
            print(f"  - Provider: {result.tracking.booking_provider}")
            print(f"CRM:")
            print(f"  - Has CRM: {result.tracking.has_crm}")
            print(f"  - Provider: {result.tracking.crm_provider}")
            print(f"Email Marketing:")
            print(f"  - Has Email: {result.tracking.has_email_marketing}")
            print(f"  - Provider: {result.tracking.email_provider}")
            print(f"CMS:")
            print(f"  - Detected: {result.tracking.cms_detected}")
            print(f"Lead Capture:")
            print(f"  - Contact Form: {result.tracking.has_contact_form}")
            print(f"  - Lead Capture Form: {result.tracking.has_lead_capture_form}")

        if result.error:
            print(f"\nError: {result.error}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
