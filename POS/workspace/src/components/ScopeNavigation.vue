<template>
  <nav class="bg-white border-b border-gray-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex space-x-8 overflow-x-auto">
        <router-link
          v-for="scope in availableScopes"
          :key="scope.key"
          :to="scope.route"
          class="flex items-center px-3 py-4 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap border-b-2 border-transparent transition-colors duration-200"
          :class="{
            'text-blue-600 border-blue-500': $route.path === scope.route,
            'cursor-not-allowed opacity-50': !scope.hasAccess
          }"
          @click="scope.hasAccess ? null : $event.preventDefault()"
        >
          <component :is="scope.icon" class="w-5 h-5 mr-2" />
          {{ scope.label }}
        </router-link>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  HomeIcon,
  UserGroupIcon,
  CubeIcon,
  ShoppingCartIcon,
  UsersIcon,
  ChartBarIcon,
  DocumentChartBarIcon,
  BookOpenIcon,
  CurrencyDollarIcon
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()

interface ScopeItem {
  key: string
  label: string
  route: string
  icon: any
  hasAccess: boolean
}

const availableScopes = computed((): ScopeItem[] => {
  const user = authStore.user
  if (!user) return []

  const scopes: ScopeItem[] = [
    {
      key: 'dashboard',
      label: 'Dashboard',
      route: '/dashboard',
      icon: HomeIcon,
      hasAccess: authStore.hasScope('has_scope_dashboard')
    },
    {
      key: 'users',
      label: 'Usuarios',
      route: '/users',
      icon: UserGroupIcon,
      hasAccess: authStore.hasScope('has_scope_users')
    },
    {
      key: 'inventory',
      label: 'Inventario',
      route: '/inventory',
      icon: CubeIcon,
      hasAccess: authStore.hasScope(['has_scope_inventory', 'has_scope_inventory_level_1', 'has_scope_inventory_level_2'])
    },
    {
      key: 'orders',
      label: 'Pedidos',
      route: '/orders',
      icon: ShoppingCartIcon,
      hasAccess: authStore.hasScope('has_scope_orders')
    },
    {
      key: 'customers',
      label: 'Clientes',
      route: '/customers',
      icon: UsersIcon,
      hasAccess: authStore.hasScope('has_scope_customers')
    },
    {
      key: 'catalog',
      label: 'Catálogo',
      route: '/catalog',
      icon: BookOpenIcon,
      hasAccess: authStore.hasScope('has_scope_catalog')
    },
    {
      key: 'caja',
      label: 'Caja',
      route: '/caja',
      icon: CurrencyDollarIcon,
      hasAccess: authStore.hasScope('has_scope_caja')
    },
    {
      key: 'reports',
      label: 'Reportes',
      route: '/reports',
      icon: DocumentChartBarIcon,
      hasAccess: authStore.hasScope('has_scope_reports')
    },
    {
      key: 'analytics',
      label: 'Analytics',
      route: '/analytics',
      icon: ChartBarIcon,
      hasAccess: authStore.hasScope('has_scope_analytics')
    }
  ]

  // Filtrar solo los scopes a los que el usuario tiene acceso
  return scopes.filter(scope => scope.hasAccess)
})
</script>

<style scoped>
/* Estilos adicionales si son necesarios */
.router-link-active {
  @apply text-blue-600 border-blue-500;
}
</style>