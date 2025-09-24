export interface ToastOptions {
  message: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
}

export interface Toast extends ToastOptions {
  id: string;
  timestamp: number;
}

class ToastManager {
  private toasts: Toast[] = [];
  private listeners: ((toasts: Toast[]) => void)[] = [];

  constructor() {
    // Escuchar eventos personalizados del axiosClient
    if (typeof window !== 'undefined') {
      window.addEventListener('auth-error', (event: any) => {
        this.show({
          message: event.detail.message,
          type: 'error',
          duration: 5000
        });
      });

      window.addEventListener('server-error', (event: any) => {
        this.show({
          message: event.detail.message,
          type: 'error',
          duration: 4000
        });
      });

      window.addEventListener('client-error', (event: any) => {
        this.show({
          message: event.detail.message,
          type: 'warning',
          duration: 4000
        });
      });

      window.addEventListener('timeout-error', (event: any) => {
        this.show({
          message: event.detail.message,
          type: 'warning',
          duration: 4000
        });
      });

      window.addEventListener('network-error', (event: any) => {
        this.show({
          message: event.detail.message,
          type: 'error',
          duration: 4000
        });
      });
    }
  }

  show(options: ToastOptions): string {
    const toast: Toast = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: Date.now(),
      type: 'info',
      duration: 3000,
      position: 'top-right',
      ...options
    };

    this.toasts.push(toast);
    this.notifyListeners();

    // Auto-remove después del duration especificado
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        this.remove(toast.id);
      }, toast.duration);
    }

    return toast.id;
  }

  remove(id: string): void {
    this.toasts = this.toasts.filter(toast => toast.id !== id);
    this.notifyListeners();
  }

  clear(): void {
    this.toasts = [];
    this.notifyListeners();
  }

  getToasts(): Toast[] {
    return [...this.toasts];
  }

  subscribe(listener: (toasts: Toast[]) => void): () => void {
    this.listeners.push(listener);
    
    // Retornar función de cleanup
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener([...this.toasts]));
  }

  // Métodos de conveniencia
  success(message: string, duration = 3000): string {
    return this.show({ message, type: 'success', duration });
  }

  error(message: string, duration = 4000): string {
    return this.show({ message, type: 'error', duration });
  }

  warning(message: string, duration = 3500): string {
    return this.show({ message, type: 'warning', duration });
  }

  info(message: string, duration = 3000): string {
    return this.show({ message, type: 'info', duration });
  }
}

// Instancia singleton
export const toast = new ToastManager();

// Hook para Vue
export function useToast() {
  return {
    toast,
    success: toast.success.bind(toast),
    error: toast.error.bind(toast),
    warning: toast.warning.bind(toast),
    info: toast.info.bind(toast),
    show: toast.show.bind(toast),
    remove: toast.remove.bind(toast),
    clear: toast.clear.bind(toast)
  };
}