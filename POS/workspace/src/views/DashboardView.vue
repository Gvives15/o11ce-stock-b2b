<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p class="text-sm text-gray-600 mt-1">
              Rol: {{ userRole }} | Bienvenido, {{ authStore.user?.first_name || authStore.user?.username }}
            </p>
          </div>
          <button
            @click="handleLogout"
            class="text-sm text-red-600 hover:text-red-800 font-medium"
          >
            Cerrar Sesión
          </button>
        </div>
      </div>
    </header>

    <!-- Scope Navigation -->
    <ScopeNavigation />

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <!-- Welcome Message -->
      <div class="mb-8">
        <div class="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
          <h2 class="text-xl font-bold mb-2">¡Bienvenido al Sistema POS!</h2>
          <p class="text-blue-100">
            {{ welcomeMessage }}
          </p>
        </div>
      </div>

      <!-- Main Dashboard Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <DashboardCard
          v-for="card in availableCards"
          :key="card.key"
          :title="card.title"
          :description="card.description"
          :icon="card.icon"
          :icon-color="card.iconColor"
          :route="card.route"
          :stats="card.stats"
          :footer-text="card.footerText"
        />
      </div>

      <!-- Notifications Section (only if user has relevant scopes) -->
      <div v-if="hasNotificationScopes" class="mb-8">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Notificaciones</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Low Stock Notification -->
          <div 
            v-if="authStore.hasScope(['has_scope_inventory_level_1', 'has_scope_inventory_level_2'])"
            class="bg-yellow-50 border border-yellow-200 rounded-lg p-4"
          >
            <div class="flex items-center">
              <i class="fas fa-exclamation-triangle text-yellow-600 mr-2"></i>
              <h3 class="text-sm font-medium text-yellow-800">Stock Bajo</h3>
            </div>
            <p class="text-sm text-yellow-700 mt-1">
              {{ lowStockCount }} productos con stock bajo
            </p>
            <router-link 
              to="/inventory" 
              class="text-sm text-yellow-800 hover:text-yellow-900 font-medium"
            >
              Ver inventario →
            </router-link>
          </div>

          <!-- Expiring Products Notification -->
          <div 
            v-if="authStore.hasScope(['has_scope_inventory_level_1', 'has_scope_inventory_level_2'])"
            class="bg-red-50 border border-red-200 rounded-lg p-4"
          >
            <div class="flex items-center">
              <i class="fas fa-clock text-red-600 mr-2"></i>
              <h3 class="text-sm font-medium text-red-800">Productos por Vencer</h3>
            </div>
            <p class="text-sm text-red-700 mt-1">
              {{ expiringProductsCount }} productos próximos a vencer
            </p>
            <router-link 
              to="/inventory" 
              class="text-sm text-red-800 hover:text-red-900 font-medium"
            >
              Ver inventario →
            </router-link>
          </div>

          <!-- New Orders Notification -->
          <div 
            v-if="authStore.hasScope('has_scope_orders')"
            class="bg-blue-50 border border-blue-200 rounded-lg p-4"
          >
            <div class="flex items-center">
              <i class="fas fa-shopping-cart text-blue-600 mr-2"></i>
              <h3 class="text-sm font-medium text-blue-800">Nuevos Pedidos</h3>
            </div>
            <p class="text-sm text-blue-700 mt-1">
              {{ newOrdersCount }} pedidos pendientes
            </p>
            <router-link 
              to="/orders" 
              class="text-sm text-blue-800 hover:text-blue-900 font-medium"
            >
              Ver pedidos →
            </router-link>
          </div>
        </div>
      </div>

      <!-- Quick Stats (only for roles with dashboard scope) -->
      <div v-if="authStore.hasScope('has_scope_dashboard')" class="mb-8">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Estadísticas Rápidas</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <i class="fas fa-cube text-blue-600 text-2xl mr-4"></i>
              <div>
                <p class="text-sm font-medium text-gray-600">Total Productos</p>
                <p class="text-2xl font-bold text-gray-900">{{ totalProducts }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <i class="fas fa-users text-green-600 text-2xl mr-4"></i>
              <div>
                <p class="text-sm font-medium text-gray-600">Total Clientes</p>
                <p class="text-2xl font-bold text-gray-900">{{ totalCustomers }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <i class="fas fa-shopping-cart text-purple-600 text-2xl mr-4"></i>
              <div>
                <p class="text-sm font-medium text-gray-600">Pedidos Hoy</p>
                <p class="text-2xl font-bold text-gray-900">{{ todayOrders }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <i class="fas fa-dollar-sign text-yellow-600 text-2xl mr-4"></i>
              <div>
                <p class="text-sm font-medium text-gray-600">Ventas Hoy</p>
                <p class="text-2xl font-bold text-gray-900">${{ todaySales }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ScopeNavigation from '@/components/ScopeNavigation.vue'
import DashboardCard from '@/components/DashboardCard.vue'

const router = useRouter()
const authStore = useAuthStore()

// Notification counters
const lowStockCount = ref(0)
const expiringProductsCount = ref(0)
const newOrdersCount = ref(0)

// Quick stats
const totalProducts = ref(0)
const totalCustomers = ref(0)
const todayOrders = ref(0)
const todaySales = ref(0)

// Role-based constants
const ROLE_PERMISSIONS = {
  admin: {
    scopes: [
      'has_scope_dashboard', 'has_scope_users', 'has_scope_inventory_level_2',
      'has_scope_orders', 'has_scope_customers', 'has_scope_catalog',
      'has_scope_caja', 'has_scope_reports', 'has_scope_analytics'
    ],
    defaultRoute: '/dashboard'
  },
  encargado: {
    scopes: [
      'has_scope_dashboard', 'has_scope_inventory_level_2', 'has_scope_orders',
      'has_scope_customers', 'has_scope_catalog', 'has_scope_caja'
    ],
    defaultRoute: '/dashboard'
  },
  vendedor_caja: {
    scopes: [
      'has_scope_inventory_level_1', 'has_scope_orders', 'has_scope_customers', 'has_scope_caja'
    ],
    defaultRoute: '/caja'
  },
  vendedor_ruta: {
    scopes: [
      'has_scope_inventory_level_1', 'has_scope_orders', 'has_scope_customers'
    ],
    defaultRoute: '/orders'
  }
}

// Computed properties
const userRole = computed(() => {
  const roles = authStore.user?.roles || []
  if (roles.includes('admin')) return 'Administrador'
  if (roles.includes('encargado')) return 'Encargado'
  if (roles.includes('vendedor_caja')) return 'Vendedor de Caja'
  if (roles.includes('vendedor_ruta')) return 'Vendedor de Ruta'
  return 'Usuario'
})

const welcomeMessage = computed(() => {
  const role = userRole.value
  const messages = {
    'Administrador': 'Tienes acceso completo al sistema. Gestiona usuarios, inventario, reportes y más.',
    'Encargado': 'Supervisa las operaciones diarias, gestiona inventario y coordina el equipo.',
    'Vendedor de Caja': 'Procesa ventas, gestiona la caja y atiende a los clientes en el punto de venta.',
    'Vendedor de Ruta': 'Gestiona pedidos de clientes externos y mantén actualizado el inventario de ruta.'
  }
  return messages[role] || 'Bienvenido al sistema POS.'
})

const hasNotificationScopes = computed(() => {
  return authStore.hasScope(['has_scope_inventory_level_1', 'has_scope_inventory_level_2', 'has_scope_orders'])
})

const availableCards = computed(() => {
  const cards = []

  // Dashboard card (solo para admin y encargado)
  if (authStore.hasScope('has_scope_dashboard')) {
    cards.push({
      key: 'dashboard',
      title: 'Panel Principal',
      description: 'Resumen general del sistema y estadísticas',
      icon: 'fas fa-tachometer-alt',
      iconColor: '#3B82F6',
      route: '/dashboard',
      footerText: 'Ver estadísticas',
      stats: [
        { label: 'Productos', value: totalProducts.value },
        { label: 'Clientes', value: totalCustomers.value }
      ]
    })
  }

  // POS card (para vendedores de caja)
  if (authStore.hasScope('has_scope_caja')) {
    cards.push({
      key: 'pos',
      title: 'Punto de Venta',
      description: 'Procesar ventas y gestionar transacciones',
      icon: 'fas fa-cash-register',
      iconColor: '#10B981',
      route: '/caja',
      footerText: 'Abrir POS',
      stats: [
        { label: 'Ventas Hoy', value: `$${todaySales.value}` },
        { label: 'Transacciones', value: todayOrders.value }
      ]
    })
  }

  // Inventory card
  if (authStore.hasScope(['has_scope_inventory_level_1', 'has_scope_inventory_level_2'])) {
    const isLevel2 = authStore.hasScope('has_scope_inventory_level_2')
    cards.push({
      key: 'inventory',
      title: 'Inventario',
      description: isLevel2 ? 'Gestión completa de inventario y stock' : 'Consulta de inventario y stock',
      icon: 'fas fa-boxes',
      iconColor: '#F59E0B',
      route: '/inventory',
      footerText: isLevel2 ? 'Gestionar inventario' : 'Ver inventario',
      stats: [
        { label: 'Productos', value: totalProducts.value },
        { label: 'Stock Bajo', value: lowStockCount.value }
      ]
    })
  }

  // Orders card
  if (authStore.hasScope('has_scope_orders')) {
    cards.push({
      key: 'orders',
      title: 'Pedidos',
      description: 'Gestión de pedidos y órdenes de compra',
      icon: 'fas fa-shopping-cart',
      iconColor: '#8B5CF6',
      route: '/orders',
      footerText: 'Ver pedidos',
      stats: [
        { label: 'Pendientes', value: newOrdersCount.value },
        { label: 'Hoy', value: todayOrders.value }
      ]
    })
  }

  // Customers card
  if (authStore.hasScope('has_scope_customers')) {
    cards.push({
      key: 'customers',
      title: 'Clientes',
      description: 'Gestión de clientes y base de datos',
      icon: 'fas fa-users',
      iconColor: '#06B6D4',
      route: '/customers',
      footerText: 'Ver clientes',
      stats: [
        { label: 'Total', value: totalCustomers.value },
        { label: 'Activos', value: Math.floor(totalCustomers.value * 0.8) }
      ]
    })
  }

  // Catalog card (solo admin y encargado)
  if (authStore.hasScope('has_scope_catalog')) {
    cards.push({
      key: 'catalog',
      title: 'Catálogo',
      description: 'Gestión de productos y categorías',
      icon: 'fas fa-book',
      iconColor: '#EF4444',
      route: '/catalog',
      footerText: 'Gestionar catálogo'
    })
  }

  // Reports card (solo admin)
  if (authStore.hasScope('has_scope_reports')) {
    cards.push({
      key: 'reports',
      title: 'Reportes',
      description: 'Informes y análisis de ventas',
      icon: 'fas fa-chart-bar',
      iconColor: '#84CC16',
      route: '/reports',
      footerText: 'Ver reportes'
    })
  }

  // Analytics card (solo admin)
  if (authStore.hasScope('has_scope_analytics')) {
    cards.push({
      key: 'analytics',
      title: 'Analíticas',
      description: 'Análisis avanzado y métricas',
      icon: 'fas fa-chart-line',
      iconColor: '#F97316',
      route: '/analytics',
      footerText: 'Ver analíticas'
    })
  }

  // Users card (solo admin)
  if (authStore.hasScope('has_scope_users')) {
    cards.push({
      key: 'users',
      title: 'Usuarios',
      description: 'Gestión de usuarios y permisos',
      icon: 'fas fa-user-cog',
      iconColor: '#6366F1',
      route: '/users',
      footerText: 'Gestionar usuarios'
    })
  }

  return cards
})

const loadDashboardData = async () => {
  try {
    // Aquí se cargarían los datos reales desde la API
    // Por ahora usamos datos de ejemplo
    lowStockCount.value = 5
    expiringProductsCount.value = 3
    newOrdersCount.value = 12
    totalProducts.value = 150
    totalCustomers.value = 45
    todayOrders.value = 8
    todaySales.value = 1250.50
  } catch (error) {
    console.error('Error loading dashboard data:', error)
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
/* Estilos adicionales si son necesarios */
</style>