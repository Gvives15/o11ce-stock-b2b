import { computed } from 'vue'
import { useOpsStore } from '@/stores/ops'

export function useBlockers() {
  const opsStore = useOpsStore()

  const canCheckout = computed(() => {
    return !opsStore.offline && opsStore.hasShiftOpen && opsStore.hasCashboxOpen
  })

  const checkoutBlockReason = computed(() => {
    if (opsStore.offline) return 'Sin conexión a internet'
    if (!opsStore.hasShiftOpen) return 'No hay turno abierto'
    if (!opsStore.hasCashboxOpen) return 'Caja cerrada'
    return null
  })

  const canOperate = computed(() => {
    return opsStore.canOperate
  })

  const operationBlockReason = computed(() => {
    if (opsStore.offline) return 'Sistema sin conexión'
    if (!opsStore.hasShiftOpen) return 'Turno no iniciado'
    if (!opsStore.hasCashboxOpen) return 'Caja no disponible'
    return null
  })

  const getBlockedButtonClass = (isBlocked: boolean) => {
    return isBlocked 
      ? 'opacity-50 cursor-not-allowed' 
      : 'hover:bg-blue-700'
  }

  const getTooltipMessage = (reason: string | null) => {
    return reason ? `Acción bloqueada: ${reason}` : ''
  }

  return {
    canCheckout,
    checkoutBlockReason,
    canOperate,
    operationBlockReason,
    getBlockedButtonClass,
    getTooltipMessage
  }
}