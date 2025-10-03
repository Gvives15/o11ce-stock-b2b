"""API endpoints for stock operations."""

from datetime import date
from decimal import Decimal
from typing import Optional, List

from ninja import Router, Schema, Query
from django.http import HttpRequest, Http404
from django.shortcuts import get_object_or_404

from apps.catalog.models import Product
from .models import Warehouse, StockLot, Movement
from .services import (
    validate_stock_availability, request_stock_entry, request_stock_exit,
    create_entry, create_exit, StockError, 
    NotEnoughStock, NoLotsAvailable, handle_stock_validation_request, 
    handle_stock_entry_request, handle_stock_exit_request, 
    handle_legacy_stock_entry, handle_legacy_stock_exit, handle_stock_lots_query
)
from .idempotency_service import IdempotencyService
from apps.events.manager import EventSystemManager

router = Router()

# Schemas
class EntryIn(Schema):
    product_id: int
    lot_code: str
    expiry_date: date
    qty: Decimal
    unit_cost: Decimal
    warehouse_id: int
    reason: Optional[str] = Movement.Reason.PURCHASE

class EntryOut(Schema):
    movement_id: int
    lot_id: int
    product_id: int
    lot_code: str
    new_qty_on_hand: Decimal
    warehouse_name: str

class ExitIn(Schema):
    product_id: int
    qty_total: Decimal
    warehouse_id: int
    reason: Optional[str] = Movement.Reason.SALE

class ExitMovementOut(Schema):
    movement_id: int
    lot_id: int
    lot_code: str
    qty_taken: Decimal
    unit_cost: Decimal
    expiry_date: date

class ExitOut(Schema):
    total_qty: Decimal
    movements: List[ExitMovementOut]
    warehouse_name: str

class LotOut(Schema):
    id: int
    lot_code: str
    expiry_date: date
    qty_on_hand: Decimal
    qty_available: Decimal
    unit_cost: Decimal
    warehouse_name: str
    is_quarantined: bool
    is_reserved: bool
    created_at: date

class LotsListOut(Schema):
    lots: List[LotOut]
    total_count: int

class ErrorOut(Schema):
    error: str
    message: str

# New event-driven endpoints (v2)

