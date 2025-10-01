<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Inventario</h1>
            <p class="text-sm text-gray-600 mt-1">
              {{ isLevel2 ? 'Gestión completa de inventario' : 'Consulta de inventario' }}
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <!-- Add Product Button (Level 2 only) -->
            <button
              v-if="isLevel2"
              @click="showAddProductModal = true"
              class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
            >
              <i class="fas fa-plus mr-2"></i>
              Agregar Producto
            </button>
            <!-- Export Button -->
            <button
              @click="exportInventory"
              class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center"
            >
              <i class="fas fa-download mr-2"></i>
              Exportar
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-boxes text-blue-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Total Productos</p>
              <p class="text-2xl font-bold text-gray-900">{{ totalProducts }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-exclamation-triangle text-yellow-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Stock Bajo</p>
              <p class="text-2xl font-bold text-gray-900">{{ lowStockProducts }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-clock text-red-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Por Vencer</p>
              <p class="text-2xl font-bold text-gray-900">{{ expiringProducts }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-dollar-sign text-green-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Valor Total</p>
              <p class="text-2xl font-bold text-gray-900">${{ totalValue }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters and Search -->
      <div class="bg-white rounded-lg shadow mb-6">
        <div class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <!-- Search -->
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-2">Buscar</label>
              <div class="relative">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Buscar por nombre, código o categoría..."
                  class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                <i class="fas fa-search absolute left-3 top-3 text-gray-400"></i>
              </div>
            </div>

            <!-- Category Filter -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Categoría</label>
              <select
                v-model="selectedCategory"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todas las categorías</option>
                <option v-for="category in categories" :key="category" :value="category">
                  {{ category }}
                </option>
              </select>
            </div>

            <!-- Stock Filter -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Estado</label>
              <select
                v-model="stockFilter"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todos</option>
                <option value="in_stock">En Stock</option>
                <option value="low_stock">Stock Bajo</option>
                <option value="out_of_stock">Sin Stock</option>
                <option value="expiring">Por Vencer</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Products Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            Productos ({{ filteredProducts.length }})
          </h3>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Producto
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Código
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Categoría
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stock
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Precio
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th v-if="isLevel2" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="product in paginatedProducts" :key="product.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <img
                        :src="product.image || '/placeholder-product.png'"
                        :alt="product.name"
                        class="h-10 w-10 rounded-lg object-cover"
                      >
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{{ product.name }}</div>
                      <div class="text-sm text-gray-500">{{ product.description }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ product.code }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ product.category }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">{{ product.stock }}</div>
                  <div class="text-xs text-gray-500">Min: {{ product.min_stock }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${{ product.price }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getStatusClass(product)" class="px-2 py-1 text-xs font-medium rounded-full">
                    {{ getStatusText(product) }}
                  </span>
                </td>
                <td v-if="isLevel2" class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div class="flex space-x-2">
                    <button
                      @click="editProduct(product)"
                      class="text-blue-600 hover:text-blue-900"
                      title="Editar"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      @click="adjustStock(product)"
                      class="text-green-600 hover:text-green-900"
                      title="Ajustar Stock"
                    >
                      <i class="fas fa-plus-minus"></i>
                    </button>
                    <button
                      @click="deleteProduct(product)"
                      class="text-red-600 hover:text-red-900"
                      title="Eliminar"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
          <div class="flex-1 flex justify-between sm:hidden">
            <button
              @click="previousPage"
              :disabled="currentPage === 1"
              class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Anterior
            </button>
            <button
              @click="nextPage"
              :disabled="currentPage === totalPages"
              class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
          <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p class="text-sm text-gray-700">
                Mostrando {{ startIndex }} a {{ endIndex }} de {{ filteredProducts.length }} productos
              </p>
            </div>
            <div>
              <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button
                  @click="previousPage"
                  :disabled="currentPage === 1"
                  class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  <i class="fas fa-chevron-left"></i>
                </button>
                <button
                  v-for="page in visiblePages"
                  :key="page"
                  @click="goToPage(page)"
                  :class="[
                    'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
                    page === currentPage
                      ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                      : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                  ]"
                >
                  {{ page }}
                </button>
                <button
                  @click="nextPage"
                  :disabled="currentPage === totalPages"
                  class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  <i class="fas fa-chevron-right"></i>
                </button>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Add/Edit Product Modal (Level 2 only) -->
    <div
      v-if="isLevel2 && (showAddProductModal || showEditProductModal)"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="closeModals"
    >
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ showAddProductModal ? 'Agregar Producto' : 'Editar Producto' }}
          </h3>
          
          <form @submit.prevent="saveProduct" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Nombre</label>
                <input
                  v-model="productForm.name"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Código</label>
                <input
                  v-model="productForm.code"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Categoría</label>
                <select
                  v-model="productForm.category"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Seleccionar categoría</option>
                  <option v-for="category in categories" :key="category" :value="category">
                    {{ category }}
                  </option>
                </select>
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Precio</label>
                <input
                  v-model="productForm.price"
                  type="number"
                  step="0.01"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Stock Actual</label>
                <input
                  v-model="productForm.stock"
                  type="number"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Stock Mínimo</label>
                <input
                  v-model="productForm.min_stock"
                  type="number"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Descripción</label>
              <textarea
                v-model="productForm.description"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              ></textarea>
            </div>
            
            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeModals"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {{ showAddProductModal ? 'Agregar' : 'Guardar' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Stock Adjustment Modal (Level 2 only) -->
    <div
      v-if="isLevel2 && showStockModal"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="closeModals"
    >
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 shadow-lg rounded-md bg-white" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            Ajustar Stock - {{ selectedProduct?.name }}
          </h3>
          
          <div class="mb-4">
            <p class="text-sm text-gray-600">Stock actual: <span class="font-medium">{{ selectedProduct?.stock }}</span></p>
          </div>
          
          <form @submit.prevent="saveStockAdjustment" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Tipo de Ajuste</label>
              <select
                v-model="stockAdjustment.type"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="add">Agregar Stock</option>
                <option value="subtract">Reducir Stock</option>
                <option value="set">Establecer Stock</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Cantidad</label>
              <input
                v-model="stockAdjustment.quantity"
                type="number"
                required
                min="0"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Motivo</label>
              <textarea
                v-model="stockAdjustment.reason"
                rows="3"
                required
                placeholder="Describe el motivo del ajuste..."
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              ></textarea>
            </div>
            
            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeModals"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Ajustar Stock
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Computed properties for access control
const isLevel2 = computed(() => authStore.hasScope('has_scope_inventory_level_2'))

// Reactive data
const products = ref([])
const categories = ref(['Bebidas', 'Snacks', 'Lácteos', 'Panadería', 'Limpieza', 'Otros'])
const searchQuery = ref('')
const selectedCategory = ref('')
const stockFilter = ref('')

// Pagination
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Modals
const showAddProductModal = ref(false)
const showEditProductModal = ref(false)
const showStockModal = ref(false)
const selectedProduct = ref(null)

// Forms
const productForm = ref({
  id: null,
  name: '',
  code: '',
  category: '',
  price: 0,
  stock: 0,
  min_stock: 0,
  description: ''
})

const stockAdjustment = ref({
  type: 'add',
  quantity: 0,
  reason: ''
})

// Stats computed properties
const totalProducts = computed(() => products.value.length)
const lowStockProducts = computed(() => 
  products.value.filter(p => p.stock <= p.min_stock).length
)
const expiringProducts = computed(() => 
  products.value.filter(p => p.expiry_date && new Date(p.expiry_date) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)).length
)
const totalValue = computed(() => 
  products.value.reduce((sum, p) => sum + (p.price * p.stock), 0).toFixed(2)
)

// Filtered products
const filteredProducts = computed(() => {
  let filtered = products.value

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(p => 
      p.name.toLowerCase().includes(query) ||
      p.code.toLowerCase().includes(query) ||
      p.category.toLowerCase().includes(query)
    )
  }

  // Category filter
  if (selectedCategory.value) {
    filtered = filtered.filter(p => p.category === selectedCategory.value)
  }

  // Stock filter
  if (stockFilter.value) {
    switch (stockFilter.value) {
      case 'in_stock':
        filtered = filtered.filter(p => p.stock > p.min_stock)
        break
      case 'low_stock':
        filtered = filtered.filter(p => p.stock <= p.min_stock && p.stock > 0)
        break
      case 'out_of_stock':
        filtered = filtered.filter(p => p.stock === 0)
        break
      case 'expiring':
        filtered = filtered.filter(p => 
          p.expiry_date && new Date(p.expiry_date) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
        )
        break
    }
  }

  return filtered
})

