import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import CustomersView from '@/views/CustomersView.vue'
import CajaView from '@/views/CajaView.vue'
import CatalogView from '@/views/CatalogView.vue'
import ReportsView from '@/views/ReportsView.vue'
import AnalyticsView from '@/views/AnalyticsView.vue'
import UsersView from '@/views/UsersView.vue'
import InventoryView from '@/views/InventoryView.vue'
import OrdersView from '@/views/OrdersView.vue'

const router = createRouter({
  history: createWebHistory('/pos/'),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      name: 'Login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: DashboardView,
      meta: { 
        requiresAuth: true,
        scopes: ['has_scope_dashboard']
      }
    },
    {
      path: '/inventory',
      name: 'Inventory',
      component: InventoryView,
      meta: { 
        requiresAuth: true,
        scopes: ['has_scope_inventory']
      }
    },
    {
      path: '/orders',
      name: 'Orders',
      component: OrdersView,
      meta: { 
        requiresAuth: true,
        scopes: ['has_scope_orders']
      }
    },
    {
      path: '/customers',
      name: 'Customers',
      component: CustomersView,
      meta: { 
        requiresAuth: true,
        scopes: ['has_scope_customers']
      }
    },
    {
      path: '/caja',
      name: 'Caja',
      component: CajaView,
      meta: { 
        requiresAuth: true,
        scopes: ['has_scope_caja']
      }
    },
    {
      path: '/catalog',
      name: 'Catalog',
      component: CatalogView,
      meta: { 
        requiresAuth: true,
        roles: ['admin', 'encargado']
      }
    },
    {
      path: '/reports',
      name: 'Reports',
      component: ReportsView,
      meta: { 
        requiresAuth: true,
        roles: ['admin']
      }
    },
    {
      path: '/analytics',
      name: 'Analytics',
      component: AnalyticsView,
      meta: { 
        requiresAuth: true,
        roles: ['admin']
      }
    },
    {
      path: '/users',
      name: 'Users',
      component: UsersView,
      meta: { 
        requiresAuth: true,
        roles: ['admin']
      }
    }
  ]
})

// Guard global para autenticación y roles
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Si la ruta no requiere autenticación, permitir acceso
  if (to.meta.requiresAuth === false) {
    // Si ya está autenticado y va a login, redirigir al dashboard
    if (authStore.isAuthenticated && to.path === '/login') {
      next('/dashboard')
      return
    }
    next()
    return
  }
  
  // Verificar autenticación
  if (!authStore.accessToken) {
    next('/login')
    return
  }
  
  // Si hay token pero no hay usuario, verificar autenticación
  if (authStore.accessToken && !authStore.user) {
    const isValid = await authStore.checkAuth()
    if (!isValid) {
      next('/login')
      return
    }
  }
  
  // Verificar roles si están definidos
  if (to.meta.roles && Array.isArray(to.meta.roles)) {
    const hasRequiredRole = authStore.hasRole(to.meta.roles)
    if (!hasRequiredRole) {
      // Evitar redirección infinita: no redirigir a la misma ruta
      if (to.path === from.path) {
        next(false) // Cancelar navegación
        return
      }
      
      // Redirigir al dashboard - será el centro de redirección
      if (to.path !== '/dashboard') {
        next('/dashboard')
      } else {
        next('/login') // Si no puede acceder al dashboard, ir a login
      }
      return
    }
  }

  // Verificar scopes si están definidos
  if (to.meta.scopes && Array.isArray(to.meta.scopes)) {
    const hasRequiredScope = authStore.hasScope(to.meta.scopes)
    if (!hasRequiredScope) {
      // Evitar redirección infinita: no redirigir a la misma ruta
      if (to.path === from.path) {
        next(false) // Cancelar navegación
        return
      }
      
      // Redirigir al dashboard - será el centro de redirección
      if (to.path !== '/dashboard') {
        next('/dashboard')
      } else {
        next('/login') // Si no puede acceder al dashboard, ir a login
      }
      return
    }
  }

  next()
})

export default router