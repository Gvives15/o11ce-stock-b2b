"""API endpoints for POS (Point of Sale) operations."""

from ninja import Router, Schema, Query
from ninja.errors import HttpError
from decimal import Decimal
from datetime import date
from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
import uuid

from apps.catalog.models import Product
from apps.catalog.utils import normalize_qty
from apps.catalog.pricing import price_quote
from apps.stock.models import StockLot, Movement
from apps.stock.services import allocate_lots_fefo, record_exit_fefo, StockError, ExitError
from apps.customers.models import Customer
from apps.panel.security import has_scope
from apps.pos.models import LotOverrideAudit

router = Router()


# ============================================================================
# SCHEMAS
# ============================================================================

class SaleItemIn(Schema):
    """Schema para un ítem de venta."""
    product_id: int
    qty: Decimal
    unit_price: Decimal
    sequence: int = 1  # Posición del ítem en la venta
    lot_id: Optional[int] = None
    lot_override_reason: Optional[str] = None


class SaleIn(Schema):
    """Schema para una venta POS."""
    items: List[SaleItemIn]
    customer_id: Optional[int] = None
    override_pin: Optional[str] = None


class SaleMovementOut(Schema):
    """Schema para movimiento de venta."""
    product_id: int
    product_name: str
    lot_id: int
    lot_code: str
    qty: Decimal
    unit_cost: Decimal


class SaleOut(Schema):
    """Schema para respuesta de venta."""
    sale_id: str
    total_items: int
    movements: List[SaleMovementOut]


# ============================================================================
# SCHEMAS PARA TRAZABILIDAD (BLOQUE G)
# ============================================================================

class ProductOut(Schema):
    """Schema para información básica de producto."""
    id: int
    code: str
    name: str


class LotDetailOut(Schema):
    """Schema para detalle de lote consumido."""
    lot_id: int
    lot_code: str
    expiry_date: Optional[date]
    qty: Decimal


class OverrideDetailOut(Schema):
    """Schema para información de override."""
    used: bool
    reason: Optional[str] = None


class SaleItemDetailOut(Schema):
    """Schema para detalle de ítem de venta con trazabilidad."""
    item_id: int
    product: ProductOut
    qty: Decimal
    unit_price: Decimal
    lots: List[LotDetailOut]
    override: OverrideDetailOut


class SaleDetailOut(Schema):
    """Schema para respuesta completa de detalle de venta."""
    sale_id: str
    items: List[SaleItemDetailOut]


class ErrorOut(Schema):
    """Schema para errores."""
    error: str
    detail: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health", response={200: dict})
def pos_health_check(request):
    """Health check para el router POS."""
    return {"status": "ok", "service": "pos"}


