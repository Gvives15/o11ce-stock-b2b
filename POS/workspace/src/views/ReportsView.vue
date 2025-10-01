<template>
  <div class="reports-view">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Reportes y Estadísticas</h1>
          <p class="text-gray-600 mt-1">Análisis detallado del rendimiento del negocio</p>
        </div>
        <div class="flex space-x-3">
          <button
            @click="generateReport"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-chart-line"></i>
            <span>Generar Reporte</span>
          </button>
          <button
            @click="exportAllReports"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-download"></i>
            <span>Exportar Todo</span>
          </button>
          <button
            @click="scheduleReport"
            class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-clock"></i>
            <span>Programar</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Date Range Filter -->
    <div class="bg-white border-b border-gray-200 px-6 py-4">
      <div class="flex flex-wrap items-center space-x-4">
        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700">Período:</label>
          <select
            v-model="selectedPeriod"
            @change="updateDateRange"
            class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="today">Hoy</option>
            <option value="yesterday">Ayer</option>
            <option value="week">Esta Semana</option>
            <option value="month">Este Mes</option>
            <option value="quarter">Este Trimestre</option>
            <option value="year">Este Año</option>
            <option value="custom">Personalizado</option>
          </select>
        </div>
        
        <div v-if="selectedPeriod === 'custom'" class="flex items-center space-x-2">
          <input
            v-model="customDateRange.start"
            type="date"
            class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
          <span class="text-gray-500">a</span>
          <input
            v-model="customDateRange.end"
            type="date"
            class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
        </div>

        <button
          @click="refreshData"
          class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm flex items-center space-x-1 transition-colors"
        >
          <i class="fas fa-sync-alt"></i>
          <span>Actualizar</span>
        </button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-green-100 text-green-600">
              <i class="fas fa-dollar-sign text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Ventas Totales</p>
              <p class="text-2xl font-bold text-gray-900">${{ formatCurrency(totalSales) }}</p>
              <p :class="salesGrowthClass" class="text-sm flex items-center">
                <i :class="salesGrowthIcon" class="mr-1"></i>
                {{ salesGrowth }}% vs período anterior
              </p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-blue-100 text-blue-600">
              <i class="fas fa-shopping-cart text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Órdenes</p>
              <p class="text-2xl font-bold text-gray-900">{{ totalOrders }}</p>
              <p :class="ordersGrowthClass" class="text-sm flex items-center">
                <i :class="ordersGrowthIcon" class="mr-1"></i>
                {{ ordersGrowth }}% vs período anterior
              </p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-purple-100 text-purple-600">
              <i class="fas fa-users text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Clientes Nuevos</p>
              <p class="text-2xl font-bold text-gray-900">{{ newCustomers }}</p>
              <p :class="customersGrowthClass" class="text-sm flex items-center">
                <i :class="customersGrowthIcon" class="mr-1"></i>
                {{ customersGrowth }}% vs período anterior
              </p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
              <i class="fas fa-chart-line text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Ticket Promedio</p>
              <p class="text-2xl font-bold text-gray-900">${{ formatCurrency(averageTicket) }}</p>
              <p :class="ticketGrowthClass" class="text-sm flex items-center">
                <i :class="ticketGrowthIcon" class="mr-1"></i>
                {{ ticketGrowth }}% vs período anterior
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <!-- Sales Chart -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Ventas por Día</h3>
            <select
              v-model="salesChartType"
              class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="line">Línea</option>
              <option value="bar">Barras</option>
              <option value="area">Área</option>
            </select>
          </div>
          <div class="h-64 flex items-center justify-center bg-gray-50 rounded">
            <div class="text-center">
              <i class="fas fa-chart-line text-4xl text-gray-400 mb-2"></i>
              <p class="text-gray-500">Gráfico de Ventas</p>
              <p class="text-sm text-gray-400">{{ salesChartData.length }} puntos de datos</p>
            </div>
          </div>
        </div>

        <!-- Products Chart -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Productos Más Vendidos</h3>
            <select
              v-model="productsChartType"
              class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="pie">Circular</option>
              <option value="doughnut">Dona</option>
              <option value="bar">Barras</option>
            </select>
          </div>
          <div class="h-64 flex items-center justify-center bg-gray-50 rounded">
            <div class="text-center">
              <i class="fas fa-chart-pie text-4xl text-gray-400 mb-2"></i>
              <p class="text-gray-500">Productos Top</p>
              <p class="text-sm text-gray-400">{{ topProducts.length }} productos</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Reports -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Sales by Category -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900">Ventas por Categoría</h3>
              <button
                @click="exportCategoryReport"
                class="text-blue-600 hover:text-blue-800 text-sm"
              >
                <i class="fas fa-download mr-1"></i>
                Exportar
              </button>
            </div>
          </div>
          <div class="p-6">
            <div class="space-y-4">
              <div
                v-for="category in salesByCategory"
                :key="category.id"
                class="flex items-center justify-between"
              >
                <div class="flex items-center space-x-3">
                  <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: category.color }"></div>
                  <span class="text-sm font-medium text-gray-900">{{ category.name }}</span>
                </div>
                <div class="text-right">
                  <p class="text-sm font-bold text-gray-900">${{ formatCurrency(category.sales) }}</p>
                  <p class="text-xs text-gray-500">{{ category.percentage }}%</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Payment Methods -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900">Métodos de Pago</h3>
              <button
                @click="exportPaymentReport"
                class="text-blue-600 hover:text-blue-800 text-sm"
              >
                <i class="fas fa-download mr-1"></i>
                Exportar
              </button>
            </div>
          </div>
          <div class="p-6">
            <div class="space-y-4">
              <div
                v-for="method in paymentMethods"
                :key="method.id"
                class="flex items-center justify-between"
              >
                <div class="flex items-center space-x-3">
                  <i :class="method.icon" class="text-gray-400"></i>
                  <span class="text-sm font-medium text-gray-900">{{ method.name }}</span>
                </div>
                <div class="text-right">
                  <p class="text-sm font-bold text-gray-900">${{ formatCurrency(method.amount) }}</p>
                  <p class="text-xs text-gray-500">{{ method.transactions }} transacciones</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Top Customers -->
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900">Mejores Clientes</h3>
              <button
                @click="exportCustomerReport"
                class="text-blue-600 hover:text-blue-800 text-sm"
              >
                <i class="fas fa-download mr-1"></i>
                Exportar
              </button>
            </div>
          </div>
          <div class="p-6">
            <div class="space-y-4">
              <div
                v-for="(customer, index) in topCustomers"
                :key="customer.id"
                class="flex items-center justify-between"
              >
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span class="text-sm font-bold text-blue-600">{{ index + 1 }}</span>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ customer.name }}</p>
                    <p class="text-xs text-gray-500">{{ customer.orders }} órdenes</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-sm font-bold text-gray-900">${{ formatCurrency(customer.total) }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Inventory Reports -->
      <div class="mt-8">
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-medium text-gray-900">Reporte de Inventario</h3>
              <div class="flex space-x-2">
                <select
                  v-model="inventoryReportType"
                  class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="low-stock">Stock Bajo</option>
                  <option value="out-of-stock">Sin Stock</option>
                  <option value="expiring">Por Vencer</option>
                  <option value="slow-moving">Movimiento Lento</option>
                </select>
                <button
                  @click="exportInventoryReport"
                  class="text-blue-600 hover:text-blue-800 text-sm"
                >
                  <i class="fas fa-download mr-1"></i>
                  Exportar
                </button>
              </div>
            </div>
          </div>
          <div class="p-6">
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Producto
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      SKU
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Stock Actual
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Stock Mínimo
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Última Venta
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr v-for="product in filteredInventoryReport" :key="product.id">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="text-sm font-medium text-gray-900">{{ product.name }}</div>
                      <div class="text-sm text-gray-500">{{ product.category }}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {{ product.sku }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {{ product.currentStock }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {{ product.minStock }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span :class="getInventoryStatusClass(product.status)" class="px-2 py-1 text-xs font-semibold rounded-full">
                        {{ getInventoryStatusLabel(product.status) }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {{ formatDate(product.lastSale) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Generate Report Modal -->
    <div v-if="showReportModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Generar Reporte Personalizado</h3>
            <button @click="closeReportModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="generateCustomReport" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Tipo de Reporte *</label>
              <select
                v-model="reportForm.type"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Seleccionar tipo</option>
                <option value="sales">Ventas Detalladas</option>
                <option value="inventory">Inventario Completo</option>
                <option value="customers">Análisis de Clientes</option>
                <option value="financial">Reporte Financiero</option>
                <option value="performance">Rendimiento de Productos</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Formato de Exportación</label>
              <select
                v-model="reportForm.format"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="pdf">PDF</option>
                <option value="excel">Excel</option>
                <option value="csv">CSV</option>
              </select>
            </div>

            <div>
              <label class="flex items-center">
                <input
                  v-model="reportForm.includeCharts"
                  type="checkbox"
                  class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                >
                <span class="ml-2 text-sm text-gray-700">Incluir gráficos</span>
              </label>
            </div>

            <div>
              <label class="flex items-center">
                <input
                  v-model="reportForm.sendEmail"
                  type="checkbox"
                  class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                >
                <span class="ml-2 text-sm text-gray-700">Enviar por email</span>
              </label>
            </div>

            <div v-if="reportForm.sendEmail">
              <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                v-model="reportForm.email"
                type="email"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeReportModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Generar Reporte
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Schedule Report Modal -->
    <div v-if="showScheduleModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Programar Reporte Automático</h3>
            <button @click="closeScheduleModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="saveScheduledReport" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre del Reporte *</label>
              <input
                v-model="scheduleForm.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Tipo de Reporte *</label>
              <select
                v-model="scheduleForm.type"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Seleccionar tipo</option>
                <option value="daily-sales">Ventas Diarias</option>
                <option value="weekly-summary">Resumen Semanal</option>
                <option value="monthly-report">Reporte Mensual</option>
                <option value="inventory-alert">Alertas de Inventario</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Frecuencia *</label>
              <select
                v-model="scheduleForm.frequency"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="daily">Diario</option>
                <option value="weekly">Semanal</option>
                <option value="monthly">Mensual</option>
                <option value="quarterly">Trimestral</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Email de Destino *</label>
              <input
                v-model="scheduleForm.email"
                type="email"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
            </div>

            <div>
              <label class="flex items-center">
                <input
                  v-model="scheduleForm.isActive"
                  type="checkbox"
                  class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                >
                <span class="ml-2 text-sm text-gray-700">Activar programación</span>
              </label>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closeScheduleModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Programar Reporte
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

// Check if user has admin access
if (!authStore.isAdmin) {
  // Redirect to dashboard or show access denied
  console.warn('Access denied: Admin role required for Reports')
}

// Reactive data
const selectedPeriod = ref('month')
const customDateRange = ref({
  start: '',
  end: ''
})

// Chart types
const salesChartType = ref('line')
const productsChartType = ref('pie')
const inventoryReportType = ref('low-stock')

// Modal states
const showReportModal = ref(false)
const showScheduleModal = ref(false)

// Form data
const reportForm = ref({
  type: '',
  format: 'pdf',
  includeCharts: true,
  sendEmail: false,
  email: ''
})

const scheduleForm = ref({
  name: '',
  type: '',
  frequency: 'monthly',
  email: '',
  isActive: true
})

// Data
const totalSales = ref(125000)
const salesGrowth = ref(12.5)
const totalOrders = ref(450)
const ordersGrowth = ref(8.3)
const newCustomers = ref(35)
const customersGrowth = ref(-2.1)
const averageTicket = ref(277.78)
const ticketGrowth = ref(5.2)

const salesChartData = ref([])
const topProducts = ref([])
const salesByCategory = ref([])
const paymentMethods = ref([])
const topCustomers = ref([])
const inventoryReport = ref([])

// Computed properties
const salesGrowthClass = computed(() => 
  salesGrowth.value >= 0 ? 'text-green-600' : 'text-red-600'
)
const salesGrowthIcon = computed(() => 
  salesGrowth.value >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'
)

const ordersGrowthClass = computed(() => 
  ordersGrowth.value >= 0 ? 'text-green-600' : 'text-red-600'
)
const ordersGrowthIcon = computed(() => 
  ordersGrowth.value >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'
)

const customersGrowthClass = computed(() => 
  customersGrowth.value >= 0 ? 'text-green-600' : 'text-red-600'
)
const customersGrowthIcon = computed(() => 
  customersGrowth.value >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'
)

const ticketGrowthClass = computed(() => 
  ticketGrowth.value >= 0 ? 'text-green-600' : 'text-red-600'
)
const ticketGrowthIcon = computed(() => 
  ticketGrowth.value >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'
)

const filteredInventoryReport = computed(() => {
  return inventoryReport.value.filter(product => {
    switch (inventoryReportType.value) {
      case 'low-stock':
        return product.currentStock <= product.minStock
      case 'out-of-stock':
        return product.currentStock === 0
      case 'expiring':
        return product.status === 'expiring'
      case 'slow-moving':
        return product.status === 'slow-moving'
      default:
        return true
    }
  })
})

// Methods
const loadData = async () => {
  try {
    // TODO: Replace with actual API calls
    // const salesData = await api.get('/reports/sales', { params: { period: selectedPeriod.value } })
    // const inventoryData = await api.get('/reports/inventory')
    // const customersData = await api.get('/reports/customers')
    
    // Mock data for development
    salesByCategory.value = [
      { id: 1, name: 'Electrónicos', sales: 45000, percentage: 36, color: '#3B82F6' },
      { id: 2, name: 'Ropa', sales: 35000, percentage: 28, color: '#10B981' },
      { id: 3, name: 'Hogar', sales: 25000, percentage: 20, color: '#F59E0B' },
      { id: 4, name: 'Deportes', sales: 20000, percentage: 16, color: '#EF4444' }
    ]

    paymentMethods.value = [
      { id: 1, name: 'Efectivo', amount: 50000, transactions: 180, icon: 'fas fa-money-bill-wave' },
      { id: 2, name: 'Tarjeta de Crédito', amount: 45000, transactions: 150, icon: 'fas fa-credit-card' },
      { id: 3, name: 'Tarjeta de Débito', amount: 25000, transactions: 90, icon: 'fas fa-credit-card' },
      { id: 4, name: 'Transferencia', amount: 5000, transactions: 30, icon: 'fas fa-university' }
    ]

    topCustomers.value = [
      { id: 1, name: 'María González', total: 5500, orders: 12 },
      { id: 2, name: 'Carlos Rodríguez', total: 4800, orders: 8 },
      { id: 3, name: 'Ana Martínez', total: 4200, orders: 15 },
      { id: 4, name: 'Luis Pérez', total: 3900, orders: 7 },
      { id: 5, name: 'Carmen López', total: 3600, orders: 9 }
    ]

    inventoryReport.value = [
      {
        id: 1,
        name: 'iPhone 13 Pro',
        sku: 'IPH13P-128',
        category: 'Smartphones',
        currentStock: 2,
        minStock: 5,
        status: 'low-stock',
        lastSale: '2023-12-15'
      },
      {
        id: 2,
        name: 'Samsung Galaxy S21',
        sku: 'SGS21-256',
        category: 'Smartphones',
        currentStock: 0,
        minStock: 3,
        status: 'out-of-stock',
        lastSale: '2023-12-10'
      },
      {
        id: 3,
        name: 'MacBook Air M2',
        sku: 'MBA-M2-512',
        category: 'Laptops',
        currentStock: 1,
        minStock: 2,
        status: 'low-stock',
        lastSale: '2023-12-12'
      },
      {
        id: 4,
        name: 'Camiseta Nike',
        sku: 'NK-TS-001',
        category: 'Ropa',
        currentStock: 15,
        minStock: 10,
        status: 'slow-moving',
        lastSale: '2023-11-20'
      }
    ]

    topProducts.value = [
      { id: 1, name: 'iPhone 13', sales: 150, revenue: 120000 },
      { id: 2, name: 'Samsung TV 55"', sales: 85, revenue: 85000 },
      { id: 3, name: 'Nike Air Max', sales: 120, revenue: 72000 },
      { id: 4, name: 'MacBook Pro', sales: 45, revenue: 90000 }
    ]

    salesChartData.value = Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      sales: Math.floor(Math.random() * 5000) + 2000
    }))
  } catch (error) {
    console.error('Error loading reports data:', error)
  }
}

const updateDateRange = () => {
  const today = new Date()
  const startDate = new Date()

  switch (selectedPeriod.value) {
    case 'today':
      startDate.setDate(today.getDate())
      break
    case 'yesterday':
      startDate.setDate(today.getDate() - 1)
      break
    case 'week':
      startDate.setDate(today.getDate() - 7)
      break
    case 'month':
      startDate.setMonth(today.getMonth() - 1)
      break
    case 'quarter':
      startDate.setMonth(today.getMonth() - 3)
      break
    case 'year':
      startDate.setFullYear(today.getFullYear() - 1)
      break
  }

  if (selectedPeriod.value !== 'custom') {
    customDateRange.value.start = startDate.toISOString().split('T')[0]
    customDateRange.value.end = today.toISOString().split('T')[0]
  }

  refreshData()
}

const refreshData = () => {
  loadData()
}

// Modal methods
const generateReport = () => {
  showReportModal.value = true
}

const closeReportModal = () => {
  showReportModal.value = false
  reportForm.value = {
    type: '',
    format: 'pdf',
    includeCharts: true,
    sendEmail: false,
    email: ''
  }
}

const generateCustomReport = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.post('/reports/generate', reportForm.value)
    
    console.log('Generating custom report:', reportForm.value)
    closeReportModal()
  } catch (error) {
    console.error('Error generating report:', error)
  }
}

const scheduleReport = () => {
  showScheduleModal.value = true
}

const closeScheduleModal = () => {
  showScheduleModal.value = false
  scheduleForm.value = {
    name: '',
    type: '',
    frequency: 'monthly',
    email: '',
    isActive: true
  }
}

const saveScheduledReport = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.post('/reports/schedule', scheduleForm.value)
    
    console.log('Scheduling report:', scheduleForm.value)
    closeScheduleModal()
  } catch (error) {
    console.error('Error scheduling report:', error)
  }
}

