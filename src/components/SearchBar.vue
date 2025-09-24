<template>
  <div class="relative">
    <!-- Input de búsqueda -->
    <div class="relative">
      <input
        ref="searchInput"
        v-model="searchQuery"
        @keydown.enter.prevent="selectFirstResult"
        @keydown.escape="clearSearch"
        @keydown.arrow-down.prevent="navigateDown"
        @keydown.arrow-up.prevent="navigateUp"
        @focus="showSuggestions = true"
        @blur="handleBlur"
        type="text"
        placeholder="Buscar productos... (Enter para agregar)"
        class="w-full px-4 py-3 pl-12 pr-4 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
      />
      
      <!-- Icono de búsqueda -->
      <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      
      <!-- Indicador de carga -->
      <div v-if="isLoading" class="absolute inset-y-0 right-0 pr-3 flex items-center">
        <svg class="animate-spin h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
      
      <!-- Botón limpiar -->
      <button
        v-if="searchQuery && !isLoading"
        @click="clearSearch"
        class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    
    <!-- Sugerencias dropdown -->
    <div
      v-if="showSuggestions && (suggestions.length > 0 || (searchQuery && !isLoading))"
      class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto"
    >
      <!-- Resultados -->
      <div v-if="suggestions.length > 0">
        <div
          v-for="(product, index) in suggestions"
          :key="product.id"
          @click="selectProduct(product)"
          @mouseenter="selectedIndex = index"
          :class="[
            'px-4 py-3 cursor-pointer border-b border-gray-100 last:border-b-0 transition-colors duration-150',
            selectedIndex === index ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'
          ]"
        >
          <div class="flex justify-between items-start">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">
                {{ product.name }}
              </p>
              <p class="text-xs text-gray-500 mt-1">
                SKU: {{ product.sku }} | {{ product.unit }}
                <span v-if="product.pack_size" class="ml-2">Pack x{{ product.pack_size }}</span>
              </p>
            </div>
            <div class="ml-4 flex-shrink-0">
              <span class="text-sm font-semibold text-blue-600">
                ${{ product.price_base }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Sin resultados -->
      <div v-else-if="searchQuery && !isLoading" class="px-4 py-6 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0120 12a8 8 0 10-16 0 8 8 0 002 5.291z" />
        </svg>
        <p class="mt-2 text-sm text-gray-500">
          No se encontraron productos para "{{ searchQuery }}"
        </p>
        <p class="text-xs text-gray-400 mt-1">
          Intenta con otro término de búsqueda
        </p>
      </div>
      
      <!-- Ayuda -->
      <div v-if="suggestions.length > 0" class="px-4 py-2 bg-gray-50 border-t border-gray-200">
        <p class="text-xs text-gray-500">
          <kbd class="px-1 py-0.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded">Enter</kbd>
          para agregar el primero |
          <kbd class="px-1 py-0.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded">↑↓</kbd>
          para navegar |
          <kbd class="px-1 py-0.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded">Esc</kbd>
          para cerrar
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import axiosClient from '../lib/axiosClient'

// Props y emits
const emit = defineEmits<{
  productSelected: [product: any]
}>()

// Reactive data
const searchInput = ref<HTMLInputElement>()
const searchQuery = ref('')
const suggestions = ref([])
const showSuggestions = ref(false)
const isLoading = ref(false)
const selectedIndex = ref(0)

// Debounce timer
let debounceTimer: NodeJS.Timeout | null = null

// Interfaces
interface SearchResult {
  id: number
  sku: string
  name: string
  unit: string
  pack_size?: string
  price_base: number
}

interface SearchResponse {
  results: SearchResult[]
  next?: string
}

// Methods
const searchProducts = async (query: string) => {
  if (!query.trim()) {
    suggestions.value = []
    return
  }
  
  isLoading.value = true
  
  try {
    const response = await axiosClient.get<SearchResponse>('/catalog/search', {
      params: {
        q: query,
        page: 1,
        size: 10 // Limitamos a 10 sugerencias
      }
    })
    
    suggestions.value = response.data.results
    selectedIndex.value = 0 // Reset selection to first item
    
    console.log(`Búsqueda "${query}": ${response.data.results.length} resultados`)
    
  } catch (error) {
    console.error('Error en búsqueda:', error)
    suggestions.value = []
  } finally {
    isLoading.value = false
  }
}

const selectProduct = (product: SearchResult) => {
  emit('productSelected', {
    id: product.id,
    name: product.name,
    price: product.price_base,
    stock: 999, // Asumimos stock disponible
    sku: product.sku,
    unit: product.unit,
    pack_size: product.pack_size
  })
  
  clearSearch()
  console.log(`Producto seleccionado: ${product.name} (${product.sku})`)
}

const selectFirstResult = () => {
  if (suggestions.value.length > 0) {
    const selectedProduct = suggestions.value[selectedIndex.value]
    selectProduct(selectedProduct)
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  suggestions.value = []
  showSuggestions.value = false
  selectedIndex.value = 0
}

const navigateDown = () => {
  if (selectedIndex.value < suggestions.value.length - 1) {
    selectedIndex.value++
  }
}

const navigateUp = () => {
  if (selectedIndex.value > 0) {
    selectedIndex.value--
  }
}

const handleBlur = () => {
  // Delay hiding suggestions to allow click events
  setTimeout(() => {
    showSuggestions.value = false
  }, 200)
}

// Focus method for external use
const focus = () => {
  nextTick(() => {
    searchInput.value?.focus()
  })
}

// Watch for search query changes with debounce
watch(searchQuery, (newQuery) => {
  // Clear previous timer
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }
  
  // Set new timer with 250ms debounce
  debounceTimer = setTimeout(() => {
    searchProducts(newQuery)
  }, 250)
})

// Expose methods for parent component
defineExpose({
  focus,
  clearSearch
})
</script>

<style scoped>
/* Custom scrollbar for suggestions */
.max-h-80::-webkit-scrollbar {
  width: 6px;
}

.max-h-80::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.max-h-80::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.max-h-80::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Keyboard shortcuts styling */
kbd {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
}
</style>