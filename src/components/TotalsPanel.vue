<template>
  <div class="bg-white border-t border-gray-200 p-4">
    <!-- Loading Skeleton -->
    <div v-if="isLoading" class="space-y-3">
      <div class="flex justify-between items-center">
        <div class="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
        <div class="h-4 bg-gray-200 rounded w-16 animate-pulse"></div>
      </div>
      <div class="flex justify-between items-center">
        <div class="h-4 bg-gray-200 rounded w-24 animate-pulse"></div>
        <div class="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
      </div>
      <div class="flex justify-between items-center pt-2 border-t">
        <div class="h-6 bg-gray-200 rounded w-16 animate-pulse"></div>
        <div class="h-6 bg-gray-200 rounded w-24 animate-pulse"></div>
      </div>
    </div>

    <!-- Totals Content -->
    <div v-else-if="quote" class="space-y-3">
      <!-- Subtotal -->
      <div class="flex justify-between items-center">
        <span class="text-sm text-gray-600">Subtotal:</span>
        <span class="text-sm font-medium text-gray-900">
          {{ formatCurrency(quote.subtotal) }}
        </span>
      </div>

      <!-- Combo Discounts -->
      <div v-if="quote.combo_discounts.length > 0" class="space-y-2">
        <div class="text-sm font-medium text-gray-700">Descuentos:</div>
        <div
          v-for="combo in quote.combo_discounts"
          :key="combo.id"
          class="flex justify-between items-center pl-4"
        >
          <div class="flex-1">
            <div class="text-sm text-green-700 font-medium">{{ combo.name }}</div>
            <div class="text-xs text-gray-500">{{ combo.description }}</div>
          </div>
          <span class="text-sm font-medium text-green-700">
            -{{ formatCurrency(combo.amount) }}
          </span>
        </div>
      </div>

      <!-- Tax -->
      <div class="flex justify-between items-center">
        <span class="text-sm text-gray-600">IVA (21%):</span>
        <span class="text-sm font-medium text-gray-900">
          {{ formatCurrency(quote.tax_amount) }}
        </span>
      </div>

      <!-- Total -->
      <div class="flex justify-between items-center pt-3 border-t border-gray-200">
        <span class="text-lg font-semibold text-gray-900">Total:</span>
        <span
          ref="totalElement"
          class="text-2xl font-bold text-gray-900 transition-all duration-100"
          :class="{ 'animate-pulse': isAnimating }"
          aria-live="polite"
        >
          {{ formatCurrency(quote.total) }}
        </span>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-4">
      <div class="text-red-600 text-sm font-medium mb-2">{{ error }}</div>
      <div v-if="lastValidTotal" class="text-xs text-gray-500">
        Último total válido: {{ formatCurrency(lastValidTotal) }}
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-4 text-gray-500 text-sm">
      Los totales aparecerán aquí
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface ComboDiscount {
  id: string
  name: string
  amount: number
  description: string
}

interface Quote {
  subtotal: number
  discounts_total: number
  total: number
  combo_discounts: ComboDiscount[]
  tax_amount: number
  currency: string
}

interface Props {
  quote: Quote | null
  isLoading: boolean
  error: string | null
}

const props = defineProps<Props>()

const totalElement = ref<HTMLElement>()
const isAnimating = ref(false)
const lastValidTotal = ref<number | null>(null)
const lastComboCount = ref(0)

// Format currency
const formatCurrency = (amount: number): string => {
  return `$${amount.toFixed(2)}`
}

// Watch for total changes and animate
watch(() => props.quote?.total, async (newTotal, oldTotal) => {
  if (newTotal !== undefined && oldTotal !== undefined && newTotal !== oldTotal) {
    isAnimating.value = true
    
    // Store last valid total
    lastValidTotal.value = newTotal
    
    await nextTick()
    setTimeout(() => {
      isAnimating.value = false
    }, 100)
  }
})

// Watch for new combo discounts and show toast
watch(() => props.quote?.combo_discounts, (newCombos, oldCombos) => {
  if (newCombos && oldCombos) {
    const newComboCount = newCombos.length
    const oldComboCount = oldCombos.length
    
    if (newComboCount > oldComboCount) {
      // New combo applied
      const newCombo = newCombos[newCombos.length - 1]
      showComboToast(newCombo)
    }
  }
  
  if (newCombos) {
    lastComboCount.value = newCombos.length
  }
}, { deep: true })

// Show combo toast notification
const showComboToast = (combo: ComboDiscount) => {
  // Create toast element
  const toast = document.createElement('div')
  toast.className = `
    fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg
    transform transition-all duration-300 translate-x-full opacity-0 max-w-sm
  `
  toast.innerHTML = `
    <div class="flex items-center space-x-2">
      <svg class="w-5 h-5 text-green-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
      <div>
        <div class="font-medium">Aplicado: ${combo.name}</div>
        <div class="text-sm text-green-200">Ahorrás ${formatCurrency(combo.amount)}</div>
      </div>
    </div>
  `
  
  document.body.appendChild(toast)
  
  // Animate in
  setTimeout(() => {
    toast.classList.remove('translate-x-full', 'opacity-0')
  }, 10)
  
  // Auto remove after 4 seconds
  setTimeout(() => {
    toast.classList.add('translate-x-full', 'opacity-0')
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast)
      }
    }, 300)
  }, 4000)
}

// Initialize last valid total
watch(() => props.quote?.total, (total) => {
  if (total !== undefined) {
    lastValidTotal.value = total
  }
}, { immediate: true })
</script>