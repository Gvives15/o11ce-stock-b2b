# apps/pos/services.py
"""
Servicios de negocio para el dominio POS (Point of Sale).

Este módulo contiene toda la lógica de negocio para operaciones de punto de venta,
siguiendo el patrón de servicios establecido en el dominio Stock.

Estructura:
- API Service Layer: Funciones para manejar lógica de endpoints
- Event-driven service functions: Funciones que usan eventos
- Business Logic Functions: Lógica de negocio pura
- Data Types: Tipos auxiliares y estructuras de datos
"""

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
from django.conf import settings

from apps.catalog.models import Product
from apps.catalog.utils import normalize_qty
from apps.catalog.pricing import price_quote
from apps.customers.models import Customer
from apps.panel.security import has_scope
from .models import SaleItemLot, LotOverrideAudit
from apps.core.events import publish_pos_event
from .events import (
    SaleCreated,
    SaleItemProcessed,
    LotOverrideRequested,
    LotOverrideExecuted,
    PriceQuoteGenerated,
    SaleDetailRequested,
    SaleDataExported,
    StockValidationRequested,
    CustomerValidationRequested,
    SaleProcessingFailed,
    PriceQuoteProcessingFailed,
    SaleItemData
)

logger = logging.getLogger(__name__)


# ============================================================================
# API Service Layer - Funciones para manejar lógica de endpoints
# ============================================================================

