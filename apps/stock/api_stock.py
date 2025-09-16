# api/stock.py
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.db.models import Sum
import os

from apps.catalog.models import Product
from apps.stock.models import StockLot

router = Router(tags=["stock"])

# ===== Schemas =====
class ProductMini(Schema):
    id: int
    code: str
    name: str

class LotOut(Schema):
    id: int
    lot_code: str
    expiry_date: date
    qty_on_hand: Decimal
    warehouse: Optional[str] = None
    near_expiry: bool
    days_to_expiry: int

class StockOut(Schema):
    product: ProductMini
    on_hand_total: Decimal
    low_stock: bool
    lots: List[LotOut]

class ErrorOut(Schema):
    error: str
    message: str

# ===== Endpoint =====
@router.get("/stock/{product_id}", response={200: StockOut, 404: ErrorOut})
def get_stock_by_product(request, product_id: int):
    """
    Devuelve los lotes de un producto ordenados por expiry (FEFO),
    con total en mano y flags: near_expiry y low_stock.
    """
    product = get_object_or_404(Product, id=product_id)

    # Parámetros (usar ENV si existen; defaults razonables)
    NEAR_EXPIRY_DAYS = int(os.getenv("NEAR_EXPIRY_DAYS", "30"))
    LOW_STOCK_DEFAULT = Decimal(os.getenv("LOW_STOCK_THRESHOLD_DEFAULT", "5"))
    low_stock_threshold = product.low_stock_threshold or LOW_STOCK_DEFAULT

    # Traer lotes (orden FEFO) y calcular flags
    today = date.today()
    limit = today + timedelta(days=NEAR_EXPIRY_DAYS)

    lots_qs = (
        StockLot.objects
        .select_related("warehouse")
        .filter(product=product)
        .order_by("expiry_date", "id")
    )

    lots_out: List[LotOut] = []
    on_hand_total = Decimal("0")
    for lot in lots_qs:
        qty = lot.qty_on_hand or 0
        on_hand_total += qty
        dte = (lot.expiry_date - today).days
        lots_out.append(
            LotOut(
                id=lot.id,
                lot_code=lot.lot_code,
                expiry_date=lot.expiry_date,
                qty_on_hand=qty,
                warehouse=(lot.warehouse.name if getattr(lot, "warehouse_id", None) else None),
                near_expiry=(lot.expiry_date <= limit),
                days_to_expiry=dte,
            )
        )

    return {
        "product": ProductMini(id=product.id, code=product.code, name=product.name),
        "on_hand_total": on_hand_total,
        "low_stock": on_hand_total <= low_stock_threshold,
        "lots": lots_out,
    }