<template>
  <div class="relative w-full">
    <!-- Search Input -->
    <div class="relative">
      <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      <input
        ref="searchInput"
        v-model="searchQuery"
        type="text"
        class="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg"
        :class="{
          'border-blue-500 ring-2 ring-blue-500': showDropdown,
          'animate-pulse border-blue-300': isLoading,
          'border-red-500 ring-2 ring-red-500': hasError
        }"
        placeholder="Escribí código o nombre… (Ej: GAS500)"
        @keydown="handleKeydown"
        @focus="handleFocus"
        @blur="handleBlur"
        autocomplete="off"
      />
      
      <!-- Loading indicator -->
      <div v-if="isLoading" class="absolute inset-y-0 right-0 pr-3 flex items-center">
        <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
      </div>
    </div>

    <!-- Connection Status -->
    <div v-if="hasError" class="mt-1 text-sm text-red-600">
      Sin conexión. Los precios pueden no ser exactos.
    </div>

    <!-- Suggestions Dropdown -->
    <div
      v-if="showDropdown && (suggestions.length > 0 || isLoading || noResults)"
      class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto"
      role="listbox"
      :aria-label="'Resultados de búsqueda para ' + searchQuery"
    >
      <!-- Loading state -->
      <div v-if="isLoading" class="px-4 py-3 text-sm text-gray-500 text-center">
        <div class="flex items-center justify-center space-x-2">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span>Buscando productos…</span>
        </div>
      </div>

      <!-- No results -->
      <div v-else-if="noResults" class="px-4 py-3 text-sm text-gray-500 text-center">
        No se encontraron productos para "{{ searchQuery }}"
      </div>

      <!-- Suggestions list -->
      <div v-else class="py-1">
        <div
          v-for="(product, index) in suggestions"
          :key="product.id"
          role="option"
          :aria-selected="index === selectedIndex"
          class="px-4 py-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
          :class="{
            'bg-blue-50 border-blue-200': index === selectedIndex
          }"
          @click="selectProduct(product)"
          @mouseenter="selectedIndex = index"
        >
          <div class="flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center space-x-3">
                <!-- Product icon -->
                <div class="flex-shrink-0 w-10 h-10 bg-gray-200 rounded-lg flex items-center justify-center">
                  <svg class="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
                
                <div class="flex-1 min-w-0">
                  <!-- Product name with highlighted search term -->
                  <p class="text-sm font-medium text-gray-900 truncate" v-html="highlightMatch(product.name)"></p>
                  
                  <!-- Product details -->
                  <div class="flex items-center space-x-2 mt-1">
                    <span class="text-xs text-gray-500 font-medium">{{ product.sku }}</span>
                    <span class="text-xs text-gray-300">•</span>
                    <span class="text-xs text-gray-500">{{ product.category }}</span>
                    <span class="text-xs text-gray-300">•</span>
                    <span class="text-xs text-gray-500">Stock: {{ product.stock }}</span>
                    <span v-if="product.packageSize" class="text-xs bg-blue-100 text-blue-800 px-1 rounded">
                      PACK×{{ product.packageSize }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Price -->
            <div class="flex-shrink-0 text-right">
              <div class="text-sm font-semibold text-gray-900">${{ product.price.toFixed(2) }}</div>
              <div class="text-xs text-gray-500">{{ product.unit }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Backdrop to close dropdown -->
    <div
      v-if="showDropdown"
      class="fixed inset-0 z-40"
      @click="closeDropdown"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { debounce } from 'lodash-es'

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

interface AddItemEvent {
  product: Product
  unit: string
}

// Props & Emits
const emit = defineEmits<{
  addItem: [event: AddItemEvent]
  searchPerformed: [query: string, resultsCount: number, ms: number]
}>()

// Reactive state
const searchInput = ref<HTMLInputElement>()
const searchQuery = ref('')
const suggestions = ref<Product[]>([])
const selectedIndex = ref(-1)
const showDropdown = ref(false)
const isLoading = ref(false)
const hasError = ref(false)
const searchStartTime = ref(0)

// Computed
const noResults = computed(() => 
  !isLoading.value && searchQuery.value.trim().length > 0 && suggestions.value.length === 0
)

// Barcode scanner detection
const barcodeBuffer = ref('')
const barcodeTimeout = ref<NodeJS.Timeout>()
const BARCODE_TIMEOUT = 100 // ms between characters for barcode detection
const MIN_BARCODE_LENGTH = 8

// Mock products with enhanced data
const mockProducts: Product[] = [
  {
    id: '1',
    name: 'Gasolina Premium 95',
    sku: 'GAS500',
    price: 1.45,
    category: 'Combustibles',
    stock: 1000,
    unit: 'litro'
  },
  {
    id: '2',
    name: 'Gasolina Regular 87',
    sku: 'GAS400',
    price: 1.35,
    category: 'Combustibles',
    stock: 1500,
    unit: 'litro'
  },
  {
    id: '3',
    name: 'Gasóleo Diesel',
    sku: 'DIE001',
    price: 1.25,
    category: 'Combustibles',
    stock: 800,
    unit: 'litro'
  },
  {
    id: '4',
    name: 'Aceite Motor 5W-30',
    sku: 'ACE530',
    price: 25.99,
    category: 'Lubricantes',
    stock: 50,
    unit: 'botella',
    packageSize: 12
  },
  {
    id: '5',
    name: 'Aceite Motor 10W-40',
    sku: 'ACE1040',
    price: 22.99,
    category: 'Lubricantes',
    stock: 45,
    unit: 'botella',
    packageSize: 12
  },
  {
    id: '6',
    name: 'Refrigerante Coca Cola',
    sku: 'COC500',
    price: 2.50,
    category: 'Bebidas',
    stock: 120,
    unit: 'unidad',
    packageSize: 24
  },
  {
    id: '7',
    name: 'Agua Mineral 1L',
    sku: 'AGU001',
    price: 1.25,
    category: 'Bebidas',
    stock: 200,
    unit: 'unidad',
    packageSize: 12
  }
]

// Debounced search function (250ms as per UX requirements)
const debouncedSearch = debounce(async (query: string) => {
  await searchProducts(query)
}, 250)

// Watch search query with debounce
watch(searchQuery, (newQuery) => {
  if (newQuery.trim().length === 0) {
    suggestions.value = []
    showDropdown.value = false
    selectedIndex.value = -1
    hasError.value = false
    return
  }
  
  if (newQuery.trim().length < 2) {
    return
  }
  
  searchStartTime.value = performance.now()
  debouncedSearch(newQuery.trim())
})

// Search products function
const searchProducts = async (query: string) => {
  if (!query || query.length < 2) return
  
  isLoading.value = true
  hasError.value = false
  
  try {
    // Mock API call - in real app, this would be actual API call to /catalog/search?q=
    await new Promise(resolve => setTimeout(resolve, 300))
    
    // Filter products that match the query
    const filtered = mockProducts.filter(product =>
      product.name.toLowerCase().includes(query.toLowerCase()) ||
      product.category.toLowerCase().includes(query.toLowerCase()) ||
      product.sku.toLowerCase().includes(query.toLowerCase())
    )
    
    suggestions.value = filtered
    selectedIndex.value = filtered.length > 0 ? 0 : -1
    showDropdown.value = true
    
    // Emit search metrics
    const searchTime = performance.now() - searchStartTime.value
    emit('searchPerformed', query, filtered.length, searchTime)
    
  } catch (error) {
    console.error('Error searching products:', error)
    hasError.value = true
    suggestions.value = []
  } finally {
    isLoading.value = false
  }
}

// Highlight matching text in suggestions
const highlightMatch = (text: string): string => {
  if (!searchQuery.value.trim()) return text
  
  const query = searchQuery.value.trim()
  const regex = new RegExp(`(${query})`, 'gi')
  return text.replace(regex, '<mark class="bg-yellow-200 px-1 rounded">$1</mark>')
}

// Keyboard navigation and shortcuts
const handleKeydown = (event: KeyboardEvent) => {
  // Global shortcuts
  if (event.key === 'F2') {
    event.preventDefault()
    searchInput.value?.focus()
    return
  }
  
  if (!showDropdown.value || suggestions.value.length === 0) {
    // Handle potential barcode input
    handleBarcodeInput(event)
    return
  }
  
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, suggestions.value.length - 1)
      break
      
    case 'ArrowUp':
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      break
      
    case 'Enter':
      event.preventDefault()
      if (selectedIndex.value >= 0 && selectedIndex.value < suggestions.value.length) {
        selectProduct(suggestions.value[selectedIndex.value])
      } else if (suggestions.value.length > 0) {
        // Add first result if no specific selection
        selectProduct(suggestions.value[0])
      }
      break
      
    case 'Escape':
      event.preventDefault()
      closeDropdown()
      break
      
    case 'ArrowRight':
      event.preventDefault()
      // TODO: Implement unit switching (unit/package) if applicable
      break
  }
}