def handle_pos_sale_creation(
    request_user,
    sale_data: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de creación de venta POS para endpoints.
    
    Args:
        request_user: Usuario de la request
        sale_data: Datos de la venta
        correlation_id: ID de correlación para trazabilidad
        
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Validaciones básicas
        if not sale_data.get('items'):
            return 400, {
                "error": "VALIDATION_ERROR", 
                "detail": "La venta debe tener al menos un ítem"
            }
        
        # Verificar autenticación
        if not hasattr(request_user, 'is_authenticated') or not request_user.is_authenticated:
            return 403, {
                "error": "AUTHENTICATION_REQUIRED", 
                "detail": "Autenticación requerida"
            }
        
        # Generar ID único para la venta
        sale_id = str(uuid.uuid4())
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Validar cliente si se especifica
        customer = None
        if sale_data.get('customer_id'):
            try:
                customer = Customer.objects.get(id=sale_data['customer_id'])
            except Customer.DoesNotExist:
                return 400, {
                    "error": "CUSTOMER_NOT_FOUND", 
                    "detail": f"Cliente {sale_data['customer_id']} no encontrado"
                }
        
        # Procesar la venta usando eventos
        result = process_pos_sale(
            sale_id=sale_id,
            user=request_user,
            customer=customer,
            items=sale_data['items'],
            override_pin=sale_data.get('override_pin'),
            correlation_id=correlation_id
        )
        
        if result['success']:
            return 200, {
                "sale_id": sale_id,
                "total_items": result['total_items'],
                "movements": result['movements'],
                "correlation_id": correlation_id
            }
        else:
            return 400, {
                "error": result['error_code'],
                "detail": result['error_message']
            }
            
    except Exception as e:
        logger.error(f"Error in handle_pos_sale_creation: {str(e)}")
        return 500, {
            "error": "INTERNAL_ERROR", 
            "detail": f"Error interno: {str(e)}"
        }


def handle_sale_detail_request(
    request_user,
    sale_id: str
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de obtención de detalle de venta para endpoints.
    
    Args:
        request_user: Usuario de la request
        sale_id: ID de la venta
        
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Verificar autenticación
        if not hasattr(request_user, 'is_authenticated') or not request_user.is_authenticated:
            return 401, {
                "error": "AUTHENTICATION_REQUIRED", 
                "detail": "Autenticación requerida"
            }
        
        # Publicar evento de solicitud de detalle
        detail_event = SaleDetailRequested(
            sale_id=sale_id,
            requested_by_user_id=request_user.id,
            requested_by_username=request_user.username,
            access_reason="api_request"
        )
        publish_pos_event(detail_event)
        
        # Obtener detalle de la venta
        sale_detail = get_sale_detail_data(sale_id, request_user)
        
        if sale_detail['found']:
            return 200, {
                "sale_id": sale_id,
                "items": sale_detail['items']
            }
        elif sale_detail['access_denied']:
            return 403, {
                "error": "ACCESS_DENIED", 
                "detail": "No tiene permisos para ver esta venta"
            }
        else:
            return 404, {
                "error": "SALE_NOT_FOUND", 
                "detail": f"Venta {sale_id} no encontrada"
            }
            
    except Exception as e:
        logger.error(f"Error in handle_sale_detail_request: {str(e)}")
        return 500, {
            "error": "INTERNAL_ERROR", 
            "detail": f"Error interno: {str(e)}"
        }


def handle_price_quote_request(
    customer_id: int,
    items: List[Dict[str, Any]]
) -> Tuple[int, Dict[str, Any]]:
    """
    Maneja la lógica de cotización de precios para endpoints.
    
    Args:
        customer_id: ID del cliente
        items: Lista de items para cotizar
        
    Returns:
        Tuple[int, Dict]: (status_code, response_data)
    """
    try:
        # Validaciones básicas
        if not items:
            return 400, {
                "error": "VALIDATION_ERROR", 
                "detail": "Debe incluir al menos un item"
            }
        
        if len(items) > 50:
            return 400, {
                "error": "VALIDATION_ERROR", 
                "detail": "Máximo 50 items permitidos por cotización"
            }
        
        # Generar cotización usando eventos
        result = generate_price_quote(customer_id, items)
        
        if result['success']:
            return 200, result['quote_data']
        else:
            return 400, {
                "error": result['error_code'],
                "detail": result['error_message']
            }
            
    except Exception as e:
        logger.error(f"Error in handle_price_quote_request: {str(e)}")
        return 500, {
            "error": "INTERNAL_ERROR", 
            "detail": f"Error interno: {str(e)}"
        }


# ============================================================================
# Event-driven service functions
# ============================================================================

def request_sale_creation(
    sale_id: str,
    user_id: int,
    customer_id: Optional[int],
    items: List[Dict[str, Any]],
    override_pin: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> str:
    """
    Solicita la creación de una venta usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = SaleCreated(
        sale_id=sale_id,
        user_id=user_id,
        customer_id=customer_id,
        items=[SaleItemData(**item) for item in items],
        total_items=len(items),
        override_pin_used=bool(override_pin),
        correlation_id=correlation_id
    )
    
    return publish_pos_event(event)


def request_stock_validation_for_sale(
    product_id: int,
    qty: Decimal,
    customer_id: Optional[int] = None,
    min_shelf_life_days: int = 0,
    correlation_id: Optional[str] = None
) -> str:
    """
    Solicita validación de stock para una venta usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = StockValidationRequested(
        product_id=product_id,
        qty=qty,
        customer_id=customer_id,
        min_shelf_life_days=min_shelf_life_days,
        correlation_id=correlation_id
    )
    
    return publish_pos_event(event)


def request_lot_override(
    sale_id: str,
    product_id: int,
    lot_id: int,
    qty: Decimal,
    user_id: int,
    override_pin: str,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> str:
    """
    Solicita un override de lote usando eventos.
    
    Returns:
        str: ID del evento publicado
    """
    event = LotOverrideRequested(
        sale_id=sale_id,
        product_id=product_id,
        lot_id=lot_id,
        qty=qty,
        user_id=user_id,
        override_pin=override_pin,
        reason=reason,
        correlation_id=correlation_id
    )
    
    return publish_pos_event(event)


# ============================================================================
# Business Logic Functions
# ============================================================================

@transaction.atomic
def process_pos_sale(
    sale_id: str,
    user: User,
    customer: Optional[Customer],
    items: List[Dict[str, Any]],
    override_pin: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Procesa una venta POS completa usando eventos para validaciones y movimientos.
    
    Args:
        sale_id: ID único de la venta
        user: Usuario que realiza la venta
        customer: Cliente (opcional)
        items: Lista de items de la venta
        override_pin: PIN para overrides (opcional)
        correlation_id: ID de correlación
        
    Returns:
        Dict con resultado del procesamiento
    """
    try:
        # Validar items básicamente
        validated_items = []
        for idx, item in enumerate(items, 1):
            # Validar producto
            try:
                product = Product.objects.get(id=item['product_id'])
            except Product.DoesNotExist:
                return {
                    'success': False,
                    'error_code': 'PRODUCT_NOT_FOUND',
                    'error_message': f"Producto {item['product_id']} no encontrado"
                }
            
            # Validar cantidad y precio
            if item['qty'] <= 0:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'error_message': f"Cantidad debe ser mayor a 0 para producto {product.name}"
                }
            
            if item['unit_price'] <= 0:
                return {
                    'success': False,
                    'error_code': 'VALIDATION_ERROR',
                    'error_message': f"Precio unitario debe ser mayor a 0 para producto {product.name}"
                }
            
            # Determinar estrategia de asignación
            effective_lot_id = item.get('lot_id') if settings.FEATURE_LOT_OVERRIDE else None
            
            validated_items.append({
                'product': product,
                'qty': Decimal(str(item['qty'])),
                'unit_price': Decimal(str(item['unit_price'])),
                'sequence': item.get('sequence', idx),
                'lot_id': effective_lot_id,
                'lot_override_reason': item.get('lot_override_reason')
            })
        
        # Procesar cada item usando eventos
        all_movements = []
        total_amount = Decimal('0')
        
        for item in validated_items:
            if item['lot_id'] is None:
                # FEFO automático - usar eventos
                result = process_fefo_allocation(
                    product=item['product'],
                    qty=item['qty'],
                    customer=customer,
                    user=user,
                    sale_id=sale_id,
                    sequence=item['sequence'],
                    correlation_id=correlation_id
                )
            else:
                # Override de lote - usar eventos
                result = process_lot_override(
                    product=item['product'],
                    lot_id=item['lot_id'],
                    qty=item['qty'],
                    user=user,
                    sale_id=sale_id,
                    sequence=item['sequence'],
                    override_pin=override_pin,
                    reason=item['lot_override_reason'],
                    correlation_id=correlation_id
                )
            
            if not result['success']:
                return result
            
            all_movements.extend(result['movements'])
            total_amount += sum(Decimal(str(m['qty'])) * Decimal(str(m['unit_cost'])) 
                              for m in result['movements'])
        
        # Publicar evento de venta creada
        sale_created_event = SaleCreated(
            sale_id=sale_id,
            user_id=user.id,
            username=user.username,
            customer_id=customer.id if customer else None,
            total_items=len(validated_items),
            total_amount=total_amount,
            override_pin_used=bool(override_pin),
            correlation_id=correlation_id
        )
        publish_pos_event(sale_created_event)
        
        return {
            'success': True,
            'total_items': len(validated_items),
            'movements': all_movements,
            'total_amount': total_amount
        }
        
    except Exception as e:
        logger.error(f"Error processing POS sale {sale_id}: {str(e)}")
        
        # Publicar evento de error
        error_event = SaleProcessingFailed(
            sale_id=sale_id,
            error_type='sale_processing_error',
            error_message=str(e),
            user_id=user.id,
            correlation_id=correlation_id
        )
        publish_pos_event(error_event)
        
        return {
            'success': False,
            'error_code': 'PROCESSING_ERROR',
            'error_message': str(e)
        }


def process_fefo_allocation(
    product: Product,
    qty: Decimal,
    customer: Optional[Customer],
    user: User,
    sale_id: str,
    sequence: int,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Procesa la asignación FEFO para un producto usando eventos.
    
    Returns:
        Dict con resultado del procesamiento
    """
    try:
        # Determinar vida útil mínima
        min_shelf_life_days = customer.min_shelf_life_days if customer else 0
        
        # Solicitar validación de stock via eventos
        validation_event = StockValidationRequested(
            product_id=product.id,
            qty=qty,
            customer_id=customer.id if customer else None,
            min_shelf_life_days=min_shelf_life_days,
            allocation_type='fefo',
            sale_id=sale_id,
            user_id=user.id,
            correlation_id=correlation_id
        )
        
        # Publicar evento y esperar respuesta del handler
        validation_result = publish_pos_event(validation_event)
        
        if validation_result.get('error'):
            return {
                'success': False,
                'error_code': validation_result['error_code'],
                'error_message': validation_result['detail']
            }
        
        # Procesar cada asignación del plan FEFO
        movements = []
        for allocation in validation_result.get('allocation_plan', []):
            # Crear datos del ítem para el evento
            sale_item_data = SaleItemData(
                product_id=product.id,
                lot_id=allocation['lot_id'],
                qty_allocated=allocation['qty_allocated'],
                unit_price=Decimal('0'),  # Se calculará en el handler
                sequence=sequence
            )
            
            # Publicar evento de procesamiento de ítem
            item_event = SaleItemProcessed(
                sale_id=sale_id,
                item_data=sale_item_data,
                allocation_type='fefo',
                user_id=user.id,
                correlation_id=correlation_id
            )
            
            item_result = publish_pos_event(item_event)
            
            if item_result.get('error'):
                return {
                    'success': False,
                    'error_code': item_result['error_code'],
                    'error_message': item_result['detail']
                }
            
            movements.append({
                'product_id': product.id,
                'lot_id': allocation['lot_id'],
                'qty': allocation['qty_allocated'],
                'unit_cost': item_result.get('unit_cost', Decimal('0')),
                'movement_id': item_result.get('movement_id'),
                'sequence': sequence
            })
        
        return {
            'success': True,
            'movements': movements
        }
        
    except Exception as e:
        logger.error(f"Error in FEFO allocation for product {product.id}: {str(e)}")
        return {
            'success': False,
            'error_code': 'FEFO_ERROR',
            'error_message': str(e)
        }


def process_lot_override(
    product: Product,
    lot_id: int,
    qty: Decimal,
    user: User,
    sale_id: str,
    sequence: int,
    override_pin: Optional[str] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Procesa un override de lote específico usando eventos.
    
    Returns:
        Dict con resultado del procesamiento
    """
    try:
        # Solicitar override via eventos
        override_event = LotOverrideRequested(
            sale_id=sale_id,
            product_id=product.id,
            lot_id=lot_id,
            qty=qty,
            user_id=user.id,
            override_pin=override_pin or '',
            reason=reason,
            correlation_id=correlation_id
        )
        
        # Publicar evento y esperar respuesta del handler
        override_result = publish_pos_event(override_event)
        
        if override_result.get('error'):
            return {
                'success': False,
                'error_code': override_result['error_code'],
                'error_message': override_result['detail']
            }
        
        # Crear datos del ítem para el evento de procesamiento
        sale_item_data = SaleItemData(
            product_id=product.id,
            lot_id=lot_id,
            qty_allocated=qty,
            unit_price=Decimal('0'),  # Se calculará en el handler
            sequence=sequence
        )
        
        # Publicar evento de procesamiento de ítem
        item_event = SaleItemProcessed(
            sale_id=sale_id,
            item_data=sale_item_data,
            allocation_type='override',
            override_reason=reason,
            user_id=user.id,
            correlation_id=correlation_id
        )
        
        item_result = publish_pos_event(item_event)
        
        if item_result.get('error'):
            return {
                'success': False,
                'error_code': item_result['error_code'],
                'error_message': item_result['detail']
            }
        
        # Publicar evento de override ejecutado
        override_executed_event = LotOverrideExecuted(
            sale_id=sale_id,
            product_id=product.id,
            lot_id=lot_id,
            qty=qty,
            reason=reason,
            user_id=user.id,
            username=user.username,
            lot_code=override_result.get('lot_code', f'LOT-{lot_id}'),
            movement_id=item_result.get('movement_id'),
            correlation_id=correlation_id
        )
        publish_pos_event(override_executed_event)
        
        movement_data = {
            'product_id': product.id,
            'lot_id': lot_id,
            'qty': qty,
            'unit_cost': item_result.get('unit_cost', Decimal('0')),
            'movement_id': item_result.get('movement_id'),
            'sequence': sequence
        }
        
        return {
            'success': True,
            'movements': [movement_data]
        }
        
    except Exception as e:
        logger.error(f"Error in lot override for product {product.id}, lot {lot_id}: {str(e)}")
        return {
            'success': False,
            'error_code': 'OVERRIDE_ERROR',
            'error_message': str(e)
        }


def get_sale_detail_data(sale_id: str, user: User) -> Dict[str, Any]:
    """
    Obtiene los datos de detalle de una venta con control de acceso.
    
    Args:
        sale_id: ID de la venta
        user: Usuario que solicita el detalle
        
    Returns:
        Dict con los datos de la venta o información de error
    """
    try:
        # Verificar que la venta existe
        sale_items = SaleItemLot.objects.filter(sale_id=sale_id).select_related(
            'product', 'lot', 'movement'
        ).order_by('item_sequence', 'lot__expiry_date')
        
        if not sale_items.exists():
            return {
                'found': False,
                'access_denied': False,
                'items': []
            }
        
        # Control de acceso por roles
        if not has_scope(user, 'reports'):  # Admin scope
            # Verificar si el usuario fue quien hizo la venta
            first_movement = sale_items.first().movement
            if first_movement.created_by != user:
                return {
                    'found': True,
                    'access_denied': True,
                    'items': []
                }
        
        # Agrupar por ítem
        items_dict = {}
        for sale_item in sale_items:
            item_seq = sale_item.item_sequence
            
            if item_seq not in items_dict:
                items_dict[item_seq] = {
                    'product': sale_item.product,
                    'unit_price': sale_item.unit_price,
                    'lots': [],
                    'total_qty': Decimal('0')
                }
            
            # Agregar lote al ítem
            items_dict[item_seq]['lots'].append({
                'lot_id': sale_item.lot.id,
                'lot_code': sale_item.lot.lot_code,
                'expiry_date': sale_item.lot.expiry_date,
                'qty_consumed': sale_item.qty_consumed
            })
            items_dict[item_seq]['total_qty'] += sale_item.qty_consumed
        
        # Obtener información de overrides
        overrides = LotOverrideAudit.objects.filter(sale_id=sale_id).select_related('product', 'lot_chosen')
        override_by_product = {audit.product.id: audit for audit in overrides}
        
        # Construir respuesta
        items_out = []
        for item_seq in sorted(items_dict.keys()):
            item_data = items_dict[item_seq]
            product = item_data['product']
            
            # Verificar si hubo override para este producto
            override_info = None
            if product.id in override_by_product:
                audit = override_by_product[product.id]
                override_info = {
                    'reason': audit.reason,
                    'actor': audit.created_by.username if audit.created_by else None,
                    'timestamp': audit.created_at.date() if audit.created_at else None
                }
            
            items_out.append({
                'item_id': item_seq,
                'product': {
                    'id': product.id,
                    'code': product.code,
                    'name': product.name
                },
                'qty': item_data['total_qty'],
                'unit_price': item_data['unit_price'],
                'lots': item_data['lots'],
                'override': override_info
            })
        
        return {
            'found': True,
            'access_denied': False,
            'items': items_out
        }
        
    except Exception as e:
        logger.error(f"Error getting sale detail for {sale_id}: {str(e)}")
        return {
            'found': False,
            'access_denied': False,
            'items': []
        }


def generate_price_quote(customer: Customer, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Genera una cotización de precios para un cliente y lista de items.
    
    Args:
        customer: Cliente para la cotización
        items: Lista de items a cotizar
        
    Returns:
        Dict con resultado de la cotización
    """
    try:
        # Preparar items para el motor de pricing
        items_data = []
        original_items = {}
        
        for item in items:
            try:
                product = Product.objects.get(id=item['product_id'])
            except Product.DoesNotExist:
                return {
                    'success': False,
                    'error_code': 'PRODUCT_NOT_FOUND',
                    'error_message': f"Producto {item['product_id']} no encontrado"
                }
            
            # Normalizar cantidad
            normalized_qty = normalize_qty(product, Decimal(str(item['qty'])))
            
            items_data.append({
                'product': product,
                'quantity': normalized_qty
            })
            
            original_items[product.id] = {
                'original_qty': Decimal(str(item['qty'])),
                'normalized_qty': normalized_qty
            }
        
        # Generar cotización usando el motor de pricing
        quote = price_quote(customer, items_data)
        
        # Convertir resultado
        response_items = []
        for pricing_item in quote.items:
            original_data = original_items[pricing_item.product.id]
            
            response_items.append({
                'product_id': pricing_item.product.id,
                'name': pricing_item.product.name,
                'qty': original_data['original_qty'],
                'unit_price': pricing_item.unit_price,
                'discount_item': pricing_item.discount_amount,
                'subtotal': pricing_item.subtotal
            })
        
        # Publicar evento de cotización generada
        quote_event = PriceQuoteGenerated(
            customer_id=customer.id,
            items_count=len(items),
            total_amount=quote.total,
            correlation_id=str(uuid.uuid4())
        )
        publish_pos_event(quote_event)
        
        return {
            'success': True,
            'data': {
                'items': response_items,
                'subtotal': quote.subtotal,
                'segment_discount_amount': quote.segment_discount_amount,
                'combo_discounts': [combo.__dict__ for combo in quote.combo_discounts],
                'total_combo_discount': quote.total_combo_discount,
                'total': quote.total
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating price quote for customer {customer.id}: {str(e)}")
        
        # Publicar evento de fallo
        failure_event = PriceQuoteProcessingFailed(
            customer_id=customer.id,
            error_code='QUOTE_ERROR',
            error_message=str(e),
            correlation_id=str(uuid.uuid4())
        )
        publish_pos_event(failure_event)
        
        return {
            'success': False,
            'error_code': 'QUOTE_ERROR',
            'error_message': str(e)
        }


# ============================================================================
# Data Types and Auxiliary Functions
# ============================================================================

class POSError(Exception):
    """Errores de negocio para operaciones POS."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class SaleAllocationPlan(NamedTuple):
    """Plan de asignación para una venta."""
    product_id: int
    lot_id: int
    qty_allocated: Decimal
    is_override: bool
    sequence: int


class SaleMovementData(NamedTuple):
    """Datos de movimiento para una venta."""
    product_id: int
    product_name: str
    lot_id: int
    lot_code: str
    qty: Decimal
    unit_cost: Decimal
    movement_id: str


def validate_pos_permissions(user: User, operation: str) -> bool:
    """
    Valida permisos para operaciones POS.
    
    Args:
        user: Usuario a validar
        operation: Operación a realizar ('sale', 'override', 'reports')
        
    Returns:
        bool: True si tiene permisos
    """
    if operation == 'sale':
        return user.is_authenticated
    elif operation == 'override':
        return has_scope(user, 'pos_override')
    elif operation == 'reports':
        return has_scope(user, 'reports')
    else:
        return False


def calculate_sale_totals(items: List[Dict[str, Any]]) -> Dict[str, Decimal]:
    """
    Calcula totales de una venta.
    
    Args:
        items: Lista de items de la venta
        
    Returns:
        Dict con totales calculados
    """
    subtotal = Decimal('0')
    total_qty = Decimal('0')
    
    for item in items:
        qty = Decimal(str(item['qty']))
        unit_price = Decimal(str(item['unit_price']))
        
        subtotal += qty * unit_price
        total_qty += qty
    
    return {
        'subtotal': subtotal,
        'total_qty': total_qty,
        'total_items': len(items)
    }


# ============================================================================
# Legacy compatibility functions (if needed)
# ============================================================================

# Estas funciones pueden agregarse si se necesita compatibilidad hacia atrás
# con código existente que no use el patrón de servicios