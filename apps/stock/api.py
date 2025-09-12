"""API endpoints for stock operations."""

from ninja import Router

from .services import record_entry, record_exit_fefo

router = Router()


@router.post("/entry")
def api_record_entry(request, product_id: int, quantity: int) -> dict:
    """Endpoint to register incoming stock."""
    entry = record_entry(product_id, quantity)
    return {"entry": entry}


@router.post("/exit-fefo")
def api_record_exit_fefo(request, product_id: int, quantity: int) -> dict:
    """Endpoint to remove stock using FEFO strategy."""
    removed = record_exit_fefo(product_id, quantity)
    return {"removed": removed}
