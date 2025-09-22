# Sistema POS - Autenticación y Roles

Una aplicación Vue.js completa para punto de venta con autenticación, control de acceso por roles, y manejo de estado operacional.

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
```

## Estructura del Proyecto

```
src/
├── components/          # Componentes reutilizables
│   ├── Sidebar.vue     # Navegación lateral con filtrado por rol
│   ├── Topbar.vue      # Barra superior con estado
│   └── GlobalBanners.vue # Banners de estado operacional
├── composables/         # Lógica reutilizable
│   └── useBlockers.ts  # Bloqueo de acciones por estado
├── config/             # Configuraciones
│   └── menu.ts         # Definición de menú y roles
├── layouts/            # Layouts de página
│   └── POSLayout.vue   # Layout principal del sistema
├── stores/             # Estado global (Pinia)
│   ├── auth.ts         # Autenticación y roles
│   └── ops.ts          # Estado operacional
├── views/              # Páginas principales
└── router/             # Configuración de rutas
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
- **Axios** para peticiones HTTP

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

## Testing

El sistema incluye un panel de pruebas en la vista POS para simular diferentes estados operacionales sin necesidad de configuración externa.

## Próximas Mejoras

- [ ] Tests unitarios automatizados
- [ ] Persistencia de estado en localStorage
- [ ] Notificaciones toast
- [ ] Modo oscuro
- [ ] PWA (Progressive Web App)
- [ ] Sincronización offline