// Pagination computed properties
const totalPages = computed(() => Math.ceil(filteredProducts.value.length / itemsPerPage.value))
const startIndex = computed(() => (currentPage.value - 1) * itemsPerPage.value + 1)
const endIndex = computed(() => Math.min(currentPage.value * itemsPerPage.value, filteredProducts.value.length))

const paginatedProducts = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredProducts.value.slice(start, end)
})

const visiblePages = computed(() => {
  const pages = []
  const maxVisible = 5
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)
  
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

// Methods
const loadProducts = async () => {
  try {
    // Simulated API call - replace with actual API
    const response = await fetch('/api/products')
    if (response.ok) {
      products.value = await response.json()
    } else {
      // Fallback with mock data
      products.value = [
        {
          id: 1,
          name: 'Coca Cola 500ml',
          code: 'CC500',
          category: 'Bebidas',
          price: 2.50,
          stock: 45,
          min_stock: 10,
          description: 'Bebida gaseosa sabor cola',
          image: null,
          expiry_date: '2024-12-31'
        },
        {
          id: 2,
          name: 'Pan Integral',
          code: 'PI001',
          category: 'Panadería',
          price: 3.20,
          stock: 8,
          min_stock: 15,
          description: 'Pan integral artesanal',
          image: null,
          expiry_date: '2024-02-15'
        },
        {
          id: 3,
          name: 'Leche Entera 1L',
          code: 'LE1L',
          category: 'Lácteos',
          price: 1.80,
          stock: 0,
          min_stock: 20,
          description: 'Leche entera pasteurizada',
          image: null,
          expiry_date: '2024-02-20'
        },
        {
          id: 4,
          name: 'Detergente Líquido',
          code: 'DL500',
          category: 'Limpieza',
          price: 4.50,
          stock: 25,
          min_stock: 5,
          description: 'Detergente líquido para ropa',
          image: null,
          expiry_date: null
        }
      ]
    }
  } catch (error) {
    console.error('Error loading products:', error)
    // Use mock data on error
    products.value = []
  }
}

const getStatusClass = (product) => {
  if (product.stock === 0) {
    return 'bg-red-100 text-red-800'
  } else if (product.stock <= product.min_stock) {
    return 'bg-yellow-100 text-yellow-800'
  } else if (product.expiry_date && new Date(product.expiry_date) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)) {
    return 'bg-orange-100 text-orange-800'
  } else {
    return 'bg-green-100 text-green-800'
  }
}

