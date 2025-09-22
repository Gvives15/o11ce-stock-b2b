<template>
  <POSLayout>
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Configuración POS</h1>
        <div class="flex items-center space-x-2">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            Solo Admin
          </span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- General Settings -->
        <div class="space-y-6">
          <div>
            <h2 class="text-lg font-medium text-gray-900 mb-4">Configuración General</h2>
            
            <div class="space-y-4">
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
                  Dirección
                </label>
                <textarea
                  v-model="settings.address"
                  rows="3"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                ></textarea>
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Teléfono
                </label>
                <input
                  v-model="settings.phone"
                  type="tel"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  v-model="settings.email"
                  type="email"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          <!-- Tax Settings -->
          <div>
            <h3 class="text-md font-medium text-gray-900 mb-3">Configuración de Impuestos</h3>
            
            <div class="space-y-4">
              <div class="flex items-center">
                <input
                  id="tax-enabled"
                  v-model="settings.taxEnabled"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="tax-enabled" class="ml-2 block text-sm text-gray-900">
                  Habilitar cálculo de impuestos
                </label>
              </div>
              
              <div v-if="settings.taxEnabled">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Tasa de Impuesto (%)
                </label>
                <input
                  v-model.number="settings.taxRate"
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- System Settings -->
        <div class="space-y-6">
          <div>
            <h2 class="text-lg font-medium text-gray-900 mb-4">Configuración del Sistema</h2>
            
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Moneda
                </label>
                <select
                  v-model="settings.currency"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="USD">Dólar Estadounidense (USD)</option>
                  <option value="EUR">Euro (EUR)</option>
                  <option value="ARS">Peso Argentino (ARS)</option>
                  <option value="MXN">Peso Mexicano (MXN)</option>
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
                  <option value="America/New_York">Este (UTC-5)</option>
                  <option value="America/Chicago">Central (UTC-6)</option>
                  <option value="America/Denver">Montaña (UTC-7)</option>
                  <option value="America/Los_Angeles">Pacífico (UTC-8)</option>
                  <option value="America/Argentina/Buenos_Aires">Buenos Aires (UTC-3)</option>
                </select>
              </div>
              
              <div class="flex items-center">
                <input
                  id="receipt-print"
                  v-model="settings.autoprint"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="receipt-print" class="ml-2 block text-sm text-gray-900">
                  Imprimir recibo automáticamente
                </label>
              </div>
              
              <div class="flex items-center">
                <input
                  id="sound-enabled"
                  v-model="settings.soundEnabled"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="sound-enabled" class="ml-2 block text-sm text-gray-900">
                  Habilitar sonidos del sistema
                </label>
              </div>
            </div>
          </div>

          <!-- User Management -->
          <div>
            <h3 class="text-md font-medium text-gray-900 mb-3">Gestión de Usuarios</h3>
            
            <div class="space-y-3">
              <div
                v-for="user in mockUsers"
                :key="user.id"
                class="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
              >
                <div>
                  <div class="font-medium text-gray-900">{{ user.email }}</div>
                  <div class="text-sm text-gray-500">
                    <span
                      v-for="role in user.roles"
                      :key="role"
                      class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-1"
                    >
                      {{ role }}
                    </span>
                  </div>
                </div>
                <div class="flex space-x-2">
                  <button class="text-blue-600 hover:text-blue-800 text-sm">Editar</button>
                  <button class="text-red-600 hover:text-red-800 text-sm">Eliminar</button>
                </div>
              </div>
              
              <button class="w-full py-2 px-4 border border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-gray-400 hover:text-gray-800 transition-colors">
                + Agregar Usuario
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Save Button -->
      <div class="mt-8 flex justify-end space-x-4">
        <button
          @click="resetSettings"
          class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Restablecer
        </button>
        <button
          @click="saveSettings"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Guardar Cambios
        </button>
      </div>
    </div>
  </POSLayout>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import POSLayout from '@/layouts/POSLayout.vue'

interface User {
  id: number
  email: string
  roles: string[]
}

const mockUsers: User[] = [
  { id: 1, email: 'admin@pos.com', roles: ['admin'] },
  { id: 2, email: 'vendedor@pos.com', roles: ['vendedor_caja'] },
  { id: 3, email: 'ruta@pos.com', roles: ['vendedor_ruta'] }
]

const settings = reactive({
  businessName: 'Mi Negocio POS',
  address: 'Calle Principal 123\nCiudad, Estado 12345',
  phone: '+1 (555) 123-4567',
  email: 'contacto@minegocio.com',
  taxEnabled: true,
  taxRate: 21.0,
  currency: 'USD',
  timezone: 'America/New_York',
  autoprint: true,
  soundEnabled: true
})

const saveSettings = () => {
  // Mock save operation
  console.log('Saving settings:', settings)
  alert('Configuración guardada exitosamente')
}

const resetSettings = () => {
  // Reset to default values
  Object.assign(settings, {
    businessName: 'Mi Negocio POS',
    address: 'Calle Principal 123\nCiudad, Estado 12345',
    phone: '+1 (555) 123-4567',
    email: 'contacto@minegocio.com',
    taxEnabled: true,
    taxRate: 21.0,
    currency: 'USD',
    timezone: 'America/New_York',
    autoprint: true,
    soundEnabled: true
  })
}
</script>