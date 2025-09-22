<template>
  <div v-if="show" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 transform transition-all">
      <!-- Header -->
      <div class="bg-green-600 text-white p-6 rounded-t-lg text-center">
        <div class="text-4xl mb-2">✅</div>
        <h2 class="text-xl font-bold">¡Venta Realizada!</h2>
      </div>

      <!-- Content -->
      <div class="p-6 space-y-4">
        <!-- Receipt Info -->
        <div class="text-center">
          <div class="text-sm text-gray-600 mb-1">Número de Ticket</div>
          <div class="text-2xl font-bold text-gray-900">{{ receipt?.number }}</div>
        </div>

        <!-- Totals Summary -->
        <div class="bg-gray-50 rounded-lg p-4 space-y-2">
          <div class="flex justify-between">
            <span class="text-gray-600">Total:</span>
            <span class="font-semibold">${{ totals?.total.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600">Pagado:</span>
            <span class="font-semibold">${{ totals?.paid.toFixed(2) }}</span>
          </div>
          <div v-if="totals && totals.change > 0" class="flex justify-between border-t pt-2">
            <span class="text-gray-600">Vuelto:</span>
            <span class="text-lg font-bold text-green-600">${{ totals.change.toFixed(2) }}</span>
          </div>
        </div>

        <!-- Payment Methods Used -->
        <div v-if="paymentsUsed.length > 0" class="space-y-2">
          <div class="text-sm font-medium text-gray-700">Métodos de pago:</div>
          <div class="space-y-1">
            <div
              v-for="payment in paymentsUsed"
              :key="payment.method"
              class="flex justify-between text-sm"
            >
              <span class="text-gray-600">{{ getMethodLabel(payment.method) }}:</span>
              <span>${{ payment.amount.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="space-y-3 pt-4">
          <!-- Print Receipt -->
          <button
            @click="printReceipt"
            class="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors flex items-center justify-center space-x-2"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            <span>Imprimir Ticket</span>
          </button>

          <!-- New Sale -->
          <button
            @click="startNewSale"
            class="w-full bg-gray-200 text-gray-800 py-3 px-4 rounded-lg font-semibold hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
          >
            Nueva Venta
          </button>
        </div>

        <!-- Auto-close timer -->
        <div v-if="autoCloseSeconds > 0" class="text-center text-sm text-gray-500">
          Cerrando automáticamente en {{ autoCloseSeconds }}s
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import type { CheckoutTotals, CheckoutReceipt } from '@/composables/useCheckout'
import type { Payment } from '@/stores/payments'

interface Props {
  show: boolean
  totals: CheckoutTotals | null
  receipt: CheckoutReceipt | null
  paymentsUsed: Payment[]
  autoClose?: boolean
  autoCloseDelay?: number
}

interface Emits {
  (e: 'close'): void
  (e: 'newSale'): void
  (e: 'print'): void
}

const props = withDefaults(defineProps<Props>(), {
  autoClose: true,
  autoCloseDelay: 10
})

const emit = defineEmits<Emits>()

const autoCloseSeconds = ref(0)
let autoCloseTimer: NodeJS.Timeout | null = null

const paymentMethodLabels = {
  cash: 'Efectivo',
  card: 'Tarjeta Débito', 
  transfer: 'Transferencia',
  cc: 'Tarjeta Crédito'
}

const getMethodLabel = (method: string): string => {
  return paymentMethodLabels[method as keyof typeof paymentMethodLabels] || method
}

const printReceipt = () => {
  if (props.receipt?.print_url) {
    // Open print URL in new window
    const printWindow = window.open(props.receipt.print_url, '_blank', 'width=400,height=600')
    if (printWindow) {
      printWindow.focus()
    }
    emit('print')
  }
}

const startNewSale = () => {
  emit('newSale')
  emit('close')
}

const startAutoCloseTimer = () => {
  if (!props.autoClose) return
  
  autoCloseSeconds.value = props.autoCloseDelay
  
  autoCloseTimer = setInterval(() => {
    autoCloseSeconds.value--
    if (autoCloseSeconds.value <= 0) {
      clearAutoCloseTimer()
      startNewSale()
    }
  }, 1000)
}

const clearAutoCloseTimer = () => {
  if (autoCloseTimer) {
    clearInterval(autoCloseTimer)
    autoCloseTimer = null
  }
  autoCloseSeconds.value = 0
}

// Watch for modal show/hide
watch(() => props.show, (show) => {
  if (show) {
    startAutoCloseTimer()
  } else {
    clearAutoCloseTimer()
  }
})

// Keyboard shortcuts
const handleKeydown = (event: KeyboardEvent) => {
  if (!props.show) return

  switch (event.key) {
    case 'Enter':
    case 'p':
    case 'P':
      event.preventDefault()
      printReceipt()
      break
    case 'Escape':
    case 'n':
    case 'N':
      event.preventDefault()
      startNewSale()
      break
    case ' ': // Spacebar pauses auto-close
      event.preventDefault()
      if (autoCloseTimer) {
        clearAutoCloseTimer()
      } else if (props.autoClose) {
        startAutoCloseTimer()
      }
      break
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  clearAutoCloseTimer()
})
</script>