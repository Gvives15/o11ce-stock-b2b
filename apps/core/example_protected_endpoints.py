"""
Ejemplos de endpoints protegidos usando los decoradores de permisos B0-BE-02.
Estos son ejemplos para demostrar el uso de los decoradores.
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .permissions import (
    admin_required,
    vendedor_required,
    vendedor_caja_required,
    vendedor_ruta_required,
    pos_operation_required,
    cancellation_required
)


@csrf_exempt
@require_http_methods(["GET"])
@admin_required
def admin_only_endpoint(request):
    """Endpoint que solo pueden acceder administradores."""
    return JsonResponse({
        'message': 'Solo administradores pueden ver este endpoint',
        'user_roles': getattr(request, 'user_roles', [])
    })


@csrf_exempt
@require_http_methods(["GET"])
@vendedor_required
def vendedor_endpoint(request):
    """Endpoint que pueden acceder vendedores de caja o ruta."""
    return JsonResponse({
        'message': 'Vendedores pueden ver este endpoint',
        'user_roles': getattr(request, 'user_roles', [])
    })


@csrf_exempt
@require_http_methods(["POST"])
@vendedor_caja_required
def caja_operation_endpoint(request):
    """Endpoint específico para operaciones de caja."""
    return JsonResponse({
        'message': 'Operación de caja realizada',
        'user_roles': getattr(request, 'user_roles', [])
    })


@csrf_exempt
@require_http_methods(["POST"])
@vendedor_ruta_required
def ruta_operation_endpoint(request):
    """Endpoint específico para operaciones de ruta."""
    return JsonResponse({
        'message': 'Operación de ruta realizada',
        'user_roles': getattr(request, 'user_roles', [])
    })


@csrf_exempt
@require_http_methods(["POST"])
@pos_operation_required
def pos_sensitive_operation(request):
    """Endpoint para operaciones sensibles del POS."""
    return JsonResponse({
        'message': 'Operación sensible del POS realizada',
        'user_roles': getattr(request, 'user_roles', [])
    })


@csrf_exempt
@require_http_methods(["POST"])
@cancellation_required
def cancel_operation(request):
    """Endpoint para operaciones de anulación."""
    return JsonResponse({
        'message': 'Operación de anulación realizada',
        'user_roles': getattr(request, 'user_roles', [])
    })
