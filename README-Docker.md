# Configuración Docker Multi-Entorno

Este proyecto utiliza una configuración Docker modular que permite ejecutar diferentes entornos (desarrollo y producción) de manera eficiente.

## Estructura de Archivos

```
docker/
├── docker-compose.yml          # Configuración base compartida
├── docker-compose.dev.yml      # Configuración específica de desarrollo
├── docker-compose.prod.yml     # Configuración específica de producción
└── scripts/
    ├── dev.ps1                 # Script para desarrollo (Windows)
    └── prod.ps1                # Script para producción (Windows)
```

## Entorno de Desarrollo

### Características
- ✅ **Hot Reload**: Los cambios en el código se reflejan automáticamente
- ✅ **Volúmenes montados**: Código fuente sincronizado en tiempo real
- ✅ **Django Development Server**: Servidor de desarrollo con debug activado
- ✅ **Vite Dev Server**: Frontend con hot module replacement
- ✅ **MailHog**: Servidor de email para testing

### Comandos de Desarrollo

```powershell
# Iniciar entorno de desarrollo
cd docker
.\scripts\dev.ps1 up

# Construir e iniciar (cuando hay cambios en Dockerfile)
.\scripts\dev.ps1 build

# Ver logs en tiempo real
.\scripts\dev.ps1 logs

# Reiniciar servicios
.\scripts\dev.ps1 restart

# Ver estado de contenedores
.\scripts\dev.ps1 status

# Detener entorno
.\scripts\dev.ps1 down
```

### URLs de Desarrollo
- **Aplicación POS**: http://localhost/pos/
- **API Django**: http://localhost/api/
- **MailHog**: http://localhost:8025/
- **Frontend directo**: http://localhost:5173/

## Entorno de Producción

### Características
- ✅ **Optimizado**: Sin volúmenes de código fuente
- ✅ **Gunicorn**: Servidor WSGI para producción
- ✅ **Build optimizado**: Frontend construido para producción
- ✅ **Sin MailHog**: Configuración limpia para servidor
- ✅ **Restart policies**: Reinicio automático de contenedores

### Comandos de Producción

```powershell
# Iniciar entorno de producción
cd docker
.\scripts\prod.ps1 up

# Construir e iniciar
.\scripts\prod.ps1 build

# Ver logs
.\scripts\prod.ps1 logs

# Reiniciar servicios
.\scripts\prod.ps1 restart

# Ver estado
.\scripts\prod.ps1 status

# Detener entorno
.\scripts\prod.ps1 down
```

## Comandos Manuales (Alternativa)

Si prefieres usar docker-compose directamente:

### Desarrollo
```bash
# Iniciar desarrollo
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Con build
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

### Producción
```bash
# Iniciar producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Con build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

## Migración desde Configuración Anterior

Si vienes de la configuración anterior con un solo `docker-compose.yml`:

1. **Detén los contenedores actuales**:
   ```powershell
   docker-compose down
   ```

2. **Usa la nueva configuración de desarrollo**:
   ```powershell
   .\scripts\dev.ps1 up
   ```

## Ventajas de esta Configuración

### Para Desarrollo
- **Sin rebuilds**: Los cambios se ven instantáneamente
- **Debugging fácil**: Acceso directo al código fuente
- **Hot reload**: Frontend y backend se actualizan automáticamente

### Para Producción
- **Optimizado**: Imágenes más pequeñas sin código fuente
- **Seguro**: Sin volúmenes de desarrollo expuestos
- **Escalable**: Configuración lista para despliegue

## Troubleshooting

### Problema: Los cambios no se reflejan
- Verifica que estés usando la configuración de desarrollo
- Asegúrate de que los volúmenes estén montados correctamente

### Problema: Puerto ocupado
- Verifica que no haya otros servicios corriendo en los puertos 80, 5173, 8025
- Usa `docker ps` para ver contenedores activos

### Problema: Contenedores no inician
- Revisa los logs: `.\scripts\dev.ps1 logs`
- Verifica que los archivos `.env` estén configurados correctamente