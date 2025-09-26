"""API endpoints for stock operations."""

from datetime import date
from decimal import Decimal
from typing import Optional, List

from ninja import Router, Schema, Query
from django.http import HttpRequest, Http404
from django.shortcuts import get_object_or_404

from apps.catalog.models import Product
from .models import Warehouse, StockLot, Movement
from .services import create_entry, create_exit, StockError, NotEnoughStock, NoLotsAvailable
from .idempotency_service import IdempotencyService

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

@router.get("/health")
def stock_health(request) -> dict:
    """Health check endpoint for stock module."""
    return {"status": "ok", "module": "stock"}

@router.post("/entry", response={201: EntryOut, 400: ErrorOut, 404: ErrorOut})
def create_stock_entry(request: HttpRequest, payload: EntryIn):
    """
    Crea una entrada de stock de forma transaccional.
    
    - Busca o crea el lote según (product, lot_code, warehouse)
    - Incrementa qty_on_hand del lote
    - Crea Movement de tipo ENTRY
    - Validaciones: qty > 0, unit_cost > 0, consistencia de fechas
    - Soporta idempotencia mediante Idempotency-Key header
    """
    try:
        # Check for idempotency key
        idempotency_key = IdempotencyService.get_idempotency_key(request)
        if not idempotency_key:
            return 400, {"error": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"}
        
        # Prepare request data for idempotency check
        request_data = {
            "product_id": payload.product_id,
            "lot_code": payload.lot_code,
            "expiry_date": payload.expiry_date.isoformat(),
            "qty": str(payload.qty),
            "unit_cost": str(payload.unit_cost),
            "warehouse_id": payload.warehouse_id,
            "reason": payload.reason,
        }
        
        # Check if this request was already processed
        existing_response = IdempotencyService.check_existing_request(
            idempotency_key, "entry", request_data
        )
        if existing_response:
            status_code, response_data = existing_response
            return status_code, response_data
        
        # Obtener objetos
        product = get_object_or_404(Product, id=payload.product_id)
        warehouse = get_object_or_404(Warehouse, id=payload.warehouse_id)
        
        # Crear entrada usando el servicio transaccional
        movement = create_entry(
            product=product,
            lot_code=payload.lot_code,
            expiry_date=payload.expiry_date,
            qty=payload.qty,
            unit_cost=payload.unit_cost,
            warehouse=warehouse,
            reason=payload.reason,
            created_by=getattr(request, 'user', None)
        )
        
        response_data = {
            "movement_id": movement.id,
            "lot_id": movement.lot.id,
            "product_id": movement.product.id,
            "lot_code": movement.lot.lot_code,
            "new_qty_on_hand": float(movement.lot.qty_on_hand),
            "warehouse_name": warehouse.name
        }
        
        # Store response for idempotency
        IdempotencyService.store_response(
            idempotency_key, "entry", request_data, 201, response_data,
            created_by=getattr(request, 'user', None)
        )
        
        return 201, EntryOut(**response_data)
        
    except ValueError as e:
        # Idempotency validation error
        error_data = {"error": "IDEMPOTENCY_ERROR", "message": str(e)}
        return 400, error_data
    except StockError as e:
        error_data = {"error": e.code, "message": str(e)}
        # Store error response for idempotency
        try:
            IdempotencyService.store_response(
                idempotency_key, "entry", request_data, 400, error_data,
                created_by=getattr(request, 'user', None)
            )
        except:
            pass  # Don't fail the request if idempotency storage fails
        return 400, error_data
    except Http404 as e:
        error_data = {"error": "NOT_FOUND", "message": str(e)}
        # Store 404 error response for idempotency
        try:
            IdempotencyService.store_response(
                idempotency_key, "entry", request_data, 404, error_data,
                created_by=getattr(request, 'user', None)
            )
        except:
            pass  # Don't fail the request if idempotency storage fails
        return 404, error_data
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data

@router.post("/exit", response={201: ExitOut, 400: ErrorOut, 404: ErrorOut})
def create_stock_exit(request: HttpRequest, payload: ExitIn):
    """
    Crea una salida de stock siguiendo FEFO de forma transaccional.
    
    - Selecciona lotes disponibles ordenados por FEFO
    - Puede generar múltiples movimientos si se necesitan varios lotes
    - Validaciones: qty > 0, stock suficiente disponible
    - Respeta is_quarantined=False y is_reserved=False
    - Soporta idempotencia mediante Idempotency-Key header
    """
    try:
        # Check for idempotency key
        idempotency_key = IdempotencyService.get_idempotency_key(request)
        if not idempotency_key:
            return 400, {"error": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"}
        
        # Prepare request data for idempotency check
        request_data = {
            "product_id": payload.product_id,
            "qty_total": str(payload.qty_total),
            "warehouse_id": payload.warehouse_id,
            "reason": payload.reason,
        }
        
        # Check if this request was already processed
        existing_response = IdempotencyService.check_existing_request(
            idempotency_key, "exit", request_data
        )
        if existing_response:
            status_code, response_data = existing_response
            return status_code, response_data
        
        # Obtener objetos
        product = get_object_or_404(Product, id=payload.product_id)
        warehouse = get_object_or_404(Warehouse, id=payload.warehouse_id)
        
        # Crear salida usando el servicio transaccional FEFO
        movements = create_exit(
            product=product,
            qty_total=payload.qty_total,
            warehouse=warehouse,
            reason=payload.reason,
            created_by=getattr(request, 'user', None)
        )
        
        # Preparar respuesta con detalles de cada movimiento
        movement_details = [
            {
                "movement_id": mv.id,
                "lot_id": mv.lot.id,
                "lot_code": mv.lot.lot_code,
                "qty_taken": float(mv.qty),
                "unit_cost": float(mv.unit_cost),
                "expiry_date": mv.lot.expiry_date.isoformat()
            }
            for mv in movements
        ]
        
        response_data = {
            "total_qty": str(payload.qty_total),  # Keep as string to match Django Ninja response
            "movements": movement_details,
            "warehouse_name": warehouse.name
        }
        
        # Store response for idempotency
        IdempotencyService.store_response(
            idempotency_key, "exit", request_data, 201, response_data,
            created_by=getattr(request, 'user', None)
        )
        
        return 201, ExitOut(
            total_qty=payload.qty_total,
            movements=[ExitMovementOut(**mv) for mv in movement_details],
            warehouse_name=warehouse.name
        )
        
    except ValueError as e:
        # Idempotency validation error
        error_data = {"error": "IDEMPOTENCY_ERROR", "message": str(e)}
        return 400, error_data
    except (NotEnoughStock, NoLotsAvailable) as e:
        error_data = {"error": e.code, "message": str(e)}
        # Store error response for idempotency
        try:
            IdempotencyService.store_response(
                idempotency_key, "exit", request_data, 400, error_data,
                created_by=getattr(request, 'user', None)
            )
        except:
            pass  # Don't fail the request if idempotency storage fails
        return 400, error_data
    except StockError as e:
        error_data = {"error": e.code, "message": str(e)}
        # Store error response for idempotency
        try:
            IdempotencyService.store_response(
                idempotency_key, "exit", request_data, 400, error_data,
                created_by=getattr(request, 'user', None)
            )
        except:
            pass  # Don't fail the request if idempotency storage fails
        return 400, error_data
    except Http404:
        raise
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data

@router.get("/lots", response={200: LotsListOut, 400: ErrorOut, 404: ErrorOut})
def get_stock_lots(
    request: HttpRequest,
    product_id: Optional[int] = Query(None, description="Filtrar por producto"),
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    only_available: bool = Query(False, description="Solo lotes disponibles (no cuarentena/reserva)"),
    limit: int = Query(50, description="Límite de resultados", ge=1, le=200)
):
    """
    Obtiene lista de lotes con filtros y ordenamiento FEFO.
    
    - Filtros: product_id, warehouse_id, only_available
    - Ordenamiento: FEFO (expiry_date ASC, id ASC)
    - Paginación: limit (máximo 200)
    """
    try:
        # Construir queryset base
        queryset = StockLot.objects.select_related('product', 'warehouse')
        
        # Aplicar filtros
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            queryset = queryset.filter(product=product)
            
        if warehouse_id:
            warehouse = get_object_or_404(Warehouse, id=warehouse_id)
            queryset = queryset.filter(warehouse=warehouse)
            
        if only_available:
            queryset = queryset.filter(
                qty_on_hand__gt=0,
                is_quarantined=False,
                is_reserved=False
            )
        
        # Ordenamiento FEFO y límite
        lots = queryset.order_by('expiry_date', 'id')[:limit]
        
        # Preparar respuesta
        lot_data = [
            LotOut(
                id=lot.id,
                lot_code=lot.lot_code,
                expiry_date=lot.expiry_date,
                qty_on_hand=lot.qty_on_hand,
                qty_available=lot.qty_available,
                unit_cost=lot.unit_cost,
                warehouse_name=lot.warehouse.name,
                is_quarantined=lot.is_quarantined,
                is_reserved=lot.is_reserved,
                created_at=lot.created_at.date()
            )
            for lot in lots
        ]
        
        return 200, LotsListOut(
            lots=lot_data,
            total_count=len(lot_data)
        )
        
    except Http404:
        raise
    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}
