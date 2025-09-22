# Sistema POS - Autenticación y Roles

Una aplicación Vue.js completa para punto de venta con autenticación, control de acceso por roles, manejo de estado operacional, e interceptores HTTP robustos.

## Características

### Autenticación y Roles
- **Sistema de login** con credenciales de prueba
- **Control de acceso basado en roles**:
  - `vendedor_caja`: acceso a Punto de Venta e Historial
  - `admin`: acceso completo (incluye Configuración)
- **Guards de navegación** automáticos
- **Redirección inteligente** post-login

### Navegación Inteligente
- **Menú dinámico** que se adapta según el rol del usuario
- **Sidebar** con iconos y estados activos
- **Topbar** con estado de conexión y acciones de usuario

### Estado Operacional
- **Banners de estado** con sistema de prioridades:
  1. **Offline** (crítico): "Sin conexión: modo lectura"
  2. **Sin turno** (advertencia): "No hay turno abierto"
  3. **Caja cerrada** (advertencia): "Caja cerrada"
- **Detección automática** de estado online/offline
- **Bloqueo de acciones críticas** cuando no se puede operar

### Interceptores HTTP y Manejo de Errores
- **Refresh automático de tokens** en caso de expiración (401)
- **Cola de requests** para evitar múltiples refresh simultáneos
- **Toasts user-friendly** para todos los errores HTTP
- **Logout automático** si el refresh token es inválido
- **Protección contra bucles** de refresh infinitos

### Funcionalidades POS
- **Punto de Venta** con carrito de compras
- **Historial de Ventas** con filtros y estadísticas
- **Configuración del Sistema** (solo admin)
- **Bloqueo inteligente** del botón "Procesar Pago"

## Credenciales de Prueba

```
Vendedor Caja: vendedor@pos.com / password123
Admin:         admin@pos.com / admin123
```

## Variables de Entorno

```bash
# .env
VITE_API_BASE_URL=http://localhost:3000/api
```

## Instalación y Uso

```bash
# Instalar dependencias
pnpm install

# Desarrollo
pnpm run dev

# Build para producción
pnpm run build

# Linting
pnpm run lint

# Tests unitarios
pnpm run test
```

## Estructura del Proyecto

```
src/
├── components/          # Componentes reutilizables
│   ├── Sidebar.vue     # Navegación lateral con filtrado por rol
│   ├── Topbar.vue      # Barra superior con estado
│   ├── GlobalBanners.vue # Banners de estado operacional
│   └── InterceptorDemo.vue # Demo de interceptores HTTP
├── composables/         # Lógica reutilizable
│   └── useBlockers.ts  # Bloqueo de acciones por estado
├── config/             # Configuraciones
│   └── menu.ts         # Definición de menú y roles
├── lib/                # Librerías y utilidades
│   ├── axiosClient.ts  # Cliente HTTP con interceptores
│   ├── authRefresh.ts  # Cola de refresh de tokens
│   └── errorToast.ts   # Manejo de errores y toasts
├── layouts/            # Layouts de página
│   └── POSLayout.vue   # Layout principal del sistema
├── stores/             # Estado global (Pinia)
│   ├── auth.ts         # Autenticación y roles
│   └── ops.ts          # Estado operacional
├── views/              # Páginas principales
└── router/             # Configuración de rutas
```

## Interceptores HTTP

### Flujo de Refresh Automático

```
Request → 401 token_expired → POST /auth/refresh → Retry original request
                            ↓
                         Si falla → logout() → /login + toast "Sesión expirada"
```

### Manejo de Errores

El sistema mapea automáticamente errores HTTP a mensajes user-friendly:

| Código | Mensaje |
|--------|---------|
| **401** | "Credenciales inválidas" |
| **403** | "Acceso denegado" |
| **404** | "Recurso no encontrado" |
| **409** | "Conflicto - No se pudo completar la acción" |
| **429** | "Demasiadas solicitudes - Intenta más tarde" |
| **5xx** | "Error del servidor" |
| **Network** | "Sin conexión a internet" |

### Protecciones de Seguridad

- **Anti-loops**: No refrescar si el endpoint es `/auth/refresh`
- **Límite de reintentos**: Máximo 1 reintento por request
- **Cola de requests**: Un solo refresh por vez, múltiples requests en cola
- **Timeout**: 15 segundos por request

### Testear Interceptores

1. **Ir a Configuración** (solo admin)
2. **Usar el panel "Demo de Interceptores HTTP"**
3. **Probar diferentes escenarios**:
   - Token expirado → refresh automático
   - Múltiples requests concurrentes → un solo refresh
   - Refresh inválido → logout automático
   - Errores 403, 409, red → toasts apropiados

### Debugging

```javascript
// Ver estado de tokens en consola
const authStore = useAuthStore()
console.log('Access:', authStore.getAccess())
console.log('Refresh:', authStore.getRefresh())

// Simular token expirado
authStore.setToken('expired_token')

// Invalidar refresh token
authStore.setRefresh('invalid_refresh')
```

## Manejo de Estado Operacional

