<template>
  <div class="flex flex-col h-full bg-gray-50">
    <!-- Sticky Header: Customer + SearchBar -->
    <div class="sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm">
      <div class="p-4">
        <!-- Customer Selection -->
        <div class="mb-4">
          <CustomerPicker
            v-model="selectedCustomer"
            @customer-changed="handleCustomerChange"
          />
        </div>
        
        <!-- Search Bar -->
        <SearchBar
          @add-item="handleAddItem"
          @search-performed="handleSearchMetrics"
        />
      </div>
    </div>

    <!-- Main Content: 2-Zone Layout -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Left Zone: Input (Categories & Products) -->
      <div class="flex-1 p-6 overflow-y-auto">
        <div class="max-w-4xl">
          <h2 class="text-xl font-semibold text-gray-900 mb-6">Categorías de Productos</h2>
          
          <!-- Category Grid -->
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            <button
              v-for="category in categories"
              :key="category.id"
              @click="selectCategory(category)"
              class="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-center focus:outline-none focus:ring-2 focus:ring-blue-500"
              :class="{
                'border-blue-500 bg-blue-50': selectedCategory?.id === category.id
              }"
            >
              <div class="text-2xl mb-2">{{ category.icon }}</div>
              <div class="text-sm font-medium text-gray-900">{{ category.name }}</div>
              <div class="text-xs text-gray-500">{{ category.count }} productos</div>
            </button>
          </div>

          <!-- Products in Selected Category -->
          <div v-if="selectedCategory" class="space-y-4">
            <h3 class="text-lg font-medium text-gray-900">{{ selectedCategory.name }}</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <button
                v-for="product in categoryProducts"
                :key="product.id"
                @click="addToCart(product)"
                class="p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-md transition-all text-left focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex-1 min-w-0">
                    <h4 class="font-medium text-gray-900 truncate">{{ product.name }}</h4>
                    <p class="text-xs text-gray-500 mt-1">{{ product.sku }}</p>
                  </div>
                  <span class="text-lg font-bold text-blue-600 ml-2">${{ product.price.toFixed(2) }}</span>
                </div>
                <div class="text-sm text-gray-500">
                  Stock: {{ product.stock }} {{ product.unit }}
                  <span v-if="product.packageSize" class="ml-2 text-xs bg-blue-100 text-blue-800 px-1 rounded">
                    PACK×{{ product.packageSize }}
                  </span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Zone: Execution (Cart + Payments + Totals) -->
      <div class="w-96 bg-white border-l border-gray-200 flex flex-col">
        <!-- Cart Component -->
        <div class="flex-1 overflow-hidden">
          <Cart
            :items="cartWithStockErrors"
            @update-quantity="updateQuantity"
            @update-unit="updateUnit"
            @remove-item="removeFromCart"
          />
        </div>

        <!-- Payments Panel -->
        <PaymentsPanel
          :total="quote?.total || 0"
          :allow-c-c="selectedCustomer?.segment === 'wholesale'"
          @validity-changed="handlePaymentValidityChanged"
        />

        <!-- Totals Panel -->
        <TotalsPanel
          :quote="quote"
          :is-loading="isQuoteLoading"
          :error="quoteError"
        />

        <!-- Sticky Footer: Checkout Button -->
        <div class="border-t border-gray-200 p-4 bg-gray-50">
          <button
            @click="processCheckout"
            :disabled="!canCheckout"
            :title="checkoutBlockReason || ''"
            class="w-full py-3 px-4 rounded-lg font-semibold text-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 min-h-[44px]"
            :class="canCheckout 
              ? 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500' 
              : 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-50'"
          >
            <span v-if="saleStore.isProcessing" class="flex items-center justify-center space-x-2">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Procesando...</span>
            </span>
            <span v-else>
              {{ canCheckout ? `Cobrar $${(quote?.total || 0).toFixed(2)}` : (checkoutBlockReason || 'No Disponible') }}
            </span>
          </button>

          <!-- Clear Cart -->
          <button
            v-if="cart.length > 0 && !saleStore.isProcessing"
            @click="clearCart"
            class="w-full mt-2 py-2 px-4 text-sm text-gray-600 hover:text-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 rounded"
          >
            Limpiar Carrito
          </button>

          <!-- Auto-adjust stock button -->
          <button
            v-if="hasStockErrors && !saleStore.isProcessing"
            @click="autoAdjustStock"
            class="w-full mt-2 py-2 px-4 text-sm bg-orange-100 text-orange-800 hover:bg-orange-200 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 rounded font-medium"
          >
            Ajustar Automáticamente
          </button>
        </div>
      </div>
    </div>

    <!-- Checkout Success Modal -->
    <CheckoutSuccessModal
      :show="showSuccessModal"
      :totals="lastCheckoutResult?.totals || null"
      :receipt="lastCheckoutResult?.receipt || null"
      :payments-used="lastPaymentsUsed"
      @close="closeSuccessModal"
      @new-sale="startNewSale"
      @print="handlePrintReceipt"
    />

    <!-- Network Retry Toast -->
    <div
      v-if="showRetryToast"
      class="fixed top-4 right-4 z-50 bg-yellow-600 text-white px-4 py-3 rounded-lg shadow-lg max-w-sm"
    >
      <div class="flex items-center space-x-2">
        <svg class="w-5 h-5 text-yellow-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.728-.833-2.498 0L4.316 15.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        <div>
          <div class="font-medium">Reintentando pago...</div>
          <div class="text-sm text-yellow-200">Conexión restaurada</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useBlockers } from '@/composables/useBlockers'
