"""API Router para el panel administrativo
Protegido por permisos panel_access
"""

from ninja import Router
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.core.exceptions import PermissionDenied

from .orders_api import orders_router

class JWTAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        try:
            # Usar JWTAuthentication de DRF para validar el token
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            
            return user
            
        except (InvalidToken, TokenError):
            return None

def check_panel_permission(request):
    """Verificar permiso panel_access"""
    if not request.auth.has_perm('auth.panel_access'):
        raise PermissionDenied("No tienes permisos para acceder al panel")

# Router principal del panel
panel_router = Router(auth=JWTAuth())

# Incluir sub-routers
panel_router.add_router("/orders", orders_router)

@panel_router.get("/health")
def panel_health(request):
    """Health check del panel"""
    check_panel_permission(request)
    return {"status": "ok", "service": "panel"}