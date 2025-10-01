<template>
  <div class="analytics-view">
    <!-- Header -->
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Analytics Avanzado</h1>
          <p class="text-gray-600 mt-1">Análisis profundo del rendimiento y tendencias del negocio</p>
        </div>
        <div class="flex space-x-3">
          <button
            @click="refreshAnalytics"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-sync-alt"></i>
            <span>Actualizar</span>
          </button>
          <button
            @click="exportAnalytics"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-download"></i>
            <span>Exportar</span>
          </button>
          <button
            @click="openPredictionModal"
            class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
          >
            <i class="fas fa-crystal-ball"></i>
            <span>Predicciones</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Time Range Selector -->
    <div class="bg-white border-b border-gray-200 px-6 py-4">
      <div class="flex flex-wrap items-center justify-between">
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-2">
            <label class="text-sm font-medium text-gray-700">Período de Análisis:</label>
            <select
              v-model="selectedTimeRange"
              @change="updateAnalytics"
              class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="7d">Últimos 7 días</option>
              <option value="30d">Últimos 30 días</option>
              <option value="90d">Últimos 90 días</option>
              <option value="6m">Últimos 6 meses</option>
              <option value="1y">Último año</option>
              <option value="2y">Últimos 2 años</option>
            </select>
          </div>
          
          <div class="flex items-center space-x-2">
            <label class="text-sm font-medium text-gray-700">Comparar con:</label>
            <select
              v-model="comparisonPeriod"
              @change="updateAnalytics"
              class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="previous">Período anterior</option>
              <option value="year-ago">Mismo período año anterior</option>
              <option value="none">Sin comparación</option>
            </select>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <span class="text-sm text-gray-500">Última actualización:</span>
          <span class="text-sm font-medium text-gray-900">{{ lastUpdated }}</span>
        </div>
      </div>
    </div>

    <!-- KPI Dashboard -->
    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <!-- Revenue Growth -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Crecimiento de Ingresos</p>
              <p class="text-2xl font-bold text-gray-900">{{ revenueGrowth }}%</p>
              <p :class="revenueGrowthTrendClass" class="text-sm flex items-center mt-1">
                <i :class="revenueGrowthIcon" class="mr-1"></i>
                {{ revenueGrowthTrend }}
              </p>
            </div>
            <div class="p-3 rounded-full bg-green-100 text-green-600">
              <i class="fas fa-chart-line text-xl"></i>
            </div>
          </div>
        </div>

        <!-- Customer Acquisition Cost -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Costo de Adquisición</p>
              <p class="text-2xl font-bold text-gray-900">${{ customerAcquisitionCost }}</p>
              <p :class="cacTrendClass" class="text-sm flex items-center mt-1">
                <i :class="cacTrendIcon" class="mr-1"></i>
                {{ cacTrend }}
              </p>
            </div>
            <div class="p-3 rounded-full bg-blue-100 text-blue-600">
              <i class="fas fa-user-plus text-xl"></i>
            </div>
          </div>
        </div>

        <!-- Customer Lifetime Value -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Valor de Vida del Cliente</p>
              <p class="text-2xl font-bold text-gray-900">${{ customerLifetimeValue }}</p>
              <p :class="clvTrendClass" class="text-sm flex items-center mt-1">
                <i :class="clvTrendIcon" class="mr-1"></i>
                {{ clvTrend }}
              </p>
            </div>
            <div class="p-3 rounded-full bg-purple-100 text-purple-600">
              <i class="fas fa-gem text-xl"></i>
            </div>
          </div>
        </div>

        <!-- Churn Rate -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">Tasa de Abandono</p>
              <p class="text-2xl font-bold text-gray-900">{{ churnRate }}%</p>
              <p :class="churnTrendClass" class="text-sm flex items-center mt-1">
                <i :class="churnTrendIcon" class="mr-1"></i>
                {{ churnTrend }}
              </p>
            </div>
            <div class="p-3 rounded-full bg-red-100 text-red-600">
              <i class="fas fa-user-times text-xl"></i>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced Charts Section -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <!-- Revenue Trend Analysis -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Análisis de Tendencias de Ingresos</h3>
            <div class="flex space-x-2">
              <select
                v-model="revenueChartType"
                class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="trend">Tendencia</option>
                <option value="forecast">Pronóstico</option>
                <option value="comparison">Comparación</option>
              </select>
            </div>
          </div>
          <div class="h-80 flex items-center justify-center bg-gray-50 rounded">
            <div class="text-center">
              <i class="fas fa-chart-area text-4xl text-gray-400 mb-2"></i>
              <p class="text-gray-500">Gráfico de Tendencias</p>
              <p class="text-sm text-gray-400">{{ revenueData.length }} puntos de datos</p>
            </div>
          </div>
        </div>

        <!-- Customer Behavior Analysis -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Comportamiento de Clientes</h3>
            <div class="flex space-x-2">
              <select
                v-model="behaviorMetric"
                class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="frequency">Frecuencia de Compra</option>
                <option value="recency">Recencia</option>
                <option value="monetary">Valor Monetario</option>
                <option value="rfm">Análisis RFM</option>
              </select>
            </div>
          </div>
          <div class="h-80 flex items-center justify-center bg-gray-50 rounded">
            <div class="text-center">
              <i class="fas fa-users-cog text-4xl text-gray-400 mb-2"></i>
              <p class="text-gray-500">Análisis de Comportamiento</p>
              <p class="text-sm text-gray-400">{{ customerSegments.length }} segmentos</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Product Performance Matrix -->
      <div class="bg-white rounded-lg shadow mb-8">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">Matriz de Rendimiento de Productos</h3>
            <div class="flex space-x-2">
              <select
                v-model="matrixView"
                class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="bcg">Matriz BCG</option>
                <option value="profitability">Rentabilidad vs Volumen</option>
                <option value="lifecycle">Ciclo de Vida</option>
              </select>
              <button
                @click="exportMatrix"
                class="text-blue-600 hover:text-blue-800 text-sm"
              >
                <i class="fas fa-download mr-1"></i>
                Exportar
              </button>
            </div>
          </div>
        </div>
        <div class="p-6">
          <div class="h-96 flex items-center justify-center bg-gray-50 rounded">
            <div class="text-center">
              <i class="fas fa-th text-4xl text-gray-400 mb-2"></i>
              <p class="text-gray-500">Matriz de Productos</p>
              <p class="text-sm text-gray-400">{{ productMatrix.length }} productos analizados</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Cohort Analysis -->
      <div class="bg-white rounded-lg shadow mb-8">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-medium text-gray-900">Análisis de Cohortes</h3>
            <div class="flex space-x-2">
              <select
                v-model="cohortType"
                class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="retention">Retención</option>
                <option value="revenue">Ingresos</option>
                <option value="frequency">Frecuencia</option>
              </select>
              <select
                v-model="cohortPeriod"
                class="px-3 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="monthly">Mensual</option>
                <option value="weekly">Semanal</option>
                <option value="quarterly">Trimestral</option>
              </select>
            </div>
          </div>
        </div>
        <div class="p-6">
          <div class="overflow-x-auto">
            <table class="min-w-full">
              <thead>
                <tr class="border-b border-gray-200">
                  <th class="text-left py-2 px-3 text-sm font-medium text-gray-700">Cohorte</th>
                  <th class="text-center py-2 px-3 text-sm font-medium text-gray-700">Tamaño</th>
                  <th v-for="period in cohortPeriods" :key="period" class="text-center py-2 px-3 text-sm font-medium text-gray-700">
                    {{ period }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cohort in cohortData" :key="cohort.id" class="border-b border-gray-100">
                  <td class="py-2 px-3 text-sm font-medium text-gray-900">{{ cohort.name }}</td>
                  <td class="py-2 px-3 text-sm text-center text-gray-700">{{ cohort.size }}</td>
                  <td v-for="(value, index) in cohort.values" :key="index" class="py-2 px-3 text-sm text-center">
                    <span :class="getCohortValueClass(value)" class="px-2 py-1 rounded text-xs font-medium">
                      {{ value }}%
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Predictive Analytics -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <!-- Sales Forecast -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Pronóstico de Ventas</h3>
            <i class="fas fa-chart-line text-blue-500"></i>
          </div>
          <div class="space-y-4">
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Próximos 30 días</span>
              <span class="text-lg font-bold text-gray-900">${{ salesForecast.next30Days }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Próximos 90 días</span>
              <span class="text-lg font-bold text-gray-900">${{ salesForecast.next90Days }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Confianza</span>
              <span class="text-sm font-medium text-green-600">{{ salesForecast.confidence }}%</span>
            </div>
            <div class="mt-4">
              <div class="bg-gray-200 rounded-full h-2">
                <div 
                  class="bg-blue-600 h-2 rounded-full" 
                  :style="{ width: salesForecast.confidence + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Inventory Optimization -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Optimización de Inventario</h3>
            <i class="fas fa-boxes text-green-500"></i>
          </div>
          <div class="space-y-4">
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Productos en riesgo</span>
              <span class="text-lg font-bold text-red-600">{{ inventoryOptimization.atRisk }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Sobrestock</span>
              <span class="text-lg font-bold text-yellow-600">{{ inventoryOptimization.overstock }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Ahorro potencial</span>
              <span class="text-lg font-bold text-green-600">${{ inventoryOptimization.potentialSavings }}</span>
            </div>
            <button
              @click="generateInventoryReport"
              class="w-full mt-4 bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded text-sm transition-colors"
            >
              Ver Recomendaciones
            </button>
          </div>
        </div>

        <!-- Customer Risk Analysis -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Análisis de Riesgo</h3>
            <i class="fas fa-exclamation-triangle text-yellow-500"></i>
          </div>
          <div class="space-y-4">
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Clientes en riesgo</span>
              <span class="text-lg font-bold text-red-600">{{ riskAnalysis.customersAtRisk }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Ingresos en riesgo</span>
              <span class="text-lg font-bold text-red-600">${{ riskAnalysis.revenueAtRisk }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Probabilidad de abandono</span>
              <span class="text-lg font-bold text-yellow-600">{{ riskAnalysis.churnProbability }}%</span>
            </div>
            <button
              @click="generateRetentionCampaign"
              class="w-full mt-4 bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded text-sm transition-colors"
            >
              Crear Campaña
            </button>
          </div>
        </div>
      </div>

      <!-- Advanced Insights -->
      <div class="bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">Insights Avanzados</h3>
        </div>
        <div class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
              <h4 class="font-medium text-gray-900">Oportunidades Detectadas</h4>
              <div v-for="opportunity in opportunities" :key="opportunity.id" class="flex items-start space-x-3 p-3 bg-green-50 rounded-lg">
                <div class="p-2 bg-green-100 rounded-full">
                  <i :class="opportunity.icon" class="text-green-600 text-sm"></i>
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900">{{ opportunity.title }}</p>
                  <p class="text-sm text-gray-600">{{ opportunity.description }}</p>
                  <p class="text-sm font-medium text-green-600 mt-1">Impacto: {{ opportunity.impact }}</p>
                </div>
              </div>
            </div>

            <div class="space-y-4">
              <h4 class="font-medium text-gray-900">Alertas y Riesgos</h4>
              <div v-for="alert in alerts" :key="alert.id" class="flex items-start space-x-3 p-3 bg-red-50 rounded-lg">
                <div class="p-2 bg-red-100 rounded-full">
                  <i :class="alert.icon" class="text-red-600 text-sm"></i>
                </div>
                <div>
                  <p class="text-sm font-medium text-gray-900">{{ alert.title }}</p>
                  <p class="text-sm text-gray-600">{{ alert.description }}</p>
                  <p class="text-sm font-medium text-red-600 mt-1">Severidad: {{ alert.severity }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Prediction Modal -->
    <div v-if="showPredictionModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-10 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Predicciones Avanzadas</h3>
            <button @click="closePredictionModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Tipo de Predicción</label>
                <select
                  v-model="predictionForm.type"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="sales">Ventas Futuras</option>
                  <option value="demand">Demanda de Productos</option>
                  <option value="churn">Abandono de Clientes</option>
                  <option value="inventory">Necesidades de Inventario</option>
                  <option value="seasonal">Tendencias Estacionales</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Horizonte Temporal</label>
                <select
                  v-model="predictionForm.timeHorizon"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="1m">1 Mes</option>
                  <option value="3m">3 Meses</option>
                  <option value="6m">6 Meses</option>
                  <option value="1y">1 Año</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Factores a Considerar</label>
              <div class="grid grid-cols-2 gap-2">
                <label v-for="factor in predictionFactors" :key="factor.id" class="flex items-center">
                  <input
                    v-model="predictionForm.factors"
                    :value="factor.id"
                    type="checkbox"
                    class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  >
                  <span class="ml-2 text-sm text-gray-700">{{ factor.name }}</span>
                </label>
              </div>
            </div>

            <div class="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                @click="closePredictionModal"
                class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                @click="generatePrediction"
                class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Generar Predicción
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Check if user has admin access
if (!authStore.isAdmin) {
  // Redirect to dashboard or show access denied
  console.warn('Access denied: Admin role required for Analytics')
}

// Reactive data
const selectedTimeRange = ref('30d')
const comparisonPeriod = ref('previous')
const lastUpdated = ref('')

// Chart and analysis types
const revenueChartType = ref('trend')
const behaviorMetric = ref('frequency')
const matrixView = ref('bcg')
const cohortType = ref('retention')
const cohortPeriod = ref('monthly')

// Modal states
const showPredictionModal = ref(false)

// Form data
const predictionForm = ref({
  type: 'sales',
  timeHorizon: '3m',
  factors: []
})

// KPI Data
const revenueGrowth = ref(15.8)
const revenueGrowthTrend = ref('Tendencia positiva')
const customerAcquisitionCost = ref(45)
const cacTrend = ref('Reduciendo')
const customerLifetimeValue = ref(850)
const clvTrend = ref('Incrementando')
const churnRate = ref(3.2)
const churnTrend = ref('Estable')

// Analytics data
const revenueData = ref([])
const customerSegments = ref([])
const productMatrix = ref([])
const cohortData = ref([])
const cohortPeriods = ref(['Mes 0', 'Mes 1', 'Mes 2', 'Mes 3', 'Mes 4', 'Mes 5'])

// Predictions and insights
const salesForecast = ref({
  next30Days: 125000,
  next90Days: 385000,
  confidence: 87
})

const inventoryOptimization = ref({
  atRisk: 23,
  overstock: 15,
  potentialSavings: 12500
})

const riskAnalysis = ref({
  customersAtRisk: 45,
  revenueAtRisk: 28500,
  churnProbability: 12.5
})

const opportunities = ref([])
const alerts = ref([])

const predictionFactors = ref([
  { id: 'seasonality', name: 'Estacionalidad' },
  { id: 'trends', name: 'Tendencias de Mercado' },
  { id: 'promotions', name: 'Promociones' },
  { id: 'competition', name: 'Competencia' },
  { id: 'economic', name: 'Factores Económicos' },
  { id: 'weather', name: 'Clima' }
])

// Computed properties
const revenueGrowthTrendClass = computed(() => 
  revenueGrowth.value >= 0 ? 'text-green-600' : 'text-red-600'
)
const revenueGrowthIcon = computed(() => 
  revenueGrowth.value >= 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'
)

const cacTrendClass = computed(() => 
  cacTrend.value === 'Reduciendo' ? 'text-green-600' : 'text-red-600'
)
const cacTrendIcon = computed(() => 
  cacTrend.value === 'Reduciendo' ? 'fas fa-arrow-down' : 'fas fa-arrow-up'
)

const clvTrendClass = computed(() => 
  clvTrend.value === 'Incrementando' ? 'text-green-600' : 'text-red-600'
)
const clvTrendIcon = computed(() => 
  clvTrend.value === 'Incrementando' ? 'fas fa-arrow-up' : 'fas fa-arrow-down'
)

const churnTrendClass = computed(() => {
  if (churnTrend.value === 'Reduciendo') return 'text-green-600'
  if (churnTrend.value === 'Incrementando') return 'text-red-600'
  return 'text-gray-600'
})
const churnTrendIcon = computed(() => {
  if (churnTrend.value === 'Reduciendo') return 'fas fa-arrow-down'
  if (churnTrend.value === 'Incrementando') return 'fas fa-arrow-up'
  return 'fas fa-minus'
})

// Methods
const loadAnalyticsData = async () => {
  try {
    // TODO: Replace with actual API calls
    // const analyticsData = await api.get('/analytics/dashboard', { 
    //   params: { 
    //     timeRange: selectedTimeRange.value,
    //     comparison: comparisonPeriod.value 
    //   } 
    // })
    
    // Mock data for development
    revenueData.value = Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      revenue: Math.floor(Math.random() * 5000) + 3000,
      forecast: Math.floor(Math.random() * 5500) + 3200
    }))

    customerSegments.value = [
      { id: 1, name: 'Champions', size: 156, value: 85000, retention: 95 },
      { id: 2, name: 'Loyal Customers', size: 234, value: 65000, retention: 87 },
      { id: 3, name: 'Potential Loyalists', size: 189, value: 45000, retention: 72 },
      { id: 4, name: 'At Risk', size: 78, value: 25000, retention: 45 },
      { id: 5, name: 'Cannot Lose Them', size: 45, value: 35000, retention: 35 }
    ]

    productMatrix.value = Array.from({ length: 50 }, (_, i) => ({
      id: i + 1,
      name: `Producto ${i + 1}`,
      marketShare: Math.random() * 100,
      growthRate: (Math.random() - 0.5) * 40,
      profitability: Math.random() * 100,
      volume: Math.floor(Math.random() * 1000) + 100
    }))

    cohortData.value = [
      {
        id: 1,
        name: 'Ene 2023',
        size: 150,
        values: [100, 85, 72, 65, 58, 52]
      },
      {
        id: 2,
        name: 'Feb 2023',
        size: 180,
        values: [100, 88, 75, 68, 61, 55]
      },
      {
        id: 3,
        name: 'Mar 2023',
        size: 165,
        values: [100, 82, 70, 62, 56, 50]
      },
      {
        id: 4,
        name: 'Abr 2023',
        size: 195,
        values: [100, 90, 78, 71, 64, 58]
      },
      {
        id: 5,
        name: 'May 2023',
        size: 210,
        values: [100, 87, 74, 67, 60, 54]
      }
    ]

    opportunities.value = [
      {
        id: 1,
        title: 'Optimización de Precios',
        description: 'Ajustar precios en categoría Electrónicos puede incrementar ingresos 12%',
        impact: '+$15,000/mes',
        icon: 'fas fa-dollar-sign'
      },
      {
        id: 2,
        title: 'Campaña de Retención',
        description: 'Dirigir campaña a clientes en riesgo puede reducir abandono 25%',
        impact: '+$8,500/mes',
        icon: 'fas fa-heart'
      },
      {
        id: 3,
        title: 'Cross-selling',
        description: 'Productos complementarios pueden incrementar ticket promedio 18%',
        impact: '+$12,200/mes',
        icon: 'fas fa-shopping-cart'
      }
    ]

    alerts.value = [
      {
        id: 1,
        title: 'Caída en Conversión',
        description: 'Tasa de conversión ha bajado 15% en los últimos 7 días',
        severity: 'Alta',
        icon: 'fas fa-exclamation-triangle'
      },
      {
        id: 2,
        title: 'Inventario Crítico',
        description: '23 productos están por debajo del stock mínimo',
        severity: 'Media',
        icon: 'fas fa-boxes'
      },
      {
        id: 3,
        title: 'Competencia Agresiva',
        description: 'Competidor ha reducido precios 20% en categoría principal',
        severity: 'Media',
        icon: 'fas fa-chart-line'
      }
    ]

    lastUpdated.value = new Date().toLocaleString('es-ES')
  } catch (error) {
    console.error('Error loading analytics data:', error)
  }
}

const updateAnalytics = () => {
  loadAnalyticsData()
}

const refreshAnalytics = () => {
  loadAnalyticsData()
}

// Modal methods
const openPredictionModal = () => {
  showPredictionModal.value = true
}

const closePredictionModal = () => {
  showPredictionModal.value = false
  predictionForm.value = {
    type: 'sales',
    timeHorizon: '3m',
    factors: []
  }
}

const generatePrediction = async () => {
  try {
    // TODO: Replace with actual API call
    // await api.post('/analytics/predictions', predictionForm.value)
    
    console.log('Generating prediction:', predictionForm.value)
    closePredictionModal()
  } catch (error) {
    console.error('Error generating prediction:', error)
  }
}

// Export and action methods
const exportAnalytics = () => {
  const csvContent = [
    ['Métrica', 'Valor', 'Tendencia'].join(','),
    ['Crecimiento de Ingresos', `${revenueGrowth.value}%`, revenueGrowthTrend.value].join(','),
    ['Costo de Adquisición', `$${customerAcquisitionCost.value}`, cacTrend.value].join(','),
    ['Valor de Vida del Cliente', `$${customerLifetimeValue.value}`, clvTrend.value].join(','),
    ['Tasa de Abandono', `${churnRate.value}%`, churnTrend.value].join(',')
  ].join('\n')

  downloadCSV(csvContent, `analytics_${new Date().toISOString().split('T')[0]}.csv`)
}

const exportMatrix = () => {
  const csvContent = [
    ['Producto', 'Participación de Mercado', 'Tasa de Crecimiento', 'Rentabilidad', 'Volumen'].join(','),
    ...productMatrix.value.map(product => [
      product.name,
      product.marketShare.toFixed(2),
      product.growthRate.toFixed(2),
      product.profitability.toFixed(2),
      product.volume
    ].join(','))
  ].join('\n')

  downloadCSV(csvContent, `product_matrix_${new Date().toISOString().split('T')[0]}.csv`)
}

const generateInventoryReport = () => {
  console.log('Generating inventory optimization report')
  // TODO: Implement inventory report generation
}

const generateRetentionCampaign = () => {
  console.log('Generating customer retention campaign')
  // TODO: Implement retention campaign generation
}

// Utility methods
const getCohortValueClass = (value: number) => {
  if (value >= 80) return 'bg-green-100 text-green-800'
  if (value >= 60) return 'bg-yellow-100 text-yellow-800'
  if (value >= 40) return 'bg-orange-100 text-orange-800'
  return 'bg-red-100 text-red-800'
}

const downloadCSV = (content: string, filename: string) => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Lifecycle
onMounted(() => {
  loadAnalyticsData()
})
</script>