"""
Módulo de pricing para el catálogo de productos.
Contiene lógica para calcular precios con descuentos y promociones.
"""
import time
from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db.models import QuerySet
from apps.catalog.models import Product, Benefit
from apps.catalog.utils import calculate_final_price
from apps.core.metrics import (
    increment_pricing_calculation, 
    increment_pricing_error, 
    observe_pricing_duration
)


def apply_combo_discounts(products: List[Product], segment: str = "retail") -> Dict[str, Any]:
    """
    Aplica descuentos por combo a una lista de productos.
    
    Args:
        products: Lista de productos para el combo
        segment: Segmento del cliente ('retail' o 'wholesale')
        
    Returns:
        Diccionario con información del combo y descuentos aplicados
        
    Examples:
        >>> products = [Product(code='P001', price=Decimal('100')), 
        ...            Product(code='P002', price=Decimal('50'))]
        >>> result = apply_combo_discounts(products, 'wholesale')
        >>> result['total_discount']
        Decimal('12.00')  # 8% de descuento en wholesale
    """
    start_time = time.time()
    
    try:
        # Incrementar contador de cálculos de combo
        increment_pricing_calculation(
            segment=segment,
            calculation_type='combo_discount',
            product_category='combo'
        )
        
        if not products:
            return {
                'products': [],
                'original_total': Decimal('0.00'),
                'final_total': Decimal('0.00'),
                'total_discount': Decimal('0.00'),
                'combo_applied': False
            }
        
        # Calcular precios individuales con descuentos
        product_details = []
        original_total = Decimal('0.00')
        final_total = Decimal('0.00')
        
        for product in products:
            original_price = product.price
            final_price = calculate_final_price(product, segment)
            
            product_details.append({
                'code': product.code,
                'name': product.name,
                'original_price': original_price,
                'final_price': final_price,
                'discount_applied': original_price - final_price
            })
            
            original_total += original_price
            final_total += final_price
        
        total_discount = original_total - final_total
        combo_applied = total_discount > Decimal('0.00')
        
        if combo_applied:
            # Incrementar contador de combos aplicados
            increment_pricing_calculation(
                segment=segment,
                calculation_type='combo_applied',
                product_category='combo'
            )
        
        return {
            'products': product_details,
            'original_total': original_total,
            'final_total': final_total,
            'total_discount': total_discount,
            'combo_applied': combo_applied,
            'segment': segment
        }
        
    except Exception as e:
        # Incrementar contador de errores
        increment_pricing_error(
            segment=segment,
            error_type='combo_calculation_error',
            product_category='combo'
        )
        
        # Devolver estructura básica en caso de error
        return {
            'products': [],
            'original_total': Decimal('0.00'),
            'final_total': Decimal('0.00'),
            'total_discount': Decimal('0.00'),
            'combo_applied': False,
            'error': str(e)
        }
        
    finally:
        # Observar duración del cálculo
        duration = time.time() - start_time
        observe_pricing_duration(
            duration_seconds=duration,
            segment=segment,
            calculation_type='combo_discount'
        )


def price_quote(product_codes: List[str], segment: str = "retail", quantities: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Genera una cotización de precios para una lista de productos.
    
    Args:
        product_codes: Lista de códigos de productos
        segment: Segmento del cliente ('retail' o 'wholesale')
        quantities: Lista de cantidades (opcional, por defecto 1 para cada producto)
        
    Returns:
        Diccionario con la cotización completa
        
    Examples:
        >>> quote = price_quote(['P001', 'P002'], 'wholesale', [2, 1])
        >>> quote['total_amount']
        Decimal('242.00')  # Precios con descuento wholesale
    """
    start_time = time.time()
    
    try:
        # Incrementar contador de cotizaciones
        increment_pricing_calculation(
            segment=segment,
            calculation_type='price_quote',
            product_category='quote'
        )
        
        if not product_codes:
            return {
                'items': [],
                'subtotal': Decimal('0.00'),
                'total_discount': Decimal('0.00'),
                'total_amount': Decimal('0.00'),
                'segment': segment,
                'quote_id': None
            }
        
        # Establecer cantidades por defecto si no se proporcionan
        if quantities is None:
            quantities = [1] * len(product_codes)
        elif len(quantities) != len(product_codes):
            raise ValueError("La cantidad de productos y cantidades debe coincidir")
        
        # Obtener productos de la base de datos
        products = Product.objects.filter(code__in=product_codes)
        product_dict = {p.code: p for p in products}
        
        # Verificar que todos los productos existen
        missing_products = set(product_codes) - set(product_dict.keys())
        if missing_products:
            raise ValueError(f"Productos no encontrados: {', '.join(missing_products)}")
        
        # Calcular precios para cada item
        quote_items = []
        subtotal = Decimal('0.00')
        total_discount = Decimal('0.00')
        
        for code, qty in zip(product_codes, quantities):
            product = product_dict[code]
            original_price = product.price
            final_price = calculate_final_price(product, segment)
            
            line_original = original_price * qty
            line_final = final_price * qty
            line_discount = line_original - line_final
            
            quote_items.append({
                'product_code': code,
                'product_name': product.name,
                'quantity': qty,
                'unit_price': original_price,
                'unit_final_price': final_price,
                'line_total': line_final,
                'line_discount': line_discount
            })
            
            subtotal += line_original
            total_discount += line_discount
        
        total_amount = subtotal - total_discount
        
        # Incrementar contador de cotizaciones exitosas
        increment_pricing_calculation(
            segment=segment,
            calculation_type='quote_success',
            product_category='quote'
        )
        
        return {
            'items': quote_items,
            'subtotal': subtotal,
            'total_discount': total_discount,
            'total_amount': total_amount,
            'segment': segment,
            'quote_id': f"Q-{int(time.time())}"  # ID simple basado en timestamp
        }
        
    except Exception as e:
        # Incrementar contador de errores
        increment_pricing_error(
            segment=segment,
            error_type='quote_error',
            product_category='quote'
        )
        
        # Devolver estructura básica en caso de error
        return {
            'items': [],
            'subtotal': Decimal('0.00'),
            'total_discount': Decimal('0.00'),
            'total_amount': Decimal('0.00'),
            'segment': segment,
            'quote_id': None,
            'error': str(e)
        }
        
    finally:
        # Observar duración del cálculo
        duration = time.time() - start_time
        observe_pricing_duration(
            duration_seconds=duration,
            segment=segment,
            calculation_type='price_quote'
        )