// Handle barcode scanner input
const handleBarcodeInput = (event: KeyboardEvent) => {
  // Clear previous timeout
  if (barcodeTimeout.value) {
    clearTimeout(barcodeTimeout.value)
  }
  
  // Add character to buffer
  if (event.key.length === 1) {
    barcodeBuffer.value += event.key
  }
  
  // Set timeout to process barcode
  barcodeTimeout.value = setTimeout(() => {
    if (barcodeBuffer.value.length >= MIN_BARCODE_LENGTH) {
      processBarcode(barcodeBuffer.value)
    }
    barcodeBuffer.value = ''
  }, BARCODE_TIMEOUT)
}

// Process scanned barcode
const processBarcode = async (barcode: string) => {
  try {
    // Search for product by barcode/SKU
    await searchProducts(barcode)
    
    // If we found exactly one product, auto-select it
    if (suggestions.value.length === 1) {
      selectProduct(suggestions.value[0])
    } else if (suggestions.value.length > 1) {
      // Multiple matches, show dropdown
      showDropdown.value = true
      selectedIndex.value = 0
    }
  } catch (error) {
    console.error('Error processing barcode:', error)
  }
}

// Select product and emit event
const selectProduct = (product: Product) => {
  emit('addItem', {
    product,
    unit: 'unit' // Default unit, can be changed later
  })
  
  // Clear search and close dropdown
  searchQuery.value = ''
  suggestions.value = []
  showDropdown.value = false
  selectedIndex.value = -1
  hasError.value = false
  
  // Focus back to input for next search
  nextTick(() => {
    searchInput.value?.focus()
  })
}

// Handle focus/blur events
const handleFocus = () => {
  if (suggestions.value.length > 0) {
    showDropdown.value = true
  }
}

const handleBlur = () => {
  // Delay closing to allow click events on suggestions
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

const closeDropdown = () => {
  showDropdown.value = false
  selectedIndex.value = -1
}

// Global keyboard shortcuts
const handleGlobalKeydown = (event: KeyboardEvent) => {
  if (event.key === 'F2') {
    event.preventDefault()
    searchInput.value?.focus()
  }
}

// Auto-focus input on mount
onMounted(() => {
  nextTick(() => {
    searchInput.value?.focus()
  })
  
  // Add global keyboard listener
  document.addEventListener('keydown', handleGlobalKeydown)
})

// Cleanup timeouts and listeners
onUnmounted(() => {
  debouncedSearch.cancel()
  if (barcodeTimeout.value) {
    clearTimeout(barcodeTimeout.value)
  }
  document.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<style scoped>
/* Custom scrollbar for dropdown */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Ensure mark elements don't break layout */
mark {
  display: inline;
  line-height: inherit;
}
</style>