# apps/stock/fefo_service.py
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, NamedTuple
from django.db import transaction, models
from django.db.models import F, Sum
from django.core.exceptions import ValidationError

from apps.catalog.models import Product
from .models import StockLot, Movement, Warehouse
from .services import NotEnoughStock, NoLotsAvailable, StockError


class FEFOAllocation(NamedTuple):
    """Resultado de asignación FEFO."""
    lot_id: int
    lot_code: str
    expiry_date: date
    qty_allocated: Decimal
    unit_cost: Decimal


class FEFOService:
    """Servicio para operaciones FEFO (First Expired, First Out) thread-safe."""
    
    @staticmethod
    def allocate_stock_fefo(
        product_id: int,
        qty_needed: Decimal,
        user_id: int,
        warehouse_id: Optional[int] = None,
        min_shelf_life_days: int = 0,
        reason: str = "FEFO allocation"
    ) -> List[FEFOAllocation]:
        """
        Asigna stock siguiendo FEFO de manera thread-safe.
        
        Args:
            product_id: ID del producto
            qty_needed: Cantidad necesaria
            user_id: ID del usuario que realiza la operación
            warehouse_id: ID del almacén (opcional)
            min_shelf_life_days: Días mínimos de vida útil
            reason: Razón del movimiento
            
        Returns:
            Lista de asignaciones FEFO realizadas
            
        Raises:
            NotEnoughStock: Si no hay suficiente stock
            NoLotsAvailable: Si no hay lotes disponibles
        """
        if qty_needed <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        
        with transaction.atomic():
            # Obtener producto
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise ValidationError(f"Producto {product_id} no existe")
            
            # Fecha mínima de vencimiento
            min_expiry_date = date.today() + timedelta(days=min_shelf_life_days)
            
            # Query FEFO con lock para evitar condiciones de carrera
            lots_query = StockLot.objects.select_for_update(skip_locked=True).filter(
                product_id=product_id,
                qty_on_hand__gt=0,
                expiry_date__gte=min_expiry_date,
                is_quarantined=False,
                is_reserved=False
            )
            
            if warehouse_id is not None:
                lots_query = lots_query.filter(warehouse_id=warehouse_id)
            
            # Ordenar por FEFO: expiry_date ASC, id ASC (para estabilidad)
            available_lots = list(lots_query.order_by('expiry_date', 'id'))
            
            if not available_lots:
                criteria = f"vida útil >= {min_shelf_life_days} días"
                if warehouse_id:
                    criteria += f", almacén {warehouse_id}"
                raise NoLotsAvailable(product_id, criteria)
            
            # Verificar stock total disponible
            total_available = sum(lot.qty_on_hand for lot in available_lots)
            if total_available < qty_needed:
                raise NotEnoughStock(product_id, qty_needed, total_available)
            
            # Realizar asignación FEFO
            allocations = []
            remaining_qty = qty_needed
            
            for lot in available_lots:
                if remaining_qty <= 0:
                    break
                
                # Cantidad a asignar de este lote
                qty_from_lot = min(remaining_qty, lot.qty_on_hand)
                
                # Update atómico usando F() para evitar condiciones de carrera
                updated_rows = StockLot.objects.filter(
                    id=lot.id,
                    qty_on_hand__gte=qty_from_lot  # Verificación adicional
                ).update(
                    qty_on_hand=F('qty_on_hand') - qty_from_lot
                )
                
                if updated_rows == 0:
                    # El lote fue modificado por otro proceso, reintentar
                    raise StockError(
                        "CONCURRENT_MODIFICATION",
                        f"Lote {lot.id} fue modificado concurrentemente"
                    )
                
                # Crear movimiento de salida
                Movement.objects.create(
                    type=Movement.Type.EXIT,
                    product=product,
                    lot_id=lot.id,
                    qty=qty_from_lot,
                    unit_cost=lot.unit_cost,
                    reason=reason,
                    created_by_id=user_id
                )
                
                # Agregar a asignaciones
                allocations.append(FEFOAllocation(
                    lot_id=lot.id,
                    lot_code=lot.lot_code,
                    expiry_date=lot.expiry_date,
                    qty_allocated=qty_from_lot,
                    unit_cost=lot.unit_cost
                ))
                
                remaining_qty -= qty_from_lot
            
            if remaining_qty > 0:
                # Esto no debería pasar si la lógica es correcta
                raise StockError(
                    "ALLOCATION_ERROR",
                    f"No se pudo asignar toda la cantidad. Faltante: {remaining_qty}"
                )
            
            return allocations
    
    @staticmethod
    def get_available_stock(
        product_id: int,
        warehouse_id: Optional[int] = None,
        min_shelf_life_days: int = 0
    ) -> Decimal:
        """
        Obtiene el stock total disponible para un producto.
        
        Args:
            product_id: ID del producto
            warehouse_id: ID del almacén (opcional)
            min_shelf_life_days: Días mínimos de vida útil
            
        Returns:
            Cantidad total disponible
        """
        min_expiry_date = date.today() + timedelta(days=min_shelf_life_days)
        
        lots_query = StockLot.objects.filter(
            product_id=product_id,
            qty_on_hand__gt=0,
            expiry_date__gte=min_expiry_date,
            is_quarantined=False,
            is_reserved=False
        )
        
        if warehouse_id is not None:
            lots_query = lots_query.filter(warehouse_id=warehouse_id)
        
        result = lots_query.aggregate(total=Sum('qty_on_hand'))
        return result['total'] or Decimal('0')
    
    @staticmethod
    def get_lots_fefo_order(
        product_id: int,
        warehouse_id: Optional[int] = None,
        min_shelf_life_days: int = 0
    ) -> List[dict]:
        """
        Obtiene los lotes en orden FEFO para visualización.
        
        Args:
            product_id: ID del producto
            warehouse_id: ID del almacén (opcional)
            min_shelf_life_days: Días mínimos de vida útil
            
        Returns:
            Lista de lotes ordenados por FEFO
        """
        min_expiry_date = date.today() + timedelta(days=min_shelf_life_days)
        
        lots_query = StockLot.objects.select_related('warehouse').filter(
            product_id=product_id,
            qty_on_hand__gt=0,
            expiry_date__gte=min_expiry_date,
            is_quarantined=False,
            is_reserved=False
        )
        
        if warehouse_id is not None:
            lots_query = lots_query.filter(warehouse_id=warehouse_id)
        
        lots = lots_query.order_by('expiry_date', 'id')
        
        return [
            {
                'lot_id': lot.id,
                'lot_code': lot.lot_code,
                'expiry_date': lot.expiry_date,
                'qty_on_hand': lot.qty_on_hand,
                'unit_cost': lot.unit_cost,
                'warehouse_name': lot.warehouse.name if lot.warehouse else None,
                'days_to_expiry': (lot.expiry_date - date.today()).days
            }
            for lot in lots
        ]