<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  // Initialize token from localStorage if available
  const token = localStorage.getItem('access_token')
  if (token) {
    authStore.setToken(token)
  }
})
</script>