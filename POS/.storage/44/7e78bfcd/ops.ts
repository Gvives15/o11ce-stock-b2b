import { defineStore } from 'pinia'

export const useOpsStore = defineStore('ops', {
  state: () => ({
    hasShiftOpen: false,
    hasCashboxOpen: false,
    offline: false
  }),

  getters: {
    canOperate: (state) => !state.offline && state.hasShiftOpen && state.hasCashboxOpen,
    canCheckout: (state) => !state.offline && state.hasShiftOpen && state.hasCashboxOpen,
    operationalStatus: (state) => {
      if (state.offline) return 'offline'
      if (!state.hasShiftOpen) return 'no-shift'
      if (!state.hasCashboxOpen) return 'no-cashbox'
      return 'operational'
    },
    statusMessage: (state) => {
      if (state.offline) return 'Sin conexión: modo lectura'
      if (!state.hasShiftOpen) return 'No hay turno abierto'
      if (!state.hasCashboxOpen) return 'Caja cerrada'
      return 'Sistema operativo'
    }
  },

  actions: {
    setShift(open: boolean) {
      this.hasShiftOpen = open
    },

    setCashbox(open: boolean) {
      this.hasCashboxOpen = open
    },

    setOffline(flag: boolean) {
      this.offline = flag
    },

    initializeNetworkListeners() {
      // Set initial offline state
      this.setOffline(!navigator.onLine)

      // Listen for network changes
      const handleOnline = () => this.setOffline(false)
      const handleOffline = () => this.setOffline(true)

      window.addEventListener('online', handleOnline)
      window.addEventListener('offline', handleOffline)

      // Return cleanup function
      return () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
      }
    }
  }
})