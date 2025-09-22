# Runbook - Métricas y Monitoreo

## Descripción General

Este runbook describe el sistema de métricas implementado en la aplicación BFF, incluyendo métricas de Prometheus, integración con Sentry para manejo de errores, y procedimientos de monitoreo.

## Métricas Implementadas

### 1. Métricas de Django-Prometheus

La aplicación utiliza `django-prometheus` para recopilar métricas automáticas:

- **django_http_requests_total**: Counter de requests HTTP por método, endpoint y código de estado
- **django_http_request_duration_seconds**: Histograma de duración de requests HTTP
- **django_http_responses_body_total_bytes**: Histograma del tamaño de respuestas
- **django_db_connections_total**: Métricas de conexiones a base de datos

### 2. Métricas Custom

#### Counter: orders_placed_total
- **Descripción**: Cuenta el número total de órdenes creadas
- **Labels**: `customer_type` (tipo de cliente)
- **Ubicación**: Se incrementa en `apps/orders/services.py` función `checkout()`
- **Uso**: Monitorear volumen de órdenes por tipo de cliente

#### Gauge: near_expiry_lots
- **Descripción**: Número de lotes próximos a vencer por categoría y rango de días
- **Labels**: 
  - `product_category`: Categoría del producto
  - `days_to_expiry_range`: Rango de días hasta vencimiento (ej: "0-7", "8-15")
- **Ubicación**: Se actualiza mediante comando `python manage.py update_metrics`
- **Uso**: Alertas tempranas sobre productos próximos a vencer

## Endpoints

### /metrics
- **URL**: `http://localhost:8000/metrics`
- **Método**: GET
- **Descripción**: Endpoint de Prometheus que expone todas las métricas
- **Formato**: Texto plano compatible con Prometheus
- **Autenticación**: Ninguna (considerar protección en producción)

### /sentry-test/
- **URL**: `http://localhost:8000/sentry-test/`
- **Método**: POST
- **Descripción**: Endpoint para probar la captura de errores en Sentry
- **Respuesta**: JSON con confirmación de error capturado

## Comandos de Gestión

### update_metrics
```bash
python manage.py update_metrics
```
- **Descripción**: Actualiza las métricas gauge de lotes próximos a vencer
- **Frecuencia recomendada**: Cada hora via cron
- **Logs**: Registra en logs estructurados el número de métricas actualizadas

## Integración con Sentry

### Configuración
- **DSN**: Configurado via variable de entorno `SENTRY_DSN`
- **Entorno**: Configurado via variable de entorno `SENTRY_ENVIRONMENT`
- **Captura**: Errores automáticos + captura manual con `sentry_sdk.capture_exception()`

### Monitoreo de Errores
- Todos los errores 500 se capturan automáticamente
- Errores de negocio se pueden capturar manualmente
- Endpoint de prueba disponible para verificar funcionamiento

## Alertas y Monitoreo

### Métricas P95 Recomendadas

#### Latencia de Requests (P95)
```promql
histogram_quantile(0.95, 
  rate(django_http_request_duration_seconds_bucket[5m])
)
```
- **Umbral recomendado**: < 500ms
- **Acción**: Investigar endpoints lentos si supera umbral

#### Tasa de Errores
```promql
rate(django_http_requests_total{status=~"5.."}[5m]) / 
rate(django_http_requests_total[5m]) * 100
```
- **Umbral recomendado**: < 1%
- **Acción**: Revisar logs y Sentry si supera umbral

#### Órdenes por Minuto
```promql
rate(orders_placed_total[1m]) * 60
```
- **Uso**: Monitorear volumen de negocio
- **Alertas**: Caída significativa o picos inusuales

#### Lotes Próximos a Vencer (Crítico: 0-7 días)
```promql
near_expiry_lots{days_to_expiry_range="0-7"}
```
- **Umbral recomendado**: Alerta si > 10 lotes
- **Acción**: Notificar al equipo de inventario

### Dashboards Recomendados

1. **Dashboard de Aplicación**
   - Latencia P95, P99
   - Tasa de errores
   - Throughput de requests
   - Órdenes por hora

2. **Dashboard de Negocio**
   - Órdenes por tipo de cliente
   - Lotes próximos a vencer por categoría
   - Tendencias de inventario

3. **Dashboard de Errores**
   - Errores por endpoint
   - Integración con alertas de Sentry
   - Top errores por frecuencia

## Procedimientos de Troubleshooting

### Métricas no aparecen
1. Verificar que el endpoint `/metrics` responde 200
2. Confirmar que django-prometheus está en INSTALLED_APPS
3. Revisar middleware en settings.py
4. Verificar logs de aplicación

### Métricas custom no se actualizan
1. Ejecutar manualmente `python manage.py update_metrics`
2. Revisar logs del comando
3. Verificar conexión a base de datos
4. Confirmar que existen datos para procesar

### Sentry no captura errores
1. Verificar variable SENTRY_DSN
2. Probar endpoint `/sentry-test/`
3. Revisar configuración en settings.py
4. Verificar conectividad a Sentry

## Mantenimiento

### Tareas Regulares
- **Diario**: Revisar dashboards de métricas
- **Semanal**: Analizar tendencias de errores en Sentry
- **Mensual**: Revisar y ajustar umbrales de alertas

### Actualizaciones
- Mantener django-prometheus actualizado
- Revisar nuevas métricas de negocio necesarias
- Actualizar documentación según cambios

## Contactos y Escalación

- **Equipo de Desarrollo**: Para errores de aplicación
- **Equipo de Infraestructura**: Para problemas de métricas/Prometheus
- **Equipo de Negocio**: Para alertas de inventario y órdenes

---

**Última actualización**: 2025-01-16
**Versión**: 1.0