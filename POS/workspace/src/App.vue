<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <router-view />
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import ToastContainer from '@/components/ToastContainer.vue'

const authStore = useAuthStore()

onMounted(() => {
  // Verificar si hay token guardado al iniciar la app
  authStore.checkAuth()
})
</script>

<style>
#app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>