<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 text-center">
      <!-- 403 Icon -->
      <div class="mx-auto flex items-center justify-center h-24 w-24 rounded-full bg-red-100">
        <svg class="h-12 w-12 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      </div>

      <!-- Error Message -->
      <div>
        <h2 class="mt-6 text-3xl font-extrabold text-gray-900">
          Acceso Denegado
        </h2>
        <p class="mt-2 text-sm text-gray-600">
          No tienes permisos suficientes para acceder a esta página.
        </p>
        <p class="mt-1 text-xs text-gray-500">
          Código de error: 403 - Forbidden
        </p>
      </div>

      <!-- User Info -->
      <div v-if="authStore.user" class="bg-gray-100 rounded-lg p-4">
        <p class="text-sm text-gray-700">
          <strong>Usuario:</strong> {{ authStore.user.email }}
        </p>
        <p class="text-sm text-gray-700 mt-1">
          <strong>Roles actuales:</strong>
        </p>
        <div class="flex justify-center space-x-1 mt-2">
          <span
            v-for="role in authStore.roles"
            :key="role"
            class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
          >
            {{ role }}
          </span>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="space-y-3">
        <button
          @click="goBack"
          class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Volver Atrás
        </button>
        
        <button
          @click="goHome"
          class="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          Ir al Inicio
        </button>
        
        <button
          @click="logout"
          class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
        >
          Cerrar Sesión
        </button>
      </div>

      <!-- Help Text -->
      <div class="text-xs text-gray-500">
        <p>Si crees que esto es un error, contacta al administrador del sistema.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const goBack = () => {
  router.back()
}

const goHome = () => {
  // Redirect to appropriate home based on user role
  if (authStore.hasAnyRole(['vendedor_caja', 'admin'])) {
    router.push('/pos')
  } else {
    router.push('/login')
  }
}

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>