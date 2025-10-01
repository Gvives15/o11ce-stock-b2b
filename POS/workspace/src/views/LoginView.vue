<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Iniciar Sesión
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Sistema POS
        </p>
      </div>
      <form class="mt-8 space-y-6" @submit.prevent="handleLogin">
        <div class="space-y-4">
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
              Usuario
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              class="input-field"
              placeholder="tu_usuario"
            />
          </div>
          
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
              Contraseña
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              class="input-field"
              placeholder="••••••••"
            />
          </div>
          
          <button
            @click="handleLogin"
            :disabled="loading"
            class="btn-primary w-full"
          >
            {{ loading ? 'Iniciando sesión...' : 'Iniciar Sesión' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useToast } from '@/lib/toast';

const router = useRouter();
const authStore = useAuthStore();
const { success, error } = useToast();

const username = ref('');
const password = ref('');
const loading = ref(false);

const handleLogin = async () => {
  if (!username.value || !password.value) {
    error('Por favor, completa todos los campos')
    return
  }

  try {
    loading.value = true
    await authStore.login(username.value, password.value)
    success('¡Inicio de sesión exitoso!')
    
    // Redirigir siempre al dashboard - será el centro de redirección
    await router.push('/dashboard')
  } catch (err: any) {
    error(err.message || 'Error al iniciar sesión')
  } finally {
    loading.value = false
  }
}
</script>