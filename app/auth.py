"""
Simple API-key authentication, standing in for the blueprint's Step 1
"strict Role-Based Access Control (RBAC)" requirement.

In production this would be replaced with GA's real identity provider
(e.g. Azure AD / OAuth2 client-credentials flow) issuing scoped tokens
(ingest:write, review:approve, core:push) instead of one shared key.
This PoC uses a single header-based key so the access-control *seam*
exists in the code and every protected route already depends on it —
swapping the verification logic later does not require touching routes.
"""
from fastapi import Header, HTTPException
from app.config import settings


def require_api_key(x_api_key: str = Header(default=None)) -> None:
    if not settings.require_auth:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")
