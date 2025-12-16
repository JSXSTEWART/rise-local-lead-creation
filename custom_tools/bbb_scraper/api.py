"""
FastAPI wrapper for BBB Scraper
Phase 2E: Reputation Analysis API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging

from bbb_scraper import BBBScraper, BBBResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BBB Scraper API",
    description="Better Business Bureau reputation analysis for Rise Local Lead System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BBBSearchRequest(BaseModel):
    """Request model for BBB search"""
    business_name: str = Field(..., description="Business name to search")
    city: str = Field(..., description="City name")
    state: str = Field("TX", description="State code")
    google_rating: float = Field(0.0, description="Google rating for reputation gap calculation")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class BBBResponse(BaseModel):
    """Response model matching Phase 2E output specification"""
    bbb_rating: str = Field(..., description="A+, A, B, C, D, F, or NR")
    bbb_accredited: bool
    complaints_total: int
    complaints_3yr: int
    complaints_resolved: int
    reputation_gap: float = Field(..., description="Google rating - BBB implied rating")
    years_in_business: Optional[int] = None
    business_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    bbb_url: Optional[str] = None
    lead_id: Optional[str] = None
    error: Optional[str] = None


_scraper: Optional[BBBScraper] = None
_scraper_lock = asyncio.Lock()


async def get_scraper() -> BBBScraper:
    global _scraper
    async with _scraper_lock:
        if _scraper is None:
            _scraper = BBBScraper(headless=True)
            await _scraper.start()
    return _scraper


@app.on_event("startup")
async def startup():
    logger.info("Starting BBB Scraper API...")
    await get_scraper()


@app.on_event("shutdown")
async def shutdown():
    global _scraper
    if _scraper:
        await _scraper.close()
        _scraper = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bbb-scraper"}


@app.post("/search", response_model=BBBResponse)
async def search_business(request: BBBSearchRequest) -> BBBResponse:
    """Search BBB for business reputation data."""
    try:
        scraper = await get_scraper()
        result = await scraper.search_business(
            business_name=request.business_name,
            city=request.city,
            state=request.state,
            google_rating=request.google_rating
        )

        return BBBResponse(
            bbb_rating=result.bbb_rating,
            bbb_accredited=result.bbb_accredited,
            complaints_total=result.complaints_total,
            complaints_3yr=result.complaints_3yr,
            complaints_resolved=result.complaints_resolved,
            reputation_gap=result.reputation_gap,
            years_in_business=result.years_in_business,
            business_name=result.business_name,
            city=result.city,
            state=result.state,
            bbb_url=result.bbb_url,
            lead_id=request.lead_id,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
