"""
Celery tasks for stock management with fault tolerance.
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from celery import shared_task
from django.db import transaction, models
from django.utils import timezone
from apps.catalog.models import Product
from apps.stock.models import StockLot
from apps.notifications.tasks import send_email_alert, send_low_stock_alert
from apps.core.metrics import increment_counter, set_gauge

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=180,  # 3 minutes
    time_limit=300,  # 5 minutes
)
def scan_near_expiry(self, days_ahead: int = 7):
    """
    Scan for products near expiry and send alerts.
    
    Args:
        days_ahead: Number of days ahead to check for expiry
    """
    try:
        logger.info(f"Starting near expiry scan for {days_ahead} days ahead")
        
        # Calculate expiry threshold
        expiry_threshold = date.today() + timedelta(days=days_ahead)
        
        # Find lots near expiry with available stock
        near_expiry_lots = StockLot.objects.select_related('product').filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=date.today(),  # Not already expired
            qty_on_hand__gt=0
        ).order_by('expiry_date', 'product__name')
        
        if not near_expiry_lots.exists():
            logger.info("No products near expiry found")
            set_gauge('products_near_expiry', 0)
            increment_counter('near_expiry_scans_total', {'status': 'no_products'})
            
            return {
                'status': 'success',
                'products_found': 0,
                'alerts_sent': 0
            }
        
        # Group by product for better reporting
        products_by_expiry = {}
        total_lots = 0
        
        for lot in near_expiry_lots:
            total_lots += 1
            product_key = lot.product.name
            
            if product_key not in products_by_expiry:
                products_by_expiry[product_key] = {
                    'product': lot.product,
                    'lots': [],
                    'total_qty': Decimal('0')
                }
            
            products_by_expiry[product_key]['lots'].append(lot)
            products_by_expiry[product_key]['total_qty'] += lot.qty_on_hand
        
        logger.info(f"Found {len(products_by_expiry)} products with {total_lots} lots near expiry")
        
        # Send alerts for each product
        alerts_sent = 0
        for product_name, product_data in products_by_expiry.items():
            try:
                # Prepare alert message
                lots_info = []
                for lot in product_data['lots']:
                    days_to_expiry = (lot.expiry_date - date.today()).days
                    lots_info.append(
                        f"  - Lote {lot.lot_code}: {lot.qty_on_hand} unidades "
                        f"(vence en {days_to_expiry} días - {lot.expiry_date})"
                    )
                
                subject = f"⚠️ Productos próximos a vencer: {product_name}"
                message = f"""
ALERTA DE VENCIMIENTO PRÓXIMO

Producto: {product_name}
Total en riesgo: {product_data['total_qty']} unidades
Lotes afectados: {len(product_data['lots'])}

Detalle de lotes:
{chr(10).join(lots_info)}

Se recomienda:
1. Priorizar la venta de estos lotes (FEFO)
2. Considerar promociones o descuentos
3. Evaluar donación si no se puede vender

