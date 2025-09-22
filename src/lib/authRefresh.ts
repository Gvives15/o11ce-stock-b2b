// Queue management for token refresh to avoid race conditions
let isRefreshing = false
let pendingRequests: ((token: string) => void)[] = []

export function isCurrentlyRefreshing(): boolean {
  return isRefreshing
}

export function setRefreshing(status: boolean): void {
  isRefreshing = status
}

export function enqueue(callback: (token: string) => void): void {
  pendingRequests.push(callback)
}

export function resolveAll(newToken: string): void {
  pendingRequests.forEach(callback => callback(newToken))
  pendingRequests = []
}

export function clearQueue(): void {
  pendingRequests = []
}

export function getQueueLength(): number {
  return pendingRequests.length
}