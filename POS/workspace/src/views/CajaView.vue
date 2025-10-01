<template>
  <div class="caja-view">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Gestión de Caja</h1>
          <p class="text-gray-600 mt-1">
            {{ currentSession ? `Sesión iniciada: ${formatDateTime(currentSession.startTime)}` : 'No hay sesión activa' }}
          </p>
        </div>
        <div class="flex space-x-3">
          <button
            v-if="!currentSession"
            @click="openSession"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-play"></i>
            <span>Abrir Caja</span>
          </button>
          <button
            v-if="currentSession"
            @click="showCloseSessionModal = true"
            class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-stop"></i>
            <span>Cerrar Caja</span>
          </button>
          <button
            @click="printReport"
            :disabled="!currentSession"
            class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-print"></i>
            <span>Imprimir</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Session Status -->
    <div class="p-6">
      <div v-if="currentSession" class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <i class="fas fa-check-circle text-green-400 text-xl"></i>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-green-800">Sesión de Caja Activa</h3>
            <div class="mt-2 text-sm text-green-700">
              <p>Cajero: {{ authStore.user?.name }}</p>
              <p>Inicio: {{ formatDateTime(currentSession.startTime) }}</p>
              <p>Duración: {{ getSessionDuration() }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <div class="flex items-center">
          <div class="flex-shrink-0">
            <i class="fas fa-exclamation-triangle text-yellow-400 text-xl"></i>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-yellow-800">No hay sesión activa</h3>
            <p class="mt-2 text-sm text-yellow-700">
              Debes abrir una sesión de caja para comenzar a registrar transacciones.
            </p>
          </div>
        </div>
      </div>

      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-green-100 text-green-600">
              <i class="fas fa-cash-register text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Ventas del Día</p>
              <p class="text-2xl font-bold text-gray-900">${{ todaySales.toLocaleString() }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-blue-100 text-blue-600">
              <i class="fas fa-receipt text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Transacciones</p>
              <p class="text-2xl font-bold text-gray-900">{{ todayTransactions }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-purple-100 text-purple-600">
              <i class="fas fa-money-bill-wave text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Efectivo</p>
              <p class="text-2xl font-bold text-gray-900">${{ cashAmount.toLocaleString() }}</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center">
            <div class="p-3 rounded-full bg-indigo-100 text-indigo-600">
              <i class="fas fa-credit-card text-xl"></i>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">Tarjetas</p>
              <p class="text-2xl font-bold text-gray-900">${{ cardAmount.toLocaleString() }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Payment Methods Breakdown -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Desglose por Método de Pago</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="method in paymentMethods" :key="method.type" class="border rounded-lg p-4">
            <div class="flex justify-between items-center">
              <div>
                <p class="text-sm font-medium text-gray-600">{{ method.name }}</p>
                <p class="text-lg font-bold text-gray-900">${{ method.amount.toLocaleString() }}</p>
              </div>
              <div class="text-right">
                <p class="text-sm text-gray-500">{{ method.count }} transacciones</p>
                <p class="text-xs text-gray-400">{{ method.percentage }}%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Transactions -->
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">Transacciones Recientes</h3>
            <div class="flex space-x-2">
              <select
                v-model="transactionFilter"
                class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">Todas</option>
                <option value="sale">Ventas</option>
                <option value="refund">Devoluciones</option>
                <option value="cash_in">Ingreso Efectivo</option>
                <option value="cash_out">Egreso Efectivo</option>
              </select>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hora
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Descripción
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Método de Pago
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Monto
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="transaction in filteredTransactions" :key="transaction.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ formatTime(transaction.timestamp) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="getTransactionTypeClass(transaction.type)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                    {{ getTransactionTypeLabel(transaction.type) }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm text-gray-900">
                  {{ transaction.description }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ getPaymentMethodLabel(transaction.paymentMethod) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <span :class="transaction.type === 'cash_out' || transaction.type === 'refund' ? 'text-red-600' : 'text-green-600'">
                    {{ transaction.type === 'cash_out' || transaction.type === 'refund' ? '-' : '+' }}${{ transaction.amount.toLocaleString() }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    @click="viewTransaction(transaction)"
                    class="text-blue-600 hover:text-blue-900 p-1"
                    title="Ver detalles"
                  >
                    <i class="fas fa-eye"></i>
                  </button>
                  <button
                    v-if="transaction.type === 'sale' && canRefund"
                    @click="refundTransaction(transaction)"
                    class="text-red-600 hover:text-red-900 p-1 ml-2"
                    title="Devolver"
                  >
                    <i class="fas fa-undo"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="filteredTransactions.length === 0" class="text-center py-8">
          <i class="fas fa-receipt text-gray-300 text-4xl mb-4"></i>
          <p class="text-gray-500">No hay transacciones para mostrar</p>
        </div>
      </div>
    </div>

    <!-- Open Session Modal -->
    <div v-if="showOpenSessionModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Abrir Sesión de Caja</h3>
            <button @click="showOpenSessionModal = false" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <form @submit.prevent="confirmOpenSession" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Monto inicial en efectivo *</label>
              <div class="relative">
                <span class="absolute left-3 top-3 text-gray-500">$</span>
                <input
                  v-model.number="openingAmount"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  class="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0.00"
                >
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Notas (opcional)</label>
              <textarea
                v-model="openingNotes"
                rows="3"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Observaciones sobre la apertura de caja..."
              ></textarea>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="showOpenSessionModal = false"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Abrir Caja
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Close Session Modal -->
    <div v-if="showCloseSessionModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-2/3 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Cerrar Sesión de Caja</h3>
            <button @click="showCloseSessionModal = false" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div class="space-y-4">
            <!-- Session Summary -->
            <div class="bg-gray-50 rounded-lg p-4">
              <h4 class="font-medium text-gray-900 mb-3">Resumen de la Sesión</h4>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p class="text-gray-600">Inicio:</p>
                  <p class="font-medium">{{ formatDateTime(currentSession?.startTime) }}</p>
                </div>
                <div>
                  <p class="text-gray-600">Duración:</p>
                  <p class="font-medium">{{ getSessionDuration() }}</p>
                </div>
                <div>
                  <p class="text-gray-600">Monto inicial:</p>
                  <p class="font-medium">${{ currentSession?.openingAmount?.toLocaleString() }}</p>
                </div>
                <div>
                  <p class="text-gray-600">Total ventas:</p>
                  <p class="font-medium">${{ todaySales.toLocaleString() }}</p>
                </div>
                <div>
                  <p class="text-gray-600">Efectivo esperado:</p>
                  <p class="font-medium">${{ expectedCash.toLocaleString() }}</p>
                </div>
                <div>
                  <p class="text-gray-600">Transacciones:</p>
                  <p class="font-medium">{{ todayTransactions }}</p>
                </div>
              </div>
            </div>

            <form @submit.prevent="confirmCloseSession" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Efectivo real en caja *</label>
                <div class="relative">
                  <span class="absolute left-3 top-3 text-gray-500">$</span>
                  <input
                    v-model.number="closingAmount"
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    class="w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="0.00"
                  >
                </div>
                <div v-if="cashDifference !== 0" class="mt-2">
                  <p :class="cashDifference > 0 ? 'text-green-600' : 'text-red-600'" class="text-sm font-medium">
                    {{ cashDifference > 0 ? 'Sobrante' : 'Faltante' }}: ${{ Math.abs(cashDifference).toLocaleString() }}
                  </p>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Notas de cierre</label>
                <textarea
                  v-model="closingNotes"
                  rows="3"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Observaciones sobre el cierre de caja..."
                ></textarea>
              </div>

              <div class="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  @click="showCloseSessionModal = false"
                  class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Cerrar Caja
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Transaction Detail Modal -->
    <div v-if="showTransactionModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Detalles de Transacción</h3>
            <button @click="showTransactionModal = false" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div v-if="selectedTransaction" class="space-y-4">
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p class="text-gray-600">ID:</p>
                <p class="font-medium">{{ selectedTransaction.id }}</p>
              </div>
              <div>
                <p class="text-gray-600">Fecha y Hora:</p>
                <p class="font-medium">{{ formatDateTime(selectedTransaction.timestamp) }}</p>
              </div>
              <div>
                <p class="text-gray-600">Tipo:</p>
                <span :class="getTransactionTypeClass(selectedTransaction.type)" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full">
                  {{ getTransactionTypeLabel(selectedTransaction.type) }}
                </span>
              </div>
              <div>
                <p class="text-gray-600">Método de Pago:</p>
                <p class="font-medium">{{ getPaymentMethodLabel(selectedTransaction.paymentMethod) }}</p>
              </div>
              <div class="col-span-2">
                <p class="text-gray-600">Descripción:</p>
                <p class="font-medium">{{ selectedTransaction.description }}</p>
              </div>
              <div class="col-span-2">
                <p class="text-gray-600">Monto:</p>
                <p class="text-lg font-bold" :class="selectedTransaction.type === 'cash_out' || selectedTransaction.type === 'refund' ? 'text-red-600' : 'text-green-600'">
                  {{ selectedTransaction.type === 'cash_out' || selectedTransaction.type === 'refund' ? '-' : '+' }}${{ selectedTransaction.amount.toLocaleString() }}
                </p>
              </div>
            </div>

            <div v-if="selectedTransaction.items && selectedTransaction.items.length > 0" class="border-t pt-4">
              <h4 class="font-medium text-gray-900 mb-2">Productos</h4>
              <div class="space-y-2">
                <div v-for="item in selectedTransaction.items" :key="item.id" class="flex justify-between text-sm">
                  <span>{{ item.name }} x{{ item.quantity }}</span>
                  <span>${{ (item.price * item.quantity).toLocaleString() }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end pt-4">
            <button
              @click="showTransactionModal = false"
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
const currentSession = ref(null)
const transactions = ref([])
const transactionFilter = ref('all')

// Modal states
const showOpenSessionModal = ref(false)
const showCloseSessionModal = ref(false)
const showTransactionModal = ref(false)
const selectedTransaction = ref(null)

// Form data
const openingAmount = ref(0)
const openingNotes = ref('')
const closingAmount = ref(0)
const closingNotes = ref('')

// Computed properties
const canRefund = computed(() => {
  return authStore.hasScope('admin') || 
         authStore.hasScope('encargado') || 
         authStore.hasScope('has_scope_pos')
})

const todayTransactions = computed(() => {
  const today = new Date().toDateString()
  return transactions.value.filter(t => new Date(t.timestamp).toDateString() === today).length
})

const todaySales = computed(() => {
  const today = new Date().toDateString()
  return transactions.value
    .filter(t => new Date(t.timestamp).toDateString() === today && (t.type === 'sale'))
    .reduce((sum, t) => sum + t.amount, 0)
})

const cashAmount = computed(() => {
  const today = new Date().toDateString()
  return transactions.value
    .filter(t => new Date(t.timestamp).toDateString() === today && t.paymentMethod === 'cash')
    .reduce((sum, t) => {
      if (t.type === 'cash_out' || t.type === 'refund') {
        return sum - t.amount
      }
      return sum + t.amount
    }, currentSession.value?.openingAmount || 0)
})

const cardAmount = computed(() => {
  const today = new Date().toDateString()
  return transactions.value
    .filter(t => new Date(t.timestamp).toDateString() === today && (t.paymentMethod === 'card' || t.paymentMethod === 'credit_card' || t.paymentMethod === 'debit_card'))
    .reduce((sum, t) => {
      if (t.type === 'refund') {
        return sum - t.amount
      }
      return sum + t.amount
    }, 0)
})

const expectedCash = computed(() => {
  return (currentSession.value?.openingAmount || 0) + cashAmount.value
})

const cashDifference = computed(() => {
  return closingAmount.value - expectedCash.value
})

const paymentMethods = computed(() => {
  const today = new Date().toDateString()
  const todayTransactions = transactions.value.filter(t => new Date(t.timestamp).toDateString() === today && t.type === 'sale')
  const total = todayTransactions.reduce((sum, t) => sum + t.amount, 0)
  
  const methods = [
    { type: 'cash', name: 'Efectivo', amount: 0, count: 0 },
    { type: 'card', name: 'Tarjeta', amount: 0, count: 0 },
    { type: 'transfer', name: 'Transferencia', amount: 0, count: 0 }
  ]
  
  todayTransactions.forEach(t => {
    const method = methods.find(m => {
      if (m.type === 'card') {
        return t.paymentMethod === 'card' || t.paymentMethod === 'credit_card' || t.paymentMethod === 'debit_card'
      }
      return m.type === t.paymentMethod
    })
    if (method) {
      method.amount += t.amount
      method.count++
    }
  })
  
  return methods.map(m => ({
    ...m,
    percentage: total > 0 ? Math.round((m.amount / total) * 100) : 0
  }))
})

const filteredTransactions = computed(() => {
  const today = new Date().toDateString()
  let filtered = transactions.value.filter(t => new Date(t.timestamp).toDateString() === today)
  
  if (transactionFilter.value !== 'all') {
    filtered = filtered.filter(t => t.type === transactionFilter.value)
  }
  
  return filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
})

// Methods
const loadData = async () => {
  try {
    // TODO: Replace with actual API calls
    // const sessionResponse = await api.get('/cash-sessions/current')
    // currentSession.value = sessionResponse.data
    
    // const transactionsResponse = await api.get('/transactions/today')
    // transactions.value = transactionsResponse.data
    
    // Mock data for development
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    
    // Mock current session
    currentSession.value = {
      id: 1,
      startTime: today.toISOString(),
      openingAmount: 100000,
      cashierId: authStore.user?.id,
      cashierName: authStore.user?.name,
      notes: 'Apertura normal'
    }
    
    // Mock transactions
    transactions.value = [
      {
        id: 'TXN001',
        timestamp: new Date(today.getTime() - 3600000).toISOString(),
        type: 'sale',
        description: 'Venta #001 - 3 productos',
        paymentMethod: 'cash',
        amount: 45000,
        items: [
          { id: 1, name: 'Producto A', quantity: 2, price: 15000 },
          { id: 2, name: 'Producto B', quantity: 1, price: 15000 }
        ]
      },
      {
        id: 'TXN002',
        timestamp: new Date(today.getTime() - 3000000).toISOString(),
        type: 'sale',
        description: 'Venta #002 - 1 producto',
        paymentMethod: 'card',
        amount: 25000,
        items: [
          { id: 3, name: 'Producto C', quantity: 1, price: 25000 }
        ]
      },
      {
        id: 'TXN003',
        timestamp: new Date(today.getTime() - 2400000).toISOString(),
        type: 'cash_in',
        description: 'Ingreso adicional de efectivo',
        paymentMethod: 'cash',
        amount: 50000
      },
      {
        id: 'TXN004',
        timestamp: new Date(today.getTime() - 1800000).toISOString(),
        type: 'sale',
        description: 'Venta #003 - 2 productos',
        paymentMethod: 'transfer',
        amount: 80000,
        items: [
          { id: 4, name: 'Producto D', quantity: 2, price: 40000 }
        ]
      },
      {
        id: 'TXN005',
        timestamp: new Date(today.getTime() - 1200000).toISOString(),
        type: 'refund',
        description: 'Devolución venta #001',
        paymentMethod: 'cash',
        amount: 15000
      }
    ]
  } catch (error) {
    console.error('Error loading data:', error)
  }
}

const openSession = () => {
  openingAmount.value = 0
  openingNotes.value = ''
  showOpenSessionModal.value = true
}

const confirmOpenSession = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.post('/cash-sessions', {
    //   openingAmount: openingAmount.value,
    //   notes: openingNotes.value
    // })
    
    currentSession.value = {
      id: Date.now(),
      startTime: new Date().toISOString(),
      openingAmount: openingAmount.value,
      cashierId: authStore.user?.id,
      cashierName: authStore.user?.name,
      notes: openingNotes.value
    }
    
    showOpenSessionModal.value = false
    console.log('Sesión de caja abierta')
  } catch (error) {
    console.error('Error opening session:', error)
  }
}

const confirmCloseSession = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.put(`/cash-sessions/${currentSession.value.id}/close`, {
    //   closingAmount: closingAmount.value,
    //   notes: closingNotes.value
    // })
    
    console.log('Sesión cerrada:', {
      openingAmount: currentSession.value.openingAmount,
      closingAmount: closingAmount.value,
      difference: cashDifference.value,
      notes: closingNotes.value
    })
    
    currentSession.value = null
    showCloseSessionModal.value = false
    console.log('Sesión de caja cerrada')
  } catch (error) {
    console.error('Error closing session:', error)
  }
}

const viewTransaction = (transaction: any) => {
  selectedTransaction.value = transaction
  showTransactionModal.value = true
}

const refundTransaction = async (transaction: any) => {
  if (confirm(`¿Estás seguro de que deseas devolver la transacción ${transaction.id}?`)) {
    try {
      // TODO: Replace with actual API call
      // await api.post(`/transactions/${transaction.id}/refund`)
      
      const refundTransaction = {
        id: `REF${transaction.id}`,
        timestamp: new Date().toISOString(),
        type: 'refund',
        description: `Devolución ${transaction.id}`,
        paymentMethod: transaction.paymentMethod,
        amount: transaction.amount,
        originalTransactionId: transaction.id
      }
      
      transactions.value.push(refundTransaction)
      console.log('Transacción devuelta')
    } catch (error) {
      console.error('Error refunding transaction:', error)
    }
  }
}

const getTransactionTypeClass = (type: string) => {
  const classes = {
    sale: 'bg-green-100 text-green-800',
    refund: 'bg-red-100 text-red-800',
    cash_in: 'bg-blue-100 text-blue-800',
    cash_out: 'bg-orange-100 text-orange-800'
  }
  return classes[type] || classes.sale
}

const getTransactionTypeLabel = (type: string) => {
  const labels = {
    sale: 'Venta',
    refund: 'Devolución',
    cash_in: 'Ingreso',
    cash_out: 'Egreso'
  }
  return labels[type] || 'Venta'
}

const getPaymentMethodLabel = (method: string) => {
  const labels = {
    cash: 'Efectivo',
    card: 'Tarjeta',
    credit_card: 'Tarjeta de Crédito',
    debit_card: 'Tarjeta de Débito',
    transfer: 'Transferencia'
  }
  return labels[method] || 'Efectivo'
}

const formatDateTime = (dateString: string) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('es-ES')
}

const formatTime = (dateString: string) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleTimeString('es-ES', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const getSessionDuration = () => {
  if (!currentSession.value?.startTime) return 'N/A'
  
  const start = new Date(currentSession.value.startTime)
  const now = new Date()
  const diff = now.getTime() - start.getTime()
  
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  
  return `${hours}h ${minutes}m`
}

const printReport = () => {
  // TODO: Implement print functionality
  console.log('Imprimiendo reporte de caja...')
  
  const reportContent = `
    REPORTE DE CAJA
    ===============
    
    Cajero: ${authStore.user?.name}
    Fecha: ${new Date().toLocaleDateString('es-ES')}
    Sesión: ${formatDateTime(currentSession.value?.startTime)} - ${new Date().toLocaleTimeString('es-ES')}
    
    RESUMEN:
    - Monto inicial: $${currentSession.value?.openingAmount?.toLocaleString()}
    - Total ventas: $${todaySales.value.toLocaleString()}
    - Transacciones: ${todayTransactions.value}
    - Efectivo: $${cashAmount.value.toLocaleString()}
    - Tarjetas: $${cardAmount.value.toLocaleString()}
    
    MÉTODOS DE PAGO:
    ${paymentMethods.value.map(m => `- ${m.name}: $${m.amount.toLocaleString()} (${m.count} transacciones)`).join('\n')}
  `
  
  console.log(reportContent)
}

// Lifecycle
onMounted(() => {
  loadData()
})
</script>