# apps/orders/api.py
from datetime import date, time
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from ninja import Router, Schema
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet

from apps.orders.services import checkout
from apps.stock.services import ExitError
from .models import Order, OrderItem
from apps.customers.models import Customer
from apps.catalog.models import Product

router = Router(tags=["orders"])

# ========= Helpers =========
def _clamp_page(page: int, page_size: int) -> tuple[int, int]:
    if page < 1: page = 1
    if page_size < 1: page_size = 1
    if page_size > 100: page_size = 100
    return page, page_size

# ==== Schemas ====
class CheckoutItemIn(Schema):
    product_id: int
    qty: Decimal

class CheckoutIn(Schema):
    customer_id: int
    items: List[CheckoutItemIn]
    delivery_method: str                     # "delivery" | "pickup"
    delivery_address_text: Optional[str] = ""   # requerido si delivery
    delivery_window_from: Optional[time] = None
    delivery_window_to: Optional[time] = None
    requested_delivery_date: Optional[date] = None
    delivery_instructions: Optional[str] = ""
    client_req_id: Optional[str] = None      # para idempotencia

class CheckoutOut(Schema):
    order_id: int
    status: str
    total: Decimal

class ErrorOut(Schema):
    error: str
    message: str

# ========= Schemas de salida para listado y detalle =========
class OrderListItem(Schema):
    id: int
    customer_id: int
    customer_name: str
    status: str
    total: str               # string para mantener Decimals consistentes
    created_at: datetime

class OrdersPageOut(Schema):
    items: List[OrderListItem]
    page: int
    page_size: int
    total: int

class OrderItemOut(Schema):
    product_id: int
    code: str
    name: str
    qty: str                 # string para Decimal
    unit_price: str          # string para Decimal
    benefit_applied: Optional[dict] = None

class OrderDetailOut(Schema):
    id: int
    customer: dict
    status: str
    delivery_method: str
    delivery_address_text: Optional[str] = ""
    delivery_window_from: Optional[str] = None
    delivery_window_to: Optional[str] = None
    requested_delivery_date: Optional[str] = None
    delivery_instructions: Optional[str] = ""
    items: List[OrderItemOut]
    subtotal: str
    discount_total: str
    tax_total: str
    total: str
    created_at: datetime

# ==== Endpoint ====
@router.post("/order/checkout", response={201: CheckoutOut, 400: ErrorOut, 404: ErrorOut, 409: ErrorOut})
def order_checkout(request, payload: CheckoutIn):
    try:
        o = checkout(
            customer_id=payload.customer_id,
            items=[i.dict() for i in payload.items],
            delivery_method=payload.delivery_method,
            delivery_address_text=payload.delivery_address_text or "",
            delivery_window_from=payload.delivery_window_from,
            delivery_window_to=payload.delivery_window_to,
            requested_delivery_date=payload.requested_delivery_date,
            delivery_instructions=payload.delivery_instructions or "",
            client_req_id=payload.client_req_id,
        )
        return 201, CheckoutOut(order_id=o.id, status=o.status, total=o.total)

    except ExitError as e:
        # Falta de stock (FEFO) -> 409
        return 409, {"error": e.code, "message": str(e)}

    except ValidationError as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}

    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}


@router.get("/orders", response={200: OrdersPageOut, 400: ErrorOut})
def list_orders(
    request,
    status: Optional[str] = None,            # draft|placed
    customer_id: Optional[int] = None,       # filtra por cliente
    page: int = 1,
    page_size: int = 20,
):
    """
    Lista órdenes con filtros simples. Devuelve totales y página.
    """
    page, page_size = _clamp_page(page, page_size)

    qs: QuerySet[Order] = (
        Order.objects.select_related("customer")
        .order_by("-id")
    )
    if status:
        if status not in (Order.Status.DRAFT, Order.Status.PLACED):
            return 400, {"error": "VALIDATION_ERROR", "message": "status inválido"}
        qs = qs.filter(status=status)
    if customer_id:
        qs = qs.filter(customer_id=customer_id)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size

    items = [
        OrderListItem(
            id=o.id,
            customer_id=o.customer_id,
            customer_name=o.customer.name,
            status=o.status,
            total=str(o.total),
            created_at=o.created_at,
        )
        for o in qs[start:end]
    ]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/orders/{order_id}", response={200: OrderDetailOut, 404: ErrorOut})
def get_order(request, order_id: int):
    """
    Devuelve una orden con sus ítems y el snapshot de entrega.
    """
    o: Order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("orderitem_set__product"),
        id=order_id,
    )

    items: List[OrderItemOut] = []
    for it in o.orderitem_set.all():
        items.append(
            OrderItemOut(
                product_id=it.product_id,
                code=it.product.code,
                name=it.product.name,
                qty=str(it.qty),
                unit_price=str(it.unit_price),
                benefit_applied=it.benefit_applied or None,
            )
        )

    return {
        "id": o.id,
        "customer": {"id": o.customer_id, "name": o.customer.name},
        "status": o.status,
        "delivery_method": o.delivery_method,
        "delivery_address_text": o.delivery_address_text or "",
        "delivery_window_from": o.delivery_window_from.isoformat() if o.delivery_window_from else None,
        "delivery_window_to": o.delivery_window_to.isoformat() if o.delivery_window_to else None,
        "requested_delivery_date": o.requested_delivery_date.isoformat() if o.requested_delivery_date else None,
        "delivery_instructions": o.delivery_instructions or "",
        "items": items,
        "subtotal": str(o.subtotal),
        "discount_total": str(o.discount_total),
        "tax_total": str(o.tax_total),
        "total": str(o.total),
        "created_at": o.created_at,
    }