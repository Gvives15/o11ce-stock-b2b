import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import axiosClient from '@/lib/axiosClient'

interface UserScopes {
  has_scope_users: boolean
  has_scope_dashboard: boolean
  has_scope_inventory: boolean
  has_scope_inventory_level_1: boolean
  has_scope_inventory_level_2: boolean
  has_scope_orders: boolean
  has_scope_customers: boolean
  has_scope_reports: boolean
  has_scope_analytics: boolean
  has_scope_catalog: boolean
  has_scope_caja: boolean
  has_scope_pos_override: boolean
}

interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  date_joined: string
  last_login: string | null
  scopes: UserScopes
  roles: string[]
}

interface LoginCredentials {
  username: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const userRoles = computed(() => user.value?.roles || [])

  // Función para establecer tokens
  const setTokens = (access: string, refresh: string) => {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  // Login real con /auth/login
  const login = async (username: string, password: string) => {
    isLoading.value = true
    try {
      const authBaseURL = import.meta.env.VITE_AUTH_BASE_URL || 'http://localhost/api'
      const response = await axios.post(`${authBaseURL}/auth/login/`, {
        username,
        password
      })

      const { access, refresh } = response.data
      setTokens(access, refresh)

      // Cargar perfil del usuario después del login
      await loadProfile()

      return true
    } catch (error: any) {
      // Limpiar tokens en caso de error
      logout()
      
      if (error.response?.status === 400 || error.response?.status === 401) {
        throw new Error('Usuario o clave inválidos')
      }
      throw new Error('Error al iniciar sesión')
    } finally {
      isLoading.value = false
    }
  }

  // Cargar perfil del usuario con /auth/me
  const loadProfile = async () => {
    try {
      const authBaseURL = import.meta.env.VITE_AUTH_BASE_URL || 'http://localhost/api'
      const token = localStorage.getItem('access_token')
      const response = await axios.get(`${authBaseURL}/auth/me/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      })
      user.value = response.data
      localStorage.setItem('user_data', JSON.stringify(response.data))
      return true
    } catch (error) {
      logout()
      return false
    }
  }

  const logout = () => {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_data')
  }

  const checkAuth = async () => {
    if (!accessToken.value) return false
    return await loadProfile()
  }

  const hasRole = (requiredRole: string | string[]) => {
    if (!user.value?.roles) return false
    
    if (Array.isArray(requiredRole)) {
      return requiredRole.some(role => user.value!.roles.includes(role))
    }
    
    return user.value.roles.includes(requiredRole)
  }

  const hasScope = (requiredScope: string | string[]) => {
    if (!user.value?.scopes) return false
    
    if (Array.isArray(requiredScope)) {
      return requiredScope.some(scope => user.value!.scopes[scope as keyof UserScopes])
    }
    
    return user.value.scopes[requiredScope as keyof UserScopes]
  }

  return {
    user,
    accessToken,
    refreshToken,
    isLoading,
    isAuthenticated,
    userRoles,
    setTokens,
    login,
    logout,
    loadProfile,
    checkAuth,
    hasRole,
    hasScope
  }
})