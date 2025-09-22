<template>
  <POSLayout>
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Historial de Ventas</h1>
        <div class="flex items-center space-x-4">
          <input
            v-model="searchTerm"
            type="text"
            placeholder="Buscar ventas..."
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            v-model="filterPeriod"
            class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="today">Hoy</option>
            <option value="week">Esta semana</option>
            <option value="month">Este mes</option>
            <option value="all">Todos</option>
          </select>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-blue-50 p-4 rounded-lg">
          <div class="text-sm font-medium text-blue-600">Ventas Hoy</div>
          <div class="text-2xl font-bold text-blue-900">{{ todaySales.count }}</div>
          <div class="text-sm text-blue-600">${{ todaySales.total.toFixed(2) }}</div>
        </div>
        
        <div class="bg-green-50 p-4 rounded-lg">
          <div class="text-sm font-medium text-green-600">Promedio por Venta</div>
          <div class="text-2xl font-bold text-green-900">${{ averageSale.toFixed(2) }}</div>
        </div>
        
        <div class="bg-purple-50 p-4 rounded-lg">
          <div class="text-sm font-medium text-purple-600">Total Ventas</div>
          <div class="text-2xl font-bold text-purple-900">{{ filteredSales.length }}</div>
        </div>
        
        <div class="bg-orange-50 p-4 rounded-lg">
          <div class="text-sm font-medium text-orange-600">Ingresos Totales</div>
          <div class="text-2xl font-bold text-orange-900">${{ totalRevenue.toFixed(2) }}</div>
        </div>
      </div>

      <!-- Sales Table -->
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID Venta
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Fecha
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cliente
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Items
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Total
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Estado
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="sale in paginatedSales"
              :key="sale.id"
              class="hover:bg-gray-50"
            >
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                #{{ sale.id }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(sale.date) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ sale.customer }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ sale.items }} items
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                ${{ sale.total.toFixed(2) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="inline-flex px-2 py-1 text-xs font-semibold rounded-full"
                  :class="{
                    'bg-green-100 text-green-800': sale.status === 'completed',
                    'bg-yellow-100 text-yellow-800': sale.status === 'pending',
                    'bg-red-100 text-red-800': sale.status === 'cancelled'
                  }"
                >
                  {{ sale.status === 'completed' ? 'Completada' : 
                     sale.status === 'pending' ? 'Pendiente' : 'Cancelada' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between mt-6">
        <div class="text-sm text-gray-700">
          Mostrando {{ (currentPage - 1) * pageSize + 1 }} a {{ Math.min(currentPage * pageSize, filteredSales.length) }} 
          de {{ filteredSales.length }} ventas
        </div>
        <div class="flex space-x-2">
          <button
            @click="currentPage--"
            :disabled="currentPage === 1"
            class="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Anterior
          </button>
          <button
            @click="currentPage++"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1 border border-gray-300 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  </POSLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import POSLayout from '@/layouts/POSLayout.vue'

interface Sale {
  id: number
  date: Date
  customer: string
  items: number
  total: number
  status: 'completed' | 'pending' | 'cancelled'
}

// Mock sales data
const mockSales: Sale[] = [
  { id: 1001, date: new Date(), customer: 'Cliente Anónimo', items: 3, total: 15.50, status: 'completed' },
  { id: 1002, date: new Date(Date.now() - 86400000), customer: 'Juan Pérez', items: 5, total: 28.90, status: 'completed' },
  { id: 1003, date: new Date(Date.now() - 172800000), customer: 'María García', items: 2, total: 12.40, status: 'completed' },
  { id: 1004, date: new Date(Date.now() - 259200000), customer: 'Carlos López', items: 7, total: 45.60, status: 'completed' },
  { id: 1005, date: new Date(Date.now() - 345600000), customer: 'Ana Martín', items: 1, total: 8.50, status: 'cancelled' },
  { id: 1006, date: new Date(Date.now() - 432000000), customer: 'Luis Rodríguez', items: 4, total: 22.30, status: 'completed' },
  { id: 1007, date: new Date(Date.now() - 518400000), customer: 'Elena Sánchez', items: 6, total: 38.70, status: 'completed' },
  { id: 1008, date: new Date(Date.now() - 604800000), customer: 'Pedro Gómez', items: 3, total: 19.80, status: 'pending' }
]

const searchTerm = ref('')
const filterPeriod = ref('all')
const currentPage = ref(1)
const pageSize = ref(10)

const filteredSales = computed(() => {
  let filtered = mockSales

  // Filter by search term
  if (searchTerm.value) {
    filtered = filtered.filter(sale => 
      sale.customer.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
      sale.id.toString().includes(searchTerm.value)
    )
  }

  // Filter by period
  const now = new Date()
  if (filterPeriod.value === 'today') {
    filtered = filtered.filter(sale => 
      sale.date.toDateString() === now.toDateString()
    )
  } else if (filterPeriod.value === 'week') {
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    filtered = filtered.filter(sale => sale.date >= weekAgo)
  } else if (filterPeriod.value === 'month') {
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    filtered = filtered.filter(sale => sale.date >= monthAgo)
  }

  return filtered.sort((a, b) => b.date.getTime() - a.date.getTime())
})

const paginatedSales = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredSales.value.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(filteredSales.value.length / pageSize.value)
})

const todaySales = computed(() => {
  const today = new Date().toDateString()
  const sales = mockSales.filter(sale => sale.date.toDateString() === today)
  return {
    count: sales.length,
    total: sales.reduce((sum, sale) => sum + sale.total, 0)
  }
})

const averageSale = computed(() => {
  if (filteredSales.value.length === 0) return 0
  return totalRevenue.value / filteredSales.value.length
})

const totalRevenue = computed(() => {
  return filteredSales.value.reduce((sum, sale) => sum + sale.total, 0)
})

const formatDate = (date: Date) => {
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>