from decimal import Decimal
from typing import Optional, List
from ninja import Router, Schema

from apps.stock.services import record_exit_fefo, ExitError


router = Router()


class ErrorOut(Schema):
    error: str
    message: str


class ExitIn(Schema):
    product_id: int
    qty: Decimal
    warehouse_id: Optional[int] = None
    order_id: Optional[int] = None  # usado cuando descuenta por checkout


class ExitMovementOut(Schema):
    lot_id: int
    qty: Decimal


class ExitOut(Schema):
    movements: List[ExitMovementOut]


@router.post("/exit", response={200: ExitOut, 400: ErrorOut, 404: ErrorOut, 409: ErrorOut})
def create_exit(request, payload: ExitIn):
    user_id = getattr(getattr(request, "user", None), "id", None) or 1
    try:
        mvs = record_exit_fefo(
            product_id=payload.product_id,
            qty=payload.qty,
            user_id=user_id,
            order_id=payload.order_id,
            warehouse_id=payload.warehouse_id,
        )
        return {
            "movements": [{"lot_id": mv.lot_id, "qty": mv.qty} for mv in mvs]
        }
    except ExitError as e:
        status = 409 if e.code == "INSUFFICIENT_STOCK" else 400
        return status, {"error": e.code, "message": str(e)}