# 🐳 Entorno Docker - BFF

Este directorio contiene la configuración completa para ejecutar la aplicación BFF en contenedores Docker.

## 🚀 Inicio Rápido

### 1. Configuración Inicial

```bash
# Clonar el repositorio y navegar al directorio
cd BFF

# Copiar el archivo de variables de entorno
cp .env.example .env

# Editar las variables según sea necesario
# Especialmente las credenciales de base de datos y claves secretas
```

### 2. Construir y Ejecutar

```bash
# Construir e iniciar todos los servicios
docker-compose -f docker/docker-compose.yml up --build

# O en modo detached (segundo plano)
docker-compose -f docker/docker-compose.yml up --build -d
```

### 3. Acceso a la Aplicación

Una vez que todos los contenedores estén ejecutándose:

- **Frontend POS**: http://localhost:5173/pos/
- **API Backend**: http://localhost/api/
- **Panel Admin**: http://localhost/admin/
- **MailHog (Email Testing)**: http://localhost:8025/

## 👤 Usuario de Prueba

El sistema se inicializa automáticamente con un usuario de prueba:

- **Usuario**: `alejandro.vives`
- **Contraseña**: `ale12345`
- **Rol**: Encargado
- **Permisos**: Dashboard, Usuarios, Inventario (Nivel 1 y 2), Pedidos, Clientes, Catálogo, Caja

## 🏗️ Arquitectura de Servicios

### Backend Services
- **web**: Aplicación Django principal (Puerto 8000)
- **worker**: Celery worker para tareas asíncronas
- **beat**: Celery beat scheduler para tareas programadas

### Frontend Services
- **pos-frontend**: Aplicación Vue.js para POS (Puerto 5173)
- **nginx**: Reverse proxy y servidor de archivos estáticos (Puerto 80/443)

### Infrastructure Services
- **db**: PostgreSQL 16 con extensiones UUID y pg_trgm
- **redis**: Cache y message broker para Celery
- **mailhog**: Servidor de email para desarrollo

## 🔧 Comandos Útiles

### Gestión de Contenedores

```bash
# Ver logs de todos los servicios
docker-compose -f docker/docker-compose.yml logs

# Ver logs de un servicio específico
docker-compose -f docker/docker-compose.yml logs web

# Parar todos los servicios
docker-compose -f docker/docker-compose.yml down

# Parar y eliminar volúmenes (⚠️ Elimina datos de BD)
docker-compose -f docker/docker-compose.yml down -v

# Reconstruir un servicio específico
docker-compose -f docker/docker-compose.yml up --build web
```

### Comandos Django en Contenedor

```bash
# Ejecutar comando Django
docker-compose -f docker/docker-compose.yml exec web python manage.py <comando>

# Crear migraciones
docker-compose -f docker/docker-compose.yml exec web python manage.py makemigrations

# Aplicar migraciones
docker-compose -f docker/docker-compose.yml exec web python manage.py migrate

# Crear superusuario
docker-compose -f docker/docker-compose.yml exec web python manage.py createsuperuser

# Acceder al shell de Django
docker-compose -f docker/docker-compose.yml exec web python manage.py shell

# Acceder al bash del contenedor
docker-compose -f docker/docker-compose.yml exec web bash
```

### Comandos de Inicialización Manual

Si necesitas ejecutar los comandos de inicialización manualmente:

```bash
# Crear roles básicos
docker-compose -f docker/docker-compose.yml exec web python manage.py seed_roles

# Crear usuario de prueba
docker-compose -f docker/docker-compose.yml exec web python manage.py create_test_user

# Aplicar scopes a roles
docker-compose -f docker/docker-compose.yml exec web python manage.py apply_role_scopes
```

## 📁 Estructura de Archivos

```
docker/
├── docker-compose.yml          # Configuración principal de servicios
├── init_data.sh               # Script de inicialización automática
├── README.md                  # Esta documentación
├── frontend/                  # Dockerfiles para frontends
│   ├── pos.Dockerfile
│   ├── b2b.Dockerfile
│   └── panel.Dockerfile
├── postgres/
│   └── init.sql              # Script de inicialización de PostgreSQL
└── web/
    └── Dockerfile            # Dockerfile para backend Django
```

## 🔒 Seguridad

### Variables de Entorno Importantes

Asegúrate de configurar estas variables en tu archivo `.env`:

```env
# Django
SECRET_KEY=tu-clave-secreta-muy-segura
DEBUG=False

# Base de Datos
POSTGRES_DB=bff_production
POSTGRES_USER=bff_user
POSTGRES_PASSWORD=password-muy-seguro

# Redis
REDIS_PASSWORD=password-redis-seguro
```

### Consideraciones de Producción

- Cambiar todas las contraseñas por defecto
- Usar certificados SSL/TLS para HTTPS
- Configurar firewall apropiado
- Implementar backup automático de base de datos
- Monitorear logs y métricas

## 🐛 Troubleshooting

### Problemas Comunes

1. **Error de conexión a base de datos**
   ```bash
   # Verificar que el contenedor de BD esté corriendo
   docker-compose -f docker/docker-compose.yml ps db
   
   # Ver logs de la base de datos
   docker-compose -f docker/docker-compose.yml logs db
   ```

2. **Frontend no carga**
   ```bash
   # Verificar que el contenedor frontend esté corriendo
   docker-compose -f docker/docker-compose.yml ps pos-frontend
   
   # Reconstruir el frontend
   docker-compose -f docker/docker-compose.yml up --build pos-frontend
   ```

3. **Permisos de archivos**
   ```bash
   # En sistemas Unix, asegurar permisos correctos
   chmod +x docker/init_data.sh
   ```

### Logs y Debugging

```bash
# Ver todos los logs en tiempo real
docker-compose -f docker/docker-compose.yml logs -f

# Ver logs de un servicio específico
docker-compose -f docker/docker-compose.yml logs -f web

# Ver logs de los últimos 100 líneas
docker-compose -f docker/docker-compose.yml logs --tail=100 web
```

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs de los contenedores
2. Verifica que todas las variables de entorno estén configuradas
3. Asegúrate de que los puertos no estén siendo usados por otros servicios
4. Consulta la documentación de cada servicio individual

---

🎉 **¡Listo!** Tu entorno Docker está configurado y listo para desarrollo y producción.