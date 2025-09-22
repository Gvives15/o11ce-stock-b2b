import { ref } from 'vue'
import { showErrorToast } from '@/lib/errorToast'
import type { Payment } from '@/stores/payments'

export interface CheckoutItem {
  product_id: string
  qty: number
  unit: string
}

export interface CheckoutRequest {
  customer_id: string
  items: CheckoutItem[]
  payments: Array<{
    method: string
    amount: number
  }>
}

export interface CheckoutTotals {
  subtotal: number
  discounts: number
  total: number
  paid: number
  change: number
}

export interface CheckoutReceipt {
  number: string
  print_url: string
}

export interface CheckoutSuccessResponse {
  order_id: number
  status: string
  totals: CheckoutTotals
  receipt: CheckoutReceipt
}

export interface StockMissing {
  product_id: string
  requested: number
  available: number
}

export interface CheckoutStockError {
  error: 'OUT_OF_STOCK'
  missing: StockMissing[]
  message: string
}

export interface CheckoutResult {
  ok: boolean
  data?: CheckoutSuccessResponse
  missing?: StockMissing[]
  error?: string
  isStockError?: boolean
  isNetworkError?: boolean
}

export function useCheckout() {
  const isLoading = ref(false)
  const lastError = ref<string | null>(null)
  const abortController = ref<AbortController | null>(null)

  const checkout = async (params: {
    customerId: string
    items: CheckoutItem[]
    payments: Payment[]
    idempotencyKey: string
  }): Promise<CheckoutResult> => {
    
    // Abort previous request if exists
    if (abortController.value) {
      abortController.value.abort()
    }

    abortController.value = new AbortController()
    isLoading.value = true
    lastError.value = null

    try {
      const request: CheckoutRequest = {
        customer_id: params.customerId,
        items: params.items,
        payments: params.payments.map(p => ({
          method: p.method,
          amount: p.amount
        }))
      }

      console.log('Checkout request:', {
        idempotencyKey: params.idempotencyKey,
        request
      })

      // Mock API call - in real app, this would be actual API
      const response = await mockCheckoutAPI(request, params.idempotencyKey, abortController.value.signal)

      if (response.status === 201) {
        console.log('Checkout successful:', response.data)
        return {
          ok: true,
          data: response.data
        }
      } else if (response.status === 409) {
        console.log('Stock error:', response.data)
        return {
          ok: false,
          missing: response.data.missing,
          error: response.data.message,
          isStockError: true
        }
      } else {
        throw new Error(`Unexpected response status: ${response.status}`)
      }

    } catch (err: any) {
      console.error('Checkout error:', err)
      
      if (err.name === 'AbortError') {
        return {
          ok: false,
          error: 'Request cancelled'
        }
      }

      const isNetworkError = err.code === 'NETWORK_ERROR' || err.message?.includes('fetch')
      lastError.value = err.message || 'Error desconocido en checkout'
      
      if (isNetworkError) {
        showErrorToast(new Error('No se pudo cobrar. Revisá conexión e intentá de nuevo.'))
      } else {
        showErrorToast(err)
      }

      return {
        ok: false,
        error: lastError.value,
        isNetworkError
      }
    } finally {
      isLoading.value = false
      abortController.value = null
    }
  }

  const cleanup = () => {
    if (abortController.value) {
      abortController.value.abort()
    }
  }

  return {
    isLoading,
    lastError,
    checkout,
    cleanup
  }
}

// Mock API implementation
async function mockCheckoutAPI(
  request: CheckoutRequest, 
  idempotencyKey: string, 
  signal: AbortSignal
): Promise<{ status: number; data: any }> {
  
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      // Check for idempotency (same key returns same result)
      const storedResult = localStorage.getItem(`checkout_${idempotencyKey}`)
      if (storedResult) {
        console.log('Returning cached result for idempotency key:', idempotencyKey)
        resolve(JSON.parse(storedResult))
        return
      }

      // Mock stock validation
      const mockStock: Record<string, number> = {
        '1': 3, // Gasolina Premium has only 3 units available
        '2': 10,
        '3': 15,
        '4': 8,
        '5': 12
      }

      // Check for stock issues
      const missing: StockMissing[] = []
      for (const item of request.items) {
        const available = mockStock[item.product_id] || 0
        if (item.qty > available) {
          missing.push({
            product_id: item.product_id,
            requested: item.qty,
            available
          })
        }
      }

      if (missing.length > 0) {
        const result = {
          status: 409,
          data: {
            error: 'OUT_OF_STOCK',
            missing,
            message: 'No hay stock suficiente para algunos ítems'
          }
        }
        resolve(result)
        return
      }

      // Calculate totals (simplified)
      const subtotal = request.items.reduce((sum, item) => {
        const price = item.product_id === '1' ? 1.45 : 
                     item.product_id === '2' ? 1.35 :
                     item.product_id === '4' ? 25.99 : 22.99
        return sum + (price * item.qty)
      }, 0)

      const discounts = 5.00 // Mock combo discount
      const total = subtotal - discounts
      const paid = request.payments.reduce((sum, p) => sum + p.amount, 0)
      const change = paid - total

      const orderId = Math.floor(Math.random() * 1000) + 100
      const receiptNumber = `A-0001-${String(orderId).padStart(7, '0')}`

      const successResult = {
        status: 201,
        data: {
          order_id: orderId,
          status: 'placed',
          totals: {
            subtotal: Math.round(subtotal * 100) / 100,
            discounts: Math.round(discounts * 100) / 100,
            total: Math.round(total * 100) / 100,
            paid: Math.round(paid * 100) / 100,
            change: Math.round(change * 100) / 100
          },
          receipt: {
            number: receiptNumber,
            print_url: `/pos/receipt/${orderId}`
          }
        }
      }

      // Store for idempotency
      localStorage.setItem(`checkout_${idempotencyKey}`, JSON.stringify(successResult))
      
      resolve(successResult)
    }, 800) // Simulate API delay

    // Handle abort
    signal.addEventListener('abort', () => {
      clearTimeout(timeout)
      reject(new Error('Request aborted'))
    })
  })
}