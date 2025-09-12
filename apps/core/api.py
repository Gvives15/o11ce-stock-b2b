"""API endpoints for core utilities."""

from ninja import Router

router = Router()


@router.get("/ping")
def ping(request) -> dict:
    return {"message": "core pong"}