@router.post("/sale", response={200: SaleOut, 400: ErrorOut, 403: ErrorOut})
@transaction.atomic
def create_pos_sale(request, sale_data: SaleIn):
    """
    Crea una venta POS con soporte para FEFO y override de lotes.
    
    - Si lot_id es None: usa FEFO automático
    - Si lot_id está presente: usa ese lote específico (override)
    - Transacción atómica: todo o nada
    - Genera movimientos de salida por cada lote consumido
    
    FEATURE FLAG: Si FEATURE_LOT_OVERRIDE=False, ignora lot_id y usa FEFO siempre
    """
    if not sale_data.items:
        return 400, {"error": "VALIDATION_ERROR", "detail": "La venta debe tener al menos un ítem"}
    
    # Generar ID único para la venta
    sale_id = str(uuid.uuid4())
    
    # Usuario autenticado (debe venir del request)
    if not request.user.is_authenticated:
        return 403, {"error": "AUTHENTICATION_REQUIRED", "detail": "Autenticación requerida"}
    
    user = request.user
    
    # VALIDACIÓN BLOQUE D: Obtener cliente si se especifica
    customer = None
    if sale_data.customer_id:
        try:
            customer = Customer.objects.get(id=sale_data.customer_id)
        except Customer.DoesNotExist:
            return 400, {"error": "CUSTOMER_NOT_FOUND", "detail": f"Cliente {sale_data.customer_id} no encontrado"}

    # FASE 1: Validaciones y planificación (sin modificar datos)
    allocation_plans = []
    
    for idx, item in enumerate(sale_data.items, 1):
        # Asignar secuencia automáticamente si no se proporciona
        if not hasattr(item, 'sequence') or item.sequence is None:
            item.sequence = idx
            
        if item.qty <= 0:
            return 400, {"error": "VALIDATION_ERROR", "detail": f"Cantidad debe ser mayor a 0 para producto {item.product_id}"}
        
        # Verificar que el producto existe
        try:
            product = get_object_or_404(Product, id=item.product_id)
        except Http404:
            return 400, {"error": "PRODUCT_NOT_FOUND", "detail": f"Producto {item.product_id} no encontrado"}
        
        # Validar precio unitario
        if item.unit_price <= 0:
            return 400, {"error": "VALIDATION_ERROR", "detail": f"Precio unitario debe ser mayor a 0 para producto {product.name}"}
        
        # FEATURE FLAG: Si está deshabilitado, ignorar lot_id y usar FEFO siempre
        effective_lot_id = item.lot_id if settings.FEATURE_LOT_OVERRIDE else None
        
        # Determinar estrategia: FEFO o Override
        if effective_lot_id is None:
            # FEFO automático - solo planificar
            try:
                # VALIDACIÓN BLOQUE D: Aplicar vida útil mínima del cliente
                min_shelf_life_days = customer.min_shelf_life_days if customer else 0
                
                allocation_plan = allocate_lots_fefo(
                    product=product,
                    qty_needed=item.qty,
                    min_shelf_life_days=min_shelf_life_days
                )
                allocation_plans.append({
                    'item': item,
                    'product': product,
                    'plan': allocation_plan,
                    'type': 'fefo'
                })
            except StockError as e:
                if e.code == "INSUFFICIENT_STOCK":
                    return 400, {"error": "INSUFFICIENT_STOCK", "detail": f"Stock insuficiente para producto {product.name}: {str(e)}"}
                elif e.code == "INSUFFICIENT_SHELF_LIFE":
                    return 400, {"error": "INSUFFICIENT_SHELF_LIFE", "detail": f"Vida útil insuficiente para producto {product.name}: {str(e)}"}
                else:
                    return 400, {"error": e.code, "detail": str(e)}
        else:
            # Override de lote específico (solo si feature flag está habilitado)
            if not item.lot_override_reason:
                return 400, {"error": "VALIDATION_ERROR", "detail": "lot_override_reason es requerido cuando se especifica lot_id"}
            
            # Validar que el lote existe y está disponible
            try:
                lot = StockLot.objects.get(
                    id=effective_lot_id,
                    product_id=item.product_id,
                    qty_on_hand__gt=0
                )
            except StockLot.DoesNotExist:
                return 400, {"error": "INVALID_LOT", "detail": f"Lote {effective_lot_id} no encontrado"}
            
            # VALIDACIÓN BLOQUE D: Verificar flags de bloqueo
            if lot.is_quarantined:
                return 400, {"error": "LOT_BLOCKED", "detail": f"Lote {lot.lot_code} está en cuarentena"}
            
            if lot.is_reserved:
                return 400, {"error": "LOT_BLOCKED", "detail": f"Lote {lot.lot_code} está reservado"}
            
            # VALIDACIÓN BLOQUE D: Verificar permisos para override
            if not has_scope(user, 'pos_override'):
                return 403, {"error": "PERMISSION_DENIED", "detail": "No tienes permisos para hacer override de lotes"}
            
            # VALIDACIÓN BLOQUE D: Verificar PIN si se proporciona
            if sale_data.override_pin:
                # Por simplicidad, usamos un PIN fijo. En producción sería más sofisticado
                if sale_data.override_pin != "1234":
                    return 403, {"error": "INVALID_PIN", "detail": "PIN de override inválido"}
            
            # Usar allocate_lots_fefo con override - solo planificar
            try:
                # VALIDACIÓN BLOQUE D: Verificar vida útil mínima también en override
                min_shelf_life_days = customer.min_shelf_life_days if customer else 0
                
                # Si hay requisito de vida útil mínima, verificar el lote específico
                if min_shelf_life_days > 0 and lot.expiry_date:
                    from datetime import datetime, timedelta
                    min_expiry_date = datetime.now().date() + timedelta(days=min_shelf_life_days)
                    if lot.expiry_date < min_expiry_date:
                        return 400, {"error": "INSUFFICIENT_SHELF_LIFE", "detail": f"Lote {lot.lot_code} no cumple vida útil mínima de {min_shelf_life_days} días"}
                
                allocation_plan = allocate_lots_fefo(
                    product=product,
                    qty_needed=item.qty,
                    chosen_lot_id=effective_lot_id,
                    min_shelf_life_days=min_shelf_life_days
                )
                allocation_plans.append({
                    'item': item,
                    'product': product,
                    'plan': allocation_plan,
                    'type': 'override'
                })
            except StockError as e:
                if e.code == "INSUFFICIENT_STOCK":
                    return 400, {"error": "INSUFFICIENT_STOCK", "detail": f"Stock insuficiente para producto {product.name}: {str(e)}"}
                else:
                    return 400, {"error": e.code, "detail": str(e)}
    
    # FASE 2: Verificar disponibilidad de stock para todos los planes
    for plan_data in allocation_plans:
        for allocation in plan_data['plan']:
            lot = StockLot.objects.select_for_update().get(id=allocation.lot_id)
            if lot.qty_on_hand < allocation.qty_allocated:
                return 400, {"error": "INSUFFICIENT_STOCK", "detail": f"Stock insuficiente en lote {lot.lot_code}"}
    
    # FASE 3: Ejecutar todos los cambios (solo si todo está validado)
    all_movements = []
    
    try:
        for plan_data in allocation_plans:
            item = plan_data['item']
            product = plan_data['product']
            allocation_plan = plan_data['plan']
            plan_type = plan_data['type']
            
            # Ejecutar el plan de asignación
            for allocation in allocation_plan:
                lot = StockLot.objects.select_for_update().get(id=allocation.lot_id)
                
                # Reducir stock del lote
                lot.qty_on_hand -= allocation.qty_allocated
                lot.save(update_fields=["qty_on_hand"])
                
                # Determinar razón del movimiento
                if plan_type == 'override' and allocation.lot_id == item.lot_id:
                    reason = f"pos_sale_override: {item.lot_override_reason}"
                    
                    # BLOQUE E: Registrar auditoría de override
                    LotOverrideAudit.objects.create(
                        actor=user,
                        sale_id=sale_id,
                        product=product,
                        lot_chosen=lot,
                        qty=allocation.qty_allocated,
                        reason=item.lot_override_reason
                    )
                else:
                    reason = "pos_sale_fefo"
                
                # Crear movimiento
                movement = Movement.objects.create(
                    type=Movement.Type.EXIT,
                    product=product,
                    lot=lot,
                    qty=allocation.qty_allocated,
                    unit_cost=lot.unit_cost,
                    reason=reason,
                    created_by=user
                )
                all_movements.append(movement)
                
                # BLOQUE G: Crear registro de trazabilidad
                from .models import SaleItemLot
                SaleItemLot.objects.create(
                    sale_id=sale_id,
                    item_sequence=item.sequence,
                    product=product,
                    lot=lot,
                    qty_consumed=allocation.qty_allocated,
                    unit_price=item.unit_price,
                    movement=movement
                )
    
    except Exception as e:
        # En caso de error inesperado, la transacción se revierte automáticamente
        return 400, {"error": "INTERNAL_ERROR", "detail": f"Error interno: {str(e)}"}
    
    # Preparar respuesta
    movements_out = []
    for movement in all_movements:
        movements_out.append(SaleMovementOut(
            product_id=movement.product.id,
            product_name=movement.product.name,
            lot_id=movement.lot.id,
            lot_code=movement.lot.lot_code,
            qty=movement.qty,
            unit_cost=movement.unit_cost
        ))
    
    return 200, SaleOut(
        sale_id=sale_id,
        total_items=len(sale_data.items),
        movements=movements_out
    )


