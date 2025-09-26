"""
Métricas custom para el sistema BFF Stock.

Este módulo define métricas personalizadas de Prometheus para monitorear
aspectos específicos del negocio como órdenes creadas y lotes próximos a vencer.
"""

from prometheus_client import Counter, Gauge, Histogram
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

# Métricas de pricing y observabilidad crítica
pricing_calculations_total = Counter(
    'pricing_calculations_total',
    'Total number of pricing calculations performed',
    ['segment', 'calculation_type', 'product_category']
)

pricing_errors_total = Counter(
    'pricing_errors_total',
    'Total number of pricing calculation errors',
    ['segment', 'error_type', 'product_category']
)

pricing_calculation_duration_seconds = Histogram(
    'pricing_calculation_duration_seconds',
    'Time spent calculating product pricing',
    ['segment', 'calculation_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Métricas generales del sistema
system_counters = {}
system_gauges = {}

def increment_counter(metric_name, labels=None):
    """
    Incrementa un contador genérico del sistema.
    
    Args:
        metric_name (str): Nombre de la métrica
        labels (dict): Etiquetas para la métrica
    """
    if labels is None:
        labels = {}
    
    try:
        if metric_name not in system_counters:
            system_counters[metric_name] = Counter(
                metric_name,
                f'System counter for {metric_name}',
                list(labels.keys()) if labels else []
            )
        
        if labels:
            system_counters[metric_name].labels(**labels).inc()
        else:
            system_counters[metric_name].inc()
            
        logger.info(
            "system_counter_incremented",
            metric_name=metric_name,
            labels=labels
        )
    except Exception as e:
        logger.error(
            "error_incrementing_system_counter",
            error=str(e),
            metric_name=metric_name,
            labels=labels
        )

def set_gauge(metric_name, value, labels=None):
    """
    Establece el valor de un gauge genérico del sistema.
    
    Args:
        metric_name (str): Nombre de la métrica
        value (float): Valor a establecer
        labels (dict): Etiquetas para la métrica
    """
    if labels is None:
        labels = {}
    
    try:
        if metric_name not in system_gauges:
            system_gauges[metric_name] = Gauge(
                metric_name,
                f'System gauge for {metric_name}',
                list(labels.keys()) if labels else []
            )
        
        if labels:
            system_gauges[metric_name].labels(**labels).set(value)
        else:
            system_gauges[metric_name].set(value)
            
        logger.info(
            "system_gauge_updated",
            metric_name=metric_name,
            value=value,
            labels=labels
        )
    except Exception as e:
        logger.error(
            "error_updating_system_gauge",
            error=str(e),
            metric_name=metric_name,
            value=value,
            labels=labels
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

def increment_pricing_calculation(segment='unknown', calculation_type='final_price', product_category='unknown'):
    """
    Incrementa el contador de cálculos de pricing.
    
    Args:
        segment (str): Segmento del cliente ('retail', 'wholesale', 'unknown')
        calculation_type (str): Tipo de cálculo ('final_price', 'discount', 'benefit')
        product_category (str): Categoría del producto
    """
    try:
        pricing_calculations_total.labels(
            segment=segment,
            calculation_type=calculation_type,
            product_category=product_category
        ).inc()
        
        logger.info(
            "pricing_calculation_incremented",
            segment=segment,
            calculation_type=calculation_type,
            product_category=product_category
        )
    except Exception as e:
        logger.error(
            "error_incrementing_pricing_calculation",
            error=str(e),
            segment=segment,
            calculation_type=calculation_type,
            product_category=product_category
        )

def increment_pricing_error(segment='unknown', error_type='calculation_error', product_category='unknown'):
    """
    Incrementa el contador de errores de pricing.
    
    Args:
        segment (str): Segmento del cliente ('retail', 'wholesale', 'unknown')
        error_type (str): Tipo de error ('calculation_error', 'invalid_segment', 'missing_data')
        product_category (str): Categoría del producto
    """
    try:
        pricing_errors_total.labels(
            segment=segment,
            error_type=error_type,
            product_category=product_category
        ).inc()
        
        logger.error(
            "pricing_error_incremented",
            segment=segment,
            error_type=error_type,
            product_category=product_category
        )
    except Exception as e:
        logger.error(
            "error_incrementing_pricing_error",
            error=str(e),
            segment=segment,
            error_type=error_type,
            product_category=product_category
        )

def observe_pricing_duration(duration_seconds, segment='unknown', calculation_type='final_price'):
    """
    Registra la duración de un cálculo de pricing.
    
    Args:
        duration_seconds (float): Duración del cálculo en segundos
        segment (str): Segmento del cliente ('retail', 'wholesale', 'unknown')
        calculation_type (str): Tipo de cálculo ('final_price', 'discount', 'benefit')
    """
    try:
        pricing_calculation_duration_seconds.labels(
            segment=segment,
            calculation_type=calculation_type
        ).observe(duration_seconds)
        
        logger.info(
            "pricing_duration_observed",
            duration_seconds=duration_seconds,
            segment=segment,
            calculation_type=calculation_type
        )
    except Exception as e:
        logger.error(
            "error_observing_pricing_duration",
            error=str(e),
            duration_seconds=duration_seconds,
            segment=segment,
            calculation_type=calculation_type
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
        pricing_calc_samples = list(pricing_calculations_total.collect())[0].samples
        pricing_error_samples = list(pricing_errors_total.collect())[0].samples
        
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
            ],
            'pricing_calculations_total': [
                {
                    'labels': sample.labels,
                    'value': sample.value
                } for sample in pricing_calc_samples
            ],
            'pricing_errors_total': [
                {
                    'labels': sample.labels,
                    'value': sample.value
                } for sample in pricing_error_samples
            ]
        }
    except Exception as e:
        logger.error("error_getting_metrics_summary", error=str(e))
        return {'error': str(e)}