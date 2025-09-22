# B0-FE-01 - Sistema de Rutas con Guards por Rol

## Objetivo
Implementar un sistema completo de autenticación y control de acceso basado en roles para una aplicación Vue.js POS.

## Archivos Implementados

### 1. Configuración Base
- [x] `package.json` - Dependencias del proyecto
- [x] `vite.config.ts` - Configuración de Vite
- [x] `tsconfig.json` - Configuración TypeScript
- [x] `tailwind.config.js` - Configuración Tailwind CSS
- [x] `index.html` - HTML base con título actualizado
- [x] `src/main.ts` - Punto de entrada de la aplicación
- [x] `src/style.css` - Estilos globales y NProgress

### 2. Store de Autenticación (Pinia)
- [x] `src/stores/auth.ts` - Store con:
  - Estado: `tokenAccess`, `roles`, `profileLoaded`, `user`, `loading`
  - Acciones: `setToken()`, `loadProfile()`, `login()`, `logout()`
  - Getters: `isAuthenticated`, `hasRole()`, `hasAnyRole()`, etc.

### 3. Cliente HTTP
- [x] `src/lib/axiosClient.ts` - Cliente HTTP con interceptores

### 4. Router con Guards
- [x] `src/router/index.ts` - Router con:
  - Rutas definidas con `meta.requiresAuth` y `meta.roles`
  - Guard global `beforeEach` que verifica token y roles
  - Redirección automática según permisos
  - Integración con NProgress para loading

### 5. Layout
- [x] `src/layouts/POSLayout.vue` - Layout principal con:
  - Header con navegación
  - Menú dinámico según roles
  - Información del usuario
  - Botón de logout

### 6. Vistas
- [x] `src/views/LoginView.vue` - Vista de login con:
  - Formulario de autenticación
  - Credenciales de prueba
  - Manejo de redirección post-login
  - Estados de carga
  
- [x] `src/views/PosView.vue` - Punto de venta con:
  - Interfaz de productos
  - Carrito de compras
  - Procesamiento de pagos mock
  
- [x] `src/views/HistoryView.vue` - Historial de ventas con:
  - Tabla de ventas con filtros
  - Estadísticas resumidas
  - Paginación
  - Búsqueda
  
- [x] `src/views/SettingsView.vue` - Configuración (solo admin) con:
  - Configuración general del negocio
  - Configuración de impuestos
  - Configuración del sistema
  - Gestión de usuarios
  
- [x] `src/views/DeniedView.vue` - Página de acceso denegado con:
  - Mensaje de error 403
  - Información del usuario actual
  - Botones de navegación

### 7. App Principal
- [x] `src/App.vue` - Componente raíz con inicialización del token

## Roles y Permisos Implementados

### `vendedor_caja`
- ✅ Acceso a `/pos` (Punto de Venta)
- ✅ Acceso a `/history` (Historial de Ventas)
- ❌ NO acceso a `/settings` (Configuración)

### `admin`
- ✅ Acceso a `/pos` (Punto de Venta)
- ✅ Acceso a `/history` (Historial de Ventas)
- ✅ Acceso a `/settings` (Configuración)

## Funcionalidades Implementadas

### Autenticación
- [x] Login con credenciales mock
- [x] Almacenamiento de token en localStorage
- [x] Carga automática del perfil (`/auth/me` mock)
- [x] Logout con limpieza de estado

### Guards de Navegación
- [x] Verificación de token antes de acceder a rutas protegidas
- [x] Carga del perfil si no está disponible
- [x] Verificación de roles según `meta.roles`
- [x] Redirección a `/login` con parámetro `redirect`
- [x] Redirección a `/denied` si no tiene permisos

### Estados UX
- [x] Loading con NProgress durante navegación
- [x] Estados de carga en formularios
- [x] Página de acceso denegado clara
- [x] Redirección post-login a la ruta original

### Credenciales de Prueba
- **Vendedor Caja:** `vendedor@pos.com` / `password123`
- **Admin:** `admin@pos.com` / `admin123`

## Criterios de Aceptación ✅

- [x] Sin token → redirige a `/login` con `?redirect`
- [x] `vendedor_caja` accede a `/pos` y `/history`, NO a `/settings`
- [x] `admin` accede a todas las rutas
- [x] Loading state sin parpadeo durante carga de perfil
- [x] Página de denegación clara con opciones de navegación
- [x] Redirección post-login funcional
- [x] Menú dinámico según roles del usuario
- [x] Logout limpia todo el estado

## Próximos Pasos
1. Instalar dependencias con `pnpm install`
2. Ejecutar lint con `pnpm run lint`
3. Construir proyecto con `pnpm run build`
4. Probar funcionalidad manualmente
5. Ejecutar CheckUI para validar renderizado