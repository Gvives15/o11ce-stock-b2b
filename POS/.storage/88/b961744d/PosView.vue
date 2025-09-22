<template>
  <div class="flex flex-col h-full">
    <!-- Search Bar -->
    <div class="bg-white border-b border-gray-200 p-4">
      <SearchBar @add-item="handleAddItem" />
    </div>

    <!-- Main POS Interface -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Product Grid/Categories (Left Side) -->
      <div class="flex-1 p-6 overflow-y-auto">
        <div class="mb-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">Categorías de Productos</h2>
          
          <!-- Category Grid -->
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            <button
              v-for="category in categories"
              :key="category.id"
              @click="selectCategory(category)"
              class="p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-center"
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
                class="p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-500 hover:shadow-md transition-all text-left"
              >
                <div class="flex items-center justify-between mb-2">
                  <h4 class="font-medium text-gray-900 truncate">{{ product.name }}</h4>
                  <span class="text-lg font-bold text-blue-600">${{ product.price.toFixed(2) }}</span>
                </div>
                <div class="text-sm text-gray-500">
                  Stock: {{ product.stock }} {{ product.unit }}
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Shopping Cart (Right Side) -->
      <div class="w-96 bg-gray-50 border-l border-gray-200 flex flex-col">
        <!-- Cart Header -->
        <div class="p-4 bg-white border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Carrito de Compras</h2>
          <p class="text-sm text-gray-500">{{ cart.length }} {{ cart.length === 1 ? 'artículo' : 'artículos' }}</p>
        </div>

        <!-- Cart Items -->
        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <div
            v-for="item in cart"
            :key="item.id"
            class="bg-white p-3 rounded-lg border border-gray-200"
          >
            <div class="flex items-center justify-between mb-2">
              <h4 class="font-medium text-gray-900 text-sm">{{ item.name }}</h4>
              <button
                @click="removeFromCart(item.id)"
                class="text-red-500 hover:text-red-700 text-sm"
              >
                ✕
              </button>
            </div>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <button
                  @click="updateQuantity(item.id, item.quantity - 1)"
                  class="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-sm"
                  :disabled="item.quantity <= 1"
                >
                  −
                </button>
                <span class="w-8 text-center text-sm font-medium">{{ item.quantity }}</span>
                <button
                  @click="updateQuantity(item.id, item.quantity + 1)"
                  class="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-sm"
                >
                  +
                </button>
              </div>
              
              <div class="text-right">
                <div class="text-sm font-semibold text-gray-900">
                  ${{ (item.price * item.quantity).toFixed(2) }}
                </div>
                <div class="text-xs text-gray-500">
                  ${{ item.price.toFixed(2) }} / {{ item.unit }}
                </div>
              </div>
            </div>
          </div>

          <!-- Empty Cart Message -->
          <div v-if="cart.length === 0" class="text-center py-8">
            <div class="text-gray-400 text-4xl mb-2">🛒</div>
            <p class="text-gray-500 text-sm">El carrito está vacío</p>
            <p class="text-gray-400 text-xs mt-1">Busca productos o selecciona una categoría</p>
          </div>
        </div>

        <!-- Cart Summary -->
        <div v-if="cart.length > 0" class="p-4 bg-white border-t border-gray-200">
          <!-- Subtotal -->
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm text-gray-600">Subtotal:</span>
            <span class="text-sm font-medium">${{ subtotal.toFixed(2) }}</span>
          </div>
          
          <!-- Tax -->
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm text-gray-600">IVA (21%):</span>
            <span class="text-sm font-medium">${{ tax.toFixed(2) }}</span>
          </div>
          
          <!-- Total -->
          <div class="flex justify-between items-center mb-4 pt-2 border-t border-gray-200">
            <span class="text-lg font-semibold text-gray-900">Total:</span>
            <span class="text-lg font-bold text-blue-600">${{ total.toFixed(2) }}</span>
          </div>

          <!-- Checkout Button -->
          <button
            @click="processPayment"
            :disabled="!canCheckout"
            :title="checkoutBlockReason || ''"
            class="w-full py-3 px-4 rounded-lg font-medium transition-colors"
            :class="canCheckout 
              ? 'bg-blue-600 text-white hover:bg-blue-700' 
              : 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-50'"
          >
            {{ canCheckout ? 'Procesar Pago' : (checkoutBlockReason || 'No Disponible') }}
          </button>

          <!-- Clear Cart -->
          <button
            @click="clearCart"
            class="w-full mt-2 py-2 px-4 text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            Limpiar Carrito
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useBlockers } from '@/composables/useBlockers'
import SearchBar from '@/components/SearchBar.vue'

interface Product {
  id: string
  name: string
  price: number
  category: string
  stock: number
  unit: string
  barcode?: string
}

interface CartItem extends Product {
  quantity: number
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

// Reactive state
const cart = ref<CartItem[]>([])
const selectedCategory = ref<Category | null>(null)

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
    { id: '1', name: 'Gasolina Premium 95', price: 1.45, category: 'Combustibles', stock: 1000, unit: 'litro' },
    { id: '2', name: 'Gasolina Regular 87', price: 1.35, category: 'Combustibles', stock: 1500, unit: 'litro' },
    { id: '3', name: 'Gasóleo Diesel', price: 1.25, category: 'Combustibles', stock: 800, unit: 'litro' }
  ],
  lubricants: [
    { id: '4', name: 'Aceite Motor 5W-30', price: 25.99, category: 'Lubricantes', stock: 50, unit: 'botella' },
    { id: '5', name: 'Aceite Motor 10W-40', price: 22.99, category: 'Lubricantes', stock: 45, unit: 'botella' }
  ],
  beverages: [
    { id: '6', name: 'Coca Cola 500ml', price: 2.50, category: 'Bebidas', stock: 120, unit: 'unidad' },
    { id: '7', name: 'Agua Mineral 1L', price: 1.25, category: 'Bebidas', stock: 200, unit: 'unidad' }
  ]
}

// Computed
const categoryProducts = computed(() => {
  if (!selectedCategory.value) return []
  return mockProducts[selectedCategory.value.id] || []
})

const subtotal = computed(() => {
  return cart.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
})

const tax = computed(() => {
  return subtotal.value * 0.21 // 21% IVA
})

const total = computed(() => {
  return subtotal.value + tax.value
})

// Methods
const selectCategory = (category: Category) => {
  selectedCategory.value = selectedCategory.value?.id === category.id ? null : category
}

const handleAddItem = (event: AddItemEvent) => {
  addToCart(event.product, 1)
}

const addToCart = (product: Product, quantity: number = 1) => {
  const existingItem = cart.value.find(item => item.id === product.id)
  
  if (existingItem) {
    existingItem.quantity += quantity
  } else {
    cart.value.push({
      ...product,
      quantity
    })
  }
}

const removeFromCart = (productId: string) => {
  const index = cart.value.findIndex(item => item.id === productId)
  if (index > -1) {
    cart.value.splice(index, 1)
  }
}

const updateQuantity = (productId: string, newQuantity: number) => {
  if (newQuantity <= 0) {
    removeFromCart(productId)
    return
  }
  
  const item = cart.value.find(item => item.id === productId)
  if (item) {
    item.quantity = newQuantity
  }
}

const clearCart = () => {
  cart.value = []
}

const processPayment = () => {
  if (!canCheckout.value) return
  
  // Mock payment processing
  alert(`Procesando pago de $${total.value.toFixed(2)}...`)
  
  // Clear cart after successful payment
  setTimeout(() => {
    clearCart()
    alert('¡Pago procesado exitosamente!')
  }, 1000)
}
</script>
</template>