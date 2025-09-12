"""API endpoints for order operations."""

from ninja import Router

from .services import checkout

router = Router()


@router.post("/checkout")
def api_checkout(request, order_id: int) -> dict:
    """Process a checkout with no items for demonstration purposes."""
    order = checkout(order_id, [])
    return {"order": order}
