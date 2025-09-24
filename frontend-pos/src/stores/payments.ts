import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Payment {
  method: 'cash' | 'card' | 'transfer' | 'cc'
  amount: number
}

export interface PaymentValidation {
  ok: boolean
  change: number
  error?: string
}

export const usePaymentsStore = defineStore('payments', () => {
  // State
  const payments = ref<Payment[]>([])

  // Getters
  const totalPaid = computed(() => {
    return payments.value.reduce((sum, payment) => sum + payment.amount, 0)
  })

  const paymentMethodLabels = {
    cash: 'Efectivo',
    card: 'Tarjeta Débito',
    transfer: 'Transferencia',
    cc: 'Tarjeta Crédito'
  }

  // Actions
  const addPayment = (method: Payment['method'], amount: number) => {
    if (amount <= 0) {
      throw new Error('El monto debe ser mayor a 0')
    }

    payments.value.push({
      method,
      amount: Math.round(amount * 100) / 100 // Round to 2 decimals
    })
  }

  const removePayment = (index: number) => {
    if (index >= 0 && index < payments.value.length) {
      payments.value.splice(index, 1)
    }
  }

  const setAmount = (index: number, amount: number) => {
    if (index >= 0 && index < payments.value.length) {
      if (amount <= 0) {
        throw new Error('El monto debe ser mayor a 0')
      }
      payments.value[index].amount = Math.round(amount * 100) / 100
    }
  }

  const updatePayment = (index: number, method: Payment['method'], amount: number) => {
    if (index >= 0 && index < payments.value.length) {
      if (amount <= 0) {
        throw new Error('El monto debe ser mayor a 0')
      }
      payments.value[index] = {
        method,
        amount: Math.round(amount * 100) / 100
      }
    }
  }

  const validateAgainst = (total: number): PaymentValidation => {
    const totalPaidValue = totalPaid.value
    
    if (payments.value.length === 0) {
      return {
        ok: false,
        change: 0,
        error: 'Agregá al menos un método de pago'
      }
    }

    // Check for invalid amounts
    const invalidPayment = payments.value.find(p => p.amount <= 0)
    if (invalidPayment) {
      return {
        ok: false,
        change: 0,
        error: 'Todos los montos deben ser mayores a 0'
      }
    }

    if (totalPaidValue < total) {
      const remaining = total - totalPaidValue
      return {
        ok: false,
        change: 0,
        error: `Falta pagar $${remaining.toFixed(2)}`
      }
    }

    const change = totalPaidValue - total
    return {
      ok: true,
      change: Math.round(change * 100) / 100
    }
  }

  const clearPayments = () => {
    payments.value = []
  }

  const getMethodLabel = (method: Payment['method']): string => {
    return paymentMethodLabels[method] || method
  }

  // Quick payment helpers
  const addCashPayment = (amount: number) => {
    addPayment('cash', amount)
  }

  const addCardPayment = (amount: number) => {
    addPayment('card', amount)
  }

  const addTransferPayment = (amount: number) => {
    addPayment('transfer', amount)
  }

  // Exact payment helper
  const addExactPayment = (total: number, preferredMethod: Payment['method'] = 'cash') => {
    clearPayments()
    addPayment(preferredMethod, total)
  }

  return {
    // State
    payments,
    
    // Getters
    totalPaid,
    paymentMethodLabels,
    
    // Actions
    addPayment,
    removePayment,
    setAmount,
    updatePayment,
    validateAgainst,
    clearPayments,
    getMethodLabel,
    
    // Helpers
    addCashPayment,
    addCardPayment,
    addTransferPayment,
    addExactPayment
  }
})