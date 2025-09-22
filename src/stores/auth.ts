import { defineStore } from 'pinia'

interface User {
  id: string
  email: string
  name: string
  roles: string[]
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    isAuthenticated: false
  }),

  getters: {
    roles: (state) => state.user?.roles || [],
    isAdmin: (state) => state.user?.roles.includes('admin') || false,
    isVendedor: (state) => state.user?.roles.includes('vendedor_caja') || false
  },

  actions: {
    // Token management methods
    getAccess(): string | null {
      return this.accessToken
    },

    getRefresh(): string | null {
      return this.refreshToken
    },

    setToken(access: string) {
      this.accessToken = access
      localStorage.setItem('access_token', access)
    },

    setRefresh(refresh?: string) {
      if (refresh) {
        this.refreshToken = refresh
        localStorage.setItem('refresh_token', refresh)
      }
    },

    setTokens(access: string, refresh?: string) {
      this.setToken(access)
      if (refresh) {
        this.setRefresh(refresh)
      }
    },

    async login(email: string, password: string) {
      // Mock authentication - in real app, this would be an API call
      const mockUsers = {
        'vendedor@pos.com': {
          id: '1',
          email: 'vendedor@pos.com',
          name: 'Vendedor POS',
          roles: ['vendedor_caja']
        },
        'admin@pos.com': {
          id: '2',
          email: 'admin@pos.com',
          name: 'Administrador',
          roles: ['admin', 'vendedor_caja']
        }
      }

      const user = mockUsers[email as keyof typeof mockUsers]
      
      if (!user || password !== (email.includes('admin') ? 'admin123' : 'password123')) {
        throw new Error('Credenciales inválidas')
      }

      // Mock tokens
      const mockAccessToken = `mock_access_${Date.now()}`
      const mockRefreshToken = `mock_refresh_${Date.now()}`

      this.user = user
      this.setTokens(mockAccessToken, mockRefreshToken)
      this.isAuthenticated = true

      return { user, access: mockAccessToken, refresh: mockRefreshToken }
    },

    async loadProfile() {
      if (!this.accessToken) {
        throw new Error('No access token')
      }

      // Mock profile loading - in real app, this would be an API call
      // For now, decode user from stored token or use existing user
      if (!this.user && this.accessToken) {
        // Mock user based on token
        const isAdmin = this.accessToken.includes('admin')
        this.user = isAdmin ? {
          id: '2',
          email: 'admin@pos.com',
          name: 'Administrador',
          roles: ['admin', 'vendedor_caja']
        } : {
          id: '1',
          email: 'vendedor@pos.com',
          name: 'Vendedor POS',
          roles: ['vendedor_caja']
        }
      }
      
      this.isAuthenticated = true
      return this.user
    },

    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      this.isAuthenticated = false
      
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },

    // Initialize auth state from localStorage
    initializeAuth() {
      const token = localStorage.getItem('access_token')
      const refresh = localStorage.getItem('refresh_token')
      
      if (token) {
        this.accessToken = token
        this.refreshToken = refresh
        // Profile will be loaded by router guard
      }
    }
  }
})