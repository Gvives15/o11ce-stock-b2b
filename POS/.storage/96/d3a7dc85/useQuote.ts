import { ref, computed, watch } from 'vue'
import { debounce } from 'lodash-es'
import axiosClient from '@/lib/axiosClient'
import { showErrorToast } from '@/lib/errorToast'

interface CartItem {
  id: string
  name: string
  sku: string
  price: number
  quantity: number
  unit: 'unit' | 'package'
  packageSize?: number
}

interface Customer {
  id: string
  name: string
  segment: 'retail' | 'wholesale'
}

interface ComboDiscount {
  id: string
  name: string
  amount: number
  description: string
}

interface QuoteResponse {
  subtotal: number
  discounts_total: number
  total: number
  combo_discounts: ComboDiscount[]
  tax_amount: number
  currency: string
}

interface QuoteRequest {
  customer_id: string
  items: Array<{
    product_id: string
    quantity: number
    unit: string
  }>
}

export function useQuote() {
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastValidQuote = ref<QuoteResponse | null>(null)
  const abortController = ref<AbortController | null>(null)
  
  // Cache for 5 seconds
  const cache = ref<Map<string, { quote: QuoteResponse, timestamp: number }>>(new Map())
  const CACHE_DURATION = 5000 // 5 seconds

  const quote = computed(() => lastValidQuote.value)

  // Generate cache key from request payload
  const getCacheKey = (request: QuoteRequest): string => {
    return JSON.stringify({
      customer_id: request.customer_id,
      items: request.items.sort((a, b) => a.product_id.localeCompare(b.product_id))
    })
  }

  // Check if cached quote is still valid
  const getCachedQuote = (key: string): QuoteResponse | null => {
    const cached = cache.value.get(key)
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return cached.quote
    }
    return null
  }

  // Store quote in cache
  const setCachedQuote = (key: string, quoteData: QuoteResponse) => {
    cache.value.set(key, {
      quote: quoteData,
      timestamp: Date.now()
    })
  }

  // Clear expired cache entries
  const cleanCache = () => {
    const now = Date.now()
    for (const [key, value] of cache.value.entries()) {
      if (now - value.timestamp >= CACHE_DURATION) {
        cache.value.delete(key)
      }
    }
  }

  const fetchQuote = async (customer: Customer, items: CartItem[]): Promise<void> => {
    if (items.length === 0) {
      lastValidQuote.value = null
      error.value = null
      return
    }

    const request: QuoteRequest = {
      customer_id: customer.id,
      items: items.map(item => ({
        product_id: item.id,
        quantity: item.quantity,
        unit: item.unit
      }))
    }

    const cacheKey = getCacheKey(request)
    
    // Check cache first
    const cachedQuote = getCachedQuote(cacheKey)
    if (cachedQuote) {
      lastValidQuote.value = cachedQuote
      error.value = null
      return
    }

    // Abort previous request if exists
    if (abortController.value) {
      abortController.value.abort()
    }

    abortController.value = new AbortController()
    isLoading.value = true
    error.value = null

    try {
      // Mock API call - in real app, this would be actual API
      const mockQuote = await new Promise<QuoteResponse>((resolve, reject) => {
        const timeout = setTimeout(() => {
          // Calculate mock totals
          const subtotal = items.reduce((sum, item) => {
            const unitPrice = item.unit === 'package' && item.packageSize 
              ? item.price * item.packageSize 
              : item.price
            return sum + (unitPrice * item.quantity)
          }, 0)

          // Apply segment-based pricing
          const segmentMultiplier = customer.segment === 'wholesale' ? 0.9 : 1.0
          const adjustedSubtotal = subtotal * segmentMultiplier

          // Mock combo discounts
          const comboDiscounts: ComboDiscount[] = []
          let discountsTotal = 0

          // Check for fuel + lubricant combo
          const hasFuel = items.some(item => item.name.toLowerCase().includes('gasolina'))
          const hasLubricant = items.some(item => item.name.toLowerCase().includes('aceite'))
          
          if (hasFuel && hasLubricant) {
            const comboDiscount = {
              id: 'fuel-lubricant',
              name: 'Combo Combustible + Aceite',
              amount: 5.00,
              description: 'Descuento por compra combinada'
            }
            comboDiscounts.push(comboDiscount)
            discountsTotal += comboDiscount.amount
          }

          const taxAmount = (adjustedSubtotal - discountsTotal) * 0.21 // 21% IVA
          const total = adjustedSubtotal - discountsTotal + taxAmount

          resolve({
            subtotal: adjustedSubtotal,
            discounts_total: discountsTotal,
            total,
            combo_discounts: comboDiscounts,
            tax_amount: taxAmount,
            currency: 'USD'
          })
        }, 300) // Simulate API delay

        // Handle abort
        abortController.value?.signal.addEventListener('abort', () => {
          clearTimeout(timeout)
          reject(new Error('Request aborted'))
        })
      })

      // Cache the successful quote
      setCachedQuote(cacheKey, mockQuote)
      lastValidQuote.value = mockQuote
      error.value = null

    } catch (err: any) {
      if (err.name !== 'AbortError' && err.message !== 'Request aborted') {
        error.value = 'No pudimos calcular los totales. Probá de nuevo.'
        showErrorToast(err)
        
        // Keep last valid quote as fallback
        if (!lastValidQuote.value) {
          // If no previous quote, show basic calculation
          const basicSubtotal = items.reduce((sum, item) => sum + (item.price * item.quantity), 0)
          lastValidQuote.value = {
            subtotal: basicSubtotal,
            discounts_total: 0,
            total: basicSubtotal * 1.21, // Add basic tax
            combo_discounts: [],
            tax_amount: basicSubtotal * 0.21,
            currency: 'USD'
          }
        }
      }
    } finally {
      isLoading.value = false
      abortController.value = null
      cleanCache()
    }
  }

  // Debounced quote function (350ms as per UX requirements)
  const debouncedFetchQuote = debounce(fetchQuote, 350)

  // Auto-cleanup on unmount
  const cleanup = () => {
    if (abortController.value) {
      abortController.value.abort()
    }
    cache.value.clear()
  }

  return {
    quote,
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),
    fetchQuote: debouncedFetchQuote,
    fetchQuoteImmediate: fetchQuote,
    cleanup
  }
}