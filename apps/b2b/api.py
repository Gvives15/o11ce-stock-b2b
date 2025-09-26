"""B2B BFF API endpoints using Django Ninja."""

from ninja import Router
from django.http import HttpResponse
import os

# Router B2B para el BFF
router = Router()

# Placeholder - endpoints se implementarán en siguientes bloques
@router.get("/")
def b2b_index(request):
    """Endpoint de índice B2B."""
    return {"message": "B2B BFF API", "version": "0.1.0"}

@router.get("/version")
def b2b_version(request):
    """Endpoint de versión B2B para tests CORS."""
    return {
        "version": os.environ.get('BFF_VERSION', '0.1.0'),
        "service": "B2B BFF",
        "status": "active"
    }

# OPTIONS handlers for CORS preflight
@router.api_operation(["OPTIONS"], "/")
def b2b_index_options(request):
    """Handle OPTIONS request for CORS preflight on index."""
    return HttpResponse(status=204)

@router.api_operation(["OPTIONS"], "/version")
def b2b_version_options(request):
    """Handle OPTIONS request for CORS preflight on version."""
    return HttpResponse(status=204)