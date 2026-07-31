"""Unauthenticated health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health() -> dict[str, str]:
    """Simple liveness probe. Does not require an API key."""

    return {"status": "ok"}
