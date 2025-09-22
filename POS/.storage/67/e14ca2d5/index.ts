import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showToast } from '@/lib/errorToast'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/pos'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/denied',
      name: 'Denied',
      component: () => import('@/views/DeniedView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/POSLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'pos',
          name: 'POS',
          component: () => import('@/views/PosView.vue'),
          meta: { 
            requiresAuth: true,
            allowedRoles: ['vendedor_caja', 'admin']
          }
        },
        {
          path: 'history',
          name: 'History',
          component: () => import('@/views/HistoryView.vue'),
          meta: { 
            requiresAuth: true,
            allowedRoles: ['vendedor_caja', 'admin']
          }
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { 
            requiresAuth: true,
            allowedRoles: ['admin']
          }
        }
      ]
    }
  ]
})

// Global navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Check if route requires authentication
  if (to.meta.requiresAuth) {
    // Check if user has access token
    if (!authStore.getAccess()) {
      showToast('Debes iniciar sesión', 'warning')
      return next('/login')
    }
    
    // Load user profile if not already loaded
    if (!authStore.user) {
      try {
        await authStore.loadProfile()
      } catch (error) {
        showToast('Sesión inválida', 'error')
        return next('/login')
      }
    }
    
    // Check role-based access
    if (to.meta.allowedRoles) {
      const allowedRoles = to.meta.allowedRoles as string[]
      const userRoles = authStore.roles
      
      const hasAccess = allowedRoles.some(role => userRoles.includes(role))
      
      if (!hasAccess) {
        return next('/denied')
      }
    }
  }
  
  // Redirect authenticated users away from login
  if (to.path === '/login' && authStore.isAuthenticated) {
    return next('/pos')
  }
  
  next()
})

// Listen for logout events from interceptor
if (typeof window !== 'undefined') {
  window.addEventListener('auth:logout', () => {
    const authStore = useAuthStore()
    if (authStore.isAuthenticated) {
      authStore.logout()
      router.push('/login')
      showToast('Sesión expirada', 'warning')
    }
  })
}

export default router