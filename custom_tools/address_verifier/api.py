"""
FastAPI wrapper for Address Verification (Residential vs Commercial)
Provides REST API for Phase 2F integration

Endpoints:
    POST /verify - Verify if address is residential
    GET /health - Health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import logging

from verifier import AddressVerifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Address Verification API",
    description="Verify if business address is residential (for DealMachine skip trace eligibility)",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AddressVerifyRequest(BaseModel):
    """Request model for address verification"""
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State (e.g., TX)")
    zip_code: str = Field(..., description="ZIP code")
    lead_id: Optional[str] = Field(None, description="Lead ID for tracking")


class AddressVerifyResponse(BaseModel):
    """Response model for Phase 2F output"""
    is_residential: bool = Field(..., description="True if residential, False if commercial")
    address_type: str = Field(..., description="residential, commercial, or unknown")
    verified: bool = Field(..., description="True if address was successfully verified")
    formatted_address: Optional[str] = Field(None, description="USPS standardized address")
    lead_id: Optional[str] = None
    error: Optional[str] = None


# Singleton verifier instance
_verifier: Optional[AddressVerifier] = None


def get_verifier() -> AddressVerifier:
    """Get or create verifier singleton"""
    global _verifier
    if _verifier is None:
        _verifier = AddressVerifier()
    return _verifier


@app.on_event("startup")
async def startup():
    """Initialize verifier on startup"""
    logger.info("Starting Address Verification API...")
    get_verifier()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "address-verifier"}


@app.post("/verify", response_model=AddressVerifyResponse)
async def verify_address(request: AddressVerifyRequest) -> AddressVerifyResponse:
    """
    Verify if address is residential or commercial.

    Returns is_residential=True for residential addresses (DealMachine eligible).
    """
    try:
        verifier = get_verifier()
        result = verifier.verify_address(
            address=request.address,
            city=request.city,
            state=request.state,
            zip_code=request.zip_code
        )

        return AddressVerifyResponse(
            is_residential=result["is_residential"],
            address_type=result["address_type"],
            verified=result["verified"],
            formatted_address=result.get("formatted_address"),
            lead_id=request.lead_id,
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
