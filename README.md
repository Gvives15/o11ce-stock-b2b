# O11CE Stock B2B

## Project Overview
O11CE Stock B2B provides a simple Backend-for-Frontend (BFF) service for e-commerce scenarios.
It is built with the Django framework and is intended as a starting point for managing stock information in business-to-business environments.

## Prerequisites
- Python 3.10+
- [pip](https://pip.pypa.io/)
- [virtualenv](https://virtualenv.pypa.io/) (optional but recommended)
- [Django](https://www.djangoproject.com/) and any additional dependencies used by your apps

## Environment Variables
The application is configured via environment variables. Copy `.env.example` to `.env` and update the values as needed.

Key variables include:
- `SECRET_KEY` – Django secret key.
- `DEBUG` – enable debug mode (`1` for development).
- `DATABASE_URL` – database connection string.
- `CORS_ALLOWED_ORIGINS` – comma-separated list of allowed origins.

## Local Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd o11ce-stock-b2b
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```
5. **Load seed data** (optional)
   ```bash
   python manage.py loaddata <path-to-fixture>.json
   ```
6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Docker Usage
Build and run the application with Docker:

```bash
docker build -t o11ce-stock-b2b .
docker run -p 8000:8000 --env-file .env o11ce-stock-b2b
```

Or using Docker Compose:

```bash
docker compose up --build
```

## Testing
Run the test suite with:

```bash
python manage.py test
```

## Observabilidad y Monitoreo

### Health Checks
La aplicación incluye endpoints de health check para monitoreo:

- **`/health/live/`** - Liveness probe: verifica que la aplicación esté ejecutándose
- **`/health/ready/`** - Readiness probe: verifica que todos los servicios estén disponibles (DB, Cache, SMTP, Celery)

Ejemplo de respuesta exitosa:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T01:40:03.889924Z",
  "latency_ms": 45.2,
  "service": "o11ce-stock-b2b",
  "version": "1.0.0"
}
```

### Logging Estructurado
La aplicación utiliza **structlog** para generar logs en formato JSON estructurado, facilitando el análisis y monitoreo.

#### Configuración de Logs
Los logs incluyen automáticamente:
- `request_id`: Identificador único por request (X-Request-ID)
- `timestamp`: Timestamp ISO 8601
- `level`: Nivel del log (info, warning, error, etc.)
- `logger`: Nombre del logger
- `event`: Mensaje del evento

#### Ejemplo de Log JSON
```json
{
  "event": "User authentication successful",
  "request_id": "a24cb318-ade1-46d9-a558-6bdf31cfff92",
  "user_id": 123,
  "logger": "apps.core.auth",
  "level": "info",
  "timestamp": "2025-01-22T01:40:03.889924Z"
}
```

#### Uso en el Código
```python
import structlog

logger = structlog.get_logger(__name__)

# Log simple
logger.info("Operation completed")

# Log con contexto
logger.info("User action", user_id=user.id, action="login")

# Log de error
logger.error("Database connection failed", error=str(e))
```

#### Request ID Middleware
Cada request HTTP recibe automáticamente un `X-Request-ID` único que se propaga a través de todos los logs, facilitando el trazado de requests específicos.

### Monitoreo de Servicios
Los health checks verifican:
- **Base de datos**: Conectividad y latencia
- **Cache/Redis**: Operaciones de lectura/escritura
- **SMTP**: Conectividad del servidor de email
- **Celery**: Estado de workers y broker

### Tolerancia a Fallos
El sistema está diseñado con tolerancia a fallos:
- Los health checks de cache son fault-tolerant (la app continúa funcionando aunque Redis falle)
- Los logs se mantienen incluso si algunos servicios están degradados
- Los endpoints críticos funcionan independientemente del estado de servicios auxiliares

## Architecture and Specifications
Dedicated architecture or specification documents are not yet included in this repository. Add links here once they are available.

## Contribution Guidelines
1. Fork the repository and create a feature branch for your work.
2. Follow existing code style and keep commits focused and descriptive.
3. Ensure tests run successfully before submitting a pull request.
4. Open a pull request against the default branch and describe your changes.

