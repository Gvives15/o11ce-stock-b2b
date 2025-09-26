"""
Utilidades para el catálogo de productos.
"""
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from django.utils import timezone
from django.db.models import Q
from apps.catalog.models import Benefit
from apps.core.metrics import (
    increment_pricing_calculation, 
    increment_pricing_error, 
    observe_pricing_duration
)


def apply_discount(price: Decimal, discount_percentage: Decimal) -> Decimal:
    """
    Aplica un descuento porcentual a un precio.
    
    Args:
        price: Precio original
        discount_percentage: Porcentaje de descuento (ej: 10.5 para 10.5%)
        
    Returns:
        Precio con descuento aplicado, redondeado a 2 decimales
        
    Examples:
        >>> apply_discount(Decimal('100.00'), Decimal('10.5'))
        Decimal('89.50')
        >>> apply_discount(Decimal('50.00'), Decimal('8.0'))
        Decimal('46.00')
    """
    if discount_percentage <= 0:
        return price
    
    discount_amount = (price * discount_percentage) / Decimal('100')
    discounted_price = price - discount_amount
    
    # Redondear a 2 decimales usando ROUND_HALF_UP
    return discounted_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_active_benefits(segment: Optional[str] = None, filter_date=None):
    """
    Obtiene beneficios activos para un segmento específico.
    
    Args:
        segment: Segmento del cliente ('retail' o 'wholesale')
        filter_date: Fecha para filtrar beneficios (por defecto hoy)
        
    Returns:
        QuerySet de beneficios activos
    """
    if filter_date is None:
        filter_date = timezone.now().date()
    
    qs = Benefit.objects.filter(
        Q(active_from__lte=filter_date) & 
        Q(active_to__gte=filter_date)
    )
    
    if segment:
        qs = qs.filter(segment=segment)
    
    return qs


def calculate_final_price(product, segment: Optional[str] = None) -> Decimal:
    """
    Calcula el precio final de un producto aplicando el mejor beneficio disponible.
    
    Args:
        product: Instancia del producto
        segment: Segmento del cliente ('retail' o 'wholesale')
        
    Returns:
        Precio final con descuentos aplicados
        
    Examples:
        >>> from apps.catalog.models import Product
        >>> product = Product(price=Decimal('100.00'))
        >>> calculate_final_price(product, 'wholesale')  # Con descuento del 8%
        Decimal('92.00')
        >>> calculate_final_price(product, 'retail')     # Sin descuento
        Decimal('100.00')
    """
    start_time = time.time()
    segment = segment or 'unknown'
    product_category = getattr(product, 'category', 'unknown') or 'unknown'
    
    try:
        # Incrementar contador de cálculos
        increment_pricing_calculation(
            segment=segment,
            calculation_type='final_price',
            product_category=product_category
        )
        
        if not segment or segment == 'unknown':
            return product.price
        
        # Obtener beneficios activos para el segmento
        active_benefits = get_active_benefits(segment=segment)
        
        # Filtrar solo beneficios de tipo discount
        discount_benefits = active_benefits.filter(type="discount")
        
        if not discount_benefits.exists():
            return product.price
        
        # Encontrar el mejor descuento (mayor porcentaje)
        best_benefit = discount_benefits.order_by('-value').first()
        
        if best_benefit and best_benefit.value:
            final_price = apply_discount(product.price, best_benefit.value)
            
            # Incrementar contador de descuentos aplicados
            increment_pricing_calculation(
                segment=segment,
                calculation_type='discount',
                product_category=product_category
            )
            
            return final_price
        
        return product.price
        
    except Exception as e:
        # Incrementar contador de errores
        increment_pricing_error(
            segment=segment,
            error_type='calculation_error',
            product_category=product_category
        )
        # En caso de error, devolver precio base
        return product.price
        
    finally:
        # Observar duración del cálculo
        duration = time.time() - start_time
        observe_pricing_duration(
            duration_seconds=duration,
            segment=segment,
            calculation_type='final_price'
        )


def extract_pack_size(product_name: str) -> Optional[str]:
    """
    Extrae el tamaño de pack del nombre del producto.
    
    Args:
        product_name: Nombre del producto
        
    Returns:
        Tamaño de pack extraído o None si no se encuentra
        
    Examples:
        >>> extract_pack_size("Coca Cola 500ml x12")
        "x12"
        >>> extract_pack_size("Pepsi 2L")
        None
    """
    import re
    
    # Buscar patrones como "x12", "X6", etc.
    match = re.search(r'[xX](\d+)', product_name)
    if match:
        return f"x{match.group(1)}"
    
    return None


def normalize_qty(product, qty, unit: str) -> Decimal:
    """
    Normaliza la cantidad a unidades base según el tipo de unidad especificado.
    
    Args:
        product: Instancia del producto
        qty: Cantidad a normalizar (int, float, o Decimal)
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
    from typing import Union
    
    qty = Decimal(str(qty))
    
    if unit == 'package':
        if not hasattr(product, 'pack_size') or product.pack_size is None:
            raise ValueError(f"Product {product.code} does not have pack_size defined")
        return qty * Decimal(str(product.pack_size))
    elif unit == 'unit':
        return qty
    else:
        raise ValueError(f"Invalid unit type: {unit}. Must be 'unit' or 'package'")