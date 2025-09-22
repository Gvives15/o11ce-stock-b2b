<template>
  <div v-if="activeBanner" class="banner-container">
    <div
      class="banner"
      :class="{
        'banner-critical': activeBanner.type === 'critical',
        'banner-warning': activeBanner.type === 'warning'
      }"
    >
      <div class="flex items-center">
        <svg
          class="w-5 h-5 mr-2"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            v-if="activeBanner.type === 'critical'"
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clip-rule="evenodd"
          />
          <path
            v-else
            fill-rule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="font-medium">{{ activeBanner.message }}</span>
      </div>

      <!-- Action buttons for some banners -->
      <div v-if="activeBanner.actions" class="flex space-x-2 ml-4">
        <button
          v-for="action in activeBanner.actions"
          :key="action.label"
          @click="action.handler"
          class="text-xs underline hover:no-underline"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOpsStore } from '@/stores/ops'

interface BannerAction {
  label: string
  handler: () => void
}

interface Banner {
  type: 'critical' | 'warning'
  message: string
  actions?: BannerAction[]
}

const opsStore = useOpsStore()

const activeBanner = computed((): Banner | null => {
  // Priority order: offline > no shift > no cashbox
  if (opsStore.offline) {
    return {
      type: 'critical',
      message: 'Sin conexión: modo lectura',
      actions: [
        {
          label: 'Reintentar',
          handler: () => {
            // Force check online status
            opsStore.setOffline(!navigator.onLine)
          }
        }
      ]
    }
  }

  if (!opsStore.hasShiftOpen) {
    return {
      type: 'warning',
      message: 'No hay turno abierto',
      actions: [
        {
          label: 'Abrir Turno',
          handler: () => {
            // Mock action - in real app would open shift dialog
            opsStore.setShift(true)
          }
        }
      ]
    }
  }

  if (!opsStore.hasCashboxOpen) {
    return {
      type: 'warning',
      message: 'Caja cerrada',
      actions: [
        {
          label: 'Abrir Caja',
          handler: () => {
            // Mock action - in real app would open cashbox dialog
            opsStore.setCashbox(true)
          }
        }
      ]
    }
  }

  return null
})
</script>

<style scoped>
.banner-container {
  @apply sticky top-0 z-40;
}

.banner {
  @apply px-6 py-3 flex items-center justify-between text-sm;
}

.banner-critical {
  @apply bg-red-100 text-red-800 border-b border-red-200;
}

.banner-warning {
  @apply bg-amber-100 text-amber-800 border-b border-amber-200;
}
</style>