@router.post("/v2/entry", response={202: dict, 400: ErrorOut, 404: ErrorOut})
def request_stock_entry_v2(request: HttpRequest, payload: EntryIn):
    """
    Solicita una entrada de stock usando eventos (v2 - event-driven).
    
    - Publica StockEntryRequested event
    - Procesamiento asíncrono mediante event handlers
    - Respuesta inmediata con event_id para tracking
    - Idempotencia mediante Idempotency-Key header
    """
    # Check for idempotency key
    idempotency_key = IdempotencyService.get_idempotency_key(request)
    if not idempotency_key:
        return 400, {"error": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"}
    
    status_code, response_data = handle_stock_entry_request(
        request_user=getattr(request, 'user', None),
        payload_data={
            "product_id": payload.product_id,
            "lot_code": payload.lot_code,
            "expiry_date": payload.expiry_date,
            "qty": payload.qty,
            "unit_cost": payload.unit_cost,
            "warehouse_id": payload.warehouse_id,
            "reason": payload.reason,
        },
        idempotency_key=idempotency_key
    )
    
    return status_code, response_data


@router.post("/v2/exit", response={202: dict, 400: ErrorOut, 404: ErrorOut})
def request_stock_exit_v2(request: HttpRequest, payload: ExitIn):
    """
    Solicita una salida de stock usando eventos (v2 - event-driven).
    
    - Publica StockExitRequested event
    - Procesamiento asíncrono mediante event handlers
    - Respuesta inmediata con event_id para tracking
    - Idempotencia mediante Idempotency-Key header
    """
    # Check for idempotency key
    idempotency_key = IdempotencyService.get_idempotency_key(request)
    if not idempotency_key:
        return 400, {"error": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"}
    
    status_code, response_data = handle_stock_exit_request(
        request_user=getattr(request, 'user', None),
        payload_data={
            "product_id": payload.product_id,
            "qty_total": payload.qty_total,
            "warehouse_id": payload.warehouse_id,
            "reason": payload.reason,
        },
        idempotency_key=idempotency_key
    )
    
    return status_code, response_data





@router.get("/validate-availability", response={200: dict, 400: ErrorOut, 404: ErrorOut})
def validate_stock_availability_endpoint(
    request: HttpRequest,
    product_id: int = Query(..., description="ID del producto"),
    qty: Decimal = Query(..., description="Cantidad a validar"),
    warehouse_id: Optional[int] = Query(None, description="ID del depósito")
):
    """
    Endpoint directo para validar disponibilidad de stock.
    Expone la función validate_stock_availability del módulo de servicios.
    """
    # Generate correlation ID for tracking
    import uuid
    correlation_id = str(uuid.uuid4())
    
    status_code, response_data = handle_stock_validation_request(
        product_id=product_id,
        qty=qty,
        warehouse_id=warehouse_id,
        correlation_id=correlation_id
    )
    
    return status_code, response_data


@router.get("/v2/validate/{product_id}", response={200: dict, 400: ErrorOut, 404: ErrorOut})
def validate_stock_v2(
    request: HttpRequest,
    product_id: int,
    qty: Decimal = Query(..., description="Cantidad a validar"),
    warehouse_id: Optional[int] = Query(None, description="ID del depósito")
):
    """
    Valida disponibilidad de stock usando eventos (v2 - event-driven).
    
    - Publica StockValidationRequested event
    - Procesamiento asíncrono mediante event handlers
    - Respuesta inmediata con event_id para tracking
    """
    # Generate correlation ID for tracking
    import uuid
    correlation_id = str(uuid.uuid4())
    
    status_code, response_data = handle_stock_validation_request(
        product_id=product_id,
        qty=qty,
        warehouse_id=warehouse_id,
        correlation_id=correlation_id
    )
    
    return status_code, response_data


# Legacy endpoints (v1 - deprecated but maintained for backward compatibility)

@router.get("/health")
def stock_health(request) -> dict:
    """Health check endpoint for stock module."""
    return {"status": "ok", "module": "stock", "version": "2.0.0"}

@router.post("/entry", response={201: EntryOut, 400: ErrorOut, 404: ErrorOut})
def create_stock_entry(request: HttpRequest, payload: EntryIn):
    """
    LEGACY: Crea una entrada de stock de forma transaccional.
    DEPRECATED: Usar /v2/entry para nuevas implementaciones.
    
    - Busca o crea el lote según (product, lot_code, warehouse)
    - Incrementa qty_on_hand del lote
    - Crea Movement de tipo ENTRY
    - Validaciones: qty > 0, unit_cost > 0, consistencia de fechas
    - Soporta idempotencia mediante Idempotency-Key header
    """
    # Check for idempotency key
    idempotency_key = IdempotencyService.get_idempotency_key(request)
    if not idempotency_key:
        return 400, {"error": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"}
    
    status_code, response_data = handle_legacy_stock_entry(
        request_user=getattr(request, 'user', None),
        payload_data={
            "product_id": payload.product_id,
            "lot_code": payload.lot_code,
            "expiry_date": payload.expiry_date,
            "qty": payload.qty,
            "unit_cost": payload.unit_cost,
            "warehouse_id": payload.warehouse_id,
            "reason": payload.reason,
        },
        idempotency_key=idempotency_key
    )
    
    return status_code, response_data

@router.post("/exit", response={201: ExitOut, 400: ErrorOut, 404: ErrorOut})
def create_stock_exit(request: HttpRequest, payload: ExitIn):
    """
    LEGACY: Crea una salida de stock siguiendo FEFO de forma transaccional.
    DEPRECATED: Usar /v2/exit para nuevas implementaciones.
    
    - Selecciona lotes disponibles ordenados por FEFO
    - Puede generar múltiples movimientos si se necesitan varios lotes
    - Validaciones: qty > 0, stock suficiente disponible
    - Respeta is_quarantined=False y is_reserved=False
    - Soporta idempotencia mediante Idempotency-Key header
    """
    # Check for idempotency key
    idempotency_key = IdempotencyService.get_idempotency_key(request)
    if not idempotency_key:
        return 400, {"error": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"}
    
    status_code, response_data = handle_legacy_stock_exit(
        request_user=getattr(request, 'user', None),
        payload_data={
            "product_id": payload.product_id,
            "qty_total": payload.qty_total,
            "warehouse_id": payload.warehouse_id,
            "reason": payload.reason,
        },
        idempotency_key=idempotency_key
    )
    
    return status_code, response_data

@router.get("/lots", response={200: LotsListOut, 400: ErrorOut, 404: ErrorOut})
def get_stock_lots(
    request: HttpRequest,
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    only_available: bool = Query(False, description="Solo lotes disponibles (no cuarentena/reserva)"),
    limit: int = Query(50, description="Límite de resultados", ge=1, le=200)
):
    """
    LEGACY: Obtiene lista de lotes con filtros y ordenamiento FEFO.
    
    - Filtros: product_id, warehouse_id, only_available
    - Ordenamiento: FEFO (expiry_date ASC, id ASC)
    - Paginación: limit (máximo 200)
    """
    try:
        status_code, response_data = handle_stock_lots_query(
            product_id=product_id,
            warehouse_id=warehouse_id,
            only_available=only_available,
            limit=limit
        )
        
        if status_code == 200:
            # Convertir los datos a objetos LotsListOut
            lot_objects = [
                LotOut(**lot_data) for lot_data in response_data["lots"]
            ]
            return status_code, LotsListOut(
                lots=lot_objects,
                total_count=response_data["total_count"]
            )
        else:
            return status_code, response_data
            
    except Http404:
        raise
    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}
