"""
API endpoint for exposing cache metrics.
"""

from django.http import HttpResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


def metrics_endpoint(request):
    """
    Endpoint para exponer métricas de Prometheus.
    Incluye métricas de cache hits/misses y duración de operaciones.
    """
    metrics_data = generate_latest()
    return HttpResponse(
        metrics_data,
        content_type=CONTENT_TYPE_LATEST
    )