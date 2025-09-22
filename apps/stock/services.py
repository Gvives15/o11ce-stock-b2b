# apps/stock/services.py
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, NamedTuple

from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from apps.catalog.models import Product
from .models import StockLot, Movement, Warehouse

logger = logging.getLogger(__name__)


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
    total_available = sum(lot.qty_on_hand for lot in available_lots)
    if total_available < qty_needed:
        raise NotEnoughStock(product.id, qty_needed, total_available)
    
    # Planificar asignación FEFO
    allocation_plan = []
    remaining_qty = qty_needed
    
    for lot in available_lots:
        if remaining_qty <= 0:
            break
            
        qty_to_take = min(lot.qty_on_hand, remaining_qty)
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
            qty_available=lot.qty_on_hand,
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
    total_available_any_expiry = sum(lot.qty_on_hand for lot in base_query)
    if total_available_any_expiry < qty_needed:
        raise StockError(
            "INSUFFICIENT_STOCK", 
            f"Stock insuficiente. Solicitado: {qty_needed}, disponible: {total_available_any_expiry}"
        )
    
    # Aplicar filtro de vida útil mínima solo si no hay override de lote específico
    if chosen_lot_id is None:
        base_query = base_query.filter(expiry_date__gte=min_expiry_date)
        
        # Verificar si hay stock suficiente con vida útil adecuada
        total_available_with_shelf_life = sum(lot.qty_on_hand for lot in base_query)
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
        if chosen_lot.qty_on_hand >= qty_needed and chosen_lot.expiry_date < min_expiry_date:
            raise StockError(
                "INSUFFICIENT_SHELF_LIFE", 
                f"Lote {chosen_lot.lot_code} no cumple vida útil mínima de {min_shelf_life_days} días"
            )
        
        # Asignar del lote elegido lo que se pueda
        qty_from_chosen = min(remaining_qty, chosen_lot.qty_on_hand)
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
                
            qty_from_lot = min(remaining_qty, lot.qty_on_hand)
            allocation_plan.append(AllocationPlan(
                lot_id=lot.id,
                qty_allocated=qty_from_lot
            ))
            remaining_qty -= qty_from_lot
    
    # Verificar si se pudo asignar toda la cantidad
    if remaining_qty > 0:
        total_available = sum(lot.qty_on_hand for lot in base_query)
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
