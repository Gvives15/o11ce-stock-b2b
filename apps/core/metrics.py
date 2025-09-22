"""
Métricas custom para el sistema BFF Stock.

Este módulo define métricas personalizadas de Prometheus para monitorear
aspectos específicos del negocio como órdenes creadas y lotes próximos a vencer.
"""

from prometheus_client import Counter, Gauge
import structlog

logger = structlog.get_logger(__name__)

# Métricas custom de negocio
orders_placed_total = Counter(
    'orders_placed_total',
    'Total number of orders placed in the system',
    ['customer_type', 'status']
)

near_expiry_lots = Gauge(
    'near_expiry_lots',
    'Number of lots that are near expiry (within 30 days)',
    ['product_category', 'days_to_expiry_range']
)

def increment_orders_placed(customer_type='unknown', status='created'):
    """
    Incrementa el contador de órdenes creadas.
    
    Args:
        customer_type (str): Tipo de cliente ('b2b', 'pos', 'panel')
        status (str): Estado de la orden ('created', 'completed', 'cancelled')
    """
    try:
        orders_placed_total.labels(
            customer_type=customer_type,
            status=status
        ).inc()
        
        logger.info(
            "order_metric_incremented",
            customer_type=customer_type,
            status=status
        )
    except Exception as e:
        logger.error(
            "error_incrementing_order_metric",
            error=str(e),
            customer_type=customer_type,
            status=status
        )

def update_near_expiry_lots(product_category='unknown', days_range='0-7', count=0):
    """
    Actualiza el gauge de lotes próximos a vencer.
    
    Args:
        product_category (str): Categoría del producto
        days_range (str): Rango de días hasta vencimiento ('0-7', '8-15', '16-30')
        count (int): Número de lotes en este rango
    """
    try:
        near_expiry_lots.labels(
            product_category=product_category,
            days_to_expiry_range=days_range
        ).set(count)
        
        logger.info(
            "near_expiry_metric_updated",
            product_category=product_category,
            days_range=days_range,
            count=count
        )
    except Exception as e:
        logger.error(
            "error_updating_near_expiry_metric",
            error=str(e),
            product_category=product_category,
            days_range=days_range,
            count=count
        )

def get_metrics_summary():
    """
    Retorna un resumen de las métricas actuales para debugging.
    
    Returns:
        dict: Resumen de métricas
    """
    try:
        # Obtener valores actuales de las métricas
        orders_samples = list(orders_placed_total.collect())[0].samples
        expiry_samples = list(near_expiry_lots.collect())[0].samples
        
        return {
            'orders_placed_total': [
                {
                    'labels': sample.labels,
                    'value': sample.value
                } for sample in orders_samples
            ],
            'near_expiry_lots': [
                {
                    'labels': sample.labels,
                    'value': sample.value
                } for sample in expiry_samples
            ]
        }
    except Exception as e:
        logger.error("error_getting_metrics_summary", error=str(e))
        return {'error': str(e)}