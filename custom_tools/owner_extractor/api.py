"""
FastAPI wrapper for Owner Extractor Service
Phase 2D-Enhanced: Extract owner name and license from website
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging

from owner_extractor import OwnerExtractorService, OwnerExtractionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Owner Extractor API",
    description="Extract owner information from websites using Claude Vision",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OwnerExtractionRequest(BaseModel):
    """Request model for owner extraction"""
    url: str = Field(..., description="Website URL to analyze")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class OwnerExtractionResponse(BaseModel):
    """Response model for owner extraction"""
    owner_first_name: Optional[str] = Field(None, description="Owner's first name")
    owner_last_name: Optional[str] = Field(None, description="Owner's last name")
    owner_full_name: Optional[str] = Field(None, description="Owner's full name")
    license_number: Optional[str] = Field(None, description="TECL license number if found")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    confidence: str = Field(..., description="Extraction confidence: low, medium, high")
    extraction_method: str = Field(..., description="Method used: about_page, homepage_fallback, both_pages, homepage_only")
    pages_analyzed: list = Field(default_factory=list, description="List of pages analyzed: ['about', 'homepage']")
    url: str = Field(..., description="URL analyzed")
    lead_id: Optional[str] = None
    error: Optional[str] = None


_service: Optional[OwnerExtractorService] = None
_service_lock = asyncio.Lock()


async def get_service() -> OwnerExtractorService:
    """Get or create the owner extractor service instance"""
    global _service
    async with _service_lock:
        if _service is None:
            _service = OwnerExtractorService(headless=True)
            await _service.start()
    return _service


@app.on_event("startup")
async def startup():
    logger.info("Starting Owner Extractor API...")
    await get_service()


@app.on_event("shutdown")
async def shutdown():
    global _service
    if _service:
        await _service.close()
        _service = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "owner-extractor"}


@app.post("/extract-owner", response_model=OwnerExtractionResponse)
async def extract_owner(request: OwnerExtractionRequest) -> OwnerExtractionResponse:
    """
    Extract owner information from a website.

    Uses Claude Vision to analyze screenshots and extract:
    - Owner first and last name
    - License number (if displayed)
    - Contact email and phone
    """
    try:
        service = await get_service()
        result = await service.extract_owner_info(url=request.url)

        response = OwnerExtractionResponse(
            owner_first_name=result.owner_first_name,
            owner_last_name=result.owner_last_name,
            owner_full_name=result.owner_full_name,
            license_number=result.license_number,
            email=result.email,
            phone=result.phone,
            confidence=result.confidence,
            extraction_method=result.extraction_method,
            pages_analyzed=result.pages_analyzed,
            url=result.url,
            lead_id=request.lead_id,
            error=result.error
        )

        return response

    except Exception as e:
        logger.error(f"Owner extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
