import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'
import { useOpsStore } from './stores/ops'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Initialize operational store and network listeners
const opsStore = useOpsStore()
opsStore.initializeNetworkListeners()

app.mount('#app')