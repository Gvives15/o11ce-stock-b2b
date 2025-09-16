"""API endpoints for stock operations."""

from datetime import date
from decimal import Decimal
from typing import Optional, List

from ninja import Router, Schema, Query
from django.http import HttpRequest, Http404
from django.shortcuts import get_object_or_404

from apps.catalog.models import Product
from .services import record_entry, EntryError, get_lot_options

router = Router()

# Schemas
class EntryIn(Schema):
    product_id: int
    lot_code: str
    expiry_date: date
    qty: Decimal
    unit_cost: Decimal
    warehouse_id: Optional[int] = None

class EntryOut(Schema):
    movement_id: int
    lot_id: int
    product_id: int
    new_qty_on_hand: Decimal

class LotOptionOut(Schema):
    id: int
    lot_code: str
    expiry_date: date
    qty_on_hand: Decimal

class LotOptionsOut(Schema):
    recommended_id: Optional[int]
    options: List[LotOptionOut]

class ErrorOut(Schema):
    error: str
    message: str

@router.get("/health")
def stock_health(request) -> dict:
    """Health check endpoint for stock module."""
    return {"status": "ok", "module": "stock"}

@router.get("/lots/options", response={200: LotOptionsOut, 400: ErrorOut, 404: ErrorOut})
def get_lot_options_endpoint(
    request: HttpRequest,
    product_id: int = Query(..., description="ID del producto"),
    qty: Decimal = Query(..., description="Cantidad solicitada"),
    customer_id: Optional[int] = Query(None, description="ID del cliente (opcional)")
):
    """
    Obtiene opciones de lotes para un producto con recomendación FEFO.
    
    Retorna:
    - recommended_id: ID del lote recomendado (FEFO) o null si no hay lotes
    - options: Lista de lotes disponibles ordenados por FEFO
    """
    # Validaciones
    if qty <= 0:
        return 400, {"error": "INVALID_QTY", "message": "qty inválida"}
    
    try:
        # Verificar que el producto existe
        product = get_object_or_404(Product, id=product_id)
        
        # Obtener opciones de lotes
        lot_options = get_lot_options(product, qty)
        
        # Preparar respuesta
        options = [
            LotOptionOut(
                id=option.lot_id,
                lot_code=option.lot_code,
                expiry_date=option.expiry_date,
                qty_on_hand=option.qty_available
            )
            for option in lot_options
        ]
        
        # El recomendado es el primero (FEFO) si hay opciones
        recommended_id = options[0].id if options else None
        
        return 200, LotOptionsOut(
            recommended_id=recommended_id,
            options=options
        )
    except Http404:
        # Re-lanzar Http404 para que Django Ninja devuelva 404
        raise
    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}

@router.post("/entry", response={201: EntryOut, 400: ErrorOut, 404: ErrorOut, 409: ErrorOut})
def create_entry(request: HttpRequest, payload: EntryIn):
    """
    Carga stock en un LOTE (crea o actualiza).
    Reglas:
    - qty > 0 (400)
    - Si el lote ya existe, el expiry_date debe coincidir (409 LOT_MISMATCH)
    """
    # En MVP, user_id puede venir del request.user.id si hay auth; usamos 1 como placeholder si no hay auth.
    user_id = getattr(getattr(request, "user", None), "id", None) or 1

    try:
        mv = record_entry(
            product_id=payload.product_id,
            lot_code=payload.lot_code,
            expiry_date=payload.expiry_date,
            qty=payload.qty,
            unit_cost=payload.unit_cost,
            user_id=user_id,
            warehouse_id=payload.warehouse_id,
        )
        out = EntryOut(
            movement_id=mv.id,
            lot_id=mv.lot_id,
            product_id=mv.product_id,
            new_qty_on_hand=mv.lot.qty_on_hand,
        )
        return 201, out

    except EntryError as e:
        code = e.code
        status = 409 if code in ("LOT_MISMATCH",) else 400
        return status, {"error": code, "message": str(e)}

    except Exception as e:
        # get_object_or_404 levanta Http404 -> Ninja lo convierte en 404 automáticamente;
        # si llega acá con otra excepción, devolvemos 400 genérico
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}
