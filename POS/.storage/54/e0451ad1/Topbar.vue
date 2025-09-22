<template>
  <header class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center">
        <h1 class="text-xl font-semibold text-gray-900">{{ title }}</h1>
      </div>

      <div class="flex items-center space-x-4">
        <!-- Connection Status -->
        <div class="flex items-center space-x-2">
          <div
            class="w-2 h-2 rounded-full"
            :class="{
              'bg-green-500': !opsStore.offline,
              'bg-red-500': opsStore.offline
            }"
          ></div>
          <span
            class="text-xs font-medium px-2 py-1 rounded-full"
            :class="{
              'bg-green-100 text-green-800': !opsStore.offline,
              'bg-red-100 text-red-800': opsStore.offline
            }"
          >
            {{ opsStore.offline ? 'Offline' : 'Online' }}
          </span>
        </div>

        <!-- User Actions -->
        <button
          @click="handleLogout"
          class="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          Cerrar Sesión
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useOpsStore } from '@/stores/ops'

interface Props {
  title?: string
}

withDefaults(defineProps<Props>(), {
  title: 'Sistema POS'
})

const router = useRouter()
const authStore = useAuthStore()
const opsStore = useOpsStore()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>