Revisar en el panel de stock.
                """
                
                # Send alert asynchronously
                send_email_alert.delay(
                    subject=subject,
                    message=message,
                    recipient_email='stock@company.com'  # Configure in settings
                )
                
                alerts_sent += 1
                
            except Exception as alert_exc:
                logger.error(f"Failed to send alert for {product_name}: {alert_exc}")
        
        # Update metrics
        set_gauge('products_near_expiry', len(products_by_expiry))
        set_gauge('lots_near_expiry', total_lots)
        increment_counter('near_expiry_scans_total', {'status': 'success'})
        
        logger.info(f"Near expiry scan completed: {len(products_by_expiry)} products, {alerts_sent} alerts sent")
        
        return {
            'status': 'success',
            'products_found': len(products_by_expiry),
            'lots_found': total_lots,
            'alerts_sent': alerts_sent,
            'products': list(products_by_expiry.keys())
        }
        
    except Exception as exc:
        logger.error(f"Near expiry scan failed: {exc}")
        increment_counter('near_expiry_scans_total', {'status': 'failed'})
        
        # Let autoretry handle the retry
        raise exc


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=120,  # 2 minutes
    time_limit=240,  # 4 minutes
)
def scan_low_stock(self, min_stock_threshold: float = 10.0):
    """
    Scan for products with low stock and send alerts.
    
    Args:
        min_stock_threshold: Minimum stock threshold (default from product or global)
    """
    try:
        logger.info(f"Starting low stock scan with threshold {min_stock_threshold}")
        
        # Get products with their current stock levels
        products_with_stock = []
        
        for product in Product.objects.filter(is_active=True):
            # Calculate total stock for this product
            total_stock = StockLot.objects.filter(
                product=product,
                qty_on_hand__gt=0
            ).aggregate(
                total=models.Sum('qty_on_hand')
            )['total'] or Decimal('0')
            
            # Use product-specific min_stock or global threshold
            product_min_stock = getattr(product, 'min_stock', None) or Decimal(str(min_stock_threshold))
            
            if total_stock <= product_min_stock:
                products_with_stock.append({
                    'product': product,
                    'current_stock': float(total_stock),
                    'min_stock': float(product_min_stock),
                    'shortage': float(product_min_stock - total_stock)
                })
        
        if not products_with_stock:
            logger.info("No products with low stock found")
            set_gauge('products_low_stock', 0)
            increment_counter('low_stock_scans_total', {'status': 'no_products'})
            
            return {
                'status': 'success',
                'products_found': 0,
                'alerts_sent': 0
            }
        
        logger.info(f"Found {len(products_with_stock)} products with low stock")
        
        # Send alerts for low stock products
        alerts_sent = 0
        for product_data in products_with_stock:
            try:
                # Send low stock alert asynchronously
                send_low_stock_alert.delay(
                    product_name=product_data['product'].name,
                    current_stock=product_data['current_stock'],
                    min_stock=product_data['min_stock']
                )
                
                alerts_sent += 1
                
            except Exception as alert_exc:
                logger.error(f"Failed to send low stock alert for {product_data['product'].name}: {alert_exc}")
        
        # Update metrics
        set_gauge('products_low_stock', len(products_with_stock))
        increment_counter('low_stock_scans_total', {'status': 'success'})
        
        logger.info(f"Low stock scan completed: {len(products_with_stock)} products, {alerts_sent} alerts sent")
        
        return {
            'status': 'success',
            'products_found': len(products_with_stock),
            'alerts_sent': alerts_sent,
            'products': [p['product'].name for p in products_with_stock]
        }
        
    except Exception as exc:
        logger.error(f"Low stock scan failed: {exc}")
        increment_counter('low_stock_scans_total', {'status': 'failed'})
        
        # Let autoretry handle the retry
        raise exc


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=180,  # Max 3 minutes
    retry_jitter=True,
    max_retries=1,
    soft_time_limit=60,  # 1 minute
    time_limit=120,  # 2 minutes
)
def cleanup_expired_lots(self):
    """
    Clean up expired lots with zero stock.
    This task helps maintain database performance.
    """
    try:
        logger.info("Starting cleanup of expired lots")
        
        # Find expired lots with zero stock
        expired_lots = StockLot.objects.filter(
            expiry_date__lt=date.today(),
            qty_on_hand=0
        )
        
        expired_count = expired_lots.count()
        
        if expired_count == 0:
            logger.info("No expired lots to clean up")
            increment_counter('lot_cleanup_total', {'status': 'no_lots'})
            
            return {
                'status': 'success',
                'lots_cleaned': 0
            }
        
        # Delete expired lots in batches
        with transaction.atomic():
            deleted_count = expired_lots.delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} expired lots")
        increment_counter('lot_cleanup_total', {'status': 'success'})
        set_gauge('expired_lots_cleaned', deleted_count)
        
        return {
            'status': 'success',
            'lots_cleaned': deleted_count
        }
        
    except Exception as exc:
        logger.error(f"Lot cleanup failed: {exc}")
        increment_counter('lot_cleanup_total', {'status': 'failed'})
        
        # Let autoretry handle the retry
        raise exc


@shared_task(
    bind=True,
    soft_time_limit=30,  # 30 seconds
    time_limit=60,  # 1 minute
)
def update_stock_metrics(self):
    """
    Update stock-related metrics for monitoring.
    """
    try:
        logger.info("Updating stock metrics")
        
        # Total products
        total_products = Product.objects.filter(is_active=True).count()
        set_gauge('total_active_products', total_products)
        
        # Total stock lots
        total_lots = StockLot.objects.filter(qty_on_hand__gt=0).count()
        set_gauge('total_stock_lots', total_lots)
        
        # Products with stock
        products_with_stock = StockLot.objects.filter(
            qty_on_hand__gt=0
        ).values('product').distinct().count()
        set_gauge('products_with_stock', products_with_stock)
        
        # Products without stock
        products_without_stock = total_products - products_with_stock
        set_gauge('products_without_stock', products_without_stock)
        
        logger.info("Stock metrics updated successfully")
        increment_counter('stock_metrics_updates_total', {'status': 'success'})
        
        return {
            'status': 'success',
            'metrics_updated': {
                'total_products': total_products,
                'total_lots': total_lots,
                'products_with_stock': products_with_stock,
                'products_without_stock': products_without_stock
            }
        }
        
    except Exception as exc:
        logger.error(f"Stock metrics update failed: {exc}")
        increment_counter('stock_metrics_updates_total', {'status': 'failed'})
        
        return {
            'status': 'failed',
            'error': str(exc)
        }