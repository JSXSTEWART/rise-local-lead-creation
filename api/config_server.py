"""
Secure Configuration API Server
Provides Supabase credentials to authenticated frontend without exposing in code
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
from typing import Optional
import jwt
from datetime import datetime, timedelta

app = FastAPI(title="Rise Local Config API")

# Enable CORS for dashboard origin only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "https://dashboard.riselocal.com"  # Production (update with actual domain)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

security = HTTPBearer()

# JWT secret for service account tokens
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")


class SupabaseConfig(BaseModel):
    url: str
    anonKey: str


class ServiceAccountCreate(BaseModel):
    name: str
    role: str  # agent_orchestrator or agent_intelligence


class ServiceAccountResponse(BaseModel):
    name: str
    role: str
    token: str
    expires_at: str


@app.get("/")
async def root():
    return {
        "service": "Rise Local Config API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/api/config/supabase")
async def get_supabase_config() -> SupabaseConfig:
    """
    Provide Supabase configuration to authenticated dashboard users.
    This endpoint should be protected by API Gateway or similar in production.
    """

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase configuration not found. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
        )

    return SupabaseConfig(
        url=supabase_url,
        anonKey=supabase_anon_key
    )


@app.post("/api/service-accounts/create")
async def create_service_account(
    account: ServiceAccountCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> ServiceAccountResponse:
    """
    Create JWT token for agent service accounts.
    Only accessible by admin users.
    """

    # Verify admin authorization (implement proper auth check in production)
    # For now, check if token matches admin secret
    admin_secret = os.getenv("ADMIN_SECRET", "admin-secret")

    if credentials.credentials != admin_secret:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Validate role
    if account.role not in ["agent_orchestrator", "agent_intelligence"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be 'agent_orchestrator' or 'agent_intelligence'"
        )

    # Generate JWT token
    expiry_hours = 24 if account.role == "agent_orchestrator" else 1
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)

    token_payload = {
        "sub": account.name,
        "role": account.role,
        "permissions": get_role_permissions(account.role),
        "exp": expires_at.timestamp(),
        "iat": datetime.utcnow().timestamp()
    }

    token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")

    return ServiceAccountResponse(
        name=account.name,
        role=account.role,
        token=token,
        expires_at=expires_at.isoformat()
    )


@app.get("/api/service-accounts/verify")
async def verify_service_account(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Verify and decode service account JWT token.
    """

    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

        return {
            "valid": True,
            "account": payload["sub"],
            "role": payload["role"],
            "permissions": payload["permissions"],
            "expires_at": datetime.fromtimestamp(payload["exp"]).isoformat()
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_role_permissions(role: str) -> list[str]:
    """
    Get permissions for a given role.
    """

    permissions_map = {
        "agent_orchestrator": [
            "read:leads",
            "write:agent_jobs",
            "update:enrichment_queue"
        ],
        "agent_intelligence": [
            "read:leads",
            "write:agent_decisions",
            "call:mcp_tools"
        ]
    }

    return permissions_map.get(role, [])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
