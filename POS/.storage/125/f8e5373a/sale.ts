import { defineStore } from 'pinia'
import { ref } from 'vue'
import { v4 as uuidv4 } from 'uuid'

export interface SaleState {
  customerId: string | null
  idempotencyKey: string
  isProcessing: boolean
  lastOrderId: number | null
}

export const useSaleStore = defineStore('sale', () => {
  // State
  const customerId = ref<string | null>(null)
  const idempotencyKey = ref<string>(uuidv4())
  const isProcessing = ref<boolean>(false)
  const lastOrderId = ref<number | null>(null)

  // Actions
  const setCustomerId = (id: string | null) => {
    customerId.value = id
  }

  const resetKey = () => {
    idempotencyKey.value = uuidv4()
    console.log('New idempotency key generated:', idempotencyKey.value)
  }

  const setProcessing = (processing: boolean) => {
    isProcessing.value = processing
  }

  const setLastOrderId = (orderId: number | null) => {
    lastOrderId.value = orderId
  }

  const startNewSale = () => {
    customerId.value = null
    resetKey()
    isProcessing.value = false
    lastOrderId.value = null
  }

  const completeSale = (orderId: number) => {
    lastOrderId.value = orderId
    isProcessing.value = false
    // Generate new key for next sale
    resetKey()
  }

  return {
    // State
    customerId,
    idempotencyKey,
    isProcessing,
    lastOrderId,
    
    // Actions
    setCustomerId,
    resetKey,
    setProcessing,
    setLastOrderId,
    startNewSale,
    completeSale
  }
})