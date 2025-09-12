"""API endpoints for customer related operations."""

from ninja import Router

router = Router()


@router.get("/ping")
def ping(request) -> dict:
    """Simple ping endpoint for the customers API."""
    return {"message": "customers pong"}
