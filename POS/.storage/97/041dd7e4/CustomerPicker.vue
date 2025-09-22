<template>
  <div class="flex items-center space-x-3">
    <!-- Customer Selection -->
    <div class="relative">
      <select
        v-model="selectedCustomerId"
        @change="handleCustomerChange"
        class="appearance-none bg-white border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">Seleccionar Cliente</option>
        <option
          v-for="customer in customers"
          :key="customer.id"
          :value="customer.id"
        >
          {{ customer.name }}
        </option>
      </select>
      
      <!-- Dropdown arrow -->
      <div class="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
        <svg class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>

    <!-- Segment Badge -->
    <div
      v-if="selectedCustomer"
      class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
      :class="segmentBadgeClass"
    >
      {{ segmentLabel }}
    </div>

    <!-- Customer Info -->
    <div v-if="selectedCustomer" class="text-sm text-gray-600">
      <span class="font-medium">{{ selectedCustomer.name }}</span>
      <span v-if="selectedCustomer.taxId" class="ml-2 text-gray-500">
        {{ selectedCustomer.taxId }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Customer {
  id: string
  name: string
  segment: 'retail' | 'wholesale'
  email?: string
  taxId?: string
}

interface Props {
  modelValue?: Customer | null
}

interface Emits {
  (e: 'update:modelValue', customer: Customer | null): void
  (e: 'customerChanged', customer: Customer | null): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null
})

const emit = defineEmits<Emits>()

// Mock customers data
const customers: Customer[] = [
  {
    id: 'retail-001',
    name: 'Cliente General',
    segment: 'retail'
  },
  {
    id: 'wholesale-001',
    name: 'Distribuidora Central S.A.',
    segment: 'wholesale',
    email: 'compras@distribuidora.com',
    taxId: '20-12345678-9'
  },
  {
    id: 'wholesale-002',
    name: 'Mayorista del Norte',
    segment: 'wholesale',
    email: 'ventas@mayoristanorte.com',
    taxId: '20-87654321-0'
  },
  {
    id: 'retail-002',
    name: 'Juan Pérez',
    segment: 'retail',
    taxId: '20-11111111-1'
  }
]

const selectedCustomerId = ref<string>(props.modelValue?.id || '')

const selectedCustomer = computed(() => {
  if (!selectedCustomerId.value) return null
  return customers.find(c => c.id === selectedCustomerId.value) || null
})

const segmentLabel = computed(() => {
  if (!selectedCustomer.value) return ''
  return selectedCustomer.value.segment === 'wholesale' ? 'Mayorista' : 'Minorista'
})

const segmentBadgeClass = computed(() => {
  if (!selectedCustomer.value) return ''
  
  return selectedCustomer.value.segment === 'wholesale'
    ? 'bg-purple-100 text-purple-800'
    : 'bg-blue-100 text-blue-800'
})

// Watch for external changes to modelValue
watch(() => props.modelValue, (newCustomer) => {
  selectedCustomerId.value = newCustomer?.id || ''
}, { immediate: true })

// Watch for internal changes and emit
watch(selectedCustomer, (newCustomer) => {
  emit('update:modelValue', newCustomer)
})

const handleCustomerChange = () => {
  const customer = selectedCustomer.value
  emit('customerChanged', customer)
}

// Set default customer on mount
if (!selectedCustomerId.value && customers.length > 0) {
  selectedCustomerId.value = customers[0].id
}
</script>
</template>