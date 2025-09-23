<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <h1 class="text-2xl font-bold text-gray-900">Sistema POS</h1>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600">
              Bienvenido, {{ authStore.user?.first_name || authStore.user?.username }}
            </span>
            <button
              @click="handleLogout"
              class="text-sm text-red-600 hover:text-red-800"
            >
              Cerrar Sesión
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Productos -->
        <div class="lg:col-span-2">
          <div class="card">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Productos</h2>
            <div class="mb-6">
              <SearchBar @product-selected="addToCartFromSearch" />
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div
                v-for="product in products"
                :key="product.id"
                @click="addToCart(product)"
                class="p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <h3 class="font-medium text-gray-900">{{ product.name }}</h3>
                <p class="text-sm text-gray-600">${{ product.price }}</p>
                <p class="text-xs text-gray-500">Stock: {{ product.stock }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Carrito -->
        <div class="lg:col-span-1">
          <div class="card">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Carrito</h2>
            <div class="space-y-3">
              <div
                v-for="item in cart"
                :key="item.id"
                class="flex justify-between items-center py-2 border-b border-gray-100"
              >
                <div>
                  <p class="font-medium text-gray-900">{{ item.name }}</p>
                  <p class="text-sm text-gray-600">
                    ${{ item.price }} x {{ item.quantity }}
                  </p>
                </div>
                <div class="flex items-center space-x-2">
                  <button
                    @click="updateQuantity(item.id, item.quantity - 1)"
                    class="text-gray-500 hover:text-gray-700"
                  >
                    -
                  </button>
                  <span class="text-sm">{{ item.quantity }}</span>
                  <button
                    @click="updateQuantity(item.id, item.quantity + 1)"
                    class="text-gray-500 hover:text-gray-700"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>
            
            <div class="mt-6 pt-4 border-t border-gray-200">
              <div class="flex justify-between items-center mb-4">
                <span class="text-lg font-semibold">Total:</span>
                <span class="text-lg font-bold text-blue-600">${{ total }}</span>
              </div>
              <button
                @click="processSale"
                :disabled="cart.length === 0"
                class="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Procesar Venta
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import SearchBar from '../components/SearchBar.vue'
import axiosClient from '../lib/axiosClient'

const router = useRouter()
const authStore = useAuthStore()

const products = ref([])
const cart = ref([])

// Computed properties
const total = computed(() => {
  return cart.value.reduce((sum, item) => sum + (item.price * item.quantity), 0).toFixed(2)
})

// Methods
const addToCartFromSearch = (product) => {
  console.log('Producto agregado desde búsqueda:', product)
  addToCart(product)
}

const loadProducts = async () => {
  try {
    const response = await axiosClient.get('/catalog/products/')
    products.value = response.data
  } catch (error) {
    console.error('Error cargando productos:', error)
  }
}

const addToCart = (product) => {
  const existingItem = cart.value.find(item => item.id === product.id)
  
  if (existingItem) {
    existingItem.quantity += 1
  } else {
    cart.value.push({
      ...product,
      quantity: 1
    })
  }
}

const updateQuantity = (productId, newQuantity) => {
  if (newQuantity <= 0) {
    cart.value = cart.value.filter(item => item.id !== productId)
  } else {
    const item = cart.value.find(item => item.id === productId)
    if (item) {
      item.quantity = newQuantity
    }
  }
}

const processSale = async () => {
  try {
    const saleData = {
      items: cart.value.map(item => ({
        product_id: item.id,
        quantity: item.quantity,
        price: item.price
      }))
    }
    
    await axiosClient.post('/pos/sales/', saleData)
    cart.value = []
    alert('Venta procesada exitosamente')
    
    // Recargar productos para actualizar stock
    await loadProducts()
  } catch (error) {
    console.error('Error procesando venta:', error)
    alert('Error al procesar la venta')
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  loadProducts()
})
</script>