import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NProgress from 'nprogress'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: {
      requiresAuth: false,
      title: 'Iniciar Sesión'
    }
  },
  {
    path: '/denied',
    name: 'denied',
    component: () => import('@/views/DeniedView.vue'),
    meta: {
      requiresAuth: false,
      title: 'Acceso Denegado'
    }
  },
  {
    path: '/pos',
    name: 'pos',
    component: () => import('@/views/PosView.vue'),
    meta: {
      requiresAuth: true,
      roles: ['vendedor_caja', 'admin'],
      title: 'Punto de Venta',
      layout: 'pos'
    }
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue'),
    meta: {
      requiresAuth: true,
      roles: ['vendedor_caja', 'admin'],
      title: 'Historial de Ventas',
      layout: 'pos'
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: {
      requiresAuth: true,
      roles: ['admin'],
      title: 'Configuración POS',
      layout: 'pos'
    }
  },
  {
    path: '/',
    redirect: '/pos'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/pos'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Global navigation guard
router.beforeEach(async (to, from, next) => {
  NProgress.start()
  
  const authStore = useAuthStore()
  const requiresAuth = to.meta?.requiresAuth

  // Update document title
  if (to.meta?.title) {
    document.title = `${to.meta.title} - Sistema POS`
  }

  // If route doesn't require auth, allow access
  if (!requiresAuth) {
    next()
    return
  }

  // Check if user has token
  if (!authStore.tokenAccess) {
    next({
      name: 'login',
      query: { redirect: to.fullPath }
    })
    return
  }

  // Load profile if not loaded yet
  if (!authStore.profileLoaded) {
    try {
      await authStore.loadProfile()
    } catch (error) {
      // If profile loading fails, logout and redirect to login
      authStore.logout()
      next({
        name: 'login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }

  // Check role permissions
  const allowedRoles = (to.meta?.roles || []) as string[]
  if (allowedRoles.length > 0) {
    const hasPermission = authStore.hasAnyRole(allowedRoles)
    if (!hasPermission) {
      next({ name: 'denied' })
      return
    }
  }

  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router