// Export methods
const exportAllReports = () => {
  const csvContent = [
    ['Tipo', 'Período', 'Valor', 'Crecimiento'].join(','),
    ['Ventas Totales', selectedPeriod.value, totalSales.value, `${salesGrowth.value}%`].join(','),
    ['Órdenes Totales', selectedPeriod.value, totalOrders.value, `${ordersGrowth.value}%`].join(','),
    ['Clientes Nuevos', selectedPeriod.value, newCustomers.value, `${customersGrowth.value}%`].join(','),
    ['Ticket Promedio', selectedPeriod.value, averageTicket.value, `${ticketGrowth.value}%`].join(',')
  ].join('\n')

  downloadCSV(csvContent, `reporte_completo_${new Date().toISOString().split('T')[0]}.csv`)
}

const exportCategoryReport = () => {
  const csvContent = [
    ['Categoría', 'Ventas', 'Porcentaje'].join(','),
    ...salesByCategory.value.map(cat => [cat.name, cat.sales, `${cat.percentage}%`].join(','))
  ].join('\n')

  downloadCSV(csvContent, `ventas_por_categoria_${new Date().toISOString().split('T')[0]}.csv`)
}

const exportPaymentReport = () => {
  const csvContent = [
    ['Método de Pago', 'Monto', 'Transacciones'].join(','),
    ...paymentMethods.value.map(method => [method.name, method.amount, method.transactions].join(','))
  ].join('\n')

  downloadCSV(csvContent, `metodos_pago_${new Date().toISOString().split('T')[0]}.csv`)
}

