<template>
  <div class="bg-white border-t border-gray-200 p-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">Métodos de Pago</h3>
      <div class="text-sm text-gray-500">
        {{ payments.length }} {{ payments.length === 1 ? 'método' : 'métodos' }}
      </div>
    </div>

    <!-- Add Payment Form -->
    <div class="mb-4 p-3 bg-gray-50 rounded-lg">
      <div class="flex space-x-3">
        <!-- Method Selector -->
        <select
          v-model="newPayment.method"
          class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="cash">💵 Efectivo</option>
          <option value="card">💳 Tarjeta Débito</option>
          <option value="transfer">🏦 Transferencia</option>
          <option v-if="allowCC" value="cc">💎 Tarjeta Crédito</option>
        </select>

        <!-- Amount Input -->
        <div class="flex-1">
          <input
            ref="amountInput"
            v-model.number="newPayment.amount"
            type="number"
            step="0.01"
            min="0.01"
            placeholder="Monto"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :class="{ 'border-red-500 focus:ring-red-500': amountError }"
            @keydown.enter="addPayment"
          />
          <div v-if="amountError" class="text-xs text-red-600 mt-1">{{ amountError }}</div>
        </div>

        <!-- Add Button -->
        <button
          @click="addPayment"
          :disabled="!canAddPayment"
          class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
          Agregar
        </button>
      </div>

      <!-- Quick Amount Buttons -->
      <div v-if="suggestedAmounts.length > 0" class="flex space-x-2 mt-3">
        <span class="text-xs text-gray-500 self-center">Rápido:</span>
        <button
          v-for="amount in suggestedAmounts"
          :key="amount"
          @click="setQuickAmount(amount)"
          class="px-3 py-1 text-xs bg-white border border-gray-300 rounded-full hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
          ${{ amount.toFixed(0) }}
        </button>
        <button
          @click="addExactPayment"
          class="px-3 py-1 text-xs bg-green-100 text-green-800 border border-green-300 rounded-full hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
        >
          Exacto
        </button>
      </div>
    </div>

    <!-- Payments List -->
    <div v-if="payments.length > 0" class="space-y-2 mb-4">
      <div
        v-for="(payment, index) in payments"
        :key="index"
        class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
      >
        <div class="flex items-center space-x-3">
          <div class="text-lg">{{ getMethodIcon(payment.method) }}</div>
          <div>
            <div class="text-sm font-medium text-gray-900">
              {{ paymentsStore.getMethodLabel(payment.method) }}
            </div>
            <div class="text-xs text-gray-500">
              ${{ payment.amount.toFixed(2) }}
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Edit Amount -->
          <button
            @click="editPayment(index)"
            class="p-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded transition-colors"
            :aria-label="`Editar ${paymentsStore.getMethodLabel(payment.method)}`"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>

          <!-- Remove -->
          <button
            @click="removePayment(index)"
            class="p-1 text-red-400 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 rounded transition-colors"
            :aria-label="`Eliminar ${paymentsStore.getMethodLabel(payment.method)}`"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Payment Summary -->
    <div class="border-t border-gray-200 pt-4 space-y-2">
      <div class="flex justify-between items-center">
        <span class="text-sm text-gray-600">Total a cobrar:</span>
        <span class="text-lg font-semibold text-gray-900">
          ${{ total.toFixed(2) }}
        </span>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-sm text-gray-600">Total pagado:</span>
        <span class="text-lg font-medium" :class="totalPaidClass">
          ${{ paymentsStore.totalPaid.toFixed(2) }}
        </span>
      </div>

      <div v-if="validation.change > 0" class="flex justify-between items-center">
        <span class="text-sm text-gray-600">Vuelto:</span>
        <span class="text-lg font-bold text-green-600">
          ${{ validation.change.toFixed(2) }}
        </span>
      </div>

      <div v-if="validation.error" class="text-sm text-red-600 font-medium">
        {{ validation.error }}
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="editingIndex !== null" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
        <h4 class="text-lg font-semibold mb-4">Editar Pago</h4>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Método</label>
            <select
              v-model="editForm.method"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="cash">💵 Efectivo</option>
              <option value="card">💳 Tarjeta Débito</option>
              <option value="transfer">🏦 Transferencia</option>
              <option v-if="allowCC" value="cc">💎 Tarjeta Crédito</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Monto</label>
            <input
              v-model.number="editForm.amount"
              type="number"
              step="0.01"
              min="0.01"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div class="flex space-x-3 mt-6">
          <button
            @click="saveEdit"
            class="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Guardar
          </button>
          <button
            @click="cancelEdit"
            class="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { usePaymentsStore } from '@/stores/payments'