# ============================================================================
# ENDPOINTS PARA TRAZABILIDAD (BLOQUE G)
# ============================================================================

@router.get("/sale/{sale_id}/detail", response={200: SaleDetailOut, 404: ErrorOut, 403: ErrorOut, 401: ErrorOut})
def get_sale_detail(request, sale_id: str):
    """
    Obtiene el detalle completo de una venta con trazabilidad de lotes.
    
    Incluye información de qué lotes y cantidades se usaron para cada ítem,
    así como información de overrides si los hubo.
    
    Control de acceso:
    - Vendedores: Solo pueden ver sus propias ventas
    - Administradores: Pueden ver todas las ventas
    """
    from .models import SaleItemLot
    from django.db.models import Q
    
    # Verificar que la venta existe
    sale_items = SaleItemLot.objects.filter(sale_id=sale_id).select_related(
        'product', 'lot', 'movement'
    ).order_by('item_sequence', 'lot__expiry_date')
    
    if not sale_items.exists():
        return 404, {"error": "SALE_NOT_FOUND", "detail": f"Venta {sale_id} no encontrada"}
    
    # Control de acceso por roles
    if not request.user.is_authenticated:
        return 401, {"error": "AUTHENTICATION_REQUIRED", "detail": "Autenticación requerida"}
    
    # Si no es admin, verificar que sea el vendedor de la venta
    if not has_scope(request.user, 'reports'):  # Admin scope
        # Verificar si el usuario fue quien hizo la venta
        # (Asumimos que el created_by del primer movimiento es el vendedor)
        first_movement = sale_items.first().movement
        if first_movement.created_by != request.user:
            return 403, {"error": "ACCESS_DENIED", "detail": "No tienes permisos para ver esta venta"}
    
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
            'qty': sale_item.qty_consumed
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
        override_info = OverrideDetailOut(used=False)
        if product.id in override_by_product:
            audit = override_by_product[product.id]
            override_info = OverrideDetailOut(used=True, reason=audit.reason)
        
        items_out.append(SaleItemDetailOut(
            item_id=item_seq,
            product=ProductOut(
                id=product.id,
                code=product.code,
                name=product.name
            ),
            qty=item_data['total_qty'],
            unit_price=item_data['unit_price'],
            lots=[LotDetailOut(**lot) for lot in item_data['lots']],
            override=override_info
        ))
    
    return 200, SaleDetailOut(
        sale_id=sale_id,
        items=items_out
    )


