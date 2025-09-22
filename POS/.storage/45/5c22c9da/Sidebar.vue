<template>
  <aside class="w-64 bg-white shadow-sm border-r border-gray-200 h-full">
    <div class="p-4">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Navegación</h2>
      
      <nav class="space-y-2">
        <router-link
          v-for="item in filteredMenuItems"
          :key="item.id"
          :to="item.route"
          class="nav-item"
          :class="{ 'nav-item-active': isActiveRoute(item.route) }"
          :aria-current="isActiveRoute(item.route) ? 'page' : undefined"
        >
          <svg
            class="w-5 h-5 mr-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              :d="item.icon"
            />
          </svg>
          {{ item.label }}
        </router-link>
      </nav>
    </div>

    <!-- User Info Section -->
    <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
      <div class="text-sm text-gray-600">
        <div class="font-medium">{{ authStore.user?.email }}</div>
        <div class="flex flex-wrap gap-1 mt-1">
          <span
            v-for="role in authStore.roles"
            :key="role"
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
          >
            {{ role }}
          </span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { MENU_ITEMS } from '@/config/menu'

const route = useRoute()
const authStore = useAuthStore()

const filteredMenuItems = computed(() => {
  return MENU_ITEMS.filter(item => 
    item.roles.some(role => authStore.roles.includes(role))
  )
})

const isActiveRoute = (itemRoute: string) => {
  return route.path === itemRoute
}
</script>

<style scoped>
.nav-item {
  @apply flex items-center px-3 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors;
}

.nav-item-active {
  @apply bg-blue-50 text-blue-700 border-r-2 border-blue-700;
}
</style>