const getStatusText = (product) => {
  if (product.stock === 0) {
    return 'Sin Stock'
  } else if (product.stock <= product.min_stock) {
    return 'Stock Bajo'
  } else if (product.expiry_date && new Date(product.expiry_date) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)) {
    return 'Por Vencer'
  } else {
    return 'En Stock'
  }
}

// Pagination methods
const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const goToPage = (page) => {
  currentPage.value = page
}

// Modal methods
const closeModals = () => {
  showAddProductModal.value = false
  showEditProductModal.value = false
  showStockModal.value = false
  selectedProduct.value = null
  resetProductForm()
  resetStockAdjustment()
}

const resetProductForm = () => {
  productForm.value = {
    id: null,
    name: '',
    code: '',
    category: '',
    price: 0,
    stock: 0,
    min_stock: 0,
    description: ''
  }
}

const resetStockAdjustment = () => {
  stockAdjustment.value = {
    type: 'add',
    quantity: 0,
    reason: ''
  }
}

// Product management methods (Level 2 only)
const editProduct = (product) => {
  if (!isLevel2.value) return
  
  selectedProduct.value = product
  productForm.value = { ...product }
  showEditProductModal.value = true
}

const deleteProduct = async (product) => {
  if (!isLevel2.value) return
  
  if (confirm(`¿Estás seguro de que deseas eliminar "${product.name}"?`)) {
    try {
      // API call to delete product
      const response = await fetch(`/api/products/${product.id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        products.value = products.value.filter(p => p.id !== product.id)
        alert('Producto eliminado exitosamente')
      } else {
        alert('Error al eliminar el producto')
      }
    } catch (error) {
      console.error('Error deleting product:', error)
      alert('Error al eliminar el producto')
    }
  }
}

const saveProduct = async () => {
  if (!isLevel2.value) return
  
  try {
    const isEditing = productForm.value.id !== null
    const url = isEditing ? `/api/products/${productForm.value.id}` : '/api/products'
    const method = isEditing ? 'PUT' : 'POST'
    
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(productForm.value)
    })
    
    if (response.ok) {
      const savedProduct = await response.json()
      
      if (isEditing) {
        const index = products.value.findIndex(p => p.id === savedProduct.id)
        if (index !== -1) {
          products.value[index] = savedProduct
        }
      } else {
        products.value.push(savedProduct)
      }
      
      closeModals()
      alert(isEditing ? 'Producto actualizado exitosamente' : 'Producto agregado exitosamente')
    } else {
      alert('Error al guardar el producto')
    }
  } catch (error) {
    console.error('Error saving product:', error)
    alert('Error al guardar el producto')
  }
}

// Stock adjustment methods (Level 2 only)
const adjustStock = (product) => {
  if (!isLevel2.value) return
  
  selectedProduct.value = product
  showStockModal.value = true
}

const saveStockAdjustment = async () => {
  if (!isLevel2.value || !selectedProduct.value) return
  
  try {
    let newStock = selectedProduct.value.stock
    
    switch (stockAdjustment.value.type) {
      case 'add':
        newStock += parseInt(stockAdjustment.value.quantity)
        break
      case 'subtract':
        newStock -= parseInt(stockAdjustment.value.quantity)
        break
      case 'set':
        newStock = parseInt(stockAdjustment.value.quantity)
        break
    }
    
    if (newStock < 0) {
      alert('El stock no puede ser negativo')
      return
    }
    
    const response = await fetch(`/api/products/${selectedProduct.value.id}/adjust-stock`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        new_stock: newStock,
        adjustment_type: stockAdjustment.value.type,
        quantity: stockAdjustment.value.quantity,
        reason: stockAdjustment.value.reason
      })
    })
    
    if (response.ok) {
      const updatedProduct = await response.json()
      const index = products.value.findIndex(p => p.id === updatedProduct.id)
      if (index !== -1) {
        products.value[index] = updatedProduct
      }
      
      closeModals()
      alert('Stock ajustado exitosamente')
    } else {
      alert('Error al ajustar el stock')
    }
  } catch (error) {
    console.error('Error adjusting stock:', error)
    alert('Error al ajustar el stock')
  }
}

// Export functionality
const exportInventory = () => {
  try {
    const csvContent = [
      ['Nombre', 'Código', 'Categoría', 'Stock', 'Stock Mínimo', 'Precio', 'Estado'].join(','),
      ...filteredProducts.value.map(product => [
        product.name,
        product.code,
        product.category,
        product.stock,
        product.min_stock,
        product.price,
        getStatusText(product)
      ].join(','))
    ].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `inventario_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Error exporting inventory:', error)
    alert('Error al exportar el inventario')
  }
}

// Lifecycle
onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
/* Custom styles if needed */
</style>