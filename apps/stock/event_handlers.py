"""
Event handlers for Stock domain.

This module contains all event handlers for stock operations,
including internal stock events and external events from other domains.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import uuid4

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from apps.events.base import IEventHandler, HandlerResult, DomainEvent
from apps.events.utils import event_handler, publish_event
from apps.core.events import EventBus
from .models import StockLot, Movement, Warehouse
from .events import (
    # Entry events
    StockEntryRequested, StockEntryValidated, StockEntryCompleted, StockEntryFailed,
    # Exit events
    StockExitRequested, StockAllocationPlanned, StockExitCompleted, StockExitFailed,
    # Status events
    StockUpdated, LowStockDetected, StockThresholdUpdated,
    # Reservation events
    StockReservationRequested, StockReserved, StockReservationReleased,
    # Lot events
    LotExpiryWarning, LotExpired, LotQuarantined,
    # Validation events
    ProductValidationRequested, ProductValidated, StockValidationRequested,
    WarehouseValidationRequested, WarehouseValidated,
    # Integration events
    OrderStockValidationRequested, OrderStockValidated,
    # Notification events
    StockNotificationRequested
)

logger = logging.getLogger(__name__)


# ============================================================================
# STOCK ENTRY HANDLERS
# ============================================================================

class StockEntryHandler(IEventHandler):
    """Handler para eventos de entrada de stock"""
    
    @property
    def handler_name(self) -> str:
        """Unique name for this handler"""
        return "stock_entry_handler"
    
    @property
    def handled_events(self) -> List[str]:
        """List of event types this handler can process"""
        return [
            "StockEntryRequested",
            "ProductValidated", 
            "StockEntryValidated"
        ]
    
    async def handle(self, event: DomainEvent) -> HandlerResult:
        """Handle a domain event"""
        if isinstance(event, StockEntryRequested):
            return await self.handle_stock_entry_requested(event)
        elif isinstance(event, ProductValidated):
            return await self.handle_product_validated(event)
        elif isinstance(event, StockEntryValidated):
            return await self.handle_stock_entry_validated(event)
        else:
            return HandlerResult.failure(f"Unsupported event type: {type(event).__name__}")
    
    @event_handler
    async def handle_stock_entry_requested(self, event: StockEntryRequested) -> HandlerResult:
        """Procesa solicitud de entrada de stock"""
        try:
            # 1. Validar producto (solicitar validación al dominio Catalog)
            validation_id = str(uuid4())
            await EventBus.publish(ProductValidationRequested(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.product_id,
                aggregate_type="Product",
                validation_id=validation_id,
                product_id=event.product_id,
                requested_by_domain="stock"
            ))
            
            # 2. Validar warehouse si se especifica
            if event.warehouse_id:
                warehouse_validation_id = str(uuid4())
                await EventBus.publish(WarehouseValidationRequested(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(),
                    aggregate_id=event.warehouse_id,
                    aggregate_type="Warehouse",
                    validation_id=warehouse_validation_id,
                    warehouse_id=event.warehouse_id
                ))
            
            logger.info(f"Stock entry validation requested for entry {event.entry_id}")
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error processing stock entry request {event.entry_id}: {str(e)}")
            await EventBus.publish(StockEntryFailed(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.entry_id,
                aggregate_type="StockEntry",
                entry_id=event.entry_id,
                product_id=event.product_id,
                lot_code=event.lot_code,
                quantity=event.quantity,
                error_code="PROCESSING_ERROR",
                error_message=str(e)
            ))
            return HandlerResult.failure(str(e))
    
    @event_handler
    async def handle_product_validated(self, event: ProductValidated) -> HandlerResult:
        """Procesa validación de producto para entrada de stock"""
        try:
            if not event.product_exists or not event.product_active:
                # Buscar la entrada pendiente y fallar
                logger.warning(f"Product validation failed for {event.product_id}")
                return HandlerResult.success()  # No es error del handler
            
            # Continuar con el proceso de entrada
            # Nota: En una implementación real, necesitaríamos correlacionar
            # este evento con la entrada original usando el validation_id
            logger.info(f"Product {event.product_id} validated successfully")
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error processing product validation: {str(e)}")
            return HandlerResult.failure(str(e))
    
    @event_handler
    @transaction.atomic
    async def handle_stock_entry_validated(self, event: StockEntryValidated) -> HandlerResult:
        """Procesa entrada de stock validada"""
        try:
            # Importar aquí para evitar dependencias circulares
            from apps.catalog.models import Product
            
            # Obtener objetos necesarios
            product = get_object_or_404(Product, id=event.product_id)
            warehouse = None
            if event.warehouse_id:
                warehouse = get_object_or_404(Warehouse, id=event.warehouse_id)
            
            # Buscar o crear el lote
            stock_lot, lot_created = StockLot.objects.get_or_create(
                product=product,
                lot_code=event.lot_code,
                warehouse=warehouse,
                defaults={
                    'expiry_date': event.expiry_date,
                    'unit_cost': event.unit_cost,
                    'qty_on_hand': Decimal('0')
                }
            )
            
            # Verificar consistencia si el lote ya existía
            if not lot_created and stock_lot.expiry_date != event.expiry_date:
                await EventBus.publish(StockEntryFailed(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(),
                    aggregate_id=event.entry_id,
                    aggregate_type="StockEntry",
                    entry_id=event.entry_id,
                    product_id=event.product_id,
                    lot_code=event.lot_code,
                    quantity=event.quantity,
                    error_code="LOT_MISMATCH",
                    error_message=f"Lot {event.lot_code} exists with different expiry date"
                ))
                return HandlerResult.failure("Lot expiry date mismatch")
            
            # Guardar cantidad anterior para el evento
            previous_quantity = stock_lot.qty_on_hand
            
            # Actualizar cantidad en el lote
            stock_lot.qty_on_hand += event.quantity
            stock_lot.save()
            
            # Crear el movimiento
            movement = Movement.objects.create(
                type=Movement.Type.ENTRY,
                product=product,
                lot=stock_lot,
                qty=event.quantity,
                unit_cost=event.unit_cost,
                reason=event.reason,
                created_by_id=None  # Se puede obtener del contexto del evento
            )
            
            # Publicar evento de entrada completada
            await EventBus.publish(StockEntryCompleted(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.entry_id,
                aggregate_type="StockEntry",
                entry_id=event.entry_id,
                movement_id=str(movement.id),
                lot_id=str(stock_lot.id),
                product_id=event.product_id,
                warehouse_id=event.warehouse_id,
                lot_code=event.lot_code,
                quantity=event.quantity,
                unit_cost=event.unit_cost,
                new_lot_created=lot_created,
                previous_quantity=previous_quantity,
                new_quantity=stock_lot.qty_on_hand,
                processed_at=datetime.now()
            ))
            
            # Publicar evento de stock actualizado
            await EventBus.publish(StockUpdated(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=str(stock_lot.id),
                aggregate_type="StockLot",
                product_id=event.product_id,
                lot_id=str(stock_lot.id),
                warehouse_id=event.warehouse_id,
                previous_quantity=previous_quantity,
                new_quantity=stock_lot.qty_on_hand,
                change_quantity=event.quantity,
                change_type="entry",
                reason=event.reason,
                movement_id=str(movement.id)
            ))
            
            logger.info(f"Stock entry completed: {event.entry_id}")
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error completing stock entry {event.entry_id}: {str(e)}")
            await EventBus.publish(StockEntryFailed(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.entry_id,
                aggregate_type="StockEntry",
                entry_id=event.entry_id,
                product_id=event.product_id,
                lot_code=event.lot_code,
                quantity=event.quantity,
                error_code="PROCESSING_ERROR",
                error_message=str(e)
            ))
            return HandlerResult.failure(str(e))


# ============================================================================
# STOCK EXIT HANDLERS
# ============================================================================

class StockExitHandler(IEventHandler):
    """Handler para eventos de salida de stock"""
    
    @event_handler
    async def handle_stock_exit_requested(self, event: StockExitRequested) -> HandlerResult:
        """Procesa solicitud de salida de stock usando FEFO"""
        try:
            # Importar aquí para evitar dependencias circulares
            from apps.catalog.models import Product
            
            # Obtener producto
            product = get_object_or_404(Product, id=event.product_id)
            warehouse = None
            if event.warehouse_id:
                warehouse = get_object_or_404(Warehouse, id=event.warehouse_id)
            
            # Buscar lotes disponibles usando FEFO
            lots_query = StockLot.objects.filter(
                product=product,
                qty_on_hand__gt=0
            )
            
            if event.exclude_quarantined:
                lots_query = lots_query.filter(is_quarantined=False)
            
            if event.exclude_reserved:
                lots_query = lots_query.filter(is_reserved=False)
            
            if warehouse:
                lots_query = lots_query.filter(warehouse=warehouse)
            
            if event.min_shelf_life_days > 0:
                min_expiry = date.today() + timedelta(days=event.min_shelf_life_days)
                lots_query = lots_query.filter(expiry_date__gte=min_expiry)
            
            # Ordenar por FEFO (First Expired, First Out)
            lots = lots_query.order_by('expiry_date', 'id')
            
            # Calcular plan de asignación
            total_available = sum(lot.qty_on_hand for lot in lots)
            sufficient_stock = event.quantity <= total_available
            
            allocations = []
            remaining = event.quantity
            
            if sufficient_stock:
                for lot in lots:
                    if remaining <= 0:
                        break
                    
                    allocated = min(remaining, lot.qty_on_hand)
                    if allocated > 0:
                        allocations.append({
                            "lot_id": str(lot.id),
                            "quantity": allocated,
                            "unit_cost": lot.unit_cost
                        })
                        remaining -= allocated
            
            # Publicar plan de asignación
            await EventBus.publish(StockAllocationPlanned(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.exit_id,
                aggregate_type="StockExit",
                exit_id=event.exit_id,
                product_id=event.product_id,
                total_quantity=event.quantity,
                allocations=allocations,
                sufficient_stock=sufficient_stock,
                total_available=total_available,
                shortage_quantity=max(Decimal('0'), event.quantity - total_available)
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error processing stock exit request {event.exit_id}: {str(e)}")
            await EventBus.publish(StockExitFailed(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.exit_id,
                aggregate_type="StockExit",
                exit_id=event.exit_id,
                product_id=event.product_id,
                quantity=event.quantity,
                error_code="PROCESSING_ERROR",
                error_message=str(e)
            ))
            return HandlerResult.failure(str(e))
    
    @event_handler
    @transaction.atomic
    async def handle_stock_allocation_planned(self, event: StockAllocationPlanned) -> HandlerResult:
        """Ejecuta el plan de asignación de stock"""
        try:
            if not event.sufficient_stock:
                await EventBus.publish(StockExitFailed(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(),
                    aggregate_id=event.exit_id,
                    aggregate_type="StockExit",
                    exit_id=event.exit_id,
                    product_id=event.product_id,
                    quantity=event.total_quantity,
                    error_code="INSUFFICIENT_STOCK",
                    error_message=f"Requested {event.total_quantity}, available {event.total_available}",
                    available_quantity=event.total_available
                ))
                return HandlerResult.success()  # No es error del handler
            
            # Importar aquí para evitar dependencias circulares
            from apps.catalog.models import Product
            
            product = get_object_or_404(Product, id=event.product_id)
            movements = []
            
            # Ejecutar cada asignación
            for allocation in event.allocations:
                lot = get_object_or_404(StockLot, id=allocation["lot_id"])
                quantity = allocation["quantity"]
                
                # Verificar que el lote aún tenga stock suficiente
                if lot.qty_on_hand < quantity:
                    raise ValueError(f"Lot {lot.id} has insufficient stock")
                
                # Actualizar cantidad del lote
                lot.qty_on_hand -= quantity
                lot.save()
                
                # Crear movimiento
                movement = Movement.objects.create(
                    type=Movement.Type.EXIT,
                    product=product,
                    lot=lot,
                    qty=quantity,
                    unit_cost=lot.unit_cost,
                    reason="sale",  # Se puede obtener del evento original
                    # order=order,  # Se puede obtener del contexto
                    created_by_id=None  # Se puede obtener del contexto
                )
                
                movements.append({
                    "movement_id": str(movement.id),
                    "lot_id": str(lot.id),
                    "quantity": quantity
                })
                
                # Publicar evento de stock actualizado por cada lote
                await EventBus.publish(StockUpdated(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(),
                    aggregate_id=str(lot.id),
                    aggregate_type="StockLot",
                    product_id=event.product_id,
                    lot_id=str(lot.id),
                    warehouse_id=str(lot.warehouse.id) if lot.warehouse else None,
                    previous_quantity=lot.qty_on_hand + quantity,
                    new_quantity=lot.qty_on_hand,
                    change_quantity=-quantity,
                    change_type="exit",
                    reason="sale",
                    movement_id=str(movement.id)
                ))
            
            # Publicar evento de salida completada
            await EventBus.publish(StockExitCompleted(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.exit_id,
                aggregate_type="StockExit",
                exit_id=event.exit_id,
                product_id=event.product_id,
                total_quantity=event.total_quantity,
                movements=movements,
                processed_at=datetime.now()
            ))
            
            logger.info(f"Stock exit completed: {event.exit_id}")
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error executing stock allocation {event.exit_id}: {str(e)}")
            await EventBus.publish(StockExitFailed(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.exit_id,
                aggregate_type="StockExit",
                exit_id=event.exit_id,
                product_id=event.product_id,
                quantity=event.total_quantity,
                error_code="EXECUTION_ERROR",
                error_message=str(e)
            ))
            return HandlerResult.failure(str(e))


# ============================================================================
# STOCK MONITORING HANDLERS
# ============================================================================

class StockMonitoringHandler(IEventHandler):
    """Handler para monitoreo de stock"""
    
    @event_handler
    async def handle_stock_updated(self, event: StockUpdated) -> HandlerResult:
        """Monitorea actualizaciones de stock para detectar niveles bajos"""
        try:
            # Importar aquí para evitar dependencias circulares
            from apps.catalog.models import Product
            
            # Obtener información del producto
            product = get_object_or_404(Product, id=event.product_id)
            
            # Calcular stock total del producto
            total_stock = StockLot.objects.filter(
                product=product,
                qty_on_hand__gt=0
            ).aggregate(
                total=models.Sum('qty_on_hand')
            )['total'] or Decimal('0')
            
            # Verificar si está por debajo del umbral mínimo
            # Nota: El umbral debería venir de la configuración del producto
            minimum_threshold = getattr(product, 'minimum_stock_level', Decimal('10'))
            
            if total_stock <= minimum_threshold:
                severity = "critical" if total_stock == 0 else "high" if total_stock <= minimum_threshold * Decimal('0.5') else "medium"
                
                await EventBus.publish(LowStockDetected(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(),
                    aggregate_id=event.product_id,
                    aggregate_type="Product",
                    product_id=event.product_id,
                    product_name=product.name,
                    product_sku=product.sku,
                    current_quantity=total_stock,
                    minimum_threshold=minimum_threshold,
                    shortage_quantity=minimum_threshold - total_stock,
                    warehouse_id=event.warehouse_id,
                    severity=severity,
                    requires_immediate_action=(severity in ["high", "critical"])
                ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error monitoring stock update: {str(e)}")
            return HandlerResult.failure(str(e))
    
    @event_handler
    async def handle_low_stock_detected(self, event: LowStockDetected) -> HandlerResult:
        """Maneja detección de stock bajo"""
        try:
            # Solicitar notificación
            await EventBus.publish(StockNotificationRequested(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.product_id,
                aggregate_type="Product",
                notification_id=str(uuid4()),
                notification_type="low_stock",
                priority=event.severity,
                product_id=event.product_id,
                product_name=event.product_name,
                message=f"Stock bajo para {event.product_name}: {event.current_quantity} unidades (mínimo: {event.minimum_threshold})",
                details={
                    "current_quantity": float(event.current_quantity),
                    "minimum_threshold": float(event.minimum_threshold),
                    "shortage_quantity": float(event.shortage_quantity),
                    "warehouse_id": event.warehouse_id,
                    "severity": event.severity
                },
                notify_roles=["inventory_manager", "purchasing"],
                notify_email=True,
                notify_dashboard=True
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error handling low stock detection: {str(e)}")
            return HandlerResult.failure(str(e))


# ============================================================================
# LOT MANAGEMENT HANDLERS
# ============================================================================

class LotManagementHandler(IEventHandler):
    """Handler para gestión de lotes"""
    
    @event_handler
    async def handle_lot_expiry_warning(self, event: LotExpiryWarning) -> HandlerResult:
        """Maneja advertencias de lotes próximos a vencer"""
        try:
            # Solicitar notificación
            await EventBus.publish(StockNotificationRequested(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.lot_id,
                aggregate_type="StockLot",
                notification_id=str(uuid4()),
                notification_type="expiry_warning",
                priority=event.severity,
                product_id=event.product_id,
                product_name=event.product_name,
                message=f"Lote {event.lot_code} vence en {event.days_to_expiry} días ({event.expiry_date})",
                details={
                    "lot_id": event.lot_id,
                    "lot_code": event.lot_code,
                    "expiry_date": event.expiry_date.isoformat(),
                    "days_to_expiry": event.days_to_expiry,
                    "current_quantity": float(event.current_quantity),
                    "warehouse_id": event.warehouse_id
                },
                notify_roles=["inventory_manager", "quality_control"],
                notify_email=True,
                notify_dashboard=True
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error handling lot expiry warning: {str(e)}")
            return HandlerResult.failure(str(e))
    
    @event_handler
    @transaction.atomic
    async def handle_lot_expired(self, event: LotExpired) -> HandlerResult:
        """Maneja lotes expirados"""
        try:
            if event.requires_quarantine:
                # Poner lote en cuarentena
                lot = get_object_or_404(StockLot, id=event.lot_id)
                lot.is_quarantined = True
                lot.save()
                
                await EventBus.publish(LotQuarantined(
                    event_id=str(uuid4()),
                    occurred_at=datetime.now(),
                    aggregate_id=event.lot_id,
                    aggregate_type="StockLot",
                    lot_id=event.lot_id,
                    product_id=event.product_id,
                    lot_code=event.lot_code,
                    quantity=event.remaining_quantity,
                    reason="expired",
                    quarantine_notes=f"Lote expirado el {event.expiry_date}"
                ))
            
            # Solicitar notificación
            await EventBus.publish(StockNotificationRequested(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.lot_id,
                aggregate_type="StockLot",
                notification_id=str(uuid4()),
                notification_type="lot_expired",
                priority="high",
                product_id=event.product_id,
                product_name=event.product_name,
                message=f"Lote {event.lot_code} ha expirado ({event.expiry_date})",
                details={
                    "lot_id": event.lot_id,
                    "lot_code": event.lot_code,
                    "expiry_date": event.expiry_date.isoformat(),
                    "remaining_quantity": float(event.remaining_quantity),
                    "requires_quarantine": event.requires_quarantine,
                    "requires_disposal": event.requires_disposal
                },
                notify_roles=["inventory_manager", "quality_control"],
                notify_email=True,
                notify_dashboard=True
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error handling expired lot: {str(e)}")
            return HandlerResult.failure(str(e))


# ============================================================================
# INTEGRATION HANDLERS (para otros dominios)
# ============================================================================

class StockIntegrationHandler(IEventHandler):
    """Handler para integración con otros dominios"""
    
    @event_handler
    async def handle_order_stock_validation_requested(self, event: OrderStockValidationRequested) -> HandlerResult:
        """Valida disponibilidad de stock para una orden"""
        try:
            item_validations = []
            all_items_available = True
            total_value = Decimal('0')
            
            for item in event.items:
                product_id = item["product_id"]
                requested_qty = Decimal(str(item["quantity"]))
                
                # Calcular stock disponible
                available_stock = StockLot.objects.filter(
                    product_id=product_id,
                    qty_on_hand__gt=0,
                    is_quarantined=False,
                    is_reserved=False
                ).aggregate(
                    total=models.Sum('qty_on_hand')
                )['total'] or Decimal('0')
                
                item_available = available_stock >= requested_qty
                if not item_available:
                    all_items_available = False
                
                # Calcular valor (usando costo promedio ponderado)
                if item_available:
                    lots = StockLot.objects.filter(
                        product_id=product_id,
                        qty_on_hand__gt=0,
                        is_quarantined=False,
                        is_reserved=False
                    ).order_by('expiry_date')
                    
                    remaining = requested_qty
                    item_value = Decimal('0')
                    
                    for lot in lots:
                        if remaining <= 0:
                            break
                        take = min(remaining, lot.qty_on_hand)
                        item_value += take * lot.unit_cost
                        remaining -= take
                    
                    total_value += item_value
                
                item_validations.append({
                    "product_id": product_id,
                    "available": item_available,
                    "quantity_available": available_stock,
                    "quantity_requested": requested_qty
                })
            
            # Publicar resultado de validación
            await EventBus.publish(OrderStockValidated(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.order_id,
                aggregate_type="Order",
                validation_id=event.validation_id,
                order_id=event.order_id,
                all_items_available=all_items_available,
                item_validations=item_validations,
                total_value=total_value
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error validating stock for order {event.order_id}: {str(e)}")
            return HandlerResult.failure(str(e))


# ============================================================================
# WAREHOUSE VALIDATION HANDLER
# ============================================================================

class WarehouseValidationHandler(IEventHandler):
    """Handler para validación de depósitos"""
    
    @event_handler
    async def handle_warehouse_validation_requested(self, event: WarehouseValidationRequested) -> HandlerResult:
        """Valida existencia y estado de un depósito"""
        try:
            try:
                warehouse = Warehouse.objects.get(id=event.warehouse_id)
                warehouse_exists = True
                warehouse_active = warehouse.is_active if hasattr(warehouse, 'is_active') else True
                warehouse_name = warehouse.name
            except Warehouse.DoesNotExist:
                warehouse_exists = False
                warehouse_active = False
                warehouse_name = None
            
            await EventBus.publish(WarehouseValidated(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.warehouse_id,
                aggregate_type="Warehouse",
                validation_id=event.validation_id,
                warehouse_id=event.warehouse_id,
                warehouse_exists=warehouse_exists,
                warehouse_active=warehouse_active,
                warehouse_name=warehouse_name
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error validating warehouse {event.warehouse_id}: {str(e)}")
            return HandlerResult.failure(str(e))


class StockValidationHandler(IEventHandler):
    """Handler para validación de disponibilidad de stock"""
    
    @property
    def handler_name(self) -> str:
        """Unique name for this handler"""
        return "stock_validation_handler"
    
    @property
    def handled_events(self) -> List[str]:
        """List of event types this handler can process"""
        return ["StockValidationRequested"]
    
    @event_handler
    async def handle(self, event: StockValidationRequested) -> HandlerResult:
        """Valida disponibilidad de stock y publica resultado"""
        try:
            from .models import StockLot
            from django.db import models
            from uuid import uuid4
            from datetime import datetime
            
            # Calcular stock disponible
            available_stock = StockLot.objects.filter(
                product_id=event.product_id,
                qty_on_hand__gt=0,
                is_quarantined=False,
                is_reserved=False
            )
            
            if event.warehouse_id:
                available_stock = available_stock.filter(warehouse_id=event.warehouse_id)
            
            total_available = available_stock.aggregate(
                total=models.Sum('qty_on_hand')
            )['total'] or Decimal('0')
            
            # Determinar si hay suficiente stock
            is_available = total_available >= event.quantity
            
            # Publicar evento de resultado
            await EventBus.publish(StockValidated(
                event_id=str(uuid4()),
                occurred_at=datetime.now(),
                aggregate_id=event.product_id,
                aggregate_type="Product",
                validation_id=event.validation_id,
                product_id=event.product_id,
                requested_quantity=event.quantity,
                available_quantity=total_available,
                warehouse_id=event.warehouse_id,
                is_available=is_available,
                order_id=event.order_id,
                correlation_id=event.correlation_id
            ))
            
            return HandlerResult.success()
            
        except Exception as e:
            logger.error(f"Error validating stock for product {event.product_id}: {str(e)}")
            return HandlerResult.failure(str(e))