import { useQuote } from '@/composables/useQuote'
import { useCheckout } from '@/composables/useCheckout'
import { usePaymentsStore } from '@/stores/payments'
import { useSaleStore } from '@/stores/sale'
import SearchBar from '@/components/SearchBar.vue'
import CustomerPicker from '@/components/CustomerPicker.vue'
import Cart from '@/components/Cart.vue'
import TotalsPanel from '@/components/TotalsPanel.vue'
import PaymentsPanel from '@/components/PaymentsPanel.vue'
import CheckoutSuccessModal from '@/components/CheckoutSuccessModal.vue'
import type { CheckoutSuccessResponse, StockMissing } from '@/composables/useCheckout'
import type { Payment } from '@/stores/payments'

interface Product {
  id: string
  name: string
  sku: string
  price: number
  category: string
  stock: number
  unit: string
  packageSize?: number
}

interface CartItem extends Product {
  quantity: number
  unit: 'unit' | 'package'
  hasStockError?: boolean
  availableStock?: number
}

interface Customer {
  id: string
  name: string
  segment: 'retail' | 'wholesale'
  email?: string
  taxId?: string
}

interface Category {
  id: string
  name: string
  icon: string
  count: number
}

interface AddItemEvent {
  product: Product
  unit: string
}

// Composables
const { canCheckout: blockersCanCheckout, checkoutBlockReason: blockersReason } = useBlockers()
const { quote, isLoading: isQuoteLoading, error: quoteError, fetchQuote, cleanup: cleanupQuote } = useQuote()
const { checkout, isLoading: isCheckoutLoading } = useCheckout()
const paymentsStore = usePaymentsStore()
const saleStore = useSaleStore()

// Reactive state
const cart = ref<CartItem[]>([])
const selectedCategory = ref<Category | null>(null)
const selectedCustomer = ref<Customer | null>(null)
const stockErrors = ref<StockMissing[]>([])
const paymentValidation = ref({ ok: false, change: 0 })
const showSuccessModal = ref(false)
const lastCheckoutResult = ref<CheckoutSuccessResponse | null>(null)
const lastPaymentsUsed = ref<Payment[]>([])
const showRetryToast = ref(false)
const pendingRetry = ref(false)

// Mock data
const categories: Category[] = [
  { id: 'fuel', name: 'Combustibles', icon: '⛽', count: 5 },
  { id: 'lubricants', name: 'Lubricantes', icon: '🛢️', count: 8 },
  { id: 'beverages', name: 'Bebidas', icon: '🥤', count: 12 },
  { id: 'snacks', name: 'Snacks', icon: '🍿', count: 15 },
  { id: 'automotive', name: 'Automotriz', icon: '🔧', count: 6 },
  { id: 'services', name: 'Servicios', icon: '🔧', count: 3 }
]

