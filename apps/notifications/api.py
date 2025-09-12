"""API endpoints for notification dispatch."""

from ninja import Router

from .services import send_notification

router = Router()


@router.post("/send")
def api_send_notification(request, user_id: int, message: str) -> dict:
    """Send a simple notification to a user."""
    note = send_notification(user_id, message)
    return {"notification": note}
