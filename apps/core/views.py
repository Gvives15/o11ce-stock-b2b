from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import sentry_sdk


@require_http_methods(["POST"])
@csrf_exempt
def sentry_test_error(request):
    """
    Endpoint para probar la integración con Sentry.
    Lanza una excepción de prueba que debe ser capturada por Sentry.
    """
    try:
        # Lanzar excepción de prueba
        raise Exception("Test exception for Sentry integration - this is intentional")
    except Exception as e:
        # Capturar explícitamente con Sentry
        sentry_sdk.capture_exception(e)
        
        return JsonResponse({
            "error": "TEST_EXCEPTION",
            "message": "Test exception sent to Sentry successfully",
            "sentry_event_id": sentry_sdk.last_event_id()
        }, status=500)