const mockProducts: Record<string, Product[]> = {
  fuel: [
    { id: '1', name: 'Gasolina Premium 95', sku: 'GAS500', price: 1.45, category: 'Combustibles', stock: 3, unit: 'litro' },
    { id: '2', name: 'Gasolina Regular 87', sku: 'GAS400', price: 1.35, category: 'Combustibles', stock: 1500, unit: 'litro' },
    { id: '3', name: 'Gasóleo Diesel', sku: 'DIE001', price: 1.25, category: 'Combustibles', stock: 800, unit: 'litro' }
  ],
  lubricants: [
    { id: '4', name: 'Aceite Motor 5W-30', sku: 'ACE530', price: 25.99, category: 'Lubricantes', stock: 50, unit: 'botella', packageSize: 12 },
    { id: '5', name: 'Aceite Motor 10W-40', sku: 'ACE1040', price: 22.99, category: 'Lubricantes', stock: 45, unit: 'botella', packageSize: 12 }
  ],
  beverages: [
    { id: '6', name: 'Coca Cola 500ml', sku: 'COC500', price: 2.50, category: 'Bebidas', stock: 120, unit: 'unidad', packageSize: 24 },
    { id: '7', name: 'Agua Mineral 1L', sku: 'AGU001', price: 1.25, category: 'Bebidas', stock: 200, unit: 'unidad', packageSize: 12 }
  ]
}

// Computed
const categoryProducts = computed(() => {
  if (!selectedCategory.value) return []
  return mockProducts[selectedCategory.value.id] || []
})

const cartWithStockErrors = computed(() => {
  return cart.value.map(item => ({
    ...item,
    hasStockError: stockErrors.value.some(error => error.product_id === item.id),
    availableStock: stockErrors.value.find(error => error.product_id === item.id)?.available
  }))
})

const hasStockErrors = computed(() => stockErrors.value.length > 0)

const canCheckout = computed(() => {
  return blockersCanCheckout.value && 
         paymentValidation.value.ok && 
         cart.value.length > 0 && 
         !saleStore.isProcessing &&
         !hasStockErrors.value
})

const checkoutBlockReason = computed(() => {
  if (!blockersCanCheckout.value) return blockersReason.value
  if (cart.value.length === 0) return 'Carrito vacío'
  if (hasStockErrors.value) return 'Ajustá cantidades sin stock'
  if (!paymentValidation.value.ok) return paymentValidation.value.error || 'Completá los pagos'
  if (saleStore.isProcessing) return 'Procesando...'
  return null
})

// Watch for cart or customer changes to trigger quote
watch([cart, selectedCustomer], () => {
  if (selectedCustomer.value && cart.value.length > 0) {
    fetchQuote(selectedCustomer.value, cart.value)
  }
  // Clear stock errors when cart changes
  stockErrors.value = []
}, { deep: true })

// Methods
const selectCategory = (category: Category) => {
  selectedCategory.value = selectedCategory.value?.id === category.id ? null : category
}

const handleCustomerChange = (customer: Customer | null) => {
  selectedCustomer.value = customer
  saleStore.setCustomerId(customer?.id || null)
  
  // Trigger immediate re-quote if cart has items
  if (customer && cart.value.length > 0) {
    fetchQuote(customer, cart.value)
  }
}

const handleAddItem = (event: AddItemEvent) => {
  addToCart(event.product, 1, event.unit as 'unit' | 'package')
  
  // Emit metrics
  console.log('Item added:', {
    product_id: event.product.id,
    unit: event.unit
  })
}

const handleSearchMetrics = (query: string, resultsCount: number, ms: number) => {
  console.log('Search performed:', {
    q: query,
    results_count: resultsCount,
    ms
  })
}

const addToCart = (product: Product, quantity: number = 1, unit: 'unit' | 'package' = 'unit') => {
  const existingItem = cart.value.find(item => item.id === product.id && item.unit === unit)
  
  if (existingItem) {
    existingItem.quantity += quantity
  } else {
    cart.value.push({
      ...product,
      quantity,
      unit
    })
  }
}

