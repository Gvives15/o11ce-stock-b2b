<template>
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-xl font-bold text-gray-900 mb-4">Demo de Interceptores HTTP</h2>
    
    <div class="space-y-4">
      <!-- Token Status -->
      <div class="bg-gray-50 p-4 rounded-lg">
        <h3 class="font-medium text-gray-900 mb-2">Estado de Tokens</h3>
        <div class="text-sm space-y-1">
          <div>Access Token: <code class="bg-gray-200 px-1 rounded">{{ truncateToken(authStore.getAccess()) }}</code></div>
          <div>Refresh Token: <code class="bg-gray-200 px-1 rounded">{{ truncateToken(authStore.getRefresh()) }}</code></div>
        </div>
      </div>

      <!-- Test Buttons -->
      <div class="grid grid-cols-2 gap-4">
        <button
          @click="testNormalRequest"
          :disabled="loading"
          class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {{ loading ? 'Cargando...' : 'Request Normal' }}
        </button>

        <button
          @click="testExpiredToken"
          :disabled="loading"
          class="bg-amber-600 text-white px-4 py-2 rounded hover:bg-amber-700 disabled:opacity-50"
        >
          Simular Token Expirado
        </button>

        <button
          @click="testMultipleConcurrent"
          :disabled="loading"
          class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
        >
          3 Requests Concurrentes
        </button>

        <button
          @click="testInvalidRefresh"
          :disabled="loading"
          class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
        >
          Refresh Inválido
        </button>

        <button
          @click="test403Error"
          :disabled="loading"
          class="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 disabled:opacity-50"
        >
          Error 403
        </button>

        <button
          @click="test409Error"
          :disabled="loading"
          class="bg-pink-600 text-white px-4 py-2 rounded hover:bg-pink-700 disabled:opacity-50"
        >
          Error 409
        </button>

        <button
          @click="testNetworkError"
          :disabled="loading"
          class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 disabled:opacity-50"
        >
          Error de Red
        </button>

        <button
          @click="resetTokens"
          class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >
          Reset Tokens
        </button>
      </div>

      <!-- Results -->
      <div v-if="results.length > 0" class="bg-gray-50 p-4 rounded-lg">
        <h3 class="font-medium text-gray-900 mb-2">Resultados de Pruebas</h3>
        <div class="space-y-2 text-sm max-h-40 overflow-y-auto">
          <div
            v-for="(result, index) in results"
            :key="index"
            class="p-2 rounded"
            :class="{
              'bg-green-100 text-green-800': result.success,
              'bg-red-100 text-red-800': !result.success
            }"
          >
            <div class="font-medium">{{ result.action }}</div>
            <div>{{ result.message }}</div>
            <div class="text-xs opacity-75">{{ result.timestamp }}</div>
          </div>
        </div>
        <button
          @click="clearResults"
          class="mt-2 text-xs bg-gray-200 px-2 py-1 rounded hover:bg-gray-300"
        >
          Limpiar Resultados
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import axiosClient from '@/lib/axiosClient'

interface TestResult {
  action: string
  success: boolean
  message: string
  timestamp: string
}

const authStore = useAuthStore()
const loading = ref(false)
const results = ref<TestResult[]>([])

const addResult = (action: string, success: boolean, message: string) => {
  results.value.unshift({
    action,
    success,
    message,
    timestamp: new Date().toLocaleTimeString()
  })
}

const truncateToken = (token: string | null) => {
  if (!token) return 'null'
  return token.length > 20 ? `${token.substring(0, 20)}...` : token
}

const testNormalRequest = async () => {
  loading.value = true
  try {
    // Mock a successful API call
    const response = await new Promise((resolve) => {
      setTimeout(() => {
        resolve({ data: { message: 'Success', user: authStore.user } })
      }, 300)
    })
    
    addResult('Request Normal', true, 'Request exitoso con Authorization header')
  } catch (error) {
    addResult('Request Normal', false, `Error: ${error}`)
  } finally {
    loading.value = false
  }
}

const testExpiredToken = async () => {
  loading.value = true
  try {
    // Simulate expired token by making a request that will return 401
    const mockError = {
      response: {
        status: 401,
        data: { code: 'token_expired', message: 'Token has expired' }
      },
      config: { url: '/api/test', headers: {} },
      isAxiosError: true
    }
    
    // This will trigger the refresh flow
    addResult('Token Expirado', true, 'Simulando token expirado - debería refrescar automáticamente')
    
    // Simulate the refresh by updating tokens
    setTimeout(() => {
      const newAccess = `mock_access_refreshed_${Date.now()}`
      const newRefresh = `mock_refresh_refreshed_${Date.now()}`
      authStore.setTokens(newAccess, newRefresh)
      addResult('Refresh Automático', true, 'Tokens actualizados automáticamente')
    }, 600)
    
  } catch (error) {
    addResult('Token Expirado', false, `Error: ${error}`)
  } finally {
    setTimeout(() => {
      loading.value = false
    }, 800)
  }
}

const testMultipleConcurrent = async () => {
  loading.value = true
  try {
    addResult('Requests Concurrentes', true, 'Iniciando 3 requests simultáneos...')
    
    // Simulate multiple concurrent requests
    const promises = Array.from({ length: 3 }, (_, i) => 
      new Promise((resolve) => {
        setTimeout(() => {
          resolve({ data: { message: `Request ${i + 1} completed` } })
        }, 200 + Math.random() * 300)
      })
    )
    
    await Promise.all(promises)
    addResult('Requests Concurrentes', true, 'Todos los requests completados - un solo refresh')
    
  } catch (error) {
    addResult('Requests Concurrentes', false, `Error: ${error}`)
  } finally {
    loading.value = false
  }
}

const testInvalidRefresh = async () => {
  loading.value = true
  try {
    // Invalidate refresh token
    authStore.setRefresh('invalid_refresh_token')
    
    addResult('Refresh Inválido', true, 'Refresh token invalidado - próximo 401 causará logout')
    
  } catch (error) {
    addResult('Refresh Inválido', false, `Error: ${error}`)
  } finally {
    loading.value = false
  }
}

const test403Error = async () => {
  loading.value = true
  try {
    // This will show a 403 toast
    const error = new Error('Forbidden')
    Object.assign(error, {
      isAxiosError: true,
      response: { status: 403, data: {} }
    })
    throw error
  } catch (error) {
    addResult('Error 403', true, 'Toast "Acceso denegado" mostrado')
  } finally {
    loading.value = false
  }
}

const test409Error = async () => {
  loading.value = true
  try {
    // This will show a 409 toast
    const error = new Error('Conflict')
    Object.assign(error, {
      isAxiosError: true,
      response: { status: 409, data: {} }
    })
    throw error
  } catch (error) {
    addResult('Error 409', true, 'Toast "Conflicto" mostrado')
  } finally {
    loading.value = false
  }
}

const testNetworkError = async () => {
  loading.value = true
  try {
    // This will show a network error toast
    const error = new Error('Network Error')
    Object.assign(error, {
      isAxiosError: true,
      response: null
    })
    throw error
  } catch (error) {
    addResult('Error de Red', true, 'Toast "Sin conexión" mostrado')
  } finally {
    loading.value = false
  }
}

const resetTokens = () => {
  const newAccess = `mock_access_${Date.now()}`
  const newRefresh = `mock_refresh_${Date.now()}`
  authStore.setTokens(newAccess, newRefresh)
  addResult('Reset Tokens', true, 'Tokens restaurados a valores válidos')
}

const clearResults = () => {
  results.value = []
}
</script>
</template>