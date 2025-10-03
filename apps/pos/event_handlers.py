"""
Handlers de eventos para el dominio POS.

Este módulo contiene los handlers que procesan eventos relacionados con POS,
tanto eventos internos del dominio como eventos de otros dominios que afectan
las operaciones POS.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.events.base import EventHandler
from apps.stock.events import (
    StockValidationResponse,
    StockAllocationResponse,
    StockReserved,
    StockReleased,
    LowStockDetected,
    StockExpiringSoon
)
from apps.catalog.events import ProductUpdated, ProductDiscontinued
from apps.customers.events import CustomerValidationResponse
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
    PriceQuoteProcessingFailed
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# HANDLERS PARA EVENTOS INTERNOS POS
# ============================================================================

class SaleAuditHandler(EventHandler):
    """
    Handler para auditoría de ventas.
    
    Procesa eventos de ventas para mantener registros de auditoría,
    generar reportes y notificaciones.
    """
    
    def handle_sale_created(self, event: SaleCreated) -> None:
        """Procesa la creación de una venta para auditoría."""
        logger.info(
            f"Venta creada: {event.sale_id} por usuario {event.username} "
            f"con {event.total_items} items por ${event.total_amount}"
        )
        
        # Aquí se podría integrar con sistemas de auditoría externos
        # Por ejemplo, enviar a un sistema de logging centralizado
        
        # Si se usó override PIN, registrar para auditoría especial
        if event.override_pin_used:
            logger.warning(
                f"Override PIN usado en venta {event.sale_id} por {event.username}"
            )
    
    def handle_lot_override_executed(self, event: LotOverrideExecuted) -> None:
        """Procesa overrides de lotes para auditoría especial."""
        logger.warning(
            f"Override de lote ejecutado: Venta {event.sale_id}, "
            f"Usuario {event.username}, Lote {event.lot_code}, "
            f"Razón: {event.reason}"
        )
        
        # Aquí se podría notificar a supervisores o sistemas de compliance
    
    def handle_sale_detail_requested(self, event: SaleDetailRequested) -> None:
        """Audita accesos a detalles de ventas."""
        if event.access_granted:
            logger.info(
                f"Acceso a detalle de venta {event.sale_id} "
                f"otorgado a {event.requested_by_username} "
                f"(razón: {event.access_reason})"
            )
        else:
            logger.warning(
                f"Acceso a detalle de venta {event.sale_id} "
                f"denegado a {event.requested_by_username}"
            )
    
    def handle_sale_data_exported(self, event: SaleDataExported) -> None:
        """Audita exportaciones de datos de ventas."""
        logger.info(
            f"Datos de venta {event.sale_id} exportados en formato {event.export_format} "
            f"por {event.exported_by_username} ({event.records_count} registros)"
        )


class SaleNotificationHandler(EventHandler):
    """
    Handler para notificaciones relacionadas con ventas.
    
    Envía notificaciones a diferentes sistemas cuando ocurren eventos
    importantes en las ventas.
    """
    
    def handle_sale_created(self, event: SaleCreated) -> None:
        """Envía notificaciones cuando se crea una venta."""
        # Notificar a sistemas de inventario sobre la venta
        # Esto podría ser útil para sistemas de reposición automática
        
        # Si es una venta grande, notificar a gerencia
        if event.total_amount > Decimal('10000'):
            logger.info(f"Venta grande detectada: {event.sale_id} por ${event.total_amount}")
            # Aquí se enviaría notificación a gerencia
    
    def handle_lot_override_requested(self, event: LotOverrideRequested) -> None:
        """Notifica cuando se solicita un override de lote."""
        # Notificar a supervisores sobre solicitudes de override
        logger.info(
            f"Override de lote solicitado: {event.requested_lot_code} "
            f"por {event.username} para venta {event.sale_id}"
        )
    
    def handle_sale_processing_failed(self, event: SaleProcessingFailed) -> None:
        """Notifica fallos en el procesamiento de ventas."""
        logger.error(
            f"Fallo en procesamiento de venta {event.sale_id}: "
            f"{event.error_code} - {event.error_message} "
            f"(etapa: {event.failure_stage})"
        )
        
        # Notificar a soporte técnico si es un error del sistema
        if event.error_code in ['INTERNAL_ERROR', 'DATABASE_ERROR']:
            # Aquí se enviaría alerta a soporte técnico
            pass


# ============================================================================
# HANDLERS PARA EVENTOS DE OTROS DOMINIOS
# ============================================================================

class StockEventHandler(EventHandler):
    """
    Handler para eventos del dominio Stock que afectan POS.
    
    Procesa eventos de stock para actualizar información relevante
    para las operaciones POS.
    """
    
    def handle_stock_validation_response(self, event: StockValidationResponse) -> None:
        """
        Procesa respuestas de validación de stock.
        
        Este handler se ejecuta cuando el dominio Stock responde
        a una solicitud de validación de POS.
        """
        if event.is_available:
            logger.debug(
                f"Stock disponible para validación {event.validation_id}: "
                f"{event.available_qty} unidades"
            )
        else:
            logger.warning(
                f"Stock insuficiente para validación {event.validation_id}: "
                f"Solicitado {event.requested_qty}, disponible {event.available_qty}"
            )
            
            # Aquí se podría notificar al usuario o sugerir alternativas
    
    def handle_stock_allocation_response(self, event: StockAllocationResponse) -> None:
        """
        Procesa respuestas de asignación de stock.
        
        Maneja las respuestas del dominio Stock cuando se solicita
        asignación de lotes para una venta.
        """
        if event.success:
            logger.debug(
                f"Stock asignado exitosamente para {event.allocation_id}: "
                f"{len(event.allocations)} lotes asignados"
            )
        else:
            logger.error(
                f"Fallo en asignación de stock {event.allocation_id}: "
                f"{event.error_message}"
            )
    
    def handle_low_stock_detected(self, event: LowStockDetected) -> None:
        """
        Procesa alertas de stock bajo.
        
        Cuando se detecta stock bajo, POS puede mostrar advertencias
        a los vendedores o sugerir productos alternativos.
        """
        logger.info(
            f"Stock bajo detectado para producto {event.product_name}: "
            f"{event.current_stock} unidades (umbral: {event.threshold})"
        )
        
        # Aquí se podría actualizar una cache de productos con stock bajo
        # para mostrar advertencias en la interfaz POS
    
    def handle_stock_expiring_soon(self, event: StockExpiringSoon) -> None:
        """
        Procesa alertas de productos próximos a vencer.
        
        POS puede usar esta información para sugerir promociones
        o alertar a los vendedores.
        """
        logger.info(
            f"Producto próximo a vencer: {event.product_name} "
            f"(lote {event.lot_code}, vence {event.expiry_date})"
        )
        
        # Aquí se podría actualizar una lista de productos en promoción
        # o generar alertas para los vendedores


class CustomerEventHandler(EventHandler):
    """
    Handler para eventos del dominio Customer que afectan POS.
    """
    
    def handle_customer_validation_response(self, event: CustomerValidationResponse) -> None:
        """
        Procesa respuestas de validación de clientes.
        
        Maneja las respuestas cuando POS solicita validar un cliente.
        """
        if event.is_valid:
            logger.debug(
                f"Cliente válido para validación {event.validation_id}: "
                f"{event.customer_name}"
            )
        else:
            logger.warning(
                f"Cliente inválido para validación {event.validation_id}: "
                f"ID {event.customer_id}"
            )


class ProductEventHandler(EventHandler):
    """
    Handler para eventos del dominio Product/Catalog que afectan POS.
    """
    
    def handle_product_updated(self, event: ProductUpdated) -> None:
        """
        Procesa actualizaciones de productos.
        
        Cuando se actualiza un producto, POS puede necesitar actualizar
        caches o notificar a los vendedores sobre cambios importantes.
        """
        logger.info(f"Producto actualizado: {event.product_name} (ID: {event.product_id})")
        
        # Si cambió el precio, podría ser importante para POS
        if 'price' in event.fields_changed:
            logger.info(f"Precio actualizado para producto {event.product_name}")
            # Aquí se podría invalidar cache de precios en POS
    
    def handle_product_discontinued(self, event: ProductDiscontinued) -> None:
        """
        Procesa discontinuación de productos.
        
        Cuando se discontinúa un producto, POS debe dejar de permitir
        su venta y notificar a los vendedores.
        """
        logger.warning(
            f"Producto discontinuado: {event.product_name} "
            f"(razón: {event.reason})"
        )
        
        # Aquí se podría actualizar una lista de productos no disponibles
        # o generar alertas para los vendedores


# ============================================================================
# HANDLERS PARA INTEGRACIÓN CON SISTEMAS EXTERNOS
# ============================================================================

class ExternalSystemsHandler(EventHandler):
    """
    Handler para integración con sistemas externos.
    
    Procesa eventos POS para enviar información a sistemas externos
    como ERP, CRM, sistemas de facturación, etc.
    """
    
    def handle_sale_created(self, event: SaleCreated) -> None:
        """
        Envía información de ventas a sistemas externos.
        
        Puede integrar con:
        - Sistemas de facturación
        - ERP corporativo
        - Sistemas de loyalty/puntos
        - Analytics de ventas
        """
        logger.debug(f"Enviando venta {event.sale_id} a sistemas externos")
        
        # Ejemplo de integración con sistema de facturación
        # self._send_to_billing_system(event)
        
        # Ejemplo de integración con sistema de loyalty
        # if event.customer_id:
        #     self._update_customer_points(event)
    
    def handle_price_quote_generated(self, event: PriceQuoteGenerated) -> None:
        """
        Envía cotizaciones a sistemas de CRM o analytics.
        """
        logger.debug(f"Enviando cotización {event.quote_id} a sistemas de analytics")
        
        # Aquí se podría enviar a sistemas de análisis de cotizaciones
        # para entender patrones de pricing y comportamiento de clientes
    
    def _send_to_billing_system(self, event: SaleCreated) -> None:
        """Envía venta a sistema de facturación (ejemplo)."""
        # Implementación específica del sistema de facturación
        pass
    
    def _update_customer_points(self, event: SaleCreated) -> None:
        """Actualiza puntos de loyalty del cliente (ejemplo)."""
        # Implementación específica del sistema de loyalty
        pass


# ============================================================================
# HANDLERS PARA MÉTRICAS Y ANALYTICS
# ============================================================================

class SalesMetricsHandler(EventHandler):
    """
    Handler para métricas y analytics de ventas.
    
    Procesa eventos de ventas para generar métricas en tiempo real
    y alimentar sistemas de business intelligence.
    """
    
    def handle_sale_created(self, event: SaleCreated) -> None:
        """Actualiza métricas de ventas en tiempo real."""
        logger.debug(f"Actualizando métricas para venta {event.sale_id}")
        
        # Aquí se podrían actualizar métricas como:
        # - Ventas por hora/día
        # - Productos más vendidos
        # - Performance por vendedor
        # - Análisis de overrides
        
        # Ejemplo de actualización de métricas
        # self._update_sales_metrics(event)
        # self._update_product_metrics(event)
        # self._update_user_metrics(event)
    
    def handle_lot_override_executed(self, event: LotOverrideExecuted) -> None:
        """Actualiza métricas de overrides."""
        logger.debug(f"Actualizando métricas de override para venta {event.sale_id}")
        
        # Métricas de overrides pueden ser importantes para:
        # - Compliance y auditoría
        # - Análisis de comportamiento de vendedores
        # - Optimización de procesos FEFO
    
    def _update_sales_metrics(self, event: SaleCreated) -> None:
        """Actualiza métricas generales de ventas."""
        # Implementación específica de métricas
        pass
    
    def _update_product_metrics(self, event: SaleCreated) -> None:
        """Actualiza métricas por producto."""
        # Implementación específica de métricas por producto
        pass
    
    def _update_user_metrics(self, event: SaleCreated) -> None:
        """Actualiza métricas por usuario/vendedor."""
        # Implementación específica de métricas por usuario
        pass