@router.get("/sale/{sale_id}/lots.csv")
def export_sale_lots_csv(request, sale_id: str):
    """
    Exporta el desglose de lotes por ítem en formato CSV.
    
    Columnas: sale_id, item_id, product_code, lot_code, expiry_date, qty
    """
    from .models import SaleItemLot
    from django.http import HttpResponse
    import csv
    import io
    
    # Verificar que la venta existe
    sale_items = SaleItemLot.objects.filter(sale_id=sale_id).select_related(
        'product', 'lot'
    ).order_by('item_sequence', 'lot__expiry_date')
    
    if not sale_items.exists():
        raise HttpError(404, "Venta no encontrada")
    
    # TODO: Implementar control de acceso por roles
    
    # Crear respuesta CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Escribir encabezados
    writer.writerow(['sale_id', 'item_id', 'product_code', 'lot_code', 'expiry_date', 'qty'])
    
    # Escribir datos
    for sale_item in sale_items:
        writer.writerow([
            sale_item.sale_id,
            sale_item.item_sequence,
            sale_item.product.code,
            sale_item.lot.lot_code,
            sale_item.lot.expiry_date.isoformat() if sale_item.lot.expiry_date else '',
            str(sale_item.qty_consumed)
        ])
    
    # Preparar respuesta
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sale_{sale_id}_lots.csv"'
    return response


# ============================================================================
# SCHEMAS PARA PRICE QUOTE
# ============================================================================

class PriceQuoteItemIn(Schema):
    """Schema para ítem en solicitud de cotización."""
    product_id: int
    qty: Decimal
    unit: str  # "unit" o "package"


class PriceQuoteIn(Schema):
    """Schema para solicitud de cotización de precios."""
    customer_id: int
    items: List[PriceQuoteItemIn]


class PriceQuoteItemOut(Schema):
    """Schema para ítem en respuesta de cotización."""
    product_id: int
    name: str
    qty: Decimal
    unit_price: Decimal
    discount_item: Decimal
    subtotal: Decimal


