# apps/stock/services.py
import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, NamedTuple, Tuple

from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.http import Http404

from apps.catalog.models import Product
from .models import StockLot, Movement, Warehouse
from apps.events.manager import EventSystemManager
from apps.core.events import EventBus
from apps.stock.events import (
    StockEntryRequested, StockExitRequested, StockValidationRequested,
    WarehouseValidationRequested
)
from .idempotency_service import IdempotencyService

logger = logging.getLogger(__name__)


# API Service Layer - Funciones para manejar lógica de endpoints

def handle_stock_validation_request(
    product_id: int,
    qty: Decimal,
    warehouse_id: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de validación de stock para endpoints.
    
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Validate that product exists
        product = get_object_or_404(Product, id=product_id)
        
        if warehouse_id:
            warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Request stock validation via events
        event_id = validate_stock_availability(
            product_id=product_id,
            qty=qty,
            warehouse_id=warehouse_id,
            correlation_id=correlation_id
        )
        
        response_data = {
            "event_id": event_id,
            "status": "validation_requested",
            "message": "Stock validation request submitted successfully",
            "correlation_id": correlation_id
        }
        
        return 200, response_data
        
    except Http404 as e:
        error_data = {"error": "NOT_FOUND", "message": str(e)}
        return 404, error_data
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data


def handle_stock_entry_request(
    request_user,
    payload_data: Dict[str, Any],
    idempotency_key: str,
    operation_type: str = "entry_v2"
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de entrada de stock para endpoints.
    
    Args:
        request_user: Usuario de la request
        payload_data: Datos del payload
        idempotency_key: Clave de idempotencia
        operation_type: Tipo de operación para idempotencia
        
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Prepare request data for idempotency check
        request_data = {
            "product_id": payload_data["product_id"],
            "lot_code": payload_data["lot_code"],
            "expiry_date": payload_data["expiry_date"].isoformat() if hasattr(payload_data["expiry_date"], 'isoformat') else str(payload_data["expiry_date"]),
            "qty": str(payload_data["qty"]),
            "unit_cost": str(payload_data["unit_cost"]),
            "warehouse_id": payload_data["warehouse_id"],
            "reason": payload_data.get("reason", Movement.Reason.PURCHASE),
        }
        
        # Check if this request was already processed
        existing_response = IdempotencyService.check_existing_request(
            idempotency_key, operation_type, request_data
        )
        if existing_response:
            return existing_response
        
        # Validate that product and warehouse exist
        product = get_object_or_404(Product, id=payload_data["product_id"])
        warehouse = get_object_or_404(Warehouse, id=payload_data["warehouse_id"])
        
        # Request stock entry via events
        event_id = request_stock_entry(
            product_id=payload_data["product_id"],
            lot_code=payload_data["lot_code"],
            expiry_date=payload_data["expiry_date"],
            qty=payload_data["qty"],
            unit_cost=payload_data["unit_cost"],
            user_id=getattr(request_user, 'id', None) if hasattr(request_user, 'id') else None,
            warehouse_id=payload_data["warehouse_id"],
            correlation_id=idempotency_key
        )
        
        response_data = {
            "event_id": event_id,
            "status": "requested",
            "message": "Stock entry request submitted successfully",
            "correlation_id": idempotency_key
        }
        
        # Store response for idempotency
        IdempotencyService.store_response(
            idempotency_key, operation_type, request_data, 202, response_data,
            created_by=request_user if hasattr(request_user, 'id') else None
        )
        
        return 202, response_data
        
    except ValueError as e:
        error_data = {"error": "IDEMPOTENCY_ERROR", "message": str(e)}
        return 400, error_data
    except Http404 as e:
        error_data = {"error": "NOT_FOUND", "message": str(e)}
        return 404, error_data
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data


def handle_stock_exit_request(
    request_user,
    payload_data: Dict[str, Any],
    idempotency_key: str,
    operation_type: str = "exit_v2"
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de salida de stock para endpoints.
    
    Args:
        request_user: Usuario de la request
        payload_data: Datos del payload
        idempotency_key: Clave de idempotencia
        operation_type: Tipo de operación para idempotencia
        
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Prepare request data for idempotency check
        request_data = {
            "product_id": payload_data["product_id"],
            "qty_total": str(payload_data["qty_total"]),
            "warehouse_id": payload_data["warehouse_id"],
            "reason": payload_data.get("reason", Movement.Reason.SALE),
        }
        
        # Check if this request was already processed
        existing_response = IdempotencyService.check_existing_request(
            idempotency_key, operation_type, request_data
        )
        if existing_response:
            return existing_response
        
        # Validate that product and warehouse exist
        product = get_object_or_404(Product, id=payload_data["product_id"])
        warehouse = get_object_or_404(Warehouse, id=payload_data["warehouse_id"])
        
        # Request stock exit via events
        event_id = request_stock_exit(
            product_id=payload_data["product_id"],
            qty=payload_data["qty_total"],
            user_id=getattr(request_user, 'id', None) if hasattr(request_user, 'id') else None,
            warehouse_id=payload_data["warehouse_id"],
            correlation_id=idempotency_key
        )
        
        response_data = {
            "event_id": event_id,
            "status": "requested",
            "message": "Stock exit request submitted successfully",
            "correlation_id": idempotency_key
        }
        
        # Store response for idempotency
        IdempotencyService.store_response(
            idempotency_key, operation_type, request_data, 202, response_data,
            created_by=request_user if hasattr(request_user, 'id') else None
        )
        
        return 202, response_data
        
    except ValueError as e:
        error_data = {"error": "IDEMPOTENCY_ERROR", "message": str(e)}
        return 400, error_data
    except Http404 as e:
        error_data = {"error": "NOT_FOUND", "message": str(e)}
        return 404, error_data
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data


def handle_legacy_stock_entry(
    request_user,
    payload_data: Dict[str, Any],
    idempotency_key: str
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de entrada de stock legacy para endpoints.
    
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Prepare request data for idempotency check
        request_data = {
            "product_id": payload_data["product_id"],
            "lot_code": payload_data["lot_code"],
            "expiry_date": payload_data["expiry_date"].isoformat() if hasattr(payload_data["expiry_date"], 'isoformat') else str(payload_data["expiry_date"]),
            "qty": str(payload_data["qty"]),
            "unit_cost": str(payload_data["unit_cost"]),
            "warehouse_id": payload_data["warehouse_id"],
            "reason": payload_data.get("reason", Movement.Reason.PURCHASE),
        }
        
        # Check if this request was already processed
        existing_response = IdempotencyService.check_existing_request(
            idempotency_key, "entry", request_data
        )
        if existing_response:
            return existing_response
        
        # Obtener objetos
        product = get_object_or_404(Product, id=payload_data["product_id"])
        warehouse = get_object_or_404(Warehouse, id=payload_data["warehouse_id"])
        
        # Crear entrada usando el servicio transaccional
        movement = create_entry(
            product=product,
            lot_code=payload_data["lot_code"],
            expiry_date=payload_data["expiry_date"],
            qty=payload_data["qty"],
            unit_cost=payload_data["unit_cost"],
            warehouse=warehouse,
            reason=payload_data.get("reason", Movement.Reason.PURCHASE),
            created_by=request_user if hasattr(request_user, 'id') else None
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
            created_by=request_user if hasattr(request_user, 'id') else None
        )
        
        return 201, response_data
        
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
                created_by=request_user if hasattr(request_user, 'id') else None
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
                created_by=request_user if hasattr(request_user, 'id') else None
            )
        except:
            pass  # Don't fail the request if idempotency storage fails
        return 404, error_data
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data


def handle_legacy_stock_exit(
    request_user,
    payload_data: Dict[str, Any],
    idempotency_key: str
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de salida de stock legacy para endpoints.
    
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Prepare request data for idempotency check
        request_data = {
            "product_id": payload_data["product_id"],
            "qty_total": str(payload_data["qty_total"]),
            "warehouse_id": payload_data["warehouse_id"],
            "reason": payload_data.get("reason", Movement.Reason.SALE),
        }
        
        # Check if this request was already processed
        existing_response = IdempotencyService.check_existing_request(
            idempotency_key, "exit", request_data
        )
        if existing_response:
            return existing_response
        
        # Obtener objetos
        product = get_object_or_404(Product, id=payload_data["product_id"])
        warehouse = get_object_or_404(Warehouse, id=payload_data["warehouse_id"])
        
        # Crear salida usando el servicio transaccional FEFO
        movements = create_exit(
            product=product,
            qty_total=payload_data["qty_total"],
            warehouse=warehouse,
            reason=payload_data.get("reason", Movement.Reason.SALE),
            created_by=request_user if hasattr(request_user, 'id') else None
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
            "total_qty": str(payload_data["qty_total"]),  # Keep as string to match Django Ninja response
            "movements": movement_details,
            "warehouse_name": warehouse.name
        }
        
        # Store response for idempotency
        IdempotencyService.store_response(
            idempotency_key, "exit", request_data, 201, response_data,
            created_by=request_user if hasattr(request_user, 'id') else None
        )
        
        return 201, response_data
        
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
                created_by=request_user if hasattr(request_user, 'id') else None
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
                created_by=request_user if hasattr(request_user, 'id') else None
            )
        except:
            pass  # Don't fail the request if idempotency storage fails
        return 400, error_data
    except Http404:
        raise
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data


def handle_stock_lots_query(
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    only_available: bool = False,
    limit: int = 50
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de consulta de lotes de stock para endpoints.
    
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
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
            {
                "id": lot.id,
                "lot_code": lot.lot_code,
                "expiry_date": lot.expiry_date,
                "qty_on_hand": lot.qty_on_hand,
                "qty_available": lot.qty_available,
                "unit_cost": lot.unit_cost,
                "warehouse_name": lot.warehouse.name,
                "is_quarantined": lot.is_quarantined,
                "is_reserved": lot.is_reserved,
                "created_at": lot.created_at.date()
            }
            for lot in lots
        ]
        
        response_data = {
            "lots": lot_data,
            "total_count": len(lot_data)
        }
        
        return 200, response_data
        
    except Http404:
        raise
    except Exception as e:
        error_data = {"error": "VALIDATION_ERROR", "message": str(e)}
        return 400, error_data


# Event-driven service functions (new approach)

def request_stock_entry(
    product_id: int,
    lot_code: str,
    expiry_date: date,
    qty: Decimal,
    unit_cost: Decimal,
    user_id: int,
    warehouse_id: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> str:
    """
    Solicita una entrada de stock usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = StockEntryRequested(
        product_id=product_id,
        lot_code=lot_code,
        expiry_date=expiry_date,
        qty=qty,
        unit_cost=unit_cost,
        user_id=user_id,
        warehouse_id=warehouse_id,
        correlation_id=correlation_id
    )
    
    event_manager = EventSystemManager()
    return EventBus.publish(event)


def request_stock_exit(
    product_id: int,
    qty: Decimal,
    user_id: int,
    order_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> str:
    """
    Solicita una salida de stock usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = StockExitRequested(
        product_id=product_id,
        qty=qty,
        user_id=user_id,
        order_id=order_id,
        warehouse_id=warehouse_id,
        correlation_id=correlation_id
    )
    
    event_manager = EventSystemManager()
    return EventBus.publish(event)


def validate_stock_availability(
    product_id: int,
    qty: Decimal,
    warehouse_id: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> str:
    """
    Valida disponibilidad de stock usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = StockValidationRequested(
        product_id=product_id,
        qty=qty,
        warehouse_id=warehouse_id,
        correlation_id=correlation_id
    )
    
    event_manager = EventSystemManager()
    return EventBus.publish(event)


def validate_warehouse(
    warehouse_id: int,
    correlation_id: Optional[str] = None
) -> str:
    """
    Valida un depósito usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = WarehouseValidationRequested(
        warehouse_id=warehouse_id,
        correlation_id=correlation_id
    )
    
    event_manager = EventSystemManager()
    return EventBus.publish(event)


# Tipos auxiliares

class LotOption(NamedTuple):
    """Opción de lote disponible para selección."""
    lot_id: int
    lot_code: str
    expiry_date: date
    qty_available: Decimal
    unit_cost: Decimal
    warehouse_name: Optional[str]


class AllocationPlan(NamedTuple):
    """Plan de asignación de lotes."""
    lot_id: int
    qty_allocated: Decimal


# Legacy service functions (maintained for backward compatibility)
# These will be gradually phased out as consumers migrate to event-driven approach

class StockError(Exception):
    """Errores de negocio para operaciones de stock."""
    code: str
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class NotEnoughStock(StockError):
    """Excepción cuando no hay suficiente stock disponible."""
    def __init__(self, product_id: int, requested: Decimal, available: Decimal):
        message = f"Stock insuficiente para producto {product_id}. Solicitado: {requested}, disponible: {available}"
        super().__init__("NOT_ENOUGH_STOCK", message)
        self.product_id = product_id
        self.requested = requested
        self.available = available


class NoLotsAvailable(StockError):
    """Excepción cuando no hay lotes disponibles que cumplan los criterios."""
    def __init__(self, product_id: int, criteria: str = ""):
        message = f"No hay lotes disponibles para producto {product_id}"
        if criteria:
            message += f" que cumplan: {criteria}"
        super().__init__("NO_LOTS_AVAILABLE", message)
        self.product_id = product_id
        self.criteria = criteria


@transaction.atomic
def create_entry(
    product: Product,
    lot_code: str,
    expiry_date: date,
    qty: Decimal,
    unit_cost: Decimal,
    warehouse: Warehouse,
    reason: str = Movement.Reason.PURCHASE,
    created_by: User = None
) -> Movement:
    """
    Crea una entrada de stock de forma transaccional.
    
    Args:
        product: Producto
        lot_code: Código del lote
        expiry_date: Fecha de vencimiento
        qty: Cantidad a ingresar
        unit_cost: Costo unitario
        warehouse: Depósito
        reason: Motivo del movimiento
        created_by: Usuario que crea el movimiento
    
    Returns:
        Movement creado
        
    Raises:
        ValidationError: Si los datos son inválidos
        StockError: Si hay errores de negocio
    """
    if qty <= 0:
        raise StockError("VALIDATION_ERROR", "La cantidad debe ser mayor a 0")
    
    if unit_cost <= 0:
        raise StockError("VALIDATION_ERROR", "El costo unitario debe ser mayor a 0")
    
    # Buscar o crear el lote
    stock_lot, created = StockLot.objects.get_or_create(
        product=product,
        lot_code=lot_code,
        warehouse=warehouse,
        defaults={
            'expiry_date': expiry_date,
            'unit_cost': unit_cost,
            'qty_on_hand': 0
        }
    )
    
    # Si el lote ya existía, verificar consistencia
    if not created:
        if stock_lot.expiry_date != expiry_date:
            raise StockError(
                "INCONSISTENT_LOT", 
                f"El lote {lot_code} ya existe con fecha de vencimiento {stock_lot.expiry_date}, "
                f"pero se intenta ingresar con fecha {expiry_date}"
            )
    
    # Actualizar cantidad en el lote
    stock_lot.qty_on_hand += qty
    stock_lot.save()
    
    # Crear el movimiento
    movement = Movement.objects.create(
        type=Movement.Type.ENTRY,
        product=product,
        lot=stock_lot,
        qty=qty,
        unit_cost=unit_cost,
        reason=reason,
        created_by=created_by
    )
    
    # Log estructurado
    logger.info(
        "Stock entry created",
        extra={
            'movement_id': movement.id,
            'product_code': product.code,
            'lot_code': lot_code,
            'qty': float(qty),
            'unit_cost': float(unit_cost),
            'warehouse': warehouse.name,
            'reason': reason
        }
    )
    
    return movement


def pick_lots_fefo(
    product: Product,
    qty_needed: Decimal,
    warehouse: Warehouse
) -> List[Dict[str, Any]]:
    """
    Selecciona lotes siguiendo FEFO para una cantidad específica.
    
    Args:
        product: Producto
        qty_needed: Cantidad necesaria
        warehouse: Depósito
    
    Returns:
        Lista de diccionarios con lot_id y qty_to_take
        
    Raises:
        NotEnoughStock: Si no hay suficiente stock disponible
    """
    # Obtener lotes disponibles ordenados por FEFO
    available_lots = StockLot.objects.select_for_update().filter(
        product=product,
        warehouse=warehouse,
        qty_on_hand__gt=0,
        is_quarantined=False,
        is_reserved=False
    ).order_by('expiry_date', 'id')
    
    # Verificar stock total disponible
    total_available = sum(lot.qty_available for lot in available_lots)
    if total_available < qty_needed:
        raise NotEnoughStock(product.id, qty_needed, total_available)
    
    # Planificar asignación FEFO
    allocation_plan = []
    remaining_qty = qty_needed
    
    for lot in available_lots:
        if remaining_qty <= 0:
            break
            
        qty_to_take = min(lot.qty_available, remaining_qty)
        allocation_plan.append({
            'lot_id': lot.id,
            'qty_to_take': qty_to_take
        })
        remaining_qty -= qty_to_take
    
    return allocation_plan


@transaction.atomic
def create_exit(
    product: Product,
    qty_total: Decimal,
    warehouse: Warehouse,
    reason: str = Movement.Reason.SALE,
    created_by: User = None
) -> List[Movement]:
    """
    Crea una salida de stock siguiendo FEFO de forma transaccional.
    Puede generar múltiples movimientos si se necesitan varios lotes.
    
    Args:
        product: Producto
        qty_total: Cantidad total a sacar
        warehouse: Depósito
        reason: Motivo del movimiento
        created_by: Usuario que crea el movimiento
    
    Returns:
        Lista de movimientos creados (uno por lote usado)
        
    Raises:
        NotEnoughStock: Si no hay suficiente stock disponible
        StockError: Si hay errores de negocio
    """
    if qty_total <= 0:
        raise StockError("VALIDATION_ERROR", "La cantidad debe ser mayor a 0")
    
    # Obtener plan de asignación FEFO
    allocation_plan = pick_lots_fefo(product, qty_total, warehouse)
    
    movements = []
    
    for allocation in allocation_plan:
        # Obtener el lote con lock
        lot = StockLot.objects.select_for_update().get(id=allocation['lot_id'])
        qty_to_take = allocation['qty_to_take']
        
        # Verificar que el lote aún tenga stock suficiente
        if lot.qty_on_hand < qty_to_take:
            raise StockError(
                "CONCURRENT_MODIFICATION",
                f"El lote {lot.lot_code} fue modificado concurrentemente. "
                f"Stock actual: {lot.qty_on_hand}, requerido: {qty_to_take}"
            )
        
        # Descontar del lote
        lot.qty_on_hand -= qty_to_take
        lot.save()
        
        # Crear movimiento (unit_cost se toma del lote)
        movement = Movement.objects.create(
            type=Movement.Type.EXIT,
            product=product,
            lot=lot,
            qty=qty_to_take,
            unit_cost=lot.unit_cost,  # Se toma del lote
            reason=reason,
            created_by=created_by
        )
        
        movements.append(movement)
        
        # Log estructurado
        logger.info(
            "Stock exit created",
            extra={
                'movement_id': movement.id,
                'product_code': product.code,
                'lot_code': lot.lot_code,
                'qty': float(qty_to_take),
                'unit_cost': float(lot.unit_cost),
                'warehouse': warehouse.name,
                'reason': reason
            }
        )
    
    return movements


def get_lot_options(
    product: Product, 
    qty: Decimal, 
    min_shelf_life_days: int = 0,
    warehouse_id: Optional[int] = None
) -> List[LotOption]:
    """
    Obtiene opciones de lotes disponibles para un producto.
    
    Args:
        product: Producto para el cual obtener lotes
        qty: Cantidad solicitada (para referencia)
        min_shelf_life_days: Días mínimos de vida útil requeridos
        warehouse_id: ID del depósito (opcional)
    
    Returns:
        Lista de opciones de lotes ordenadas por FEFO
    """
    # Fecha mínima de vencimiento
    min_expiry_date = date.today() + timedelta(days=min_shelf_life_days)
    
    # Query base para lotes disponibles
    lots_query = StockLot.objects.select_related('warehouse').filter(
        product=product,
        qty_on_hand__gt=0,
        expiry_date__gte=min_expiry_date,
        is_quarantined=False,
        is_reserved=False
    )
    
    if warehouse_id is not None:
        lots_query = lots_query.filter(warehouse_id=warehouse_id)
    
    # Orden FEFO estable: expiry_date, id
    lots = lots_query.order_by('expiry_date', 'id')
    
    return [
        LotOption(
            lot_id=lot.id,
            lot_code=lot.lot_code,
            expiry_date=lot.expiry_date,
            qty_available=lot.qty_available,
            unit_cost=lot.unit_cost,
            warehouse_name=lot.warehouse.name if lot.warehouse else None
        )
        for lot in lots
    ]


def allocate_lots_fefo(
    product: Product,
    qty_needed: Decimal,
    chosen_lot_id: Optional[int] = None,
    min_shelf_life_days: int = 0,
    warehouse_id: Optional[int] = None
) -> List[AllocationPlan]:
    """
    Asigna lotes siguiendo FEFO con soporte para override.
    
    Args:
        product: Producto para asignar
        qty_needed: Cantidad total necesaria
        chosen_lot_id: ID del lote específico para override (opcional)
        min_shelf_life_days: Días mínimos de vida útil requeridos
        warehouse_id: ID del depósito (opcional)
    
    Returns:
        Lista de planes de asignación
        
    Raises:
        StockError: Si no hay stock suficiente o el lote es inválido
    """
    if qty_needed <= 0:
        raise StockError("VALIDATION_ERROR", "La cantidad debe ser mayor a 0")
    
    # Fecha mínima de vencimiento
    min_expiry_date = date.today() + timedelta(days=min_shelf_life_days)
    
    # Query base para lotes disponibles (sin filtro de vida útil)
    base_query = StockLot.objects.filter(
        product=product,
        qty_on_hand__gt=0,
        is_quarantined=False,
        is_reserved=False
    )
    
    if warehouse_id is not None:
        base_query = base_query.filter(warehouse_id=warehouse_id)
    
    # Verificar si hay stock disponible sin considerar vida útil
    total_available_any_expiry = sum(lot.qty_available for lot in base_query)
    if total_available_any_expiry < qty_needed:
        raise StockError(
            "INSUFFICIENT_STOCK", 
            f"Stock insuficiente. Solicitado: {qty_needed}, disponible: {total_available_any_expiry}"
        )
    
    # Aplicar filtro de vida útil mínima solo si no hay override de lote específico
    if chosen_lot_id is None:
        base_query = base_query.filter(expiry_date__gte=min_expiry_date)
        
        # Verificar si hay stock suficiente con vida útil adecuada
        total_available_with_shelf_life = sum(lot.qty_available for lot in base_query)
        if total_available_with_shelf_life < qty_needed:
            raise StockError(
                "INSUFFICIENT_SHELF_LIFE", 
                f"Vida útil insuficiente. Solicitado: {qty_needed}, disponible con vida útil adecuada: {total_available_with_shelf_life}"
            )
    
    allocation_plan = []
    remaining_qty = qty_needed
    
    # Si hay override de lote específico
    if chosen_lot_id is not None:
        # Primero verificar que el lote elegido existe y tiene stock
        try:
            chosen_lot = StockLot.objects.get(
                id=chosen_lot_id,
                product=product,
                qty_on_hand__gt=0,
                is_quarantined=False,
                is_reserved=False
            )
        except StockLot.DoesNotExist:
            raise StockError("INVALID_LOT", f"Lote {chosen_lot_id} no válido o sin stock disponible")
        
        # Verificar que el lote elegido cumple con la vida útil mínima solo si no hay cantidad restante
        if chosen_lot.qty_available >= qty_needed and chosen_lot.expiry_date < min_expiry_date:
            raise StockError(
                "INSUFFICIENT_SHELF_LIFE", 
                f"Lote {chosen_lot.lot_code} no cumple vida útil mínima de {min_shelf_life_days} días"
            )
        
        # Asignar del lote elegido lo que se pueda
        qty_from_chosen = min(remaining_qty, chosen_lot.qty_available)
        allocation_plan.append(AllocationPlan(
            lot_id=chosen_lot.id,
            qty_allocated=qty_from_chosen
        ))
        remaining_qty -= qty_from_chosen
    
    # Si aún queda cantidad por asignar, completar con FEFO
    if remaining_qty > 0:
        # Excluir el lote ya usado en el override y aplicar filtro de vida útil
        fefo_query = base_query.order_by('expiry_date', 'id')
        if chosen_lot_id is not None:
            fefo_query = fefo_query.exclude(id=chosen_lot_id)
            # Aplicar filtro de vida útil a los lotes restantes
            fefo_query = fefo_query.filter(expiry_date__gte=min_expiry_date)
        
        for lot in fefo_query:
            if remaining_qty <= 0:
                break
                
            qty_from_lot = min(remaining_qty, lot.qty_available)
            allocation_plan.append(AllocationPlan(
                lot_id=lot.id,
                qty_allocated=qty_from_lot
            ))
            remaining_qty -= qty_from_lot
    
    # Verificar si se pudo asignar toda la cantidad
    if remaining_qty > 0:
        total_available = sum(lot.qty_available for lot in base_query)
        raise StockError(
            "INSUFFICIENT_STOCK", 
            f"Stock insuficiente. Solicitado: {qty_needed}, disponible: {total_available}"
        )
    
    return allocation_plan


class EntryError(Exception):
    """Errores de negocio para entrada de stock."""
    code: str
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@transaction.atomic
def record_entry(
    *,
    product_id: int,
    lot_code: str,
    expiry_date: date,
    qty: Decimal,
    unit_cost: Decimal,
    user_id: int,
    warehouse_id: Optional[int] = None,
) -> Movement:
    """
    LEGACY: Registra entrada de stock directamente.
    DEPRECATED: Usar request_stock_entry() para nuevas implementaciones.
    """
    if qty <= 0:
        raise EntryError("VALIDATION_ERROR", "qty debe ser > 0")

    product = get_object_or_404(Product, id=product_id)
    warehouse = None
    if warehouse_id is not None:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)

    # Buscamos un lote existente por (product, lot_code, warehouse)
    lot = StockLot.objects.select_for_update().filter(
        product=product, lot_code=lot_code, warehouse=warehouse
    ).first()

    if lot:
        # Si ya existe, el expiry_date debe coincidir para evitar inconsistencias
        if lot.expiry_date != expiry_date:
            raise EntryError("LOT_MISMATCH", "El lote existe con otra fecha de vencimiento")
        lot.qty_on_hand = (lot.qty_on_hand or 0) + qty
        # El unit_cost no se recalcula en v1 (simple): solo registramos en Movement
        lot.save(update_fields=["qty_on_hand"])
    else:
        lot = StockLot.objects.create(
            product=product,
            lot_code=lot_code,
            expiry_date=expiry_date,
            qty_on_hand=qty,
            unit_cost=unit_cost,
            warehouse=warehouse,
        )

    # Registramos el movimiento de entrada
    mv = Movement.objects.create(
        type=Movement.Type.ENTRY,
        product=product,
        lot=lot,
        qty=qty,
        unit_cost=unit_cost,
        reason="entry",
        created_by_id=user_id,
    )
    return mv


class ExitError(Exception):
    """Errores de negocio para salida de stock."""
    code: str
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@transaction.atomic
def record_exit_fefo(
    *,
    product_id: int,
    qty: Decimal,
    user_id: int,
    order_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
) -> List[Movement]:
    """
    LEGACY: Registra salida de stock usando FEFO directamente.
    DEPRECATED: Usar request_stock_exit() para nuevas implementaciones.
    """
    if qty <= 0:
        raise ExitError("VALIDATION_ERROR", "qty debe ser > 0")

    product = get_object_or_404(Product, id=product_id)
    warehouse = None
    if warehouse_id is not None:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    
    order = None
    if order_id is not None:
        from apps.orders.models import Order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            # Si la orden no existe, continuamos sin ella
            pass

    # Bloqueamos los lotes del producto (y depósito si aplica) en orden FEFO
    lots_query = StockLot.objects.select_for_update().filter(product=product, qty_on_hand__gt=0)
    if warehouse_id is not None:
        lots_query = lots_query.filter(warehouse=warehouse)
    lots = lots_query.order_by("expiry_date", "id")

    available = sum((l.qty_on_hand for l in lots), Decimal("0"))
    if qty > available:
        raise ExitError("INSUFFICIENT_STOCK", f"Solicitado {qty}, disponible {available}")

    remaining = qty
    movements: List[Movement] = []

    for lot in lots:
        if remaining <= 0:
            break
        take = min(remaining, lot.qty_on_hand)
        if take <= 0:
            continue

        # Descuento del lote
        lot.qty_on_hand = (lot.qty_on_hand or Decimal("0")) - take
        lot.save(update_fields=["qty_on_hand"])

        # Registro del movimiento (exit)
        mv = Movement.objects.create(
            type=Movement.Type.EXIT,
            product=product,
            lot=lot,
            qty=take,
            unit_cost=lot.unit_cost,   # costo del lote para trazabilidad
            reason="checkout" if order_id else "manual_exit",
            order=order,
            created_by_id=user_id,
        )
        movements.append(mv)
        remaining -= take

    return movements
