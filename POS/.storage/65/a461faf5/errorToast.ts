import type { AxiosError } from 'axios'

// Simple toast implementation - in production, use a proper toast library
class ToastManager {
  private container: HTMLElement | null = null

  private ensureContainer() {
    if (!this.container) {
      this.container = document.createElement('div')
      this.container.id = 'toast-container'
      this.container.className = 'fixed top-4 right-4 z-50 space-y-2'
      document.body.appendChild(this.container)
    }
    return this.container
  }

  show(message: string, type: 'error' | 'warning' | 'info' = 'error') {
    const container = this.ensureContainer()
    
    const toast = document.createElement('div')
    toast.className = `
      px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium
      transform transition-all duration-300 translate-x-full opacity-0
      ${type === 'error' ? 'bg-red-600' : 
        type === 'warning' ? 'bg-amber-600' : 'bg-blue-600'}
    `
    toast.textContent = message
    
    container.appendChild(toast)
    
    // Animate in
    setTimeout(() => {
      toast.classList.remove('translate-x-full', 'opacity-0')
    }, 10)
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      toast.classList.add('translate-x-full', 'opacity-0')
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast)
        }
      }, 300)
    }, 5000)
  }
}

const toastManager = new ToastManager()

export function mapErrorToMessage(error: AxiosError | Error): string {
  if ('isAxiosError' in error && error.isAxiosError) {
    const axiosError = error as AxiosError
    
    // Network errors
    if (!axiosError.response) {
      return 'Sin conexión a internet'
    }
    
    const status = axiosError.response.status
    const data = axiosError.response.data as any
    
    // Use server message if available and user-friendly
    if (data?.message && typeof data.message === 'string' && data.message.length < 100) {
      return data.message
    }
    
    // Default messages by status code
    switch (status) {
      case 400:
        return 'Datos inválidos'
      case 401:
        return 'Credenciales inválidas'
      case 403:
        return 'Acceso denegado'
      case 404:
        return 'Recurso no encontrado'
      case 409:
        return 'Conflicto - No se pudo completar la acción'
      case 422:
        return 'Datos de entrada inválidos'
      case 429:
        return 'Demasiadas solicitudes - Intenta más tarde'
      case 500:
        return 'Error interno del servidor'
      case 502:
        return 'Servidor no disponible'
      case 503:
        return 'Servicio temporalmente no disponible'
      default:
        if (status >= 500) {
          return 'Error del servidor'
        }
        if (status >= 400) {
          return 'Error en la solicitud'
        }
        return 'Error desconocido'
    }
  }
  
  // Generic error
  return error.message || 'Error inesperado'
}

export function showToast(message: string, type: 'error' | 'warning' | 'info' = 'error') {
  toastManager.show(message, type)
}

export function showErrorToast(error: AxiosError | Error) {
  const message = mapErrorToMessage(error)
  showToast(message, 'error')
}