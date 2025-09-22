"""Utility functions for catalog operations."""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional, Union
from django.db.models import Q, QuerySet
from .models import Benefit


def apply_discount(price: Decimal, value_pct: Decimal) -> Decimal:
    """
    Aplica un descuento porcentual a un precio.
    
    Args:
        price: Precio original
        value_pct: Porcentaje de descuento (ej: 10 para 10%)
    
    Returns:
        Precio con descuento aplicado, redondeado a 2 decimales
    """
    if price <= 0:
        raise ValueError("El precio debe ser mayor a 0")
    if value_pct < 0 or value_pct > 100:
        raise ValueError("El porcentaje debe estar entre 0 y 100")
    
    discount_amount = price * (value_pct / 100)
    discounted_price = price - discount_amount
    
    # Redondear a 2 decimales
    return discounted_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_active_benefits(segment: Optional[str] = None, filter_date: Optional[date] = None) -> QuerySet[Benefit]:
    """
    Obtiene beneficios activos para un segmento y fecha específicos.
    
    Args:
        segment: Segmento de cliente ('wholesale' o 'retail')
        filter_date: Fecha para filtrar beneficios activos (por defecto hoy)
    
    Returns:
        QuerySet de beneficios activos
    """
    if filter_date is None:
        filter_date = date.today()
    
    # Consulta única sin N+1
    qs = Benefit.objects.filter(
        is_active=True,
        active_from__lte=filter_date,
        active_to__gte=filter_date
    ).select_related()  # Optimización para evitar N+1
    
    if segment:
        qs = qs.filter(segment=segment)
    
    return qs.order_by('name')


def normalize_qty(product, qty: Union[int, float, Decimal], unit: str) -> Decimal:
    """
    Normaliza la cantidad a unidades base según el tipo de unidad especificado.
    
    Args:
        product: Instancia del producto
        qty: Cantidad a normalizar
        unit: Tipo de unidad ('unit' o 'package')
        
    Returns:
        Cantidad normalizada en unidades base
        
    Examples:
        >>> from apps.catalog.models import Product
        >>> product = Product(pack_size=10)
        >>> normalize_qty(product, 1, 'package')  # 1 paquete = 10 unidades
        Decimal('10')
        >>> normalize_qty(product, 5, 'unit')     # 5 unidades = 5 unidades
        Decimal('5')
    """
    qty = Decimal(str(qty))
    
    if unit == 'package':
        if product.pack_size is None:
            raise ValueError(f"Product {product.code} does not have pack_size defined")
        return qty * Decimal(str(product.pack_size))
    elif unit == 'unit':
        return qty
    else:
        raise ValueError(f"Invalid unit type: {unit}. Must be 'unit' or 'package'")