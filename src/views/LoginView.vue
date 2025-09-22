<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Iniciar Sesión
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Sistema POS - Autenticación por Roles
        </p>
      </div>
      
      <form class="mt-8 space-y-6" @submit.prevent="handleLogin">
        <div class="rounded-md shadow-sm -space-y-px">
          <div>
            <label for="email" class="sr-only">Email</label>
            <input
              id="email"
              v-model="form.email"
              name="email"
              type="email"
              autocomplete="email"
              required
              class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Email"
            />
          </div>
          <div>
            <label for="password" class="sr-only">Contraseña</label>
            <input
              id="password"
              v-model="form.password"
              name="password"
              type="password"
              autocomplete="current-password"
              required
              class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Contraseña"
            />
          </div>
        </div>

        <div v-if="error" class="text-red-600 text-sm text-center">
          {{ error }}
        </div>

        <div>
          <button
            type="submit"
            :disabled="authStore.loading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="authStore.loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            </span>
            {{ authStore.loading ? 'Iniciando sesión...' : 'Iniciar Sesión' }}
          </button>
        </div>

        <!-- Demo credentials -->
        <div class="mt-6 p-4 bg-gray-100 rounded-md">
          <h3 class="text-sm font-medium text-gray-900 mb-2">Credenciales de prueba:</h3>
          <div class="text-xs text-gray-600 space-y-1">
            <div><strong>Vendedor Caja:</strong> vendedor@pos.com / password123</div>
            <div><strong>Admin:</strong> admin@pos.com / admin123</div>
          </div>
          <div class="mt-2 space-x-2">
            <button
              type="button"
              @click="fillCredentials('vendedor')"
              class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded hover:bg-blue-200"
            >
              Usar Vendedor
            </button>
            <button
              type="button"
              @click="fillCredentials('admin')"
              class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200"
            >
              Usar Admin
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  email: '',
  password: ''
})

const error = ref('')

const fillCredentials = (type: 'vendedor' | 'admin') => {
  if (type === 'vendedor') {
    form.email = 'vendedor@pos.com'
    form.password = 'password123'
  } else {
    form.email = 'admin@pos.com'
    form.password = 'admin123'
  }
}

const handleLogin = async () => {
  error.value = ''
  
  try {
    // Mock login - in real app this would call the API
    const mockLogin = async () => {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock user data based on email
      let userData
      if (form.email === 'vendedor@pos.com' && form.password === 'password123') {
        userData = {
          access_token: 'mock-token-vendedor',
          user: {
            id: '1',
            email: 'vendedor@pos.com',
            roles: ['vendedor_caja']
          }
        }
      } else if (form.email === 'admin@pos.com' && form.password === 'admin123') {
        userData = {
          access_token: 'mock-token-admin',
          user: {
            id: '2',
            email: 'admin@pos.com',
            roles: ['admin']
          }
        }
      } else {
        throw new Error('Credenciales inválidas')
      }
      
      return userData
    }

    const data = await mockLogin()
    authStore.setToken(data.access_token)
    authStore.roles = data.user.roles
    authStore.user = data.user
    authStore.profileLoaded = true

    // Redirect to intended route or default
    const redirectTo = (route.query.redirect as string) || '/pos'
    router.push(redirectTo)
    
  } catch (err: any) {
    error.value = err.message || 'Error al iniciar sesión'
  }
}
</script>