class ComboDiscountOut(Schema):
    """Schema para descuento de combo."""
    name: str
    description: str
    discount_amount: Decimal
    items_affected: List[str]


class PriceQuoteOut(Schema):
    """Schema para respuesta de cotización de precios."""
    items: List[PriceQuoteItemOut]
    combo_discounts: List[ComboDiscountOut]
    subtotal: Decimal
    discounts_total: Decimal
    total: Decimal


@router.post("/price-quote", response={200: PriceQuoteOut, 400: ErrorOut, 404: ErrorOut})
def get_price_quote(request, data: PriceQuoteIn):
    """
    Endpoint para obtener cotización de precios con beneficios aplicados.
    
    Usa normalize_qty para conversión de unidades y el motor de pricing
    para aplicar descuentos por segmento y combos.
    """
    try:
        # Validaciones de hardening
        if not data.items:
            raise HttpError(400, "Debe incluir al menos un item")
        
        if len(data.items) > 50:
            raise HttpError(400, "Máximo 50 items permitidos por cotización")
        
        # Validar cantidades positivas
        for item in data.items:
            if item.qty <= 0:
                raise HttpError(400, f"La cantidad debe ser mayor a 0 para el producto {item.product_id}")
        
        # Obtener cliente
        try:
            customer = Customer.objects.get(id=data.customer_id)
        except Customer.DoesNotExist:
            raise HttpError(404, "Cliente no encontrado")
        
        # Preparar items para el motor de pricing
        items_data = []
        original_items = {}  # Para mantener las cantidades originales convertidas
        for item in data.items:
            try:
                product = Product.objects.get(id=item.product_id)
            except Product.DoesNotExist:
                raise HttpError(404, f"Producto {item.product_id} no encontrado")
            
            # Validar cantidad usando normalize_qty (para verificar que es válida)
            try:
                normalize_qty(product, item.qty, item.unit)
            except ValueError as e:
                raise HttpError(400, f"Error en cantidad para producto {product.code}: {str(e)}")
            
            # Guardar cantidad original para la respuesta
            original_items[product.id] = item.qty
            
            # Convertir cantidad para el motor de pricing si es necesario
            if item.unit == 'unit' and product.pack_size:
                # Si se envían unidades, convertir a paquetes para pricing
                converted_qty = item.qty / Decimal(str(product.pack_size))
            elif item.unit == 'package':
                # Si se envían paquetes, mantener como paquetes
                converted_qty = item.qty
            else:
                # Para otros casos, mantener la cantidad original
                converted_qty = item.qty
            
            # Pasar cantidad convertida al motor de pricing
            items_data.append({
                'product_id': product.id,
                'quantity': converted_qty
            })
        
        # Usar el motor de pricing para calcular precios con beneficios
        quote = price_quote(customer, items_data)
        
        # Formatear respuesta según especificación
        response_items = []
        for pricing_item in quote.items:
            # Calcular descuento individual (diferencia entre precio original y con descuento)
            original_price = pricing_item.product.price
            discount_per_unit = original_price - pricing_item.unit_price
            discount_item = discount_per_unit * pricing_item.quantity
            
            response_items.append(PriceQuoteItemOut(
                product_id=pricing_item.product.id,
                name=pricing_item.product.name,
                qty=original_items[pricing_item.product.id],  # Usar cantidad original
                unit_price=pricing_item.unit_price,
                discount_item=discount_item,
                subtotal=pricing_item.subtotal
            ))
        
        # Formatear combo discounts
        combo_discounts = []
        for combo in quote.combo_discounts:
            combo_discounts.append(ComboDiscountOut(
                name=combo.name,
                description=combo.description,
                discount_amount=combo.discount_amount,
                items_affected=combo.items_affected
            ))
        
        # Calcular totales según DoD: totales = suma ítems − descuentos
        discounts_total = quote.segment_discount_amount + quote.total_combo_discount
        
        return PriceQuoteOut(
            items=response_items,
            combo_discounts=combo_discounts,
            subtotal=quote.subtotal,
            discounts_total=discounts_total,
            total=quote.total
        )
        
    except HttpError:
         raise
    except Exception as e:
         raise HttpError(400, f"Error procesando cotización: {str(e)}")