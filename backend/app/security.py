"""API-Key authentication dependency."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency enforcing the ``X-API-Key`` header.

    Applied to every router except ``/health``. Uses a constant-time
    comparison to avoid timing side-channels on the secret. Declaring this
    via :class:`~fastapi.security.APIKeyHeader` (instead of a plain
    ``Header``) registers an ``ApiKeyHeader`` security scheme in the OpenAPI
    schema, so Swagger UI shows an "Authorize" button for protected routes.
    """

    settings = get_settings()
    if not api_key or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
