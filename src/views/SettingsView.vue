<template>
  <div class="space-y-6">
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Configuración del Sistema</h1>
        <div class="flex items-center space-x-2">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Solo Admin
          </span>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- System Settings -->
        <div class="space-y-4">
          <h2 class="text-lg font-medium text-gray-900">Configuración General</h2>
          
          <div class="space-y-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Nombre del Negocio
              </label>
              <input
                v-model="settings.businessName"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Moneda
              </label>
              <select
                v-model="settings.currency"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="USD">Dólar (USD)</option>
                <option value="EUR">Euro (EUR)</option>
                <option value="ARS">Peso Argentino (ARS)</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Zona Horaria
              </label>
              <select
                v-model="settings.timezone"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="America/Argentina/Buenos_Aires">Buenos Aires</option>
                <option value="America/New_York">Nueva York</option>
                <option value="Europe/Madrid">Madrid</option>
              </select>
            </div>
          </div>
        </div>

        <!-- User Management -->
        <div class="space-y-4">
          <h2 class="text-lg font-medium text-gray-900">Gestión de Usuarios</h2>
          
          <div class="bg-gray-50 rounded-lg p-4">
            <h3 class="font-medium text-gray-900 mb-3">Usuarios Activos</h3>
            <div class="space-y-2">
              <div
                v-for="user in mockUsers"
                :key="user.id"
                class="flex items-center justify-between py-2 px-3 bg-white rounded border"
              >
                <div>
                  <div class="font-medium text-sm">{{ user.name }}</div>
                  <div class="text-xs text-gray-500">{{ user.email }}</div>
                </div>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="role in user.roles"
                    :key="role"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {{ role }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Save Button -->
      <div class="mt-6 pt-6 border-t border-gray-200">
        <button
          @click="saveSettings"
          class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
        >
          Guardar Configuración
        </button>
      </div>
    </div>

    <!-- HTTP Interceptor Demo -->
    <InterceptorDemo />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import InterceptorDemo from '@/components/InterceptorDemo.vue'

interface Settings {
  businessName: string
  currency: string
  timezone: string
}

interface User {
  id: string
  name: string
  email: string
  roles: string[]
}

const settings = ref<Settings>({
  businessName: 'Mi Negocio POS',
  currency: 'USD',
  timezone: 'America/Argentina/Buenos_Aires'
})

const mockUsers: User[] = [
  {
    id: '1',
    name: 'Vendedor POS',
    email: 'vendedor@pos.com',
    roles: ['vendedor_caja']
  },
  {
    id: '2',
    name: 'Administrador',
    email: 'admin@pos.com',
    roles: ['admin', 'vendedor_caja']
  }
]

const saveSettings = () => {
  // Mock save - in real app, this would make an API call
  alert('Configuración guardada exitosamente')
}
</script>