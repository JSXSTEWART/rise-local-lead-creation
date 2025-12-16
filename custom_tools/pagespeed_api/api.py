"""
FastAPI wrapper for PageSpeed Insights API
Phase 2B: Technical Scores API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
import logging

from pagespeed_api import PageSpeedAPI, PageSpeedResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PageSpeed API",
    description="Google PageSpeed Insights integration for Rise Local Lead System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get optional API key from environment
API_KEY = os.getenv("GOOGLE_PAGESPEED_API_KEY")
_api: Optional[PageSpeedAPI] = None


class PageSpeedRequest(BaseModel):
    """Request model for PageSpeed analysis"""
    url: str = Field(..., description="Website URL to analyze")
    strategy: str = Field("mobile", description="'mobile' or 'desktop'")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class PageSpeedResponse(BaseModel):
    """Response model matching Phase 2B output specification"""
    performance_score: int = Field(..., description="0-100 performance score")
    mobile_score: int = Field(..., description="0-100 mobile-friendliness")
    seo_score: int = Field(..., description="0-100 SEO score")
    accessibility_score: int = Field(..., description="0-100 accessibility score")
    largest_contentful_paint: float
    cumulative_layout_shift: float
    first_input_delay: float
    has_https: bool
    has_viewport_meta: bool
    url: str
    strategy: str
    lead_id: Optional[str] = None
    error: Optional[str] = None


def get_api() -> PageSpeedAPI:
    global _api
    if _api is None:
        _api = PageSpeedAPI(api_key=API_KEY)
    return _api


@app.on_event("shutdown")
async def shutdown():
    global _api
    if _api:
        await _api.close()
        _api = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pagespeed-api"}


@app.post("/analyze", response_model=PageSpeedResponse)
async def analyze_url(request: PageSpeedRequest) -> PageSpeedResponse:
    """Analyze website performance with Google PageSpeed Insights."""
    try:
        api = get_api()
        result = await api.analyze(
            url=request.url,
            strategy=request.strategy
        )

        return PageSpeedResponse(
            performance_score=result.performance_score,
            mobile_score=result.mobile_score,
            seo_score=result.seo_score,
            accessibility_score=result.accessibility_score,
            largest_contentful_paint=result.largest_contentful_paint,
            cumulative_layout_shift=result.cumulative_layout_shift,
            first_input_delay=result.first_input_delay,
            has_https=result.has_https,
            has_viewport_meta=result.has_viewport_meta,
            url=result.url,
            strategy=result.strategy,
            lead_id=request.lead_id,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/both")
async def analyze_both_strategies(request: PageSpeedRequest):
    """Analyze website for both mobile and desktop strategies."""
    try:
        api = get_api()
        results = await api.analyze_both_strategies(request.url)
        results["lead_id"] = request.lead_id
        return results

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
