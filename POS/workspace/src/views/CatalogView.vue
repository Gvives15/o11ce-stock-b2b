<template>
  <div class="catalog-view">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Gestión de Catálogo</h1>
          <p class="text-gray-600 mt-1">Administra categorías, marcas y configuración del catálogo</p>
        </div>
        <div class="flex space-x-3">
          <button
            @click="openCategoryModal"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-plus"></i>
            <span>Nueva Categoría</span>
          </button>
          <button
            @click="openBrandModal"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-plus"></i>
            <span>Nueva Marca</span>
          </button>
          <button
            @click="exportCatalog"
            class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-download"></i>
            <span>Exportar</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="bg-white border-b border-gray-200">
      <nav class="flex space-x-8 px-6" aria-label="Tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors',
            activeTab === tab.id
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          ]"
        >
          <i :class="tab.icon" class="mr-2"></i>
          {{ tab.name }}
        </button>
      </nav>
    </div>

    <!-- Content -->
    <div class="p-6">
      <!-- Categories Tab -->
      <div v-if="activeTab === 'categories'" class="space-y-6">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-blue-100 text-blue-600">
                <i class="fas fa-layer-group text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Total Categorías</p>
                <p class="text-2xl font-bold text-gray-900">{{ totalCategories }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-green-100 text-green-600">
                <i class="fas fa-check-circle text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Activas</p>
                <p class="text-2xl font-bold text-gray-900">{{ activeCategories }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-purple-100 text-purple-600">
                <i class="fas fa-boxes text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Con Productos</p>
                <p class="text-2xl font-bold text-gray-900">{{ categoriesWithProducts }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
                <i class="fas fa-sitemap text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Subcategorías</p>
                <p class="text-2xl font-bold text-gray-900">{{ totalSubcategories }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Categories Tree -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900">Estructura de Categorías</h3>
              <div class="flex space-x-2">
                <button
                  @click="expandAll"
                  class="text-blue-600 hover:text-blue-800 text-sm"
                >
                  Expandir Todo
                </button>
                <button
                  @click="collapseAll"
                  class="text-gray-600 hover:text-gray-800 text-sm"
                >
                  Contraer Todo
                </button>
              </div>
            </div>
          </div>

          <div class="p-6">
            <div class="space-y-2">
              <div v-for="category in rootCategories" :key="category.id">
                <CategoryTreeItem
                  :category="category"
                  :level="0"
                  @edit="editCategory"
                  @delete="deleteCategory"
                  @add-subcategory="addSubcategory"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Brands Tab -->
      <div v-if="activeTab === 'brands'" class="space-y-6">
        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-indigo-100 text-indigo-600">
                <i class="fas fa-tags text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Total Marcas</p>
                <p class="text-2xl font-bold text-gray-900">{{ totalBrands }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-green-100 text-green-600">
                <i class="fas fa-check-circle text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Activas</p>
                <p class="text-2xl font-bold text-gray-900">{{ activeBrands }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-purple-100 text-purple-600">
                <i class="fas fa-boxes text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Con Productos</p>
                <p class="text-2xl font-bold text-gray-900">{{ brandsWithProducts }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-lg shadow p-6">
            <div class="flex items-center">
              <div class="p-3 rounded-full bg-red-100 text-red-600">
                <i class="fas fa-exclamation-triangle text-xl"></i>
              </div>
              <div class="ml-4">
                <p class="text-sm font-medium text-gray-600">Sin Productos</p>
                <p class="text-2xl font-bold text-gray-900">{{ brandsWithoutProducts }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Brands Grid -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900">Marcas</h3>
              <div class="flex space-x-2">
                <input
                  v-model="brandSearchTerm"
                  type="text"
                  placeholder="Buscar marcas..."
                  class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                <select
                  v-model="brandStatusFilter"
                  class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Todos los estados</option>
                  <option value="active">Activas</option>
                  <option value="inactive">Inactivas</option>
                </select>
              </div>
            </div>
          </div>

          <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              <div
                v-for="brand in filteredBrands"
                :key="brand.id"
                class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center space-x-3">
                    <div class="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                      <i v-if="!brand.logo" class="fas fa-tag text-gray-400 text-xl"></i>
                      <img v-else :src="brand.logo" :alt="brand.name" class="w-full h-full object-cover rounded-lg">
                    </div>
                    <div>
                      <h4 class="font-medium text-gray-900">{{ brand.name }}</h4>
                      <p class="text-sm text-gray-500">{{ brand.productCount }} productos</p>
                    </div>
                  </div>
                  <div class="flex space-x-1">
                    <button
                      @click="editBrand(brand)"
                      class="text-blue-600 hover:text-blue-800 p-1"
                      title="Editar"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      @click="deleteBrand(brand)"
                      class="text-red-600 hover:text-red-800 p-1"
                      title="Eliminar"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </div>
                
                <div class="flex justify-between items-center">
                  <span :class="getBrandStatusClass(brand.status)" class="px-2 py-1 text-xs font-semibold rounded-full">
                    {{ getBrandStatusLabel(brand.status) }}
                  </span>
                  <span class="text-xs text-gray-500">
                    Creada: {{ formatDate(brand.createdAt) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Settings Tab -->
      <div v-if="activeTab === 'settings'" class="space-y-6">
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">Configuración del Catálogo</h3>
          
          <form @submit.prevent="saveCatalogSettings" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Categoría por defecto para nuevos productos
                </label>
                <select
                  v-model="catalogSettings.defaultCategoryId"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Seleccionar categoría</option>
                  <option v-for="category in allCategories" :key="category.id" :value="category.id">
                    {{ category.name }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Marca por defecto para nuevos productos
                </label>
                <select
                  v-model="catalogSettings.defaultBrandId"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Seleccionar marca</option>
                  <option v-for="brand in brands" :key="brand.id" :value="brand.id">
                    {{ brand.name }}
                  </option>
                </select>
              </div>

              <div>
                <label class="flex items-center">
                  <input
                    v-model="catalogSettings.autoGenerateSkus"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <span class="ml-2 text-sm text-gray-700">Auto-generar SKUs para nuevos productos</span>
                </label>
              </div>

              <div>
                <label class="flex items-center">
                  <input
                    v-model="catalogSettings.requireBrandForProducts"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <span class="ml-2 text-sm text-gray-700">Requerir marca para todos los productos</span>
                </label>
              </div>

              <div>
                <label class="flex items-center">
                  <input
                    v-model="catalogSettings.allowEmptyCategories"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <span class="ml-2 text-sm text-gray-700">Permitir categorías vacías</span>
                </label>
              </div>

              <div>
                <label class="flex items-center">
                  <input
                    v-model="catalogSettings.enableProductVariants"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <span class="ml-2 text-sm text-gray-700">Habilitar variantes de productos</span>
                </label>
              </div>
            </div>

            <div class="flex justify-end">
              <button
                type="submit"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Guardar Configuración
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Category Modal -->
    <div v-if="showCategoryModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ editingCategory ? 'Editar Categoría' : 'Nueva Categoría' }}
            </h3>
            <button @click="closeCategoryModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="saveCategory" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
              <input
                v-model="categoryForm.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
              <textarea
                v-model="categoryForm.description"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Categoría Padre</label>
              <select
                v-model="categoryForm.parentId"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Sin categoría padre (Raíz)</option>
                <option v-for="category in availableParentCategories" :key="category.id" :value="category.id">
                  {{ category.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="flex items-center">
                <input
                  v-model="categoryForm.isActive"
                  type="checkbox"
                  class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                >
                <span class="ml-2 text-sm text-gray-700">Categoría activa</span>
              </label>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeCategoryModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {{ editingCategory ? 'Actualizar' : 'Crear' }} Categoría
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Brand Modal -->
    <div v-if="showBrandModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ editingBrand ? 'Editar Marca' : 'Nueva Marca' }}
            </h3>
            <button @click="closeBrandModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="saveBrand" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
              <input
                v-model="brandForm.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
              <textarea
                v-model="brandForm.description"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">URL del Logo</label>
              <input
                v-model="brandForm.logo"
                type="url"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>

            <div>
              <label class="flex items-center">
                <input
                  v-model="brandForm.isActive"
                  type="checkbox"
                  class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                >
                <span class="ml-2 text-sm text-gray-700">Marca activa</span>
              </label>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeBrandModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                {{ editingBrand ? 'Actualizar' : 'Crear' }} Marca
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Reactive data
const activeTab = ref('categories')
const categories = ref([])
const brands = ref([])
const catalogSettings = ref({
  defaultCategoryId: '',
  defaultBrandId: '',
  autoGenerateSkus: true,
  requireBrandForProducts: false,
  allowEmptyCategories: true,
  enableProductVariants: false
})

// Search and filters
const brandSearchTerm = ref('')
const brandStatusFilter = ref('')

// Modal states
const showCategoryModal = ref(false)
const showBrandModal = ref(false)
const editingCategory = ref(false)
const editingBrand = ref(false)
const selectedCategory = ref(null)
const selectedBrand = ref(null)

// Form data
const categoryForm = ref({
  name: '',
  description: '',
  parentId: '',
  isActive: true
})

const brandForm = ref({
  name: '',
  description: '',
  logo: '',
  isActive: true
})

// Tabs configuration
const tabs = [
  { id: 'categories', name: 'Categorías', icon: 'fas fa-layer-group' },
  { id: 'brands', name: 'Marcas', icon: 'fas fa-tags' },
  { id: 'settings', name: 'Configuración', icon: 'fas fa-cog' }
]

// Computed properties
const totalCategories = computed(() => categories.value.length)
const activeCategories = computed(() => categories.value.filter(c => c.isActive).length)
const categoriesWithProducts = computed(() => categories.value.filter(c => c.productCount > 0).length)
const totalSubcategories = computed(() => categories.value.filter(c => c.parentId).length)

const totalBrands = computed(() => brands.value.length)
const activeBrands = computed(() => brands.value.filter(b => b.isActive).length)
const brandsWithProducts = computed(() => brands.value.filter(b => b.productCount > 0).length)
const brandsWithoutProducts = computed(() => brands.value.filter(b => b.productCount === 0).length)

const rootCategories = computed(() => {
  return categories.value.filter(c => !c.parentId)
})

const allCategories = computed(() => {
  return categories.value.filter(c => c.isActive)
})

const availableParentCategories = computed(() => {
  if (editingCategory.value && selectedCategory.value) {
    return categories.value.filter(c => c.id !== selectedCategory.value.id && c.isActive)
  }
  return categories.value.filter(c => c.isActive)
})

const filteredBrands = computed(() => {
  let filtered = brands.value

  if (brandSearchTerm.value) {
    const search = brandSearchTerm.value.toLowerCase()
    filtered = filtered.filter(brand =>
      brand.name.toLowerCase().includes(search) ||
      brand.description?.toLowerCase().includes(search)
    )
  }

  if (brandStatusFilter.value) {
    filtered = filtered.filter(brand => 
      brandStatusFilter.value === 'active' ? brand.isActive : !brand.isActive
    )
  }

  return filtered
})

// Methods
const loadData = async () => {
  try {
    // TODO: Replace with actual API calls
    // const categoriesResponse = await api.get('/categories')
    // categories.value = categoriesResponse.data
    
    // const brandsResponse = await api.get('/brands')
    // brands.value = brandsResponse.data
    
    // const settingsResponse = await api.get('/catalog/settings')
    // catalogSettings.value = settingsResponse.data
    
    // Mock data for development
    categories.value = [
      {
        id: 1,
        name: 'Electrónicos',
        description: 'Productos electrónicos y tecnológicos',
        parentId: null,
        isActive: true,
        productCount: 45,
        createdAt: '2023-01-15'
      },
      {
        id: 2,
        name: 'Smartphones',
        description: 'Teléfonos inteligentes',
        parentId: 1,
        isActive: true,
        productCount: 25,
        createdAt: '2023-01-20'
      },
      {
        id: 3,
        name: 'Laptops',
        description: 'Computadoras portátiles',
        parentId: 1,
        isActive: true,
        productCount: 20,
        createdAt: '2023-01-25'
      },
      {
        id: 4,
        name: 'Ropa',
        description: 'Prendas de vestir',
        parentId: null,
        isActive: true,
        productCount: 120,
        createdAt: '2023-02-01'
      },
      {
        id: 5,
        name: 'Camisetas',
        description: 'Camisetas y polos',
        parentId: 4,
        isActive: true,
        productCount: 60,
        createdAt: '2023-02-05'
      },
      {
        id: 6,
        name: 'Pantalones',
        description: 'Pantalones y jeans',
        parentId: 4,
        isActive: true,
        productCount: 40,
        createdAt: '2023-02-10'
      },
      {
        id: 7,
        name: 'Hogar',
        description: 'Artículos para el hogar',
        parentId: null,
        isActive: false,
        productCount: 0,
        createdAt: '2023-03-01'
      }
    ]

    brands.value = [
      {
        id: 1,
        name: 'Samsung',
        description: 'Marca líder en tecnología',
        logo: '',
        isActive: true,
        productCount: 35,
        createdAt: '2023-01-10'
      },
      {
        id: 2,
        name: 'Apple',
        description: 'Innovación y diseño',
        logo: '',
        isActive: true,
        productCount: 28,
        createdAt: '2023-01-12'
      },
      {
        id: 3,
        name: 'Nike',
        description: 'Ropa deportiva premium',
        logo: '',
        isActive: true,
        productCount: 45,
        createdAt: '2023-01-15'
      },
      {
        id: 4,
        name: 'Adidas',
        description: 'Marca deportiva internacional',
        logo: '',
        isActive: true,
        productCount: 38,
        createdAt: '2023-01-18'
      },
      {
        id: 5,
        name: 'Sony',
        description: 'Electrónicos y entretenimiento',
        logo: '',
        isActive: false,
        productCount: 0,
        createdAt: '2023-02-01'
      }
    ]
  } catch (error) {
    console.error('Error loading data:', error)
  }
}

// Category methods
const openCategoryModal = () => {
  editingCategory.value = false
  categoryForm.value = {
    name: '',
    description: '',
    parentId: '',
    isActive: true
  }
  showCategoryModal.value = true
}

const closeCategoryModal = () => {
  showCategoryModal.value = false
  editingCategory.value = false
  selectedCategory.value = null
}

const editCategory = (category: any) => {
  editingCategory.value = true
  selectedCategory.value = category
  categoryForm.value = { ...category, parentId: category.parentId || '' }
  showCategoryModal.value = true
}

const deleteCategory = async (category: any) => {
  if (category.productCount > 0) {
    alert('No se puede eliminar una categoría que tiene productos asociados.')
    return
  }

  if (confirm(`¿Estás seguro de que deseas eliminar la categoría "${category.name}"?`)) {
    try {
      // TODO: Replace with actual API call
      // await api.delete(`/categories/${category.id}`)
      
      categories.value = categories.value.filter(c => c.id !== category.id)
      console.log('Categoría eliminada:', category.name)
    } catch (error) {
      console.error('Error deleting category:', error)
    }
  }
}

const addSubcategory = (parentCategory: any) => {
  editingCategory.value = false
  categoryForm.value = {
    name: '',
    description: '',
    parentId: parentCategory.id,
    isActive: true
  }
  showCategoryModal.value = true
}

const saveCategory = async () => {
  try {
    if (editingCategory.value) {
      // TODO: Replace with actual API call
      // await api.put(`/categories/${selectedCategory.value.id}`, categoryForm.value)
      
      const index = categories.value.findIndex(c => c.id === selectedCategory.value.id)
      if (index !== -1) {
        categories.value[index] = { ...categories.value[index], ...categoryForm.value }
      }
      console.log('Categoría actualizada')
    } else {
      // TODO: Replace with actual API call
      // const response = await api.post('/categories', categoryForm.value)
      
      const newCategory = {
        id: Date.now(),
        ...categoryForm.value,
        productCount: 0,
        createdAt: new Date().toISOString().split('T')[0]
      }
      categories.value.push(newCategory)
      console.log('Categoría creada')
    }
    
    closeCategoryModal()
  } catch (error) {
    console.error('Error saving category:', error)
  }
}

// Brand methods
const openBrandModal = () => {
  editingBrand.value = false
  brandForm.value = {
    name: '',
    description: '',
    logo: '',
    isActive: true
  }
  showBrandModal.value = true
}

const closeBrandModal = () => {
  showBrandModal.value = false
  editingBrand.value = false
  selectedBrand.value = null
}

const editBrand = (brand: any) => {
  editingBrand.value = true
  selectedBrand.value = brand
  brandForm.value = { ...brand }
  showBrandModal.value = true
}

const deleteBrand = async (brand: any) => {
  if (brand.productCount > 0) {
    alert('No se puede eliminar una marca que tiene productos asociados.')
    return
  }

  if (confirm(`¿Estás seguro de que deseas eliminar la marca "${brand.name}"?`)) {
    try {
      // TODO: Replace with actual API call
      // await api.delete(`/brands/${brand.id}`)
      
      brands.value = brands.value.filter(b => b.id !== brand.id)
      console.log('Marca eliminada:', brand.name)
    } catch (error) {
      console.error('Error deleting brand:', error)
    }
  }
}

const saveBrand = async () => {
  try {
    if (editingBrand.value) {
      // TODO: Replace with actual API call
      // await api.put(`/brands/${selectedBrand.value.id}`, brandForm.value)
      
      const index = brands.value.findIndex(b => b.id === selectedBrand.value.id)
      if (index !== -1) {
        brands.value[index] = { ...brands.value[index], ...brandForm.value }
      }
      console.log('Marca actualizada')
    } else {
      // TODO: Replace with actual API call
      // const response = await api.post('/brands', brandForm.value)
      
      const newBrand = {
        id: Date.now(),
        ...brandForm.value,
        productCount: 0,
        createdAt: new Date().toISOString().split('T')[0]
      }
      brands.value.push(newBrand)
      console.log('Marca creada')
    }
    
    closeBrandModal()
  } catch (error) {
    console.error('Error saving brand:', error)
  }
}

const getBrandStatusClass = (isActive: boolean) => {
  return isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
}

const getBrandStatusLabel = (isActive: boolean) => {
  return isActive ? 'Activa' : 'Inactiva'
}

// Utility methods
const formatDate = (dateString: string) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('es-ES')
}

const expandAll = () => {
  // TODO: Implement expand all functionality
  console.log('Expandir todas las categorías')
}

const collapseAll = () => {
  // TODO: Implement collapse all functionality
  console.log('Contraer todas las categorías')
}

const exportCatalog = () => {
  const csvContent = [
    ['Tipo', 'Nombre', 'Descripción', 'Estado', 'Productos', 'Fecha Creación'].join(','),
    ...categories.value.map(category => [
      'Categoría',
      category.name,
      category.description || '',
      category.isActive ? 'Activa' : 'Inactiva',
      category.productCount,
      formatDate(category.createdAt)
    ].join(',')),
    ...brands.value.map(brand => [
      'Marca',
      brand.name,
      brand.description || '',
      brand.isActive ? 'Activa' : 'Inactiva',
      brand.productCount,
      formatDate(brand.createdAt)
    ].join(','))
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `catalogo_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const saveCatalogSettings = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.put('/catalog/settings', catalogSettings.value)
    
    console.log('Configuración guardada:', catalogSettings.value)
  } catch (error) {
    console.error('Error saving settings:', error)
  }
}

// Lifecycle
onMounted(() => {
  loadData()
})
</script>

<!-- Category Tree Item Component (inline for simplicity) -->
<script lang="ts">
const CategoryTreeItem = {
  name: 'CategoryTreeItem',
  props: ['category', 'level'],
  emits: ['edit', 'delete', 'add-subcategory'],
  template: `
    <div class="category-tree-item">
      <div class="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded" :style="{ marginLeft: level * 20 + 'px' }">
        <div class="flex items-center space-x-3">
          <i class="fas fa-folder text-gray-400"></i>
          <div>
            <span class="font-medium text-gray-900">{{ category.name }}</span>
            <span v-if="category.description" class="text-sm text-gray-500 ml-2">{{ category.description }}</span>
          </div>
          <span :class="category.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'" class="px-2 py-1 text-xs font-semibold rounded-full">
            {{ category.isActive ? 'Activa' : 'Inactiva' }}
          </span>
          <span class="text-sm text-gray-500">{{ category.productCount }} productos</span>
        </div>
        <div class="flex space-x-1">
          <button @click="$emit('add-subcategory', category)" class="text-blue-600 hover:text-blue-800 p-1" title="Agregar subcategoría">
            <i class="fas fa-plus"></i>
          </button>
          <button @click="$emit('edit', category)" class="text-indigo-600 hover:text-indigo-800 p-1" title="Editar">
            <i class="fas fa-edit"></i>
          </button>
          <button @click="$emit('delete', category)" class="text-red-600 hover:text-red-800 p-1" title="Eliminar">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
      <div v-for="subcategory in getSubcategories(category.id)" :key="subcategory.id">
        <CategoryTreeItem 
          :category="subcategory" 
          :level="level + 1"
          @edit="$emit('edit', $event)"
          @delete="$emit('delete', $event)"
          @add-subcategory="$emit('add-subcategory', $event)"
        />
      </div>
    </div>
  `,
  inject: ['categories'],
  methods: {
    getSubcategories(parentId) {
      return this.categories.filter(c => c.parentId === parentId)
    }
  }
}
</script>