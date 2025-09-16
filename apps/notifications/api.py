"""API endpoints for notifications and alerts."""
from typing import Optional, Dict, Any, List
from datetime import datetime

from ninja import Router, Schema
from django.utils.dateparse import parse_datetime

from .models import Notification
from .services import (
    generate_low_stock_alerts,
    generate_near_expiry_alerts,
    notify,
    send_notification
)

router = Router()


# ===== Schemas =====
class AlertOut(Schema):
    id: int
    event: str
    channel: str
    payload: Dict[str, Any]
    created_at: datetime


class AlertsPageOut(Schema):
    items: List[AlertOut]
    page: int
    page_size: int
    total: int


class GenerateOut(Schema):
    event: str
    created: int
    skipped_rate_limited: int


class TestAlertIn(Schema):
    event: str
    payload: Dict[str, Any]
    channel: str = "system"


class ErrorOut(Schema):
    error: str
    message: str


# ===== Helpers =====
def _paging(page: int, page_size: int) -> tuple[int, int]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    return page, page_size


# ===== Legacy Endpoint =====
@router.post("/send")
def api_send_notification(request, user_id: int, message: str) -> dict:
    """Send a simple notification to a user."""
    note = send_notification(user_id, message)
    return {"notification": note}


# ===== Alerts Endpoints =====
@router.get("/alerts", response={200: AlertsPageOut})
def list_alerts(
    request,
    event: Optional[str] = None,   # new_order|low_stock|near_expiry
    since: Optional[str] = None,   # ISO datetime
    page: int = 1,
    page_size: int = 20,
):
    """
    Lista alertas con filtros simples.
    """
    page, page_size = _paging(page, page_size)
    qs = Notification.objects.all().order_by("-id")
    if event:
        qs = qs.filter(event=event)
    if since:
        dt = parse_datetime(since)
        if dt is not None:
            qs = qs.filter(created_at__gte=dt)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = [
        {
            "id": n.id,
            "event": n.event,
            "channel": n.channel,
            "payload": n.payload,
            "created_at": n.created_at
        }
        for n in qs[start:end]
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.post("/alerts/generate", response={200: GenerateOut, 400: ErrorOut})
def generate_alerts(request, type: str):
    """
    Genera alertas on-demand (útil para demo o CRON manual).
    type: 'low_stock' | 'near_expiry'
    """
    if type == "low_stock":
        res = generate_low_stock_alerts()
        return {"event": "low_stock", "created": res.created, "skipped_rate_limited": res.skipped_rate_limited}
    elif type == "near_expiry":
        res = generate_near_expiry_alerts()
        return {"event": "near_expiry", "created": res.created, "skipped_rate_limited": res.skipped_rate_limited}
    else:
        return 400, {"error": "VALIDATION_ERROR", "message": "type inválido (low_stock|near_expiry)"}


@router.post("/alerts/test", response={201: AlertOut, 400: ErrorOut})
def create_test_alert(request, payload: TestAlertIn):
    """
    Crea una alerta manual (test).
    """
    if payload.event not in ("new_order", "low_stock", "near_expiry"):
        return 400, {"error": "VALIDATION_ERROR", "message": "event inválido"}
    a = notify(event=payload.event, payload=payload.payload, channel=payload.channel)
    return 201, {
        "id": a.id,
        "event": a.event,
        "channel": a.channel,
        "payload": a.payload,
        "created_at": a.created_at
    }
