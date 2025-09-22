import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { 
  isCurrentlyRefreshing, 
  setRefreshing, 
  enqueue, 
  resolveAll, 
  clearQueue 
} from './authRefresh'
import { showErrorToast } from './errorToast'

const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - Add Authorization header
axiosClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    const token = authStore.getAccess()
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle 401 and refresh token
axiosClient.interceptors.response.use(
  (response) => {
    return response
  },
  async (error: AxiosError) => {
    const authStore = useAuthStore()
    const originalRequest = error.config as InternalAxiosRequestConfig & { __isRetry?: boolean }
    
    // Skip refresh logic for auth endpoints and already retried requests
    if (
      !originalRequest ||
      originalRequest.url?.includes('/auth/refresh') ||
      originalRequest.__isRetry
    ) {
      // Show error toast for non-refresh failures
      if (!originalRequest?.url?.includes('/auth/refresh')) {
        showErrorToast(error)
      }
      return Promise.reject(error)
    }
    
    // Handle 401 token expired
    if (error.response?.status === 401) {
      const errorData = error.response.data as any
      const isTokenExpired = errorData?.code === 'token_expired' || 
                            errorData?.message?.includes('token') ||
                            errorData?.message?.includes('expired')
      
      if (isTokenExpired && authStore.getRefresh()) {
        // If already refreshing, queue this request
        if (isCurrentlyRefreshing()) {
          return new Promise((resolve) => {
            enqueue((newToken: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`
              }
              originalRequest.__isRetry = true
              resolve(axiosClient(originalRequest))
            })
          })
        }
        
        // Start refresh process
        setRefreshing(true)
        
        try {
          // Mock refresh token call - in real app, this would be actual API
          const refreshToken = authStore.getRefresh()
          
          // Simulate refresh API call
          const mockRefreshResponse = await new Promise<{access: string, refresh?: string}>((resolve, reject) => {
            setTimeout(() => {
              // Mock success/failure based on refresh token validity
              if (refreshToken && refreshToken.includes('mock_refresh')) {
                const newAccess = `mock_access_refreshed_${Date.now()}`
                const newRefresh = `mock_refresh_refreshed_${Date.now()}`
                resolve({ access: newAccess, refresh: newRefresh })
              } else {
                reject(new Error('Invalid refresh token'))
              }
            }, 500) // Simulate network delay
          })
          
          // Update tokens
          authStore.setTokens(mockRefreshResponse.access, mockRefreshResponse.refresh)
          
          // Resolve all pending requests
          resolveAll(mockRefreshResponse.access)
          
          // Retry original request
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${mockRefreshResponse.access}`
          }
          originalRequest.__isRetry = true
          
          return axiosClient(originalRequest)
          
        } catch (refreshError) {
          // Refresh failed - logout user
          clearQueue()
          authStore.logout()
          
          // Dispatch custom event for router to handle
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('auth:logout'))
          }
          
          return Promise.reject(refreshError)
        } finally {
          setRefreshing(false)
        }
      }
    }
    
    // Show error toast for other errors (except auth failures handled above)
    if (error.response?.status !== 401) {
      showErrorToast(error)
    }
    return Promise.reject(error)
  }
)

export default axiosClient