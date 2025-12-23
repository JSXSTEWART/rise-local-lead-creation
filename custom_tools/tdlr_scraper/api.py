"""
FastAPI wrapper for TDLR License Scraper
Provides REST API for Dify workflow integration

Endpoints:
    POST /search/business - Search by business name
    POST /search/owner - Search by owner name
    POST /search/license - Search by license number
    GET /health - Health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging

from tdlr_scraper import TDLRScraper, LicenseResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TDLR License Scraper API",
    description="Texas Department of Licensing and Regulation license verification for electrical contractors",
    version="1.0.0"
)

# CORS for Dify integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BusinessSearchRequest(BaseModel):
    """Request model for business name search"""
    business_name: str = Field(..., description="Business name to search")
    city: Optional[str] = Field(None, description="City filter (Texas cities)")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class OwnerSearchRequest(BaseModel):
    """Request model for owner name search"""
    owner_name: str = Field(..., description="Owner name to search")
    city: Optional[str] = Field(None, description="City filter")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class LicenseSearchRequest(BaseModel):
    """Request model for license number search"""
    license_number: str = Field(..., description="TDLR license number")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class WaterfallSearchRequest(BaseModel):
    """Request model for waterfall search with all available data"""
    license_number: Optional[str] = Field(None, description="TDLR license number from owner extractor")
    owner_first_name: Optional[str] = Field(None, description="Owner first name from owner extractor")
    owner_last_name: Optional[str] = Field(None, description="Owner last name from owner extractor")
    business_name: Optional[str] = Field(None, description="Business name from lead data")
    city: Optional[str] = Field(None, description="City filter")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class LicenseResponse(BaseModel):
    """Response model matching Phase 2D output specification"""
    license_status: str = Field(..., description="Active, Expired, Suspended, or Not Found")
    license_number: Optional[str] = None
    license_type: Optional[str] = None
    owner_name: Optional[str] = Field(None, description="CRITICAL: Legal name on license for skip trace")
    business_name: Optional[str] = None
    license_expiry: Optional[str] = None
    violations: int = 0
    city: Optional[str] = None
    state: str = "TX"
    verification_date: str = ""
    lead_id: Optional[str] = None
    error: Optional[str] = None


# Singleton scraper instance
_scraper: Optional[TDLRScraper] = None
_scraper_lock = asyncio.Lock()


async def get_scraper() -> TDLRScraper:
    """Get or create scraper singleton"""
    global _scraper
    async with _scraper_lock:
        if _scraper is None:
            _scraper = TDLRScraper(headless=True)
            await _scraper.start()
    return _scraper


@app.on_event("startup")
async def startup():
    """Initialize scraper on startup"""
    logger.info("Starting TDLR Scraper API...")
    await get_scraper()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global _scraper
    if _scraper:
        await _scraper.close()
        _scraper = None
    logger.info("TDLR Scraper API shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "tdlr-scraper"}


@app.post("/search/business", response_model=LicenseResponse)
async def search_by_business(request: BusinessSearchRequest) -> LicenseResponse:
    """
    Search TDLR for electrical contractor by business name.

    Returns license details including owner_name (CRITICAL for skip trace).
    """
    try:
        scraper = await get_scraper()
        result = await scraper.search_by_business_name(
            business_name=request.business_name,
            city=request.city
        )

        return LicenseResponse(
            license_status=result.license_status,
            license_number=result.license_number,
            license_type=result.license_type,
            owner_name=result.owner_name,
            business_name=result.business_name,
            license_expiry=result.license_expiry,
            violations=result.violations,
            city=result.city,
            state=result.state,
            verification_date=result.verification_date,
            lead_id=request.lead_id,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/owner", response_model=LicenseResponse)
async def search_by_owner(request: OwnerSearchRequest) -> LicenseResponse:
    """
    Search TDLR for electrical contractor license by owner name.

    Returns license details.
    """
    try:
        scraper = await get_scraper()
        result = await scraper.search_by_owner_name(
            owner_name=request.owner_name,
            city=request.city
        )

        return LicenseResponse(
            license_status=result.license_status,
            license_number=result.license_number,
            license_type=result.license_type,
            owner_name=result.owner_name,
            business_name=result.business_name,
            license_expiry=result.license_expiry,
            violations=result.violations,
            city=result.city,
            state=result.state,
            verification_date=result.verification_date,
            lead_id=request.lead_id,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/license", response_model=LicenseResponse)
async def search_by_license(request: LicenseSearchRequest) -> LicenseResponse:
    """
    Search TDLR by license number (most accurate search method).

    Returns license details including owner_name.
    """
    try:
        scraper = await get_scraper()
        result = await scraper.search_by_license_number(
            license_number=request.license_number
        )

        return LicenseResponse(
            license_status=result.license_status,
            license_number=result.license_number,
            license_type=result.license_type,
            owner_name=result.owner_name,
            business_name=result.business_name,
            license_expiry=result.license_expiry,
            violations=result.violations,
            city=result.city,
            state=result.state,
            verification_date=result.verification_date,
            lead_id=request.lead_id,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/waterfall", response_model=LicenseResponse)
async def search_with_waterfall(request: WaterfallSearchRequest) -> LicenseResponse:
    """
    RECOMMENDED: Waterfall search with maximum redundancy.

    Tries multiple search methods in order until successful:
    1. License number (if provided) - most accurate
    2. Owner name (Last, First format) - if first/last name provided
    3. Business name (fallback) - if business name provided

    This maximizes match rate by trying all available information.

    Returns license details from first successful search method.
    """
    try:
        scraper = await get_scraper()
        result = await scraper.search_with_waterfall(
            license_number=request.license_number,
            owner_first_name=request.owner_first_name,
            owner_last_name=request.owner_last_name,
            business_name=request.business_name,
            city=request.city
        )

        return LicenseResponse(
            license_status=result.license_status,
            license_number=result.license_number,
            license_type=result.license_type,
            owner_name=result.owner_name,
            business_name=result.business_name,
            license_expiry=result.license_expiry,
            violations=result.violations,
            city=result.city,
            state=result.state,
            verification_date=result.verification_date,
            lead_id=request.lead_id,
            error=result.error
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
