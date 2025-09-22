<template>
  <div class="bg-white rounded-lg shadow p-6">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Punto de Venta</h1>
      <div class="flex items-center space-x-2">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          Activo
        </span>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Product Selection Area -->
      <div class="lg:col-span-2">
        <h2 class="text-lg font-medium text-gray-900 mb-4">Productos</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div
            v-for="product in mockProducts"
            :key="product.id"
            class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            :class="{ 'opacity-50 cursor-not-allowed': !canOperate }"
            @click="canOperate ? addToCart(product) : null"
          >
            <div class="text-sm font-medium text-gray-900">{{ product.name }}</div>
            <div class="text-lg font-bold text-blue-600">${{ product.price }}</div>
            <div class="text-xs text-gray-500">Stock: {{ product.stock }}</div>
          </div>
        </div>
      </div>

      <!-- Cart Area -->
      <div class="bg-gray-50 rounded-lg p-4">
        <h2 class="text-lg font-medium text-gray-900 mb-4">Carrito</h2>
        
        <div v-if="cart.length === 0" class="text-gray-500 text-center py-8">
          Carrito vacío
        </div>
        
        <div v-else class="space-y-2">
          <div
            v-for="item in cart"
            :key="item.id"
            class="flex items-center justify-between py-2 border-b border-gray-200"
          >
            <div class="flex-1">
              <div class="text-sm font-medium">{{ item.name }}</div>
              <div class="text-xs text-gray-500">{{ item.quantity }} x ${{ item.price }}</div>
            </div>
            <div class="text-sm font-bold">${{ (item.quantity * item.price).toFixed(2) }}</div>
          </div>
          
          <div class="pt-4 border-t border-gray-300">
            <div class="flex justify-between items-center text-lg font-bold">
              <span>Total:</span>
              <span>${{ cartTotal.toFixed(2) }}</span>
            </div>
            
            <!-- Checkout Button with Blocker -->
            <div class="mt-4">
              <button
                @click="canCheckout ? processPayment() : null"
                :disabled="!canCheckout"
                :title="checkoutBlockReason || ''"
                class="w-full bg-blue-600 text-white py-2 px-4 rounded-md transition-colors"
                :class="getBlockedButtonClass(!canCheckout)"
              >
                {{ canCheckout ? 'Procesar Pago' : `Bloqueado: ${checkoutBlockReason}` }}
              </button>
            </div>
            
            <button
              @click="clearCart"
              :disabled="!canOperate"
              class="w-full mt-2 bg-gray-300 text-gray-700 py-2 px-4 rounded-md transition-colors"
              :class="getBlockedButtonClass(!canOperate)"
            >
              Limpiar Carrito
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Debug Panel (for testing) -->
    <div class="mt-8 p-4 bg-gray-100 rounded-lg">
      <h3 class="text-sm font-medium text-gray-900 mb-2">Panel de Pruebas</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        <button
          @click="opsStore.setOffline(!opsStore.offline)"
          class="text-xs bg-red-100 text-red-800 px-2 py-1 rounded hover:bg-red-200"
        >
          {{ opsStore.offline ? 'Conectar' : 'Desconectar' }}
        </button>
        <button
          @click="opsStore.setShift(!opsStore.hasShiftOpen)"
          class="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded hover:bg-amber-200"
        >
          {{ opsStore.hasShiftOpen ? 'Cerrar Turno' : 'Abrir Turno' }}
        </button>
        <button
          @click="opsStore.setCashbox(!opsStore.hasCashboxOpen)"
          class="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded hover:bg-amber-200"
        >
          {{ opsStore.hasCashboxOpen ? 'Cerrar Caja' : 'Abrir Caja' }}
        </button>
        <button
          @click="resetOperationalState"
          class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200"
        >
          Reset Todo
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useOpsStore } from '@/stores/ops'
import { useBlockers } from '@/composables/useBlockers'

interface Product {
  id: number
  name: string
  price: number
  stock: number
}

interface CartItem extends Product {
  quantity: number
}

const opsStore = useOpsStore()
const { canCheckout, checkoutBlockReason, canOperate, getBlockedButtonClass } = useBlockers()

const mockProducts: Product[] = [
  { id: 1, name: 'Coca Cola 500ml', price: 2.50, stock: 50 },
  { id: 2, name: 'Pan Integral', price: 3.00, stock: 25 },
  { id: 3, name: 'Leche Entera 1L', price: 4.20, stock: 30 },
  { id: 4, name: 'Café Molido 250g', price: 8.50, stock: 15 },
  { id: 5, name: 'Galletas Chocolate', price: 2.80, stock: 40 },
  { id: 6, name: 'Yogur Natural', price: 1.90, stock: 35 }
]

const cart = ref<CartItem[]>([])

const cartTotal = computed(() => {
  return cart.value.reduce((total, item) => total + (item.quantity * item.price), 0)
})

const addToCart = (product: Product) => {
  const existingItem = cart.value.find(item => item.id === product.id)
  
  if (existingItem) {
    existingItem.quantity++
  } else {
    cart.value.push({ ...product, quantity: 1 })
  }
}

const clearCart = () => {
  cart.value = []
}

const processPayment = () => {
  if (cart.value.length === 0) return
  
  // Mock payment processing
  alert(`Pago procesado por $${cartTotal.value.toFixed(2)}`)
  clearCart()
}

const resetOperationalState = () => {
  opsStore.setOffline(false)
  opsStore.setShift(true)
  opsStore.setCashbox(true)
}
</script>
</template>