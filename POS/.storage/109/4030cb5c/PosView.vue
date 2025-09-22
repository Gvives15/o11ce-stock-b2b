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

      <!-- Right Zone: Execution (Cart + Totals) -->
      <div class="w-96 bg-white border-l border-gray-200 flex flex-col">
        <!-- Cart Component -->
        <div class="flex-1 overflow-hidden">
          <Cart
            :items="cart"
            @update-quantity="updateQuantity"
            @update-unit="updateUnit"
            @remove-item="removeFromCart"
          />
        </div>

        <!-- Sticky Footer: Totals + Checkout -->
        <div class="border-t border-gray-200">
          <TotalsPanel
            :quote="quote"
            :is-loading="isQuoteLoading"
            :error="quoteError"
          />
          
          <!-- Checkout Button -->
          <div class="p-4 bg-gray-50">
            <button
              @click="processPayment"
              :disabled="!canCheckout"
              :title="checkoutBlockReason || ''"
              class="w-full py-3 px-4 rounded-lg font-semibold text-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
              :class="canCheckout 
                ? 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500' 
                : 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-50'"
            >
              {{ canCheckout ? 'Procesar Pago' : (checkoutBlockReason || 'No Disponible') }}
            </button>

            <!-- Clear Cart -->
            <button
              v-if="cart.length > 0"
              @click="clearCart"
              class="w-full mt-2 py-2 px-4 text-sm text-gray-600 hover:text-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 rounded"
            >
              Limpiar Carrito
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useBlockers } from '@/composables/useBlockers'
import { useQuote } from '@/composables/useQuote'
import SearchBar from '@/components/SearchBar.vue'
import CustomerPicker from '@/components/CustomerPicker.vue'
import Cart from '@/components/Cart.vue'
import TotalsPanel from '@/components/TotalsPanel.vue'

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
const { canCheckout, checkoutBlockReason } = useBlockers()
const { quote, isLoading: isQuoteLoading, error: quoteError, fetchQuote, cleanup: cleanupQuote } = useQuote()

// Reactive state
const cart = ref<CartItem[]>([])
const selectedCategory = ref<Category | null>(null)
const selectedCustomer = ref<Customer | null>(null)

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
    { id: '1', name: 'Gasolina Premium 95', sku: 'GAS500', price: 1.45, category: 'Combustibles', stock: 1000, unit: 'litro' },
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

// Watch for cart or customer changes to trigger quote
watch([cart, selectedCustomer], () => {
  if (selectedCustomer.value && cart.value.length > 0) {
    fetchQuote(selectedCustomer.value, cart.value)
  }
}, { deep: true })

// Methods
const selectCategory = (category: Category) => {
  selectedCategory.value = selectedCategory.value?.id === category.id ? null : category
}

const handleCustomerChange = (customer: Customer | null) => {
  selectedCustomer.value = customer
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
}

const processPayment = () => {
  if (!canCheckout.value || !quote.value) return
  
  const startTime = performance.now()
  
  // Mock payment processing
  alert(`Procesando pago de ${quote.value.currency} ${quote.value.total.toFixed(2)}...`)
  
  // Clear cart after successful payment
  setTimeout(() => {
    clearCart()
    
    const processingTime = performance.now() - startTime
    console.log('Payment processed:', {
      total: quote.value?.total,
      currency: quote.value?.currency,
      processing_time_ms: processingTime
    })
    
    alert('¡Pago procesado exitosamente!')
  }, 1000)
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
})

// Cleanup on unmount
onUnmounted(() => {
  cleanupQuote()
})
</script>