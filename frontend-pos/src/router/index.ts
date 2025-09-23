import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'
import POSView from '@/views/POSView.vue'
import ProductsView from '@/views/ProductsView.vue'
import SalesView from '@/views/SalesView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'Login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/pos',
      name: 'POS',
      component: POSView,
      meta: { 
        requiresAuth: true,
        roles: ['vendedor_caja', 'admin']
      }
    },
    {
      path: '/history',
      name: 'History',
      component: SalesView,
      meta: { 
        requiresAuth: true,
        roles: ['vendedor_caja', 'admin']
      }
    },
    {
      path: '/products',
      name: 'Products',
      component: ProductsView,
      meta: { 
        requiresAuth: true,
        roles: ['admin']
      }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
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
    // Si ya está autenticado y va a login, redirigir según roles
    if (authStore.isAuthenticated) {
      const userRoles = authStore.userRoles
      if (userRoles.includes('admin')) {
        next('/settings')
      } else {
        next('/pos')
      }
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
      // Redirigir a una página apropiada según los roles del usuario
      const userRoles = authStore.userRoles
      if (userRoles.includes('admin')) {
        next('/settings')
      } else if (userRoles.includes('vendedor_caja')) {
        next('/pos')
      } else {
        next('/login')
      }
      return
    }
  }
  
  next()
})

export default router