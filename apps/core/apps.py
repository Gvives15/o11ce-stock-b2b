from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core Application"
    
    def ready(self):
        """Initialize the Event Bus when Django is ready."""
        try:
            from apps.core.events import EventBus
            from django.conf import settings
            
            # Initialize Event Bus with configuration from settings
            event_bus_config = getattr(settings, 'EVENT_BUS_CONFIG', {})
            if event_bus_config.get('enabled', True):
                EventBus.initialize(event_bus_config)
                logger.info("Event Bus initialized successfully")
                
                # Register Stock domain event handlers
                self._register_stock_handlers()
                
                # Register POS domain event handlers
                self._register_pos_handlers()
                
        except Exception as e:
            logger.error(f"Failed to initialize Event Bus: {e}")
            # Don't raise exception to avoid breaking Django startup
    
    def _register_stock_handlers(self):
        """Register event handlers for the Stock domain."""
        try:
            from apps.stock.event_handlers import (
                StockEntryHandler,
                StockValidationHandler
            )
            from apps.stock.events import (
                StockEntryRequested,
                ProductValidated,
                StockEntryValidated,
                StockValidationRequested
            )
            from apps.core.events import EventBus
            
            # Create handler instances
            stock_entry_handler = StockEntryHandler()
            stock_validation_handler = StockValidationHandler()
            
            # Register handlers with their corresponding events
            EventBus.register_handler(StockEntryRequested, stock_entry_handler.handle_stock_entry_requested)
            EventBus.register_handler(StockValidationRequested, stock_validation_handler.handle)
            
            logger.info("Stock domain event handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register Stock domain handlers: {e}")
            # Don't raise exception to avoid breaking Django startup
    
    def _register_pos_handlers(self):
        """Register event handlers for the POS domain."""
        try:
            from apps.pos.event_handlers import (
                SaleAuditHandler,
                SaleNotificationHandler,
                StockEventHandler,
                CustomerEventHandler,
                ProductEventHandler,
                ExternalSystemsHandler,
                SalesMetricsHandler
            )
            from apps.pos.events import (
                SaleCreated,
                SaleItemProcessed,
                LotOverrideRequested,
                LotOverrideExecuted,
                PriceQuoteGenerated,
                SaleDetailRequested,
                SaleDataExported,
                SaleProcessingFailed,
                PriceQuoteProcessingFailed
            )
            from apps.stock.events import (
                StockValidationResponse,
                StockAllocationResponse,
                LowStockDetected,
                StockExpiringSoon
            )
            from apps.catalog.events import ProductUpdated, ProductDiscontinued
            from apps.customers.events import CustomerValidationResponse
            from apps.core.events import EventBus
            
            # Create handler instances
            audit_handler = SaleAuditHandler()
            notification_handler = SaleNotificationHandler()
            stock_event_handler = StockEventHandler()
            customer_event_handler = CustomerEventHandler()
            product_event_handler = ProductEventHandler()
            external_systems_handler = ExternalSystemsHandler()
            metrics_handler = SalesMetricsHandler()
            
            # Register POS internal event handlers
            EventBus.register_handler(SaleCreated, audit_handler.handle_sale_created)
            EventBus.register_handler(SaleCreated, notification_handler.handle_sale_created)
            EventBus.register_handler(SaleCreated, external_systems_handler.handle_sale_created)
            EventBus.register_handler(SaleCreated, metrics_handler.handle_sale_created)
            
            EventBus.register_handler(LotOverrideRequested, notification_handler.handle_lot_override_requested)
            EventBus.register_handler(LotOverrideExecuted, audit_handler.handle_lot_override_executed)
            EventBus.register_handler(LotOverrideExecuted, metrics_handler.handle_lot_override_executed)
            
            EventBus.register_handler(PriceQuoteGenerated, external_systems_handler.handle_price_quote_generated)
            EventBus.register_handler(SaleDetailRequested, audit_handler.handle_sale_detail_requested)
            EventBus.register_handler(SaleDataExported, audit_handler.handle_sale_data_exported)
            
            EventBus.register_handler(SaleProcessingFailed, notification_handler.handle_sale_processing_failed)
            
            # Register handlers for external domain events
            EventBus.register_handler(StockValidationResponse, stock_event_handler.handle_stock_validation_response)
            EventBus.register_handler(StockAllocationResponse, stock_event_handler.handle_stock_allocation_response)
            EventBus.register_handler(LowStockDetected, stock_event_handler.handle_low_stock_detected)
            EventBus.register_handler(StockExpiringSoon, stock_event_handler.handle_stock_expiring_soon)
            
            EventBus.register_handler(CustomerValidationResponse, customer_event_handler.handle_customer_validation_response)
            
            EventBus.register_handler(ProductUpdated, product_event_handler.handle_product_updated)
            EventBus.register_handler(ProductDiscontinued, product_event_handler.handle_product_discontinued)
            
            logger.info("POS domain event handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register POS domain handlers: {e}")
            # Don't raise exception to avoid breaking Django startup
