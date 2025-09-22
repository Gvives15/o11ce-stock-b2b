import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { 
  isCurrentlyRefreshing, 
  setRefreshing, 
  enqueue, 
  resolveAll, 
  clearQueue,
  getQueueLength 
} from '../authRefresh'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

// Mock auth store
vi.mock('@/stores/auth')
const mockedUseAuthStore = vi.mocked(useAuthStore)

// Mock toast
vi.mock('../errorToast', () => ({
  showErrorToast: vi.fn(),
  showToast: vi.fn()
}))

describe('Auth Refresh Queue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setRefreshing(false)
    clearQueue()
  })

  afterEach(() => {
    clearQueue()
    setRefreshing(false)
  })

  it('should handle single token refresh correctly', async () => {
    // Setup
    const mockCallback = vi.fn()
    const testToken = 'new-token-123'
    
    // Test enqueue
    enqueue(mockCallback)
    expect(getQueueLength()).toBe(1)
    
    // Test resolve all
    resolveAll(testToken)
    expect(mockCallback).toHaveBeenCalledWith(testToken)
    expect(getQueueLength()).toBe(0)
  })

  it('should handle multiple concurrent requests', async () => {
    // Setup
    const mockCallback1 = vi.fn()
    const mockCallback2 = vi.fn()
    const mockCallback3 = vi.fn()
    const testToken = 'new-token-456'
    
    // Simulate concurrent requests
    enqueue(mockCallback1)
    enqueue(mockCallback2)
    enqueue(mockCallback3)
    
    expect(getQueueLength()).toBe(3)
    
    // Resolve all at once
    resolveAll(testToken)
    
    expect(mockCallback1).toHaveBeenCalledWith(testToken)
    expect(mockCallback2).toHaveBeenCalledWith(testToken)
    expect(mockCallback3).toHaveBeenCalledWith(testToken)
    expect(getQueueLength()).toBe(0)
  })

  it('should manage refreshing state correctly', () => {
    expect(isCurrentlyRefreshing()).toBe(false)
    
    setRefreshing(true)
    expect(isCurrentlyRefreshing()).toBe(true)
    
    setRefreshing(false)
    expect(isCurrentlyRefreshing()).toBe(false)
  })

  it('should clear queue when needed', () => {
    const mockCallback1 = vi.fn()
    const mockCallback2 = vi.fn()
    
    enqueue(mockCallback1)
    enqueue(mockCallback2)
    expect(getQueueLength()).toBe(2)
    
    clearQueue()
    expect(getQueueLength()).toBe(0)
  })
})

describe('Error Mapping', () => {
  it('should map HTTP status codes to user-friendly messages', () => {
    const { mapErrorToMessage } = require('../errorToast')
    
    // Mock axios errors
    const create401Error = () => ({
      isAxiosError: true,
      response: { status: 401, data: {} }
    })
    
    const create403Error = () => ({
      isAxiosError: true,
      response: { status: 403, data: {} }
    })
    
    const create409Error = () => ({
      isAxiosError: true,
      response: { status: 409, data: {} }
    })
    
    const createNetworkError = () => ({
      isAxiosError: true,
      response: null
    })
    
    expect(mapErrorToMessage(create401Error())).toBe('Credenciales inválidas')
    expect(mapErrorToMessage(create403Error())).toBe('Acceso denegado')
    expect(mapErrorToMessage(create409Error())).toBe('Conflicto - No se pudo completar la acción')
    expect(mapErrorToMessage(createNetworkError())).toBe('Sin conexión a internet')
  })
})