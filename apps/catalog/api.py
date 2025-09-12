"""API endpoints for the catalog application."""

from ninja import Router

router = Router()


@router.get("/ping")
def ping(request) -> dict:
    """Simple endpoint used for smoke testing the catalog API."""
    return {"message": "catalog pong"}