import type { Payment } from '@/stores/payments'

interface Props {
  total: number
  allowCC?: boolean
}

interface Emits {
  (e: 'validityChanged', validation: { ok: boolean; change: number; error?: string }): void
}

const props = withDefaults(defineProps<Props>(), {
  allowCC: false
})

const emit = defineEmits<Emits>()
const paymentsStore = usePaymentsStore()

// Form state
const newPayment = ref({
  method: 'cash' as Payment['method'],
  amount: 0
})

const amountInput = ref<HTMLInputElement>()
const amountError = ref<string>('')

// Edit state
const editingIndex = ref<number | null>(null)
const editForm = ref({
  method: 'cash' as Payment['method'],
  amount: 0
})

// Computed
const payments = computed(() => paymentsStore.payments)

const validation = computed(() => paymentsStore.validateAgainst(props.total))

const totalPaidClass = computed(() => {
  const totalPaid = paymentsStore.totalPaid
  if (totalPaid < props.total) return 'text-red-600'
  if (totalPaid > props.total) return 'text-green-600'
  return 'text-gray-900'
})

const canAddPayment = computed(() => {
  return newPayment.value.amount > 0 && !amountError.value
})

const suggestedAmounts = computed(() => {
  if (props.total <= 0) return []
  
  const remaining = props.total - paymentsStore.totalPaid
  if (remaining <= 0) return []

  const amounts = []
  
  // Add exact remaining amount
  amounts.push(remaining)
  
  // Add round numbers above remaining
  const roundAmounts = [10, 20, 50, 100, 200, 500, 1000]
  for (const amount of roundAmounts) {
    if (amount > remaining && amount <= remaining * 2) {
      amounts.push(amount)
    }
  }

  return [...new Set(amounts)].slice(0, 4).sort((a, b) => a - b)
})

// Watch for validation changes
watch(validation, (newValidation) => {
  emit('validityChanged', newValidation)
}, { immediate: true })

// Watch amount input for validation
watch(() => newPayment.value.amount, (amount) => {
  if (amount <= 0) {
    amountError.value = 'El monto debe ser mayor a 0'
  } else {
    amountError.value = ''
  }
})

// Methods
const getMethodIcon = (method: Payment['method']): string => {
  const icons = {
    cash: '💵',
    card: '💳',
    transfer: '🏦',
    cc: '💎'
  }
  return icons[method] || '💰'
}

const addPayment = () => {
  if (!canAddPayment.value) return

  try {
    paymentsStore.addPayment(newPayment.value.method, newPayment.value.amount)
    
    // Reset form
    newPayment.value.amount = 0
    amountError.value = ''
    
    // Focus back to amount input
    nextTick(() => {
      amountInput.value?.focus()
    })
  } catch (error: any) {
    amountError.value = error.message
  }
}

const removePayment = (index: number) => {
  paymentsStore.removePayment(index)
}

const editPayment = (index: number) => {
  const payment = payments.value[index]
  if (payment) {
    editingIndex.value = index
    editForm.value = {
      method: payment.method,
      amount: payment.amount
    }
  }
}

const saveEdit = () => {
  if (editingIndex.value !== null && editForm.value.amount > 0) {
    try {
      paymentsStore.updatePayment(
        editingIndex.value,
        editForm.value.method,
        editForm.value.amount
      )
      cancelEdit()
    } catch (error: any) {
      // Handle error
      console.error('Error updating payment:', error)
    }
  }
}

const cancelEdit = () => {
  editingIndex.value = null
  editForm.value = {
    method: 'cash',
    amount: 0
  }
}

const setQuickAmount = (amount: number) => {
  newPayment.value.amount = amount
  amountError.value = ''
}

const addExactPayment = () => {
  const remaining = props.total - paymentsStore.totalPaid
  if (remaining > 0) {
    paymentsStore.addExactPayment(remaining, newPayment.value.method)
  }
}

// Keyboard shortcuts
const handleKeydown = (event: KeyboardEvent) => {
  // Quick method selection
  if (event.altKey) {
    switch (event.key) {
      case '1':
        event.preventDefault()
        newPayment.value.method = 'cash'
        break
      case '2':
        event.preventDefault()
        newPayment.value.method = 'card'
        break
      case '3':
        event.preventDefault()
        newPayment.value.method = 'transfer'
        break
      case '4':
        if (props.allowCC) {
          event.preventDefault()
          newPayment.value.method = 'cc'
        }
        break
    }
  }
}

// Mount keyboard listeners
import { onMounted, onUnmounted } from 'vue'

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>