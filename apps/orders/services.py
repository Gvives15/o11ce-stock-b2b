# apps/orders/services.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional

from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from apps.catalog.models import Product, Benefit
from apps.customers.models import Customer
from apps.notifications.models import Notification
from .models import Order, OrderItem
from apps.stock.services import record_exit_fefo, ExitError


TWOPLACES = Decimal("0.01")


def _round2(x: Decimal) -> Decimal:
    return x.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass
class PricingInfo:
    unit_base: Decimal
    unit_price: Decimal
    benefit_payload: Optional[dict]


def apply_benefits(product: Product, customer: Customer) -> PricingInfo:
    """
    20/80: aplica el MEJOR descuento porcentual activo por segmento.
    Combos quedan para después (stub).
    """
    today = date.today()
    qs = Benefit.objects.filter(
        is_active=True,
        segment=customer.segment,
        active_from__lte=today,
        active_to__gte=today,
        type="discount",
        value__isnull=False,
    ).order_by("-value")

    unit_base = Decimal(product.price)
    if qs.exists():
        b = qs.first()
        disc = (Decimal(b.value) / Decimal(100))  # ej: 10% => 0.10
        unit_price = _round2(unit_base * (Decimal(1) - disc))
        return PricingInfo(
            unit_base=_round2(unit_base),
            unit_price=unit_price,
            benefit_payload={"id": b.id, "type": b.type, "value": float(b.value)},
        )
    else:
        return PricingInfo(
            unit_base=_round2(unit_base),
            unit_price=_round2(unit_base),
            benefit_payload=None,
        )


@transaction.atomic
def checkout(
    *,
    customer_id: int,
    items: List[Dict],  # [{product_id:int, qty:Decimal}]
    delivery_method: str,  # "delivery" | "pickup"
    delivery_address_text: str = "",
    delivery_window_from=None,
    delivery_window_to=None,
    requested_delivery_date=None,
    delivery_instructions: str = "",
    client_req_id: Optional[str] = None,
) -> Order:
    # --- Idempotencia: verificar si ya existe una orden con este client_req_id ---
    if client_req_id:
        existing_order = Order.objects.filter(client_req_id=client_req_id).first()
        if existing_order:
            return existing_order
    
    # --- Validaciones de entrada ---
    if not items:
        raise ValidationError("items no puede estar vacío")

    if delivery_method not in ("delivery", "pickup"):
        raise ValidationError("delivery_method debe ser 'delivery' o 'pickup'")

    if delivery_method == "delivery" and not delivery_address_text.strip():
        raise ValidationError("delivery_address_text es obligatorio cuando delivery_method='delivery'")

    if delivery_window_from and delivery_window_to and delivery_window_from > delivery_window_to:
        raise ValidationError("delivery_window_from no puede ser mayor a delivery_window_to")

    customer = get_object_or_404(Customer, id=customer_id)

    # --- Preparar totales ---
    subtotal = Decimal("0")
    discount_total = Decimal("0")
    tax_total = Decimal("0")

    # Creamos la Order en draft para tener id y linkear movimientos
    order = Order.objects.create(
        customer=customer,
        status=Order.Status.DRAFT,
        currency="ARS",
        subtotal=Decimal("0"),
        discount_total=Decimal("0"),
        tax_total=Decimal("0"),
        total=Decimal("0"),
        delivery_method=delivery_method,
        delivery_address_text=(delivery_address_text or "").strip(),
        delivery_window_from=delivery_window_from,
        delivery_window_to=delivery_window_to,
        delivery_instructions=delivery_instructions,
        requested_delivery_date=requested_delivery_date,
        client_req_id=client_req_id,
    )

    # --- Ítems: pricing + FEFO exit ---
    for it in items:
        pid = int(it["product_id"])
        qty = Decimal(str(it["qty"]))
        if qty <= 0:
            raise ValidationError(f"qty debe ser > 0 (product_id={pid})")

        product = get_object_or_404(Product, id=pid)

        # Precio final (beneficios)
        pricing = apply_benefits(product, customer)
        unit_price = pricing.unit_price
        unit_base = pricing.unit_base

        # Totales por ítem
        line_subtotal = _round2(unit_price * qty)
        line_discount = _round2((unit_base - unit_price) * qty)
        line_tax = _round2(line_subtotal * Decimal(product.tax_rate) / Decimal(100))

        subtotal += line_subtotal
        discount_total += line_discount
        tax_total += line_tax

        # Crear OrderItem (guardamos precio final y benefit aplicado)
        OrderItem.objects.create(
            order=order,
            product=product,
            qty=qty,
            unit_price=unit_price,
            benefit_applied=pricing.benefit_payload,
        )

        # Descontar stock por FEFO, linkeando movimientos a la orden
        # (si falla -> ExitError => 409, y hace rollback de todo)
        record_exit_fefo(
            product_id=product.id,
            qty=qty,
            user_id=1,           # reemplazar por request.user.id en capa API si hay auth
            order_id=order.id,
            warehouse_id=None,   # soporte multi-depósito opcional
        )

    # --- Cerrar totales ---
    subtotal = _round2(subtotal)
    discount_total = _round2(discount_total)
    tax_total = _round2(tax_total)
    total = _round2(subtotal + tax_total)

    # Marcar placed
    order.subtotal = subtotal
    order.discount_total = discount_total
    order.tax_total = tax_total
    order.total = total
    order.status = Order.Status.PLACED
    order.save(update_fields=["subtotal", "discount_total", "tax_total", "total", "status"])

    # Notificación simple (panel); email/whatsapp quedan para servicio posterior
    Notification.objects.create(
        event=Notification.Event.NEW_ORDER,
        channel=Notification.Channel.PANEL,
        payload={"order_id": order.id, "customer_id": customer_id, "total": str(order.total)},
    )

    return order
