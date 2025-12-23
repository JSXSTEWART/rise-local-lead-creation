"""
FastAPI wrapper for Screenshot Service
Phase 2A: Visual Analysis API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, Dict
import asyncio
import logging

from screenshot_service import ScreenshotService, VisualAnalysisResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Screenshot Service API",
    description="Visual analysis service for Rise Local Lead System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScreenshotRequest(BaseModel):
    """Request model for screenshot capture"""
    url: str = Field(..., description="Website URL to capture")
    viewport_width: int = Field(1920, description="Viewport width")
    viewport_height: int = Field(1080, description="Viewport height")
    full_page: bool = Field(False, description="Capture full page")


class VisualAnalysisRequest(BaseModel):
    """Request model for visual analysis"""
    url: str = Field(..., description="Website URL to analyze")
    include_mobile: bool = Field(True, description="Include mobile screenshot")
    include_screenshots: bool = Field(False, description="Include base64 screenshots in response")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class TrackingAnalysisResponse(BaseModel):
    """Response model for HTML tracking/tech detection - FREE enrichment"""
    # Analytics
    has_gtm: bool = False
    has_ga4: bool = False
    has_ga_universal: bool = False
    has_facebook_pixel: bool = False
    has_hotjar: bool = False

    # Chat Widgets
    has_chat_widget: bool = False
    chat_provider: Optional[str] = None

    # Booking Systems
    has_booking: bool = False
    booking_provider: Optional[str] = None

    # CRM/Marketing
    has_crm: bool = False
    crm_provider: Optional[str] = None
    has_email_marketing: bool = False
    email_provider: Optional[str] = None

    # CMS Detection
    cms_detected: Optional[str] = None

    # Lead Capture
    has_lead_capture_form: bool = False
    has_contact_form: bool = False


class VisualAnalysisResponse(BaseModel):
    """Response model matching Phase 2A output specification"""
    visual_score: int = Field(..., description="1-100 design quality rating")
    design_era: str = Field(..., description="Modern, Dated, Legacy, or Template")
    has_hero_image: bool
    has_clear_cta: bool
    color_scheme: str
    mobile_responsive: bool
    social_links: Dict[str, Optional[str]]
    trust_signals: int
    url: str
    lead_id: Optional[str] = None
    screenshot_desktop_base64: Optional[str] = None
    screenshot_mobile_base64: Optional[str] = None
    error: Optional[str] = None

    # NEW: Tracking/Tech Analysis (FREE)
    tracking: Optional[TrackingAnalysisResponse] = None


_service: Optional[ScreenshotService] = None
_service_lock = asyncio.Lock()


async def get_service() -> ScreenshotService:
    global _service
    async with _service_lock:
        if _service is None:
            _service = ScreenshotService(headless=True)
            await _service.start()
    return _service


@app.on_event("startup")
async def startup():
    logger.info("Starting Screenshot Service API...")
    await get_service()


@app.on_event("shutdown")
async def shutdown():
    global _service
    if _service:
        await _service.close()
        _service = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "screenshot-service"}


@app.post("/screenshot")
async def capture_screenshot(request: ScreenshotRequest):
    """Capture a screenshot and return as PNG image."""
    try:
        service = await get_service()
        screenshot = await service.capture_screenshot(
            url=request.url,
            viewport_width=request.viewport_width,
            viewport_height=request.viewport_height,
            full_page=request.full_page
        )

        return Response(
            content=screenshot,
            media_type="image/png"
        )

    except Exception as e:
        logger.error(f"Screenshot error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=VisualAnalysisResponse)
async def analyze_website(request: VisualAnalysisRequest) -> VisualAnalysisResponse:
    """Analyze website visual design quality and detect tracking/tech stack."""
    try:
        service = await get_service()
        result = await service.capture_and_analyze(
            url=request.url,
            include_mobile=request.include_mobile
        )

        # Convert tracking analysis to response model
        tracking_response = None
        if result.tracking:
            tracking_response = TrackingAnalysisResponse(
                has_gtm=result.tracking.has_gtm,
                has_ga4=result.tracking.has_ga4,
                has_ga_universal=result.tracking.has_ga_universal,
                has_facebook_pixel=result.tracking.has_facebook_pixel,
                has_hotjar=result.tracking.has_hotjar,
                has_chat_widget=result.tracking.has_chat_widget,
                chat_provider=result.tracking.chat_provider,
                has_booking=result.tracking.has_booking,
                booking_provider=result.tracking.booking_provider,
                has_crm=result.tracking.has_crm,
                crm_provider=result.tracking.crm_provider,
                has_email_marketing=result.tracking.has_email_marketing,
                email_provider=result.tracking.email_provider,
                cms_detected=result.tracking.cms_detected,
                has_lead_capture_form=result.tracking.has_lead_capture_form,
                has_contact_form=result.tracking.has_contact_form
            )

        response = VisualAnalysisResponse(
            visual_score=result.visual_score,
            design_era=result.design_era,
            has_hero_image=result.has_hero_image,
            has_clear_cta=result.has_clear_cta,
            color_scheme=result.color_scheme,
            mobile_responsive=result.mobile_responsive,
            social_links=result.social_links,
            trust_signals=result.trust_signals,
            url=result.url,
            lead_id=request.lead_id,
            error=result.error,
            tracking=tracking_response
        )

        # Include screenshots only if requested (they're large)
        if request.include_screenshots:
            response.screenshot_desktop_base64 = result.screenshot_desktop_base64
            response.screenshot_mobile_base64 = result.screenshot_mobile_base64

        return response

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
