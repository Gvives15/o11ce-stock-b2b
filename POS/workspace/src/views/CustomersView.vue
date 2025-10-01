<template>
  <div class="customers-view">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ canManageCustomers ? 'Gestión de Clientes' : 'Consulta de Clientes' }}
          </h1>
          <p class="text-gray-600 mt-1">
            {{ canManageCustomers ? 'Administra la base de datos de clientes' : 'Consulta información de clientes' }}
          </p>
        </div>
        <div class="flex space-x-3">
          <button
            v-if="canManageCustomers"
            @click="openAddCustomerModal"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-plus"></i>
            <span>Nuevo Cliente</span>
          </button>
          <button
            @click="exportCustomers"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-download"></i>
            <span>Exportar</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-blue-100 text-blue-600">
              <i class="fas fa-users text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Total Clientes</p>
              <p class="text-2xl font-bold text-gray-900">{{ totalCustomers }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-green-100 text-green-600">
              <i class="fas fa-user-check text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Clientes Activos</p>
              <p class="text-2xl font-bold text-gray-900">{{ activeCustomers }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
              <i class="fas fa-star text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Clientes VIP</p>
              <p class="text-2xl font-bold text-gray-900">{{ vipCustomers }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-purple-100 text-purple-600">
              <i class="fas fa-dollar-sign text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Ventas Totales</p>
              <p class="text-2xl font-bold text-gray-900">${{ totalSales.toLocaleString() }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Buscar</label>
            <div class="relative">
              <input
                v-model="searchTerm"
                type="text"
                placeholder="Nombre, email o teléfono..."
                class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
              <i class="fas fa-search absolute left-3 top-3 text-gray-400"></i>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Tipo</label>
            <select
              v-model="selectedType"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todos los tipos</option>
              <option value="regular">Regular</option>
              <option value="vip">VIP</option>
              <option value="mayorista">Mayorista</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Estado</label>
            <select
              v-model="selectedStatus"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todos los estados</option>
              <option value="active">Activo</option>
              <option value="inactive">Inactivo</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Ciudad</label>
            <select
              v-model="selectedCity"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Todas las ciudades</option>
              <option v-for="city in cities" :key="city" :value="city">{{ city }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Customers Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contacto
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Compras
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Última Compra
                </th>
                <th v-if="canManageCustomers" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="customer in paginatedCustomers" :key="customer.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                      <div class="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                        <i class="fas fa-user text-gray-600"></i>
                      </div>
                    </div>
                    <div class="ml-4">
                      <div class="text-sm font-medium text-gray-900">{{ customer.name }}</div>
                      <div class="text-sm text-gray-500">{{ customer.document }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">{{ customer.email }}</div>
                  <div class="text-sm text-gray-500">{{ customer.phone }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getTypeClass(customer.type)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                    {{ getTypeLabel(customer.type) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getStatusClass(customer.status)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                    {{ getStatusLabel(customer.status) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  ${{ customer.totalPurchases.toLocaleString() }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ formatDate(customer.lastPurchase) }}
                </td>
                <td v-if="canManageCustomers" class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div class="flex justify-end space-x-2">
                    <button
                      @click="viewCustomer(customer)"
                      class="text-blue-600 hover:text-blue-900 p-1"
                      title="Ver detalles"
                    >
                      <i class="fas fa-eye"></i>
                    </button>
                    <button
                      @click="editCustomer(customer)"
                      class="text-indigo-600 hover:text-indigo-900 p-1"
                      title="Editar"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      @click="deleteCustomer(customer)"
                      class="text-red-600 hover:text-red-900 p-1"
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
                Mostrando <span class="font-medium">{{ startIndex }}</span> a <span class="font-medium">{{ endIndex }}</span> de
                <span class="font-medium">{{ filteredCustomers.length }}</span> resultados
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
    </div>

    <!-- Add/Edit Customer Modal -->
    <div v-if="showCustomerModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ editingCustomer ? 'Editar Cliente' : 'Nuevo Cliente' }}
            </h3>
            <button @click="closeCustomerModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="saveCustomer" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                <input
                  v-model="customerForm.name"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Documento *</label>
                <input
                  v-model="customerForm.document"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  v-model="customerForm.email"
                  type="email"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                <input
                  v-model="customerForm.phone"
                  type="tel"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                <select
                  v-model="customerForm.type"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="regular">Regular</option>
                  <option value="vip">VIP</option>
                  <option value="mayorista">Mayorista</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                <select
                  v-model="customerForm.status"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="active">Activo</option>
                  <option value="inactive">Inactivo</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
              <textarea
                v-model="customerForm.address"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              ></textarea>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Ciudad</label>
                <input
                  v-model="customerForm.city"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Código Postal</label>
                <input
                  v-model="customerForm.zipCode"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
              </div>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeCustomerModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {{ editingCustomer ? 'Actualizar' : 'Crear' }} Cliente
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- View Customer Modal -->
    <div v-if="showViewModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Detalles del Cliente</h3>
            <button @click="closeViewModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div v-if="selectedCustomer" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Nombre</label>
                <p class="mt-1 text-sm text-gray-900">{{ selectedCustomer.name }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Documento</label>
                <p class="mt-1 text-sm text-gray-900">{{ selectedCustomer.document }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Email</label>
                <p class="mt-1 text-sm text-gray-900">{{ selectedCustomer.email || 'No especificado' }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Teléfono</label>
                <p class="mt-1 text-sm text-gray-900">{{ selectedCustomer.phone || 'No especificado' }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Tipo</label>
                <span :class="getTypeClass(selectedCustomer.type)" class="mt-1 px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ getTypeLabel(selectedCustomer.type) }}
                </span>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Estado</label>
                <span :class="getStatusClass(selectedCustomer.status)" class="mt-1 px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ getStatusLabel(selectedCustomer.status) }}
                </span>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700">Dirección</label>
              <p class="mt-1 text-sm text-gray-900">{{ selectedCustomer.address || 'No especificada' }}</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Ciudad</label>
                <p class="mt-1 text-sm text-gray-900">{{ selectedCustomer.city || 'No especificada' }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Total Compras</label>
                <p class="mt-1 text-sm text-gray-900">${{ selectedCustomer.totalPurchases.toLocaleString() }}</p>
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">Fecha de Registro</label>
                <p class="mt-1 text-sm text-gray-900">{{ formatDate(selectedCustomer.createdAt) }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700">Última Compra</label>
                <p class="mt-1 text-sm text-gray-900">{{ formatDate(selectedCustomer.lastPurchase) }}</p>
              </div>
            </div>
          </div>

          <div class="flex justify-end pt-4">
            <button
              @click="closeViewModal"
              class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Cerrar
            </button>
          </div>
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
const customers = ref([])
const searchTerm = ref('')
const selectedType = ref('')
const selectedStatus = ref('')
const selectedCity = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Modal states
const showCustomerModal = ref(false)
const showViewModal = ref(false)
const editingCustomer = ref(false)
const selectedCustomer = ref(null)

// Form data
const customerForm = ref({
  name: '',
  document: '',
  email: '',
  phone: '',
  type: 'regular',
  status: 'active',
  address: '',
  city: '',
  zipCode: ''
})

// Computed properties
const canManageCustomers = computed(() => {
  return authStore.hasScope('admin') || 
         authStore.hasScope('encargado') || 
         authStore.hasScope('has_scope_customers')
})

const totalCustomers = computed(() => customers.value.length)
const activeCustomers = computed(() => customers.value.filter(c => c.status === 'active').length)
const vipCustomers = computed(() => customers.value.filter(c => c.type === 'vip').length)
const totalSales = computed(() => customers.value.reduce((sum, c) => sum + c.totalPurchases, 0))

const cities = computed(() => {
  const citySet = new Set(customers.value.map(c => c.city).filter(Boolean))
  return Array.from(citySet).sort()
})

const filteredCustomers = computed(() => {
  let filtered = customers.value

  if (searchTerm.value) {
    const search = searchTerm.value.toLowerCase()
    filtered = filtered.filter(customer =>
      customer.name.toLowerCase().includes(search) ||
      customer.email?.toLowerCase().includes(search) ||
      customer.phone?.includes(search) ||
      customer.document.includes(search)
    )
  }

  if (selectedType.value) {
    filtered = filtered.filter(customer => customer.type === selectedType.value)
  }

  if (selectedStatus.value) {
    filtered = filtered.filter(customer => customer.status === selectedStatus.value)
  }

  if (selectedCity.value) {
    filtered = filtered.filter(customer => customer.city === selectedCity.value)
  }

  return filtered
})

const totalPages = computed(() => Math.ceil(filteredCustomers.value.length / itemsPerPage.value))

const paginatedCustomers = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredCustomers.value.slice(start, end)
})

const startIndex = computed(() => (currentPage.value - 1) * itemsPerPage.value + 1)
const endIndex = computed(() => Math.min(currentPage.value * itemsPerPage.value, filteredCustomers.value.length))

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

// Methods
const loadCustomers = async () => {
  try {
    // TODO: Replace with actual API call
    // const response = await api.get('/customers')
    // customers.value = response.data
    
    // Mock data for development
    customers.value = [
      {
        id: 1,
        name: 'Juan Pérez',
        document: '12345678',
        email: 'juan@email.com',
        phone: '555-0001',
        type: 'regular',
        status: 'active',
        address: 'Calle 123 #45-67',
        city: 'Bogotá',
        zipCode: '110111',
        totalPurchases: 1250000,
        lastPurchase: '2024-01-15',
        createdAt: '2023-06-15'
      },
      {
        id: 2,
        name: 'María García',
        document: '87654321',
        email: 'maria@email.com',
        phone: '555-0002',
        type: 'vip',
        status: 'active',
        address: 'Carrera 45 #12-34',
        city: 'Medellín',
        zipCode: '050001',
        totalPurchases: 3500000,
        lastPurchase: '2024-01-20',
        createdAt: '2023-03-10'
      },
      {
        id: 3,
        name: 'Carlos López',
        document: '11223344',
        email: 'carlos@email.com',
        phone: '555-0003',
        type: 'mayorista',
        status: 'active',
        address: 'Avenida 68 #23-45',
        city: 'Cali',
        zipCode: '760001',
        totalPurchases: 8750000,
        lastPurchase: '2024-01-18',
        createdAt: '2023-01-20'
      },
      {
        id: 4,
        name: 'Ana Rodríguez',
        document: '55667788',
        email: 'ana@email.com',
        phone: '555-0004',
        type: 'regular',
        status: 'inactive',
        address: 'Calle 50 #30-20',
        city: 'Barranquilla',
        zipCode: '080001',
        totalPurchases: 450000,
        lastPurchase: '2023-11-30',
        createdAt: '2023-08-05'
      },
      {
        id: 5,
        name: 'Luis Martínez',
        document: '99887766',
        email: 'luis@email.com',
        phone: '555-0005',
        type: 'vip',
        status: 'active',
        address: 'Transversal 15 #8-90',
        city: 'Bogotá',
        zipCode: '110221',
        totalPurchases: 2100000,
        lastPurchase: '2024-01-22',
        createdAt: '2023-04-12'
      }
    ]
  } catch (error) {
    console.error('Error loading customers:', error)
  }
}

const getTypeClass = (type: string) => {
  const classes = {
    regular: 'bg-gray-100 text-gray-800',
    vip: 'bg-yellow-100 text-yellow-800',
    mayorista: 'bg-purple-100 text-purple-800'
  }
  return classes[type] || classes.regular
}

const getTypeLabel = (type: string) => {
  const labels = {
    regular: 'Regular',
    vip: 'VIP',
    mayorista: 'Mayorista'
  }
  return labels[type] || 'Regular'
}

const getStatusClass = (status: string) => {
  const classes = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-red-100 text-red-800'
  }
  return classes[status] || classes.active
}

const getStatusLabel = (status: string) => {
  const labels = {
    active: 'Activo',
    inactive: 'Inactivo'
  }
  return labels[status] || 'Activo'
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('es-ES')
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

const goToPage = (page: number) => {
  currentPage.value = page
}

// Modal methods
const openAddCustomerModal = () => {
  editingCustomer.value = false
  customerForm.value = {
    name: '',
    document: '',
    email: '',
    phone: '',
    type: 'regular',
    status: 'active',
    address: '',
    city: '',
    zipCode: ''
  }
  showCustomerModal.value = true
}

const closeCustomerModal = () => {
  showCustomerModal.value = false
  editingCustomer.value = false
  selectedCustomer.value = null
}

const viewCustomer = (customer: any) => {
  selectedCustomer.value = customer
  showViewModal.value = true
}

const closeViewModal = () => {
  showViewModal.value = false
  selectedCustomer.value = null
}

const editCustomer = (customer: any) => {
  editingCustomer.value = true
  selectedCustomer.value = customer
  customerForm.value = { ...customer }
  showCustomerModal.value = true
}

const deleteCustomer = async (customer: any) => {
  if (confirm(`¿Estás seguro de que deseas eliminar al cliente ${customer.name}?`)) {
    try {
      // TODO: Replace with actual API call
      // await api.delete(`/customers/${customer.id}`)
      
      customers.value = customers.value.filter(c => c.id !== customer.id)
      console.log('Cliente eliminado:', customer.name)
    } catch (error) {
      console.error('Error deleting customer:', error)
    }
  }
}

const saveCustomer = async () => {
  try {
    if (editingCustomer.value) {
      // TODO: Replace with actual API call
      // await api.put(`/customers/${selectedCustomer.value.id}`, customerForm.value)
      
      const index = customers.value.findIndex(c => c.id === selectedCustomer.value.id)
      if (index !== -1) {
        customers.value[index] = { ...customers.value[index], ...customerForm.value }
      }
      console.log('Cliente actualizado')
    } else {
      // TODO: Replace with actual API call
      // const response = await api.post('/customers', customerForm.value)
      
      const newCustomer = {
        id: Date.now(),
        ...customerForm.value,
        totalPurchases: 0,
        lastPurchase: null,
        createdAt: new Date().toISOString().split('T')[0]
      }
      customers.value.push(newCustomer)
      console.log('Cliente creado')
    }
    
    closeCustomerModal()
  } catch (error) {
    console.error('Error saving customer:', error)
  }
}

const exportCustomers = () => {
  const csvContent = [
    ['Nombre', 'Documento', 'Email', 'Teléfono', 'Tipo', 'Estado', 'Ciudad', 'Total Compras', 'Última Compra'].join(','),
    ...filteredCustomers.value.map(customer => [
      customer.name,
      customer.document,
      customer.email || '',
      customer.phone || '',
      getTypeLabel(customer.type),
      getStatusLabel(customer.status),
      customer.city || '',
      customer.totalPurchases,
      formatDate(customer.lastPurchase)
    ].join(','))
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `clientes_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Lifecycle
onMounted(() => {
  loadCustomers()
})
</script>