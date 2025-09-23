"""
API endpoints for order picking and reservation operations.
Handles FEFO-based picking suggestions and stock reservations.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import date

from ninja import Router, Schema
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpRequest

from apps.orders.models import Order
from apps.stock.fefo_services import get_fefo_suggestions, validate_reservation_availability
from apps.stock.reservations import Reservation
from apps.stock.models import StockLot, Movement
from apps.orders.audit import DeliveryAuditLog, DeliveryAuditLogItem

picking_router = Router(tags=["picking"])


# ============================================================================
# SCHEMAS
# ============================================================================

class PickingSuggestionOut(Schema):
    """Schema para sugerencias de picking FEFO."""
    product_id: int
    lot_id: int
    lot_code: str
    qty: Decimal
    expiry_date: date
    unit_cost: Decimal
    warehouse_name: str


class PickingSuggestionsResponse(Schema):
    """Schema para respuesta de sugerencias de picking."""
    order_id: int
    suggestions: List[PickingSuggestionOut]
    total_suggestions: int


class ReservationItemIn(Schema):
    """Schema para item de reserva."""
    lot_id: int
    qty: Decimal


class CreateReservationRequest(Schema):
    """Schema para solicitud de creación de reservas."""
    reservations: List[ReservationItemIn]


class ReservationOut(Schema):
    """Schema para reserva creada."""
    id: int
    lot_id: int
    lot_code: str
    qty: Decimal
    status: str
    created_at: str


class CreateReservationResponse(Schema):
    """Schema para respuesta de creación de reservas."""
    order_id: int
    reservations: List[ReservationOut]
    total_reserved: Decimal


class ErrorResponse(Schema):
    """Schema para respuestas de error."""
    error: str
    detail: str
    availability_check: Dict[str, Any] = {}


class DeliveryMovementOut(Schema):
    """Schema para movimiento de entrega."""
    movement_id: int
    lot_id: int
    lot_code: str
    qty_delivered: Decimal
    unit_cost: Decimal


class DeliveryResponse(Schema):
    """Schema para respuesta de entrega."""
    order_id: int
    movements: List[DeliveryMovementOut]
    total_movements: int
    audit_log_id: int


class DeliveryErrorResponse(Schema):
    """Schema para errores de entrega."""
    error: str
    detail: str
    failed_at_movement: Optional[int] = None


@picking_router.get("/{order_id}/picking/suggestions", response={200: PickingSuggestionsResponse, 404: ErrorResponse})
def get_picking_suggestions(request: HttpRequest, order_id: int):
    """
    Obtiene sugerencias de picking FEFO para una orden.
    
    Devuelve lotes ordenados por FEFO que respetan:
    - Disponible = on_hand - reservas activas
    - Excluye lotes quarantined
    - Excluye lotes vencidos
    - Considera reservas existentes de otras órdenes
    
    Args:
        order_id: ID de la orden
        
    Returns:
        Lista de sugerencias FEFO con información de lotes
        
    Raises:
        404: Si la orden no existe
    """
    # Verificar que la orden existe
    order = get_object_or_404(Order, id=order_id)
    
    # Obtener sugerencias FEFO
    suggestions = get_fefo_suggestions(order)
    
    # Convertir a formato de respuesta
    suggestion_items = [
        PickingSuggestionOut(
            product_id=suggestion.product_id,
            lot_id=suggestion.lot_id,
            lot_code=suggestion.lot_code,
            qty=suggestion.qty,
            expiry_date=suggestion.expiry_date,
            unit_cost=suggestion.unit_cost,
            warehouse_name=suggestion.warehouse_name
        )
        for suggestion in suggestions
    ]
    
    return PickingSuggestionsResponse(
        order_id=order.id,
        suggestions=suggestion_items,
        total_suggestions=len(suggestion_items)
    )


@picking_router.post("/{order_id}/reserve", response={200: CreateReservationResponse, 422: ErrorResponse, 404: ErrorResponse})
def create_reservations(request: HttpRequest, order_id: int, payload: CreateReservationRequest):
    """
    Crea reservas de lotes para una orden de forma transaccional.
    
    Valida que no se supere el stock disponible considerando:
    - disponible = on_hand - reservas activas de otras órdenes
    - Lotes no quarantined
    - Lotes existentes
    
    Args:
        order_id: ID de la orden
        payload: Lista de reservas a crear {lot_id, qty}
        
    Returns:
        Lista de reservas creadas
        
    Raises:
        404: Si la orden no existe
        422: Si se excede el stock disponible
    """
    # Verificar que la orden existe
    order = get_object_or_404(Order, id=order_id)
    
    # Preparar datos de reservas para validación
    reservations_data = [
        {"lot_id": item.lot_id, "qty": item.qty}
        for item in payload.reservations
    ]
    
    # Validar disponibilidad
    validation_result = validate_reservation_availability(order, reservations_data)
    
    if not validation_result['valid']:
        return 422, ErrorResponse(
            error="INSUFFICIENT_STOCK",
            detail="; ".join(validation_result['errors']),
            availability_check=validation_result['availability_check']
        )
    
    # Crear reservas de forma transaccional
    created_reservations = []
    
    try:
        with transaction.atomic():
            # Cancelar reservas existentes para esta orden (si las hay)
            existing_reservations = Reservation.objects.filter(
                order=order,
                status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
            )
            for existing in existing_reservations:
                existing.cancel()
            
            # Eliminar reservas canceladas para evitar conflictos de unique constraint
            Reservation.objects.filter(
                order=order,
                status=Reservation.Status.CANCELLED
            ).delete()
            
            # Crear nuevas reservas
            for item in payload.reservations:
                lot = get_object_or_404(StockLot, id=item.lot_id)
                
                reservation = Reservation.objects.create(
                    order=order,
                    lot=lot,
                    qty=item.qty,
                    status=Reservation.Status.PENDING
                )
                
                created_reservations.append(ReservationOut(
                    id=reservation.id,
                    lot_id=lot.id,
                    lot_code=lot.lot_code,
                    qty=reservation.qty,
                    status=reservation.status,
                    created_at=reservation.created_at.isoformat()
                ))
    
    except Exception as e:
        # En caso de error, devolver 422 con detalles
        return 422, ErrorResponse(
            error="RESERVATION_FAILED",
            detail=f"Error al crear reservas: {str(e)}"
        )
    
    # Calcular total reservado
    total_reserved = sum(item.qty for item in payload.reservations)
    
    return CreateReservationResponse(
        order_id=order.id,
        reservations=created_reservations,
        total_reserved=total_reserved
    )


@picking_router.post("/{order_id}/deliver", response={200: DeliveryResponse, 409: DeliveryErrorResponse, 404: ErrorResponse})
def deliver_order(request: HttpRequest, order_id: int):
    """
    Entrega una orden de forma atómica creando movimientos EXIT desde las reservas.
    
    Proceso:
    1. Valida que la orden existe y tiene reservas activas
    2. Por cada reserva, valida que hay stock suficiente disponible
    3. Crea movimientos EXIT de forma transaccional (todo o nada)
    4. Registra auditoría con quién/cuándo/lotes/cantidades
    5. Actualiza estado de reservas a APPLIED
    
    Args:
        order_id: ID de la orden a entregar
        
    Returns:
        Lista de movimientos creados y auditoría
        
    Raises:
        404: Si la orden no existe
        409: Si no hay stock suficiente (sin efectos secundarios)
    """
    # Verificar que la orden existe
    order = get_object_or_404(Order, id=order_id)
    
    # Obtener reservas activas para la orden
    active_reservations = Reservation.objects.filter(
        order=order,
        status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
    ).select_related('lot', 'lot__product', 'lot__warehouse')
    
    if not active_reservations.exists():
        return 409, DeliveryErrorResponse(
            error="NO_RESERVATIONS",
            detail="La orden no tiene reservas activas para entregar"
        )
    
    # Validar stock disponible antes de crear movimientos
    for i, reservation in enumerate(active_reservations):
        lot = reservation.lot
        
        # Verificar que el lote tiene stock suficiente
        if lot.qty_on_hand < reservation.qty:
            return 409, DeliveryErrorResponse(
                error="INSUFFICIENT_STOCK",
                detail=f"Lote {lot.lot_code} no tiene stock suficiente. Disponible: {lot.qty_on_hand}, Requerido: {reservation.qty}",
                failed_at_movement=i + 1
            )
    
    # Crear movimientos de forma transaccional
    created_movements = []
    audit_log = None
    
    try:
        with transaction.atomic():
            # Crear registro de auditoría
            audit_log = DeliveryAuditLog.objects.create(
                order=order,
                delivered_by=getattr(request, 'user', None),
                status=DeliveryAuditLog.Status.SUCCESS,
                total_movements=len(active_reservations),
                notes=f"Entrega automática de {len(active_reservations)} lotes"
            )
            
            # Crear movimientos EXIT por cada reserva
            for i, reservation in enumerate(active_reservations):
                lot = reservation.lot
                
                # Verificar stock nuevamente con lock (protección contra concurrencia)
                lot = StockLot.objects.select_for_update().get(id=lot.id)
                
                if lot.qty_on_hand < reservation.qty:
                    raise ValueError(f"Stock insuficiente en lote {lot.lot_code} durante transacción")
                
                # Descontar del lote
                lot.qty_on_hand -= reservation.qty
                lot.save(update_fields=['qty_on_hand'])
                
                # Crear movimiento EXIT
                movement = Movement.objects.create(
                    type=Movement.Type.EXIT,
                    product=lot.product,
                    lot=lot,
                    qty=reservation.qty,
                    unit_cost=lot.unit_cost,
                    reason=Movement.Reason.SALE,
                    created_by=getattr(request, 'user', None)
                )
                
                created_movements.append(movement)
                
                # Crear detalle de auditoría
                DeliveryAuditLogItem.objects.create(
                    audit_log=audit_log,
                    lot=lot,
                    qty_delivered=reservation.qty,
                    movement_id=movement.id
                )
                
                # Marcar reserva como aplicada
                reservation.status = Reservation.Status.APPLIED
                reservation.save(update_fields=['status'])
    
    except Exception as e:
        # Actualizar auditoría con error si existe
        if audit_log:
            audit_log.status = DeliveryAuditLog.Status.FAILED
            audit_log.error_details = str(e)
            audit_log.save(update_fields=['status', 'error_details'])
        
        # Determinar en qué movimiento falló
        failed_at = len(created_movements) + 1
        
        return 409, DeliveryErrorResponse(
            error="DELIVERY_FAILED",
            detail=f"Error durante la entrega: {str(e)}",
            failed_at_movement=failed_at
        )
    
    # Preparar respuesta
    movement_details = [
        DeliveryMovementOut(
            movement_id=mv.id,
            lot_id=mv.lot.id,
            lot_code=mv.lot.lot_code,
            qty_delivered=mv.qty,
            unit_cost=mv.unit_cost
        )
        for mv in created_movements
    ]
    
    return DeliveryResponse(
        order_id=order.id,
        movements=movement_details,
        total_movements=len(created_movements),
        audit_log_id=audit_log.id
    )