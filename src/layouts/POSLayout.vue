<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo/Title -->
          <div class="flex items-center">
            <h1 class="text-xl font-semibold text-gray-900">Sistema POS</h1>
          </div>

          <!-- Navigation -->
          <nav class="flex space-x-4">
            <router-link
              v-if="authStore.hasAnyRole(['vendedor_caja', 'admin'])"
              to="/pos"
              class="nav-link"
              :class="{ 'nav-link-active': $route.name === 'pos' }"
            >
              Punto de Venta
            </router-link>
            <router-link
              v-if="authStore.hasAnyRole(['vendedor_caja', 'admin'])"
              to="/history"
              class="nav-link"
              :class="{ 'nav-link-active': $route.name === 'history' }"
            >
              Historial
            </router-link>
            <router-link
              v-if="authStore.hasRole('admin')"
              to="/settings"
              class="nav-link"
              :class="{ 'nav-link-active': $route.name === 'settings' }"
            >
              Configuración
            </router-link>
          </nav>

          <!-- User Menu -->
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-700">
              {{ authStore.user?.email }}
            </span>
            <div class="flex space-x-1">
              <span
                v-for="role in authStore.roles"
                :key="role"
                class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {{ role }}
              </span>
            </div>
            <button
              @click="handleLogout"
              class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Cerrar Sesión
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.nav-link {
  @apply px-3 py-2 rounded-md text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors;
}

.nav-link-active {
  @apply text-blue-600 bg-blue-50;
}
</style>