### Flags de Estado
- `hasShiftOpen`: Indica si hay un turno abierto
- `hasCashboxOpen`: Indica si la caja está disponible
- `offline`: Detección automática de conexión

### Cómo Usar los Flags

```javascript
import { useOpsStore } from '@/stores/ops'

const opsStore = useOpsStore()

// Abrir/cerrar turno
opsStore.setShift(true)   // Abrir turno
opsStore.setShift(false)  // Cerrar turno

// Abrir/cerrar caja
opsStore.setCashbox(true)   // Abrir caja
opsStore.setCashbox(false)  // Cerrar caja

// El estado offline se maneja automáticamente
// pero se puede forzar para pruebas
opsStore.setOffline(true)   // Simular desconexión
```

### Probar Estados Operacionales

1. **Modo Offline**: Desconecta la red o usa el botón "Desconectar" en el panel de pruebas
2. **Sin Turno**: Usa el botón "Cerrar Turno" en el panel de pruebas
3. **Caja Cerrada**: Usa el botón "Cerrar Caja" en el panel de pruebas

### Bloqueo de Acciones

El sistema bloquea automáticamente acciones críticas cuando:
- No hay conexión a internet
- No hay turno abierto
- La caja está cerrada

Los botones bloqueados muestran:
- Estilo visual deshabilitado (`opacity-50 cursor-not-allowed`)
- Tooltip explicativo del motivo del bloqueo
- Texto descriptivo en lugar de la acción normal

## Rutas Protegidas

| Ruta | Roles Permitidos | Descripción |
|------|------------------|-------------|
| `/pos` | `vendedor_caja`, `admin` | Punto de Venta |
| `/history` | `vendedor_caja`, `admin` | Historial de Ventas |
| `/settings` | `admin` | Configuración del Sistema |
| `/login` | Público | Página de autenticación |
| `/denied` | Público | Acceso denegado |

## Tecnologías

- **Vue 3** con Composition API
- **TypeScript** para tipado estático
- **Vue Router** para navegación
- **Pinia** para manejo de estado
- **Tailwind CSS** para estilos
- **Vite** para build y desarrollo
- **Axios** para peticiones HTTP con interceptores
- **Vitest** para tests unitarios

## Desarrollo

### Agregar Nuevos Items al Menú

Edita `src/config/menu.ts`:

```typescript
export const MENU_ITEMS: MenuItem[] = [
  {
    id: 'nuevo-item',
    label: 'Nueva Funcionalidad',
    icon: 'M12 4v16m8-8H4', // SVG path
    route: '/nueva-ruta',
    roles: ['admin'] // Roles que pueden ver este item
  }
]
```

### Crear Nuevos Bloqueos

Usa el composable `useBlockers`:

```typescript
import { useBlockers } from '@/composables/useBlockers'

const { canCheckout, checkoutBlockReason } = useBlockers()

// En el template
<button 
  :disabled="!canCheckout"
  :title="checkoutBlockReason || ''"
>
  Acción
</button>
```

### Agregar Interceptores Personalizados

```typescript
import axiosClient from '@/lib/axiosClient'

// Request interceptor
axiosClient.interceptors.request.use(config => {
  // Lógica personalizada
  return config
})

// Response interceptor
axiosClient.interceptors.response.use(
  response => response,
  error => {
    // Manejo de errores personalizado
    return Promise.reject(error)
  }
)
```

## Testing

### Tests Unitarios

```bash
# Ejecutar tests
pnpm run test

# Tests en modo watch
pnpm run test --watch

# Coverage
pnpm run test --coverage
```

### Tests de Interceptores

El sistema incluye tests para validar:
- Refresh automático en 401
- Cola de requests concurrentes
- Mapeo de errores HTTP
- Logout automático en refresh inválido

### Testing Manual

El sistema incluye un panel de pruebas en la vista de Configuración para simular diferentes estados operacionales y escenarios de interceptores sin necesidad de configuración externa.

## Troubleshooting

### Problemas Comunes

**1. Bucle infinito de refresh**
- Verificar que el endpoint `/auth/refresh` esté excluido
- Revisar flag `__isRetry` en requests

**2. Tokens no se actualizan**
- Verificar que `localStorage` esté disponible
- Revisar permisos del navegador

**3. Toasts no aparecen**
- Verificar que el contenedor de toasts se cree correctamente
- Revisar z-index del contenedor

**4. Logout automático no funciona**
- Verificar que el evento `auth:logout` se dispare
- Revisar listener en router

### Logs de Debug

```javascript
// Habilitar logs de axios
import axiosClient from '@/lib/axiosClient'

axiosClient.interceptors.request.use(config => {
  console.log('Request:', config)
  return config
})

axiosClient.interceptors.response.use(
  response => {
    console.log('Response:', response)
    return response
  },
  error => {
    console.log('Error:', error)
    return Promise.reject(error)
  }
)
```

## Próximas Mejoras

- [ ] Tests E2E con Playwright
- [ ] Persistencia de estado en localStorage
- [ ] Notificaciones push
- [ ] Modo oscuro
- [ ] PWA (Progressive Web App)
- [ ] Sincronización offline
- [ ] Métricas de rendimiento
- [ ] Logs centralizados