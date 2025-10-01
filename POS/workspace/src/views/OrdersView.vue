<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">Pedidos</h1>
            <p class="text-sm text-gray-600 mt-1">
              {{ canManageOrders ? 'Gestión completa de pedidos' : 'Consulta de pedidos' }}
            </p>
          </div>
          <div class="flex items-center space-x-4">
            <!-- Create Order Button -->
            <button
              v-if="canManageOrders"
              @click="showCreateOrderModal = true"
              class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
            >
              <i class="fas fa-plus mr-2"></i>
              Nuevo Pedido
            </button>
            <!-- Export Button -->
            <button
              @click="exportOrders"
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
            <i class="fas fa-shopping-cart text-blue-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Total Pedidos</p>
              <p class="text-2xl font-bold text-gray-900">{{ totalOrders }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-clock text-yellow-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Pendientes</p>
              <p class="text-2xl font-bold text-gray-900">{{ pendingOrders }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-truck text-orange-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">En Proceso</p>
              <p class="text-2xl font-bold text-gray-900">{{ processingOrders }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <i class="fas fa-dollar-sign text-green-600 text-2xl mr-4"></i>
            <div>
              <p class="text-sm font-medium text-gray-600">Total Hoy</p>
              <p class="text-2xl font-bold text-gray-900">${{ todayTotal }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters and Search -->
      <div class="bg-white rounded-lg shadow mb-6">
        <div class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
            <!-- Search -->
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-2">Buscar</label>
              <div class="relative">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Buscar por número, cliente o vendedor..."
                  class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                <i class="fas fa-search absolute left-3 top-3 text-gray-400"></i>
              </div>
            </div>

            <!-- Status Filter -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Estado</label>
              <select
                v-model="statusFilter"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Todos los estados</option>
                <option value="pending">Pendiente</option>
                <option value="processing">En Proceso</option>
                <option value="completed">Completado</option>
                <option value="cancelled">Cancelado</option>
              </select>
            </div>

            <!-- Date Range -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Fecha Desde</label>
              <input
                v-model="dateFrom"
                type="date"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Fecha Hasta</label>
              <input
                v-model="dateTo"
                type="date"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
            </div>
          </div>
        </div>
      </div>

      <!-- Orders Table -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            Pedidos ({{ filteredOrders.length }})
          </h3>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pedido
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Vendedor
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="order in paginatedOrders" :key="order.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900">#{{ order.order_number }}</div>
                  <div class="text-sm text-gray-500">{{ order.items.length }} productos</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900">{{ order.customer_name }}</div>
                  <div class="text-sm text-gray-500">{{ order.customer_phone }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ order.salesperson }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm text-gray-900">{{ formatDate(order.created_at) }}</div>
                  <div class="text-sm text-gray-500">{{ formatTime(order.created_at) }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  ${{ order.total.toFixed(2) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getStatusClass(order.status)" class="px-2 py-1 text-xs font-medium rounded-full">
                    {{ getStatusText(order.status) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div class="flex space-x-2">
                    <button
                      @click="viewOrder(order)"
                      class="text-blue-600 hover:text-blue-900"
                      title="Ver Detalles"
                    >
                      <i class="fas fa-eye"></i>
                    </button>
                    <button
                      v-if="canManageOrders && order.status !== 'completed' && order.status !== 'cancelled'"
                      @click="editOrder(order)"
                      class="text-green-600 hover:text-green-900"
                      title="Editar"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      v-if="canManageOrders && order.status === 'pending'"
                      @click="cancelOrder(order)"
                      class="text-red-600 hover:text-red-900"
                      title="Cancelar"
                    >
                      <i class="fas fa-times"></i>
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
                Mostrando {{ startIndex }} a {{ endIndex }} de {{ filteredOrders.length }} pedidos
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

    <!-- Order Details Modal -->
    <div
      v-if="showOrderModal"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="closeModals"
    >
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-2/3 shadow-lg rounded-md bg-white" @click.stop>
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">
              Detalles del Pedido #{{ selectedOrder?.order_number }}
            </h3>
            <button @click="closeModals" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>
          
          <div v-if="selectedOrder" class="space-y-6">
            <!-- Order Info -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="bg-gray-50 p-4 rounded-lg">
                <h4 class="font-medium text-gray-900 mb-2">Información del Cliente</h4>
                <p class="text-sm text-gray-600">Nombre: {{ selectedOrder.customer_name }}</p>
                <p class="text-sm text-gray-600">Teléfono: {{ selectedOrder.customer_phone }}</p>
                <p class="text-sm text-gray-600">Dirección: {{ selectedOrder.customer_address }}</p>
              </div>
              
              <div class="bg-gray-50 p-4 rounded-lg">
                <h4 class="font-medium text-gray-900 mb-2">Información del Pedido</h4>
                <p class="text-sm text-gray-600">Vendedor: {{ selectedOrder.salesperson }}</p>
                <p class="text-sm text-gray-600">Fecha: {{ formatDate(selectedOrder.created_at) }}</p>
                <p class="text-sm text-gray-600">Estado: 
                  <span :class="getStatusClass(selectedOrder.status)" class="px-2 py-1 text-xs font-medium rounded-full ml-1">
                    {{ getStatusText(selectedOrder.status) }}
                  </span>
                </p>
              </div>
            </div>

            <!-- Order Items -->
            <div>
              <h4 class="font-medium text-gray-900 mb-3">Productos</h4>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Cantidad</th>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Precio Unit.</th>
                      <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="item in selectedOrder.items" :key="item.id">
                      <td class="px-4 py-2 text-sm text-gray-900">{{ item.product_name }}</td>
                      <td class="px-4 py-2 text-sm text-gray-900">{{ item.quantity }}</td>
                      <td class="px-4 py-2 text-sm text-gray-900">${{ item.unit_price.toFixed(2) }}</td>
                      <td class="px-4 py-2 text-sm font-medium text-gray-900">${{ (item.quantity * item.unit_price).toFixed(2) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div class="mt-4 flex justify-end">
                <div class="bg-gray-50 p-4 rounded-lg">
                  <p class="text-lg font-bold text-gray-900">Total: ${{ selectedOrder.total.toFixed(2) }}</p>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div v-if="canManageOrders" class="flex justify-end space-x-3 pt-4 border-t">
              <button
                v-if="selectedOrder.status === 'pending'"
                @click="updateOrderStatus(selectedOrder, 'processing')"
                class="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
              >
                Marcar En Proceso
              </button>
              <button
                v-if="selectedOrder.status === 'processing'"
                @click="updateOrderStatus(selectedOrder, 'completed')"
                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Marcar Completado
              </button>
              <button
                v-if="selectedOrder.status === 'pending'"
                @click="updateOrderStatus(selectedOrder, 'cancelled')"
                class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Cancelar Pedido
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Order Modal -->
    <div
      v-if="canManageOrders && (showCreateOrderModal || showEditOrderModal)"
      class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
      @click="closeModals"
    >
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-2/3 shadow-lg rounded-md bg-white" @click.stop>
        <div class="mt-3">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ showCreateOrderModal ? 'Crear Nuevo Pedido' : 'Editar Pedido' }}
          </h3>
          
          <form @submit.prevent="saveOrder" class="space-y-6">
            <!-- Customer Info -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Nombre del Cliente</label>
                <input
                  v-model="orderForm.customer_name"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Teléfono</label>
                <input
                  v-model="orderForm.customer_phone"
                  type="tel"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
              </div>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Dirección</label>
              <textarea
                v-model="orderForm.customer_address"
                rows="2"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              ></textarea>
            </div>

            <!-- Order Items -->
            <div>
              <div class="flex justify-between items-center mb-3">
                <h4 class="font-medium text-gray-900">Productos</h4>
                <button
                  type="button"
                  @click="addOrderItem"
                  class="text-blue-600 hover:text-blue-800 text-sm"
                >
                  <i class="fas fa-plus mr-1"></i>Agregar Producto
                </button>
              </div>
              
              <div class="space-y-3">
                <div
                  v-for="(item, index) in orderForm.items"
                  :key="index"
                  class="grid grid-cols-1 md:grid-cols-5 gap-3 p-3 border border-gray-200 rounded-lg"
                >
                  <div class="md:col-span-2">
                    <select
                      v-model="item.product_id"
                      @change="updateItemPrice(index)"
                      required
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Seleccionar producto</option>
                      <option v-for="product in availableProducts" :key="product.id" :value="product.id">
                        {{ product.name }} - ${{ product.price }}
                      </option>
                    </select>
                  </div>
                  
                  <div>
                    <input
                      v-model="item.quantity"
                      type="number"
                      min="1"
                      required
                      placeholder="Cantidad"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                  </div>
                  
                  <div>
                    <input
                      v-model="item.unit_price"
                      type="number"
                      step="0.01"
                      required
                      placeholder="Precio"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                  </div>
                  
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-gray-900">
                      ${{ (item.quantity * item.unit_price || 0).toFixed(2) }}
                    </span>
                    <button
                      type="button"
                      @click="removeOrderItem(index)"
                      class="text-red-600 hover:text-red-800"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </div>
              </div>
              
              <div class="mt-4 flex justify-end">
                <div class="bg-gray-50 p-3 rounded-lg">
                  <p class="text-lg font-bold text-gray-900">Total: ${{ orderTotal.toFixed(2) }}</p>
                </div>
              </div>
            </div>
            
            <div class="flex justify-end space-x-3 pt-4 border-t">
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
                {{ showCreateOrderModal ? 'Crear Pedido' : 'Guardar Cambios' }}
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
const canManageOrders = computed(() => 
  authStore.hasScope('has_scope_orders') || 
  authStore.hasRole('admin') || 
  authStore.hasRole('encargado')
)

// Reactive data
const orders = ref([])
const availableProducts = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const dateFrom = ref('')
const dateTo = ref('')

// Pagination
const currentPage = ref(1)
const itemsPerPage = ref(10)

// Modals
const showOrderModal = ref(false)
const showCreateOrderModal = ref(false)
const showEditOrderModal = ref(false)
const selectedOrder = ref(null)

// Order form
const orderForm = ref({
  id: null,
  customer_name: '',
  customer_phone: '',
  customer_address: '',
  items: []
})

// Stats computed properties
const totalOrders = computed(() => orders.value.length)
const pendingOrders = computed(() => orders.value.filter(o => o.status === 'pending').length)
const processingOrders = computed(() => orders.value.filter(o => o.status === 'processing').length)
const todayTotal = computed(() => {
  const today = new Date().toDateString()
  return orders.value
    .filter(o => new Date(o.created_at).toDateString() === today)
    .reduce((sum, o) => sum + o.total, 0)
    .toFixed(2)
})

// Filtered orders
const filteredOrders = computed(() => {
  let filtered = orders.value

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(o => 
      o.order_number.toLowerCase().includes(query) ||
      o.customer_name.toLowerCase().includes(query) ||
      o.salesperson.toLowerCase().includes(query)
    )
  }

  // Status filter
  if (statusFilter.value) {
    filtered = filtered.filter(o => o.status === statusFilter.value)
  }

  // Date filters
  if (dateFrom.value) {
    filtered = filtered.filter(o => new Date(o.created_at) >= new Date(dateFrom.value))
  }
  if (dateTo.value) {
    filtered = filtered.filter(o => new Date(o.created_at) <= new Date(dateTo.value + 'T23:59:59'))
  }

  return filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

// Order form computed
const orderTotal = computed(() => {
  return orderForm.value.items.reduce((sum, item) => {
    return sum + (item.quantity * item.unit_price || 0)
  }, 0)
})

// Pagination computed properties
const totalPages = computed(() => Math.ceil(filteredOrders.value.length / itemsPerPage.value))
const startIndex = computed(() => (currentPage.value - 1) * itemsPerPage.value + 1)
const endIndex = computed(() => Math.min(currentPage.value * itemsPerPage.value, filteredOrders.value.length))

const paginatedOrders = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredOrders.value.slice(start, end)
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
const loadOrders = async () => {
  try {
    // Simulated API call - replace with actual API
    const response = await fetch('/api/orders')
    if (response.ok) {
      orders.value = await response.json()
    } else {
      // Fallback with mock data
      orders.value = [
        {
          id: 1,
          order_number: 'ORD-2024-001',
          customer_name: 'Juan Pérez',
          customer_phone: '+1234567890',
          customer_address: 'Calle Principal 123',
          salesperson: 'María García',
          status: 'pending',
          total: 45.50,
          created_at: '2024-01-15T10:30:00Z',
          items: [
            { id: 1, product_name: 'Coca Cola 500ml', quantity: 2, unit_price: 2.50 },
            { id: 2, product_name: 'Pan Integral', quantity: 3, unit_price: 3.20 },
            { id: 3, product_name: 'Leche Entera 1L', quantity: 20, unit_price: 1.80 }
          ]
        },
        {
          id: 2,
          order_number: 'ORD-2024-002',
          customer_name: 'Ana López',
          customer_phone: '+1234567891',
          customer_address: 'Avenida Central 456',
          salesperson: 'Carlos Ruiz',
          status: 'processing',
          total: 78.90,
          created_at: '2024-01-15T14:15:00Z',
          items: [
            { id: 4, product_name: 'Detergente Líquido', quantity: 5, unit_price: 4.50 },
            { id: 5, product_name: 'Coca Cola 500ml', quantity: 10, unit_price: 2.50 },
            { id: 6, product_name: 'Pan Integral', quantity: 8, unit_price: 3.20 }
          ]
        },
        {
          id: 3,
          order_number: 'ORD-2024-003',
          customer_name: 'Roberto Silva',
          customer_phone: '+1234567892',
          customer_address: 'Plaza Mayor 789',
          salesperson: 'María García',
          status: 'completed',
          total: 156.75,
          created_at: '2024-01-14T09:45:00Z',
          items: [
            { id: 7, product_name: 'Leche Entera 1L', quantity: 50, unit_price: 1.80 },
            { id: 8, product_name: 'Pan Integral', quantity: 25, unit_price: 3.20 }
          ]
        }
      ]
    }
  } catch (error) {
    console.error('Error loading orders:', error)
    orders.value = []
  }
}

const loadProducts = async () => {
  try {
    // Simulated API call - replace with actual API
    const response = await fetch('/api/products')
    if (response.ok) {
      availableProducts.value = await response.json()
    } else {
      // Fallback with mock data
      availableProducts.value = [
        { id: 1, name: 'Coca Cola 500ml', price: 2.50 },
        { id: 2, name: 'Pan Integral', price: 3.20 },
        { id: 3, name: 'Leche Entera 1L', price: 1.80 },
        { id: 4, name: 'Detergente Líquido', price: 4.50 }
      ]
    }
  } catch (error) {
    console.error('Error loading products:', error)
    availableProducts.value = []
  }
}

// Status methods
const getStatusClass = (status) => {
  switch (status) {
    case 'pending':
      return 'bg-yellow-100 text-yellow-800'
    case 'processing':
      return 'bg-blue-100 text-blue-800'
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'cancelled':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'pending':
      return 'Pendiente'
    case 'processing':
      return 'En Proceso'
    case 'completed':
      return 'Completado'
    case 'cancelled':
      return 'Cancelado'
    default:
      return 'Desconocido'
  }
}

// Date formatting
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('es-ES')
}

const formatTime = (dateString) => {
  return new Date(dateString).toLocaleTimeString('es-ES', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
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
  showOrderModal.value = false
  showCreateOrderModal.value = false
  showEditOrderModal.value = false
  selectedOrder.value = null
  resetOrderForm()
}

const resetOrderForm = () => {
  orderForm.value = {
    id: null,
    customer_name: '',
    customer_phone: '',
    customer_address: '',
    items: []
  }
}

// Order management methods
const viewOrder = (order) => {
  selectedOrder.value = order
  showOrderModal.value = true
}

const editOrder = (order) => {
  if (!canManageOrders.value) return
  
  selectedOrder.value = order
  orderForm.value = {
    id: order.id,
    customer_name: order.customer_name,
    customer_phone: order.customer_phone,
    customer_address: order.customer_address,
    items: [...order.items.map(item => ({
      product_id: availableProducts.value.find(p => p.name === item.product_name)?.id || '',
      quantity: item.quantity,
      unit_price: item.unit_price
    }))]
  }
  showEditOrderModal.value = true
}

const cancelOrder = async (order) => {
  if (!canManageOrders.value) return
  
  if (confirm(`¿Estás seguro de que deseas cancelar el pedido #${order.order_number}?`)) {
    await updateOrderStatus(order, 'cancelled')
  }
}

const updateOrderStatus = async (order, newStatus) => {
  if (!canManageOrders.value) return
  
  try {
    const response = await fetch(`/api/orders/${order.id}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status: newStatus })
    })
    
    if (response.ok) {
      const index = orders.value.findIndex(o => o.id === order.id)
      if (index !== -1) {
        orders.value[index].status = newStatus
      }
      
      if (selectedOrder.value && selectedOrder.value.id === order.id) {
        selectedOrder.value.status = newStatus
      }
      
      alert('Estado del pedido actualizado exitosamente')
    } else {
      alert('Error al actualizar el estado del pedido')
    }
  } catch (error) {
    console.error('Error updating order status:', error)
    alert('Error al actualizar el estado del pedido')
  }
}

// Order form methods
const addOrderItem = () => {
  orderForm.value.items.push({
    product_id: '',
    quantity: 1,
    unit_price: 0
  })
}

const removeOrderItem = (index) => {
  orderForm.value.items.splice(index, 1)
}

const updateItemPrice = (index) => {
  const item = orderForm.value.items[index]
  const product = availableProducts.value.find(p => p.id == item.product_id)
  if (product) {
    item.unit_price = product.price
  }
}

const saveOrder = async () => {
  if (!canManageOrders.value) return
  
  try {
    const isEditing = orderForm.value.id !== null
    const url = isEditing ? `/api/orders/${orderForm.value.id}` : '/api/orders'
    const method = isEditing ? 'PUT' : 'POST'
    
    const orderData = {
      ...orderForm.value,
      total: orderTotal.value,
      salesperson: authStore.user.name,
      status: 'pending'
    }
    
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(orderData)
    })
    
    if (response.ok) {
      const savedOrder = await response.json()
      
      if (isEditing) {
        const index = orders.value.findIndex(o => o.id === savedOrder.id)
        if (index !== -1) {
          orders.value[index] = savedOrder
        }
      } else {
        orders.value.unshift(savedOrder)
      }
      
      closeModals()
      alert(isEditing ? 'Pedido actualizado exitosamente' : 'Pedido creado exitosamente')
    } else {
      alert('Error al guardar el pedido')
    }
  } catch (error) {
    console.error('Error saving order:', error)
    alert('Error al guardar el pedido')
  }
}

// Export functionality
const exportOrders = () => {
  try {
    const csvContent = [
      ['Número', 'Cliente', 'Teléfono', 'Vendedor', 'Fecha', 'Total', 'Estado'].join(','),
      ...filteredOrders.value.map(order => [
        order.order_number,
        order.customer_name,
        order.customer_phone,
        order.salesperson,
        formatDate(order.created_at),
        order.total.toFixed(2),
        getStatusText(order.status)
      ].join(','))
    ].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `pedidos_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    console.error('Error exporting orders:', error)
    alert('Error al exportar los pedidos')
  }
}

// Lifecycle
onMounted(() => {
  loadOrders()
  loadProducts()
})
</script>

<style scoped>
/* Custom styles if needed */
</style>