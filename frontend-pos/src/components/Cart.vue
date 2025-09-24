<template>
  <div class="flex flex-col h-full">
    <!-- Cart Header -->
    <div class="p-4 bg-white border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900">Carrito de Compras</h2>
      <p class="text-sm text-gray-500">
        {{ items.length }} {{ items.length === 1 ? 'artículo' : 'artículos' }}
      </p>
    </div>

    <!-- Cart Items -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3">
      <!-- Empty State -->
      <div v-if="items.length === 0" class="text-center py-12">
        <div class="text-gray-400 text-5xl mb-4">🛒</div>
        <p class="text-gray-500 text-base font-medium">Agregá productos con el lector o buscador.</p>
        <p class="text-gray-400 text-sm mt-2">Los productos aparecerán aquí</p>
      </div>

      <!-- Cart Items List -->
      <div
        v-for="item in items"
        :key="item.id"
        :tabindex="0"
        @keydown="handleItemKeydown($event, item)"
        class="bg-white p-4 rounded-lg border border-gray-200 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
      >
        <!-- Item Header -->
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1 min-w-0">
            <h4 class="text-base font-medium text-gray-900 truncate">{{ item.name }}</h4>
            <p class="text-xs text-gray-500 mt-1">SKU: {{ item.sku }}</p>
          </div>
          
          <button
            @click="removeItem(item.id)"
            class="ml-3 text-red-500 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded p-1 transition-colors"
            :aria-label="`Eliminar ${item.name}`"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Quantity and Price Controls -->
        <div class="flex items-center justify-between">
          <!-- Quantity Controls -->
          <div class="flex items-center space-x-3">
            <button
              @click="updateQuantity(item.id, item.quantity - 1)"
              :disabled="item.quantity <= 1"
              class="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center text-lg font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
              :aria-label="'Disminuir cantidad de ' + item.name"
            >
              −
            </button>
            
            <div class="flex flex-col items-center min-w-[60px]">
              <span class="text-lg font-semibold text-gray-900">{{ item.quantity }}</span>
              <span class="text-xs text-gray-500">{{ unitLabel(item) }}</span>
            </div>
            
            <button
              @click="updateQuantity(item.id, item.quantity + 1)"
              class="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-lg font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
              :aria-label="'Aumentar cantidad de ' + item.name"
            >
              +
            </button>
          </div>

          <!-- Unit Selector -->
          <div v-if="item.packageSize" class="flex items-center space-x-2">
            <select
              :value="item.unit"
              @change="updateUnit(item.id, ($event.target as HTMLSelectElement).value as 'unit' | 'package')"
              class="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="unit">Unidad</option>
              <option value="package">Pack ({{ item.packageSize }})</option>
            </select>
          </div>

          <!-- Price Info -->
          <div class="text-right">
            <div class="text-lg font-bold text-gray-900">
              ${{ itemSubtotal(item).toFixed(2) }}
            </div>
            <div class="text-sm text-gray-500">
              ${{ unitPrice(item).toFixed(2) }} / {{ unitLabel(item) }}
            </div>
          </div>
        </div>

        <!-- Package Info Tooltip -->
        <div v-if="item.unit === 'package' && item.packageSize" class="mt-2 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
          1 pack = {{ item.packageSize }} unidades
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface CartItem {
  id: string
  name: string
  sku: string
  price: number
  quantity: number
  unit: 'unit' | 'package'
  packageSize?: number
}

interface Props {
  items: CartItem[]
}

interface Emits {
  (e: 'updateQuantity', itemId: string, quantity: number): void
  (e: 'updateUnit', itemId: string, unit: 'unit' | 'package'): void
  (e: 'removeItem', itemId: string): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

// Computed helpers
const unitLabel = (item: CartItem): string => {
  return item.unit === 'package' ? 'pack' : 'ud'
}

const unitPrice = (item: CartItem): number => {
  if (item.unit === 'package' && item.packageSize) {
    return item.price * item.packageSize
  }
  return item.price
}

const itemSubtotal = (item: CartItem): number => {
  return unitPrice(item) * item.quantity
}

// Event handlers
const updateQuantity = (itemId: string, quantity: number) => {
  if (quantity >= 1) {
    emit('updateQuantity', itemId, quantity)
  }
}

const updateUnit = (itemId: string, unit: 'unit' | 'package') => {
  emit('updateUnit', itemId, unit)
}

const removeItem = (itemId: string) => {
  emit('removeItem', itemId)
}

// Keyboard shortcuts
const handleItemKeydown = (event: KeyboardEvent, item: CartItem) => {
  switch (event.key) {
    case '+':
    case '=':
      event.preventDefault()
      updateQuantity(item.id, item.quantity + 1)
      break
      
    case '-':
      event.preventDefault()
      if (item.quantity > 1) {
        updateQuantity(item.id, item.quantity - 1)
      }
      break
      
    case 'Delete':
    case 'Backspace':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        removeItem(item.id)
      }
      break
      
    case 'd':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        // TODO: Implement discount functionality in B7
        console.log('Discount shortcut for item:', item.name)
      }
      break
  }
}
</script>