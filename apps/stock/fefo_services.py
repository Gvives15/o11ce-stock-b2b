"""
FEFO Services for Reservation System
Provides FEFO-based picking suggestions considering existing reservations.
"""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, NamedTuple
from django.db.models import Sum, Q
from django.db import models

from apps.orders.models import Order, OrderItem
from apps.stock.models import StockLot
from apps.stock.reservations import Reservation


class PickingSuggestion(NamedTuple):
    """Sugerencia de picking para un producto específico."""
    product_id: int
    lot_id: int
    lot_code: str
    qty: Decimal
    expiry_date: date
    unit_cost: Decimal
    warehouse_name: str


def get_fefo_suggestions(order: Order) -> List[PickingSuggestion]:
    """
    Devuelve sugerencias de picking FEFO para una orden.
    
    Considera:
    - Solo lotes no quarantined
    - Respeta disponible = on_hand - reservas activas
    - Orden FEFO (expiry_date, id)
    - Excluye lotes ya reservados para esta orden
    
    Args:
        order: Orden para la cual generar sugerencias
        
    Returns:
        Lista de sugerencias ordenadas por producto y FEFO
    """
    suggestions = []
    
    # Obtener items de la orden
    order_items = OrderItem.objects.filter(order=order).select_related('product')
    
    for item in order_items:
        product = item.product
        qty_needed = item.qty
        
        # Obtener reservas activas existentes para este producto (excluyendo esta orden)
        active_reservations = Reservation.objects.filter(
            lot__product=product,
            status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
        ).exclude(order=order)
        
        # Calcular cantidad reservada por lote
        reserved_by_lot = active_reservations.values('lot_id').annotate(
            total_reserved=Sum('qty')
        )
        reserved_dict = {item['lot_id']: item['total_reserved'] for item in reserved_by_lot}
        
        # Obtener lotes disponibles ordenados por FEFO
        available_lots = StockLot.objects.select_related('warehouse', 'product').filter(
            product=product,
            qty_on_hand__gt=0,
            is_quarantined=False,
            expiry_date__gte=date.today()  # Excluir lotes vencidos
        ).order_by('expiry_date', 'id')
        
        remaining_qty = qty_needed
        
        for lot in available_lots:
            if remaining_qty <= 0:
                break
                
            # Calcular cantidad disponible considerando reservas
            reserved_qty = reserved_dict.get(lot.id, Decimal('0'))
            available_qty = lot.qty_on_hand - reserved_qty
            
            if available_qty <= 0:
                continue  # Este lote no tiene stock disponible
                
            # Determinar cuánto tomar de este lote
            qty_to_suggest = min(remaining_qty, available_qty)
            
            suggestions.append(PickingSuggestion(
                product_id=product.id,
                lot_id=lot.id,
                lot_code=lot.lot_code,
                qty=qty_to_suggest,
                expiry_date=lot.expiry_date,
                unit_cost=lot.unit_cost,
                warehouse_name=lot.warehouse.name if lot.warehouse else "N/A"
            ))
            
            remaining_qty -= qty_to_suggest
    
    return suggestions


def validate_reservation_availability(order: Order, reservations_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Valida que las reservas propuestas no excedan el stock disponible.
    
    Args:
        order: Orden para la cual validar reservas
        reservations_data: Lista de diccionarios con {lot_id, qty}
        
    Returns:
        Dict con resultado de validación:
        {
            'valid': bool,
            'errors': List[str],
            'availability_check': Dict[lot_id, {'available': Decimal, 'requested': Decimal}]
        }
    """
    result = {
        'valid': True,
        'errors': [],
        'availability_check': {}
    }
    
    # Agrupar reservas por lote
    reservations_by_lot = {}
    for reservation in reservations_data:
        lot_id = reservation['lot_id']
        qty = Decimal(str(reservation['qty']))
        
        if lot_id in reservations_by_lot:
            reservations_by_lot[lot_id] += qty
        else:
            reservations_by_lot[lot_id] = qty
    
    # Validar cada lote
    for lot_id, requested_qty in reservations_by_lot.items():
        try:
            lot = StockLot.objects.get(id=lot_id)
            
            # Calcular reservas activas existentes (excluyendo esta orden)
            existing_reservations = Reservation.objects.filter(
                lot_id=lot_id,
                status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
            ).exclude(order=order).aggregate(
                total=Sum('qty')
            )['total'] or Decimal('0')
            
            available_qty = lot.qty_on_hand - existing_reservations
            
            result['availability_check'][str(lot_id)] = {
                'available': available_qty,
                'requested': requested_qty,
                'on_hand': lot.qty_on_hand,
                'existing_reservations': existing_reservations
            }
            
            if requested_qty > available_qty:
                result['valid'] = False
                result['errors'].append(
                    f"Lote {lot.lot_code}: solicitado {requested_qty}, disponible {available_qty}"
                )
                
        except StockLot.DoesNotExist:
            result['valid'] = False
            result['errors'].append(f"Lote ID {lot_id} no existe")
            result['availability_check'][str(lot_id)] = {
                'available': Decimal('0'),
                'requested': requested_qty,
                'error': 'Lote no encontrado'
            }
    
    return result


def get_product_availability(product_id: int) -> Dict[str, Any]:
    """
    Obtiene información de disponibilidad para un producto específico.
    
    Args:
        product_id: ID del producto
        
    Returns:
        Dict con información de disponibilidad por lote
    """
    # Obtener todos los lotes del producto
    lots = StockLot.objects.filter(
        product_id=product_id,
        qty_on_hand__gt=0,
        is_quarantined=False
    ).select_related('warehouse').order_by('expiry_date', 'id')
    
    # Calcular reservas activas por lote
    active_reservations = Reservation.objects.filter(
        lot__product_id=product_id,
        status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
    ).values('lot_id').annotate(
        total_reserved=Sum('qty')
    )
    
    reserved_dict = {item['lot_id']: item['total_reserved'] for item in active_reservations}
    
    availability_info = {
        'product_id': product_id,
        'lots': [],
        'total_on_hand': Decimal('0'),
        'total_reserved': Decimal('0'),
        'total_available': Decimal('0')
    }
    
    for lot in lots:
        reserved_qty = reserved_dict.get(lot.id, Decimal('0'))
        available_qty = lot.qty_on_hand - reserved_qty
        
        lot_info = {
            'lot_id': lot.id,
            'lot_code': lot.lot_code,
            'expiry_date': lot.expiry_date,
            'warehouse_name': lot.warehouse.name if lot.warehouse else "N/A",
            'qty_on_hand': lot.qty_on_hand,
            'qty_reserved': reserved_qty,
            'qty_available': available_qty,
            'is_expired': lot.expiry_date < date.today()
        }
        
        availability_info['lots'].append(lot_info)
        availability_info['total_on_hand'] += lot.qty_on_hand
        availability_info['total_reserved'] += reserved_qty
        availability_info['total_available'] += available_qty
    
    return availability_info