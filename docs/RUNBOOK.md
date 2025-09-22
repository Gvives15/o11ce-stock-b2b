# 📊 RUNBOOK - Observabilidad del Sistema BFF Stock

## 🎯 Propósito

Este runbook documenta el sistema de observabilidad implementado en BFF Stock, incluyendo logging estructurado, health checks, y procedimientos de monitoreo.

## 🏗️ Arquitectura de Observabilidad

### Componentes Principales

1. **Logging Estructurado (structlog)**
   - Logs en formato JSON
   - Contexto de request con X-Request-ID
   - Información de timing y usuario

2. **Health Endpoints**
   - `/health/live` - Liveness probe
   - `/health/ready` - Readiness probe

3. **Middlewares de Observabilidad**
   - `RequestIDMiddleware` - Tracking de requests
   - `AccessLogMiddleware` - Logging de acceso

## 🔍 Endpoints de Salud

### GET /health/live

**Propósito**: Verificar que la aplicación esté corriendo y pueda responder requests.

**Respuesta Exitosa (200)**:
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "service": "bff-stock-system",
  "version": "1.0.0",
  "uptime_check": "ok",
  "latency_ms": 5
}
```

**Uso**: 
- Kubernetes liveness probe
- Load balancer health check
- Monitoreo básico de disponibilidad

### GET /health/ready

**Propósito**: Verificar que la aplicación esté lista para recibir tráfico (dependencias funcionando).

**Respuesta Exitosa (200)**:
```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "service": "bff-stock-system",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 12,
      "details": "Database connection successful"
    },
    "cache": {
      "status": "healthy",
      "latency_ms": 3,
      "details": "Cache read/write successful"
    },
    "smtp": {
      "status": "healthy",
      "latency_ms": 45,
      "details": "SMTP connection successful"
    },
    "celery": {
      "status": "not_configured",
      "details": "Celery not configured in this deployment"
    }
  },
  "failed_checks": [],
  "latency_ms": 60
}
```

**Respuesta con Fallas (503)**:
```json
{
  "status": "unhealthy",
  "timestamp": 1703123456.789,
  "service": "bff-stock-system",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "unhealthy",
      "error": "connection timeout",
      "details": "Database connection failed"
    }
  },
  "failed_checks": ["database"],
  "latency_ms": 5000
}
```

## 📝 Logging Estructurado

### Formato de Logs

Todos los logs se emiten en formato JSON con la siguiente estructura:

```json
{
  "event": "http_request",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "logger": "apps.core.middleware",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/pos/sale",
  "status_code": 200,
  "user_id": 123,
  "username": "vendedor1",
  "latency_ms": 245,
  "remote_addr": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "content_length": 1024
}
```

### Campos Clave

- **request_id**: UUID único por request (X-Request-ID)
- **user_id**: ID del usuario autenticado
- **latency_ms**: Tiempo de respuesta en milisegundos
- **timestamp**: Timestamp ISO 8601
- **event**: Tipo de evento (http_request, health_check, etc.)

## 🚨 Alertas y Monitoreo

### Métricas Clave a Monitorear

1. **Disponibilidad**
   - `/health/live` debe retornar 200
   - Uptime > 99.9%

2. **Latencia**
   - P95 de `latency_ms` < 500ms
   - P99 de `latency_ms` < 1000ms

3. **Errores**
   - Rate de 5xx < 1%
   - Rate de 4xx < 5%

4. **Dependencias**
   - `/health/ready` debe retornar 200
   - Latencia de DB < 100ms
   - Latencia de Cache < 10ms

### Alertas Recomendadas

#### Críticas (PagerDuty)
- `/health/live` retorna != 200 por > 2 minutos
- `/health/ready` retorna 503 por > 5 minutos
- Rate de errores 5xx > 5% por > 5 minutos

#### Advertencias (Slack)
- Latencia P95 > 1000ms por > 10 minutos
- Rate de errores 4xx > 10% por > 15 minutos
- Latencia de DB > 200ms por > 10 minutos

## 🔧 Troubleshooting

### Problema: /health/ready retorna 503

**Síntomas**: 
- Endpoint `/health/ready` retorna status 503
- Campo `failed_checks` contiene servicios fallidos

**Diagnóstico**:
1. Revisar logs para identificar el servicio fallido:
   ```bash
   grep "health_ready_check" logs.json | jq '.failed_checks'
   ```

2. Verificar conectividad específica:
   - **Database**: Verificar conexión, pool de conexiones
   - **Cache**: Verificar Redis/Memcached
   - **SMTP**: Verificar servidor de correo

**Soluciones**:
- **Database**: Reiniciar pool de conexiones, verificar DB server
- **Cache**: Reiniciar Redis, verificar configuración
- **SMTP**: Verificar credenciales, firewall

### Problema: Alta Latencia

**Síntomas**:
- `latency_ms` > 1000ms en logs
- Usuarios reportan lentitud

**Diagnóstico**:
1. Analizar distribución de latencia:
   ```bash
   grep "http_request" logs.json | jq '.latency_ms' | sort -n
   ```

2. Identificar endpoints lentos:
   ```bash
   grep "http_request" logs.json | jq 'select(.latency_ms > 1000) | .path' | sort | uniq -c
   ```

**Soluciones**:
- Optimizar queries de DB
- Implementar caching
- Revisar N+1 queries
- Escalar recursos

### Problema: Request ID no se propaga

**Síntomas**:
- Logs sin `request_id`
- Dificultad para trazar requests

**Diagnóstico**:
1. Verificar middleware order en `settings.py`
2. Verificar que `RequestIDMiddleware` esté antes que `AccessLogMiddleware`

**Solución**:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.core.middleware.RequestIDMiddleware',  # DEBE estar aquí
    # ... otros middlewares ...
    'apps.core.middleware.AccessLogMiddleware',  # DESPUÉS de RequestID
]
```

## 📊 Queries Útiles

### Logs de Errores por Usuario
```bash
grep "http_request" logs.json | jq 'select(.status_code >= 400) | {user_id, path, status_code, timestamp}' | head -20
```

### Top 10 Endpoints más Lentos
```bash
grep "http_request" logs.json | jq '{path, latency_ms}' | sort -k2 -nr | head -10
```

### Requests por Usuario
```bash
grep "http_request" logs.json | jq '.user_id' | sort | uniq -c | sort -nr
```

### Health Check History
```bash
grep "health_ready_check" logs.json | jq '{timestamp, status, failed_checks, latency_ms}' | tail -20
```

## 🔄 Mantenimiento

### Rotación de Logs
- Configurar logrotate para archivos de log
- Retener logs por 30 días mínimo
- Comprimir logs antiguos

### Limpieza de Métricas
- Agregar métricas por hora/día
- Limpiar métricas raw después de 7 días
- Mantener agregados por 1 año

## 📞 Contactos

- **Equipo de Desarrollo**: dev-team@company.com
- **Ops/SRE**: ops-team@company.com
- **Escalación**: on-call@company.com

## 📚 Referencias

- [Structlog Documentation](https://www.structlog.org/)
- [Django Logging](https://docs.djangoproject.com/en/stable/topics/logging/)
- [Health Check Patterns](https://microservices.io/patterns/observability/health-check-api.html)