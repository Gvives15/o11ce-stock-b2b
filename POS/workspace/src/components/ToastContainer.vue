<template>
  <div class="toast-container">
    <TransitionGroup
      name="toast"
      tag="div"
      class="toast-list"
      :class="positionClass"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="[`toast-${toast.type}`, `toast-${toast.position || 'top-right'}`]"
        @click="removeToast(toast.id)"
      >
        <div class="toast-content">
          <div class="toast-icon">
            <svg v-if="toast.type === 'success'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            <svg v-else-if="toast.type === 'error'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
            <svg v-else-if="toast.type === 'warning'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="toast-message">{{ toast.message }}</div>
          <button
            class="toast-close"
            @click.stop="removeToast(toast.id)"
            aria-label="Cerrar notificación"
          >
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { toast, type Toast } from '@/lib/toast';

const toasts = ref<Toast[]>([]);
let unsubscribe: (() => void) | null = null;

const positionClass = computed(() => {
  const firstToast = toasts.value[0];
  if (!firstToast) return 'toast-list-top-right';
  
  const position = firstToast.position || 'top-right';
  return `toast-list-${position}`;
});

const removeToast = (id: string) => {
  toast.remove(id);
};

onMounted(() => {
  unsubscribe = toast.subscribe((newToasts) => {
    toasts.value = newToasts;
  });
  
  // Cargar toasts existentes
  toasts.value = toast.getToasts();
});

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe();
  }
});
</script>

<style scoped>
.toast-container {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
}

.toast-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
}

.toast-list-top-right {
  top: 0;
  right: 0;
}

.toast-list-top-left {
  top: 0;
  left: 0;
}

.toast-list-bottom-right {
  bottom: 0;
  right: 0;
}

.toast-list-bottom-left {
  bottom: 0;
  left: 0;
}

.toast-list-top-center {
  top: 0;
  left: 50%;
  transform: translateX(-50%);
}

.toast-list-bottom-center {
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
}

.toast {
  pointer-events: auto;
  min-width: 300px;
  max-width: 500px;
  border-radius: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: all 0.3s ease;
}

.toast:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.toast-success {
  @apply bg-green-50 border border-green-200;
}

.toast-error {
  @apply bg-red-50 border border-red-200;
}

.toast-warning {
  @apply bg-yellow-50 border border-yellow-200;
}

.toast-info {
  @apply bg-blue-50 border border-blue-200;
}

.toast-content {
  display: flex;
  align-items: flex-start;
  padding: 1rem;
  gap: 0.75rem;
}

.toast-icon {
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.toast-success .toast-icon {
  @apply text-green-600;
}

.toast-error .toast-icon {
  @apply text-red-600;
}

.toast-warning .toast-icon {
  @apply text-yellow-600;
}

.toast-info .toast-icon {
  @apply text-blue-600;
}

.toast-message {
  flex: 1;
  font-size: 0.875rem;
  line-height: 1.25rem;
  font-weight: 500;
}

.toast-success .toast-message {
  @apply text-green-800;
}

.toast-error .toast-message {
  @apply text-red-800;
}

.toast-warning .toast-message {
  @apply text-yellow-800;
}

.toast-info .toast-message {
  @apply text-blue-800;
}

.toast-close {
  flex-shrink: 0;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: background-color 0.2s ease;
}

.toast-close:hover {
  @apply bg-gray-100;
}

.toast-success .toast-close {
  @apply text-green-600 hover:bg-green-100;
}

.toast-error .toast-close {
  @apply text-red-600 hover:bg-red-100;
}

.toast-warning .toast-close {
  @apply text-yellow-600 hover:bg-yellow-100;
}

.toast-info .toast-close {
  @apply text-blue-600 hover:bg-blue-100;
}

/* Animaciones */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast-move {
  transition: transform 0.3s ease;
}

/* Animaciones para posiciones izquierdas */
.toast-list-top-left .toast-enter-from,
.toast-list-bottom-left .toast-enter-from {
  transform: translateX(-100%);
}

.toast-list-top-left .toast-leave-to,
.toast-list-bottom-left .toast-leave-to {
  transform: translateX(-100%);
}

/* Animaciones para posiciones centrales */
.toast-list-top-center .toast-enter-from,
.toast-list-bottom-center .toast-enter-from {
  transform: translateY(-100%);
}

.toast-list-top-center .toast-leave-to,
.toast-list-bottom-center .toast-leave-to {
  transform: translateY(-100%);
}
</style>