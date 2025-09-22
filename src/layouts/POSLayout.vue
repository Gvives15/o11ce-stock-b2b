<template>
  <div class="min-h-screen bg-gray-50 flex">
    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col">
      <!-- Topbar -->
      <Topbar :title="pageTitle" />
      
      <!-- Global Banners -->
      <GlobalBanners />

      <!-- Main Content -->
      <main class="flex-1 p-6 overflow-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import Topbar from '@/components/Topbar.vue'
import GlobalBanners from '@/components/GlobalBanners.vue'

const route = useRoute()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/pos': 'Punto de Venta',
    '/history': 'Historial de Ventas',
    '/settings': 'Configuración POS'
  }
  return titles[route.path] || 'Sistema POS'
})
</script>