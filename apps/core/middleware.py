"""
Middlewares para observabilidad y logging estructurado.
"""
import uuid
import time
import structlog
from django.utils.deprecation import MiddlewareMixin


logger = structlog.get_logger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware que genera un X-Request-ID único para cada request
    y lo propaga a través de los logs.
    """
    
    def process_request(self, request):
        # Obtener X-Request-ID del header o generar uno nuevo
        request_id = request.META.get('HTTP_X_REQUEST_ID')
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Almacenar en el request para uso posterior
        request.request_id = request_id
        
        # Configurar contexto de structlog para este request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
        )
        
        return None
    
    def process_response(self, request, response):
        # Agregar X-Request-ID al response header
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        return response


class StructlogMiddleware(MiddlewareMixin):
    """
    Middleware que configura el contexto de structlog para cada request
    con información adicional como usuario, IP, etc.
    """
    
    def process_request(self, request):
        # Obtener información del usuario si está autenticado
        user_id = None
        username = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            username = request.user.username
        
        # Configurar contexto adicional de structlog
        structlog.contextvars.bind_contextvars(
            method=request.method,
            path=request.path,
            user_id=user_id,
            username=username,
            remote_addr=self._get_client_ip(request),
        )
        
        return None
    
    def _get_client_ip(self, request):
        """Obtener la IP real del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AccessLogMiddleware(MiddlewareMixin):
    """
    Middleware que registra logs estructurados de cada HTTP request
    con información de timing, usuario, y contexto.
    """
    
    def process_request(self, request):
        # Marcar tiempo de inicio
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        # Calcular latencia
        if hasattr(request, '_start_time'):
            latency_ms = int((time.time() - request._start_time) * 1000)
        else:
            latency_ms = 0
        
        # Obtener información del usuario
        user_id = None
        username = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            username = request.user.username
        
        # Log estructurado del request (sin datos sensibles)
        logger.info(
            "http_request",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            user_id=user_id,
            username=username,
            latency_ms=latency_ms,
            remote_addr=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            content_length=len(response.content) if hasattr(response, 'content') else 0,
            # No incluir query params o body para evitar datos sensibles
        )
        
        return response
    
    def _get_client_ip(self, request):
        """Obtener la IP real del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip