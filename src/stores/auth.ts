import { defineStore } from 'pinia'
import axios from '@/lib/axiosClient'

export interface User {
  id: string
  email: string
  roles: string[]
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    tokenAccess: null as string | null,
    roles: [] as string[],
    profileLoaded: false,
    user: null as User | null,
    loading: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.tokenAccess,
    hasRole: (state) => (role: string) => state.roles.includes(role),
    hasAnyRole: (state) => (roles: string[]) => roles.some(role => state.roles.includes(role)),
    isAdmin: (state) => state.roles.includes('admin'),
    isVendedorCaja: (state) => state.roles.includes('vendedor_caja'),
    isVendedorRuta: (state) => state.roles.includes('vendedor_ruta')
  },

  actions: {
    setToken(token: string) {
      this.tokenAccess = token
      localStorage.setItem('access_token', token)
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    },

    async loadProfile() {
      if (!this.tokenAccess) {
        this.roles = []
        this.user = null
        this.profileLoaded = true
        return
      }

      this.loading = true
      try {
        const { data } = await axios.get('/auth/me')
        this.roles = data.roles || []
        this.user = data
        this.profileLoaded = true
      } catch (error) {
        console.error('Error loading profile:', error)
        // If profile loading fails, clear auth state
        this.logout()
        throw error
      } finally {
        this.loading = false
      }
    },

    async login(email: string, password: string) {
      this.loading = true
      try {
        const { data } = await axios.post('/auth/login', { email, password })
        this.setToken(data.access_token)
        await this.loadProfile()
        return data
      } catch (error) {
        console.error('Login error:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    logout() {
      this.tokenAccess = null
      this.roles = []
      this.user = null
      this.profileLoaded = false
      localStorage.removeItem('access_token')
      delete axios.defaults.headers.common['Authorization']
    }
  }
})