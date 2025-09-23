"""API de órdenes para el panel administrativo"""

from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http import Http404
from ninja import Router
from ninja.security import HttpBearer
from ninja.errors import HttpError
from typing import List, Optional
import logging

from apps.orders.models import Order
from .schemas import (
    OrderListSchema, OrderDetailSchema, OrderListResponse,
    StatusChangeRequest, StatusChangeResponse, OrderItemSchema
)
from .state_mapper import (
    DOMAIN_TO_PANEL, PANEL_TO_DOMAIN, VALID_TRANSITIONS,
    validate_and_map_transition, StateTransitionError
)

logger = logging.getLogger(__name__)

orders_router = Router()

def check_panel_permission(request):
    """Verificar permiso panel_access"""
    # En el contexto de Django Ninja con JWT, el usuario está en request.auth
    user = getattr(request, 'auth', None)
    if not user or not user.has_perm('auth.panel_access'):
        raise PermissionDenied("No tienes permisos para acceder al panel")

@orders_router.get("/", response=OrderListResponse)
def list_orders(request, limit: int = 10, cursor: str = None, status: str = None):
    """Listar todas las órdenes con información básica"""
    check_panel_permission(request)
    
    # Filtrar por estado si se proporciona
    queryset = Order.objects.select_related('customer').prefetch_related('orderitem_set__product')
    
    if status:
        # Convertir estado del panel al dominio
        panel_to_domain = {v: k for k, v in DOMAIN_TO_PANEL.items()}
        domain_status = panel_to_domain.get(status)
        if domain_status:
            queryset = queryset.filter(status=domain_status)
        else:
            # Estado inválido, retornar lista vacía
            return OrderListResponse(
                items=[],
                next_cursor=None,
                has_next=False
            )
    
    # Paginación por cursor
    if cursor:
        try:
            cursor_id = int(cursor)
            queryset = queryset.filter(id__lt=cursor_id)
        except (ValueError, TypeError):
            pass
    
    # Ordenar por ID descendente y limitar
    orders = queryset.order_by('-id')[:limit + 1]  # +1 para saber si hay más
    
    # Verificar si hay más páginas
    has_next = len(orders) > limit
    if has_next:
        orders = orders[:limit]
    
    # Calcular next_cursor
    next_cursor = None
    if has_next and orders:
        next_cursor = str(orders[-1].id)
    
    items = [
        OrderListSchema(
            id=order.id,
            customer={
                'id': order.customer.id,
                'name': order.customer.name,
                'email': getattr(order.customer, 'email', ''),
                'phone': getattr(order.customer, 'phone', '')
            },
            status=DOMAIN_TO_PANEL.get(order.status, order.status),
            total=order.total,
            delivery_method=getattr(order, 'delivery_method', 'PICKUP'),
            requested_delivery_date=getattr(order, 'requested_delivery_date', None),
            created_at=order.created_at,
            items_count=order.orderitem_set.count()
        )
        for order in orders
    ]
    
    return OrderListResponse(
        items=items,
        next_cursor=next_cursor,
        has_next=has_next
    )

@orders_router.get("/{order_id}", response=OrderDetailSchema)
def get_order_detail(request, order_id: int):
    """Obtener detalle de una orden"""
    check_panel_permission(request)
    
    order = get_object_or_404(Order, id=order_id)
    current_panel_status = DOMAIN_TO_PANEL.get(order.status, order.status)
    
    return OrderDetailSchema(
        id=order.id,
        customer={
            'name': order.customer.name,
            'email': getattr(order.customer, 'email', ''),
            'phone': getattr(order.customer, 'phone', '')
        },
        status=current_panel_status,
        currency=order.currency,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        tax_total=order.tax_total,
        total=order.total,
        delivery_method=order.delivery_method,
        delivery_address_text=order.delivery_address_text,
        delivery_window_from=order.delivery_window_from.strftime('%H:%M:%S') if order.delivery_window_from else None,
        delivery_window_to=order.delivery_window_to.strftime('%H:%M:%S') if order.delivery_window_to else None,
        delivery_instructions=order.delivery_instructions,
        requested_delivery_date=order.requested_delivery_date.isoformat() if order.requested_delivery_date else None,
        created_at=order.created_at,
        items=[
                OrderItemSchema(
                    id=item.id,
                    product_code=getattr(item.product, 'code', ''),
                    product_name=item.product.name,
                    qty=item.qty,
                    unit_price=item.unit_price,
                    total_price=item.unit_price * item.qty
                )
                for item in order.orderitem_set.all()
            ],
        valid_next_states=list(VALID_TRANSITIONS.get(current_panel_status, []))
    )

@orders_router.post("/{order_id}/status", response=StatusChangeResponse)
def change_order_status(request, order_id: int, data: StatusChangeRequest):
    """Cambiar el estado de una orden"""
    try:
        check_panel_permission(request)
        
        # Verificar Idempotency-Key
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            raise HttpError(400, "Idempotency-Key header is required")
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise HttpError(404, "Order not found")
        
        # Verificar idempotencia: si ya se procesó esta clave, devolver la respuesta anterior
        # Para simplificar, usamos el client_req_id del modelo Order
        if order.client_req_id == idempotency_key:
            # Ya se procesó esta request, devolver respuesta idempotente
            current_panel_status = DOMAIN_TO_PANEL.get(order.status, order.status)
            # Para idempotencia, necesitamos recordar el estado anterior
            # Como no tenemos historial, asumimos que el cambio ya se hizo
            return StatusChangeResponse(
                id=order.id,
                old_status="NEW",  # Estado inicial típico
                new_status=current_panel_status,
                changed_at=order.updated_at.isoformat() if hasattr(order, 'updated_at') else order.created_at.isoformat(),
                changed_by=request.auth.username if request.auth else ""
            )
        
        # Usar el state mapper para validar la transición
        try:
            current_panel_status_enum, new_domain_status_enum = validate_and_map_transition(
                order.status, data.status
            )
            # Convertir enums a strings para la respuesta
            current_panel_status = current_panel_status_enum.value
            new_domain_status = new_domain_status_enum.value
        except StateTransitionError as e:
            raise HttpError(422, f"Transición inválida: {str(e)}")
        except ValueError as e:
            raise HttpError(422, f"Estado inválido: {str(e)}")
        
        # Actualizar el estado en el dominio y guardar la clave de idempotencia
        order.status = new_domain_status
        order.client_req_id = idempotency_key
        order.save()
        
        # Hook: liberar reservas si la orden se cancela
        if new_domain_status == 'cancelled':
            from apps.stock.reservations import Reservation
            cancelled_reservations = Reservation.objects.filter(
                order=order,
                status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
            )
            for reservation in cancelled_reservations:
                reservation.cancel()
            
            if cancelled_reservations.exists():
                logger.info(f"Released {cancelled_reservations.count()} reservations for cancelled order {order.id}")
        
        # Log de la transición
        logger.info(
            f"Status transition: Order {order.id} from {current_panel_status} to {data.status} "
            f"by {request.auth.username if request.auth else 'unknown'}"
        )
        
        return StatusChangeResponse(
            id=order.id,
            old_status=current_panel_status,
            new_status=data.status,
            changed_at=order.updated_at.isoformat() if hasattr(order, 'updated_at') else order.created_at.isoformat(),
            changed_by=request.auth.username if request.auth else ""
        )
        
    except PermissionDenied:
        raise HttpError(403, "Permission denied")
    except HttpError:
        raise  # Re-raise HttpError as-is
    except Exception as e:
        logger.error(f"Unexpected error in change_order_status: {str(e)}")
        raise HttpError(500, "Internal server error")