const exportCustomerReport = () => {
  const csvContent = [
    ['Cliente', 'Total Compras', 'Número de Órdenes'].join(','),
    ...topCustomers.value.map(customer => [customer.name, customer.total, customer.orders].join(','))
  ].join('\n')

  downloadCSV(csvContent, `mejores_clientes_${new Date().toISOString().split('T')[0]}.csv`)
}

const exportInventoryReport = () => {
  const csvContent = [
    ['Producto', 'SKU', 'Categoría', 'Stock Actual', 'Stock Mínimo', 'Estado', 'Última Venta'].join(','),
    ...filteredInventoryReport.value.map(product => [
      product.name,
      product.sku,
      product.category,
      product.currentStock,
      product.minStock,
      getInventoryStatusLabel(product.status),
      formatDate(product.lastSale)
    ].join(','))
  ].join('\n')

  downloadCSV(csvContent, `inventario_${inventoryReportType.value}_${new Date().toISOString().split('T')[0]}.csv`)
}

// Utility methods
const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount)
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('es-ES')
}

const getInventoryStatusClass = (status: string) => {
  switch (status) {
    case 'low-stock':
      return 'bg-yellow-100 text-yellow-800'
    case 'out-of-stock':
      return 'bg-red-100 text-red-800'
    case 'expiring':
      return 'bg-orange-100 text-orange-800'
    case 'slow-moving':
      return 'bg-gray-100 text-gray-800'
    default:
      return 'bg-green-100 text-green-800'
  }
}

const getInventoryStatusLabel = (status: string) => {
  switch (status) {
    case 'low-stock':
      return 'Stock Bajo'
    case 'out-of-stock':
      return 'Sin Stock'
    case 'expiring':
      return 'Por Vencer'
    case 'slow-moving':
      return 'Movimiento Lento'
    default:
      return 'Normal'
  }
}

const downloadCSV = (content: string, filename: string) => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Lifecycle
onMounted(() => {
  updateDateRange()
})
</script>