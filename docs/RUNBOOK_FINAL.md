# 📚 BFF System Runbook Final

## 🎯 Propósito
Este runbook proporciona procedimientos operacionales completos para el sistema BFF (Backend For Frontend), incluyendo monitoreo, mantenimiento, resolución de incidentes y operaciones de rutina.

## 📋 Índice
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Monitoreo y Métricas](#monitoreo-y-métricas)
- [Gestión de Cache](#gestión-de-cache)
- [Manejo de Incidentes](#manejo-de-incidentes)
- [Operaciones de Rutina](#operaciones-de-rutina)
- [Troubleshooting](#troubleshooting)
- [Contactos y Escalación](#contactos-y-escalación)

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales
- **Django API**: Backend principal con REST API
- **PostgreSQL**: Base de datos principal
- **Redis**: Cache y broker de Celery
- **Celery**: Procesamiento asíncrono de tareas
- **Nginx**: Proxy reverso y servidor web

### Servicios Críticos
1. **Web Application** (Puerto 8000)
2. **Database** (PostgreSQL, Puerto 5432)
3. **Cache/Broker** (Redis, Puerto 6379)
4. **Task Queue** (Celery Workers)
5. **Task Scheduler** (Celery Beat)

---

## 📊 Monitoreo y Métricas

### Health Checks
```bash
# Verificar estado general del sistema
curl http://localhost:8000/health/

# Verificar componentes específicos
curl http://localhost:8000/health/database/
curl http://localhost:8000/health/cache/
curl http://localhost:8000/health/smtp/
```

### Métricas Clave

#### 🔍 Métricas de Aplicación
| Métrica | Umbral Normal | Umbral Crítico | Descripción |
|---------|---------------|----------------|-------------|
| Response Time | < 200ms | > 1000ms | Tiempo de respuesta API |
| Error Rate | < 1% | > 5% | Tasa de errores HTTP 5xx |
| Database Connections | < 80% | > 95% | Uso de conexiones DB |
| Cache Hit Rate | > 80% | < 50% | Efectividad del cache |
| Queue Length | < 100 | > 1000 | Tareas pendientes en cola |

#### 📈 Métricas de Negocio
| Métrica | Descripción | Endpoint |
|---------|-------------|----------|
| Total Products | Productos en inventario | `/api/metrics/stock/` |
| Available Stock | Stock disponible total | `/api/metrics/stock/` |
| Reserved Stock | Stock reservado | `/api/metrics/stock/` |
| Orders/Hour | Órdenes procesadas por hora | `/api/metrics/orders/` |
| FEFO Efficiency | % órdenes con FEFO correcto | `/api/metrics/fefo/` |

### Comandos de Monitoreo

```bash
# Verificar estado de servicios
systemctl status bff-web
systemctl status bff-celery
systemctl status bff-beat
systemctl status postgresql
systemctl status redis

# Verificar logs en tiempo real
tail -f /var/log/bff/application.log
tail -f /var/log/bff/celery.log
tail -f /var/log/bff/error.log

# Verificar métricas de sistema
htop
iostat -x 1
free -h
df -h
```

---

## 🗄️ Gestión de Cache

### Invalidación Manual de Cache

#### Invalidar Cache Completo
```bash
# Desde Django shell
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
>>> print("Cache cleared successfully")
```

#### Invalidar Cache por Patrones
```bash
# Invalidar cache de productos
python manage.py shell
>>> from apps.core.cache import CacheService
>>> cache_service = CacheService()
>>> cache_service.invalidate_pattern("product:*")

# Invalidar cache de stock
>>> cache_service.invalidate_pattern("stock:*")

# Invalidar cache de métricas
>>> cache_service.invalidate_pattern("metrics:*")
```

#### Invalidar Cache Específico
```bash
# Por producto específico
>>> cache_service.delete("product:123")
>>> cache_service.delete("stock:123:warehouse:1")

# Por usuario específico
>>> cache_service.delete("user:456:permissions")
```

### Monitoreo de Cache

```bash
# Conectar a Redis CLI
redis-cli

# Verificar información del servidor
INFO memory
INFO stats

# Ver claves activas
KEYS *

# Verificar TTL de claves
TTL product:123

# Estadísticas de hit/miss
INFO stats | grep keyspace
```

### Configuración de Cache por Entorno

#### Desarrollo
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocalMemoryCache',
    }
}
```

#### Producción
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## 🚨 Manejo de Incidentes

### Clasificación de Incidentes

#### 🔴 Severidad 1 - Crítico
- Sistema completamente inaccesible
- Pérdida de datos
- Fallo de seguridad

**Tiempo de Respuesta**: 15 minutos
**Tiempo de Resolución**: 1 hora

#### 🟡 Severidad 2 - Alto
- Funcionalidad principal afectada
- Performance degradada significativamente
- Errores intermitentes

**Tiempo de Respuesta**: 30 minutos
**Tiempo de Resolución**: 4 horas

#### 🟢 Severidad 3 - Medio
- Funcionalidad secundaria afectada
- Performance ligeramente degradada

**Tiempo de Respuesta**: 2 horas
**Tiempo de Resolución**: 24 horas

### Procedimientos de Respuesta

#### 1. Evaluación Inicial (5 minutos)
```bash
# Verificar servicios básicos
curl -I http://localhost:8000/health/
systemctl status bff-web bff-celery postgresql redis

# Verificar logs recientes
tail -n 100 /var/log/bff/error.log
journalctl -u bff-web --since "5 minutes ago"
```

#### 2. Diagnóstico Rápido (10 minutos)
```bash
# Verificar recursos del sistema
free -h
df -h
iostat -x 1 3

# Verificar conexiones de red
netstat -tulpn | grep :8000
netstat -tulpn | grep :5432
netstat -tulpn | grep :6379

# Verificar procesos
ps aux | grep python
ps aux | grep celery
ps aux | grep postgres
```

#### 3. Acciones de Mitigación

##### Reinicio de Servicios
```bash
# Reinicio gradual (recomendado)
systemctl restart bff-celery
sleep 10
systemctl restart bff-beat
sleep 10
systemctl restart bff-web

# Reinicio completo (solo si es necesario)
systemctl restart bff-web bff-celery bff-beat
```

##### Limpieza de Cache
```bash
# Si hay problemas de cache
redis-cli FLUSHDB
systemctl restart bff-web
```

##### Rollback de Deployment
```bash
# Volver a versión anterior
git checkout <previous-commit>
docker-compose down
docker-compose up -d --build
```

### Incidentes Comunes

#### 🔧 Base de Datos Lenta
**Síntomas**: Timeouts, response time alto
**Diagnóstico**:
```sql
-- Verificar queries lentas
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

-- Verificar conexiones activas
SELECT count(*) FROM pg_stat_activity;
```
**Solución**:
1. Identificar queries problemáticas
2. Optimizar índices
3. Aumentar connection pool si es necesario

#### 🔧 Cola de Celery Saturada
**Síntomas**: Tareas no se procesan, queue length alto
**Diagnóstico**:
```bash
# Verificar estado de la cola
celery -A config inspect active
celery -A config inspect reserved
celery -A config inspect stats
```
**Solución**:
1. Aumentar workers: `celery -A config worker --concurrency=8`
2. Purgar cola si es necesario: `celery -A config purge`
3. Verificar tareas problemáticas

#### 🔧 Memory Leak
**Síntomas**: Uso de memoria creciente, OOM kills
**Diagnóstico**:
```bash
# Monitorear memoria por proceso
ps aux --sort=-%mem | head -10
pmap -x <pid>

# Verificar logs de OOM
dmesg | grep -i "killed process"
```
**Solución**:
1. Reiniciar servicios afectados
2. Investigar código para memory leaks
3. Ajustar límites de memoria

---

## 🔄 Operaciones de Rutina

### Mantenimiento Diario

#### Verificación de Salud del Sistema
```bash
#!/bin/bash
# daily_health_check.sh

echo "=== Daily Health Check $(date) ==="

# Verificar servicios
systemctl is-active bff-web bff-celery bff-beat postgresql redis

# Verificar espacio en disco
df -h | grep -E "(/$|/var|/tmp)"

# Verificar logs de errores
echo "Errors in last 24h:"
grep -c "ERROR" /var/log/bff/application.log

# Verificar métricas
curl -s http://localhost:8000/api/metrics/system/ | jq .

echo "=== Health Check Complete ==="
```

#### Limpieza de Logs
```bash
#!/bin/bash
# log_cleanup.sh

# Rotar logs antiguos (>7 días)
find /var/log/bff/ -name "*.log" -mtime +7 -exec gzip {} \;
find /var/log/bff/ -name "*.log.gz" -mtime +30 -delete

# Limpiar logs de Django
python manage.py clearsessions
```

### Mantenimiento Semanal

#### Optimización de Base de Datos
```sql
-- Ejecutar cada domingo
VACUUM ANALYZE;
REINDEX DATABASE bff_production;

-- Verificar estadísticas de tablas
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;
```

#### Backup y Verificación
```bash
#!/bin/bash
# weekly_backup.sh

# Backup de base de datos
pg_dump bff_production > /backups/bff_$(date +%Y%m%d).sql
gzip /backups/bff_$(date +%Y%m%d).sql

# Verificar integridad del backup
gunzip -t /backups/bff_$(date +%Y%m%d).sql.gz

# Limpiar backups antiguos (>30 días)
find /backups/ -name "bff_*.sql.gz" -mtime +30 -delete
```

### Mantenimiento Mensual

#### Análisis de Performance
```bash
# Generar reporte de performance
python manage.py shell << EOF
from apps.core.metrics import MetricsService
metrics = MetricsService()
report = metrics.generate_monthly_report()
print(report)
EOF
```

#### Actualización de Dependencias
```bash
# Verificar actualizaciones disponibles
pip list --outdated

# En entorno de desarrollo
pip-review --local --interactive

# Ejecutar tests después de actualizaciones
python manage.py test
```

---

## 🔍 Troubleshooting

### Problemas de Performance

#### API Lenta
1. **Verificar métricas**:
   ```bash
   curl http://localhost:8000/api/metrics/performance/
   ```

2. **Analizar queries**:
   ```python
   # En Django shell
   from django.db import connection
   print(connection.queries)
   ```

3. **Verificar cache hit rate**:
   ```bash
   redis-cli INFO stats | grep keyspace_hits
   ```

#### Base de Datos Lenta
1. **Verificar conexiones activas**:
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
   ```

2. **Identificar queries lentas**:
   ```sql
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 5;
   ```

3. **Verificar locks**:
   ```sql
   SELECT * FROM pg_locks WHERE NOT granted;
   ```

### Problemas de Conectividad

#### Redis No Disponible
```bash
# Verificar estado de Redis
systemctl status redis
redis-cli ping

# Si no responde, reiniciar
systemctl restart redis

# Verificar logs
journalctl -u redis --since "10 minutes ago"
```

#### PostgreSQL No Disponible
```bash
# Verificar estado
systemctl status postgresql
pg_isready -h localhost -p 5432

# Verificar logs
tail -f /var/log/postgresql/postgresql-*.log

# Reiniciar si es necesario
systemctl restart postgresql
```

### Problemas de Celery

#### Workers No Procesan Tareas
```bash
# Verificar workers activos
celery -A config inspect active

# Verificar cola
celery -A config inspect reserved

# Reiniciar workers
systemctl restart bff-celery

# Verificar logs
tail -f /var/log/bff/celery.log
```

#### Beat No Programa Tareas
```bash
# Verificar estado de Beat
systemctl status bff-beat

# Verificar schedule
celery -A config inspect scheduled

# Reiniciar Beat
systemctl restart bff-beat
```

---

## 📞 Contactos y Escalación

### Equipo de Desarrollo
- **Tech Lead**: [nombre] - [email] - [teléfono]
- **Backend Developer**: [nombre] - [email] - [teléfono]
- **DevOps Engineer**: [nombre] - [email] - [teléfono]

### Escalación por Severidad

#### Severidad 1 (Crítico)
1. **Inmediato**: Notificar a Tech Lead y DevOps
2. **15 min**: Escalar a CTO si no hay respuesta
3. **30 min**: Activar protocolo de crisis

#### Severidad 2 (Alto)
1. **Inmediato**: Notificar a equipo de desarrollo
2. **1 hora**: Escalar a Tech Lead
3. **4 horas**: Escalar a management

#### Severidad 3 (Medio)
1. **2 horas**: Asignar a desarrollador disponible
2. **1 día**: Revisar progreso con Tech Lead

### Canales de Comunicación
- **Slack**: #bff-alerts (alertas automáticas)
- **Slack**: #bff-incidents (coordinación de incidentes)
- **Email**: bff-team@company.com
- **PagerDuty**: [URL del servicio]

### Herramientas de Monitoreo
- **APM**: [URL de New Relic/DataDog]
- **Logs**: [URL de ELK Stack/Splunk]
- **Metrics**: [URL de Grafana]
- **Uptime**: [URL de Pingdom/StatusPage]

---

## 📚 Referencias Adicionales

### Documentación Técnica
- [API Documentation](./docs/api.md)
- [Database Schema](./docs/database.md)
- [Deployment Guide](./docs/deployment.md)
- [Security Guidelines](./docs/security.md)

### Comandos Útiles
```bash
# Verificar configuración actual
python manage.py diffsettings

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic

# Verificar deployment
python manage.py check --deploy
```

### Scripts de Automatización
- `scripts/health_check.sh` - Verificación de salud
- `scripts/backup.sh` - Backup automático
- `scripts/deploy.sh` - Deployment automatizado
- `scripts/rollback.sh` - Rollback rápido

---

## 📝 Historial de Cambios

| Fecha | Versión | Cambios | Autor |
|-------|---------|---------|-------|
| 2024-01-XX | 1.0 | Versión inicial del runbook | [Autor] |
| 2024-01-XX | 1.1 | Agregado troubleshooting de Celery | [Autor] |
| 2024-01-XX | 1.2 | Actualizado procedimientos de cache | [Autor] |

---

**📋 Nota**: Este runbook debe actualizarse regularmente y todos los procedimientos deben probarse en entorno de desarrollo antes de aplicarse en producción.

**🔄 Última actualización**: $(date)
**👤 Mantenido por**: Equipo BFF Development