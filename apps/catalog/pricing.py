"""
Motor de beneficios (MVP) - Servicio de pricing con descuentos por segmento y combo.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.catalog.utils import apply_discount


@dataclass
class PricingItem:
    """Representa un item en el pricing con producto y cantidad."""
    product: Product
    quantity: int
    unit_price: Decimal = None
    subtotal: Decimal = None
    
    def __post_init__(self):
        if self.unit_price is None:
            self.unit_price = self.product.price
        if self.subtotal is None:
            self.subtotal = self.unit_price * Decimal(str(self.quantity))


@dataclass
class ComboDiscount:
    """Representa un descuento de combo aplicado."""
    name: str
    description: str
    discount_amount: Decimal
    items_affected: List[str]  # códigos de productos afectados


@dataclass
class PriceQuote:
    """Resultado final del pricing con todos los cálculos."""
    items: List[PricingItem]
    subtotal: Decimal
    segment_discount_amount: Decimal
    combo_discounts: List[ComboDiscount]
    total_combo_discount: Decimal
    total: Decimal


def apply_segment_discount(items: List[PricingItem], customer: Customer) -> Decimal:
    """
    Aplica descuentos por segmento de cliente.
    
    Args:
        items: Lista de items con pricing
        customer: Cliente para determinar segmento
        
    Returns:
        Monto total de descuento aplicado por segmento
        
    Examples:
        >>> # Mayorista obtiene -8% en P1/P2
        >>> items = [PricingItem(product_p1, 2), PricingItem(product_p2, 1)]
        >>> customer = Customer(segment="wholesale")
        >>> discount = apply_segment_discount(items, customer)
    """
    if customer.segment != "wholesale":
        return Decimal('0.00')
    
    total_discount = Decimal('0.00')
    discount_rate = Decimal('8.00')  # 8% para mayoristas
    
    for item in items:
        # Aplicar descuento solo a productos P1 y P2
        if item.product.code.startswith(('P1-', 'P2-')):
            item_discount = item.subtotal * (discount_rate / 100)
            total_discount += item_discount
            
            # Actualizar precios del item
            discounted_unit_price = apply_discount(item.unit_price, discount_rate)
            item.unit_price = discounted_unit_price
            item.subtotal = discounted_unit_price * Decimal(str(item.quantity))
    
    return total_discount


def apply_combo_discounts(items: List[PricingItem]) -> List[ComboDiscount]:
    """
    Aplica descuentos por combos específicos.
    
    Args:
        items: Lista de items con pricing
        
    Returns:
        Lista de descuentos de combo aplicados
        
    Examples:
        >>> # Combo: 1×P2 + 5×P1 → -300
        >>> items = [PricingItem(product_p1, 5), PricingItem(product_p2, 1)]
        >>> combos = apply_combo_discounts(items)
    """
    combo_discounts = []
    
    # Contar productos P1 y P2
    p1_count = 0
    p2_count = 0
    p1_items = []
    p2_items = []
    
    for item in items:
        if item.product.code.startswith('P1-'):
            p1_count += item.quantity
            p1_items.append(item)
        elif item.product.code.startswith('P2-'):
            p2_count += item.quantity
            p2_items.append(item)
    
    # Aplicar combo: 1×P2 + 5×P1 → -300
    if p1_count >= 5 and p2_count >= 1:
        # Calcular cuántos combos se pueden aplicar
        max_combos = min(p1_count // 5, p2_count // 1)
        
        if max_combos > 0:
            combo_discount_amount = Decimal('300.00') * max_combos
            
            # Aplicar descuento proporcionalmente a los items afectados
            affected_items = p1_items + p2_items
            total_affected_subtotal = sum(item.subtotal for item in affected_items)
            
            for item in affected_items:
                if total_affected_subtotal > 0:
                    item_proportion = item.subtotal / total_affected_subtotal
                    item_discount = combo_discount_amount * item_proportion
                    item.subtotal -= item_discount
            
            combo_discounts.append(ComboDiscount(
                name="Combo P1+P2",
                description=f"Combo {max_combos}x: 1×P2 + 5×P1 → -$300 c/u",
                discount_amount=combo_discount_amount,
                items_affected=[item.product.code for item in affected_items]
            ))
    
    return combo_discounts


def price_quote(customer: Customer, items: List[Dict[str, Any]]) -> PriceQuote:
    """
    Calcula cotización completa con descuentos por segmento y combo.
    
    Args:
        customer: Cliente para aplicar descuentos por segmento
        items: Lista de diccionarios con 'product_id' y 'quantity'
        
    Returns:
        PriceQuote con cálculos completos
        
    Examples:
        >>> customer = Customer(segment="wholesale")
        >>> items = [{'product_id': 1, 'quantity': 5}, {'product_id': 2, 'quantity': 1}]
        >>> quote = price_quote(customer, items)
        >>> print(f"Total: ${quote.total}")
    """
    # Convertir items a PricingItems
    pricing_items = []
    for item_data in items:
        try:
            product = Product.objects.get(id=item_data['product_id'])
            pricing_item = PricingItem(
                product=product,
                quantity=item_data['quantity']
            )
            pricing_items.append(pricing_item)
        except Product.DoesNotExist:
            continue  # Ignorar productos que no existen
    
    # Calcular subtotal inicial
    initial_subtotal = sum(item.subtotal for item in pricing_items)
    
    # Aplicar descuentos por segmento
    segment_discount_amount = apply_segment_discount(pricing_items, customer)
    
    # Aplicar descuentos por combo
    combo_discounts = apply_combo_discounts(pricing_items)
    total_combo_discount = sum(combo.discount_amount for combo in combo_discounts)
    
    # Calcular subtotal después de descuentos por segmento
    subtotal_after_segment = sum(item.subtotal for item in pricing_items)
    
    # Calcular total final
    total = subtotal_after_segment
    
    return PriceQuote(
        items=pricing_items,
        subtotal=initial_subtotal,
        segment_discount_amount=segment_discount_amount,
        combo_discounts=combo_discounts,
        total_combo_discount=total_combo_discount,
        total=total
    )