const updateQuantity = (itemId: string, newQuantity: number) => {
  const item = cart.value.find(item => item.id === itemId)
  if (item) {
    const oldQuantity = item.quantity
    item.quantity = newQuantity
    
    // Emit metrics
    console.log('Quantity changed:', {
      direction: newQuantity > oldQuantity ? 'increase' : 'decrease',
      before: oldQuantity,
      after: newQuantity
    })
  }
}

const updateUnit = (itemId: string, newUnit: 'unit' | 'package') => {
  const item = cart.value.find(item => item.id === itemId)
  if (item) {
    item.unit = newUnit
  }
}

const removeFromCart = (productId: string) => {
  const index = cart.value.findIndex(item => item.id === productId)
  if (index > -1) {
    cart.value.splice(index, 1)
  }
}

const clearCart = () => {
  cart.value = []
  stockErrors.value = []
}

const handlePaymentValidityChanged = (validation: { ok: boolean; change: number; error?: string }) => {
  paymentValidation.value = validation
}

const autoAdjustStock = () => {
  for (const error of stockErrors.value) {
    const item = cart.value.find(item => item.id === error.product_id)
    if (item) {
      if (error.available > 0) {
        item.quantity = error.available
      } else {
        // Remove item if no stock available
        removeFromCart(error.product_id)
      }
    }
  }
  stockErrors.value = []
}

const processCheckout = async () => {
  if (!canCheckout.value || !selectedCustomer.value || !quote.value) return
  
  saleStore.setProcessing(true)
  
  const checkoutItems = cart.value.map(item => ({
    product_id: item.id,
    qty: item.quantity,
    unit: item.unit
  }))

  const result = await checkout({
    customerId: selectedCustomer.value.id,
    items: checkoutItems,
    payments: paymentsStore.payments,
    idempotencyKey: saleStore.idempotencyKey
  })

  if (result.ok && result.data) {
    // Success - show modal
    lastCheckoutResult.value = result.data
    lastPaymentsUsed.value = [...paymentsStore.payments]
    showSuccessModal.value = true
    
    // Complete sale
    saleStore.completeSale(result.data.order_id)
    
    console.log('Payment processed:', {
      order_id: result.data.order_id,
      total: result.data.totals.total,
      change: result.data.totals.change
    })
    
  } else if (result.isStockError && result.missing) {
    // Stock error - highlight items
    stockErrors.value = result.missing
    saleStore.setProcessing(false)
    
  } else if (result.isNetworkError) {
    // Network error - setup retry
    saleStore.setProcessing(false)
    setupNetworkRetry()
    
  } else {
    // Other error
    saleStore.setProcessing(false)
    console.error('Checkout error:', result.error)
  }
}

const setupNetworkRetry = () => {
  if (pendingRetry.value) return
  
  pendingRetry.value = true
  
  // Watch for online status
  const handleOnline = () => {
    if (pendingRetry.value) {
      showRetryToast.value = true
      
      setTimeout(() => {
        showRetryToast.value = false
        pendingRetry.value = false
        
        // Retry checkout
        if (canCheckout.value) {
          processCheckout()
        }
      }, 800)
    }
  }

  window.addEventListener('online', handleOnline, { once: true })
  
  // Clear pending retry after 30 seconds
  setTimeout(() => {
    pendingRetry.value = false
    window.removeEventListener('online', handleOnline)
  }, 30000)
}

const closeSuccessModal = () => {
  showSuccessModal.value = false
  lastCheckoutResult.value = null
  lastPaymentsUsed.value = []
}

const startNewSale = () => {
  // Clear all state
  clearCart()
  paymentsStore.clearPayments()
  saleStore.startNewSale()
  
  closeSuccessModal()
  
  console.log('New sale started')
}

const handlePrintReceipt = () => {
  console.log('Print receipt requested')
}

// Set default customer on mount
onMounted(() => {
  // Auto-select first customer (retail)
  const defaultCustomer: Customer = {
    id: 'retail-001',
    name: 'Cliente General',
    segment: 'retail'
  }
  selectedCustomer.value = defaultCustomer
  saleStore.setCustomerId(defaultCustomer.id)
})

// Cleanup on unmount
onUnmounted(() => {
  cleanupQuote()
})
</script>