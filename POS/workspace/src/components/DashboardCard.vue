<template>
  <div 
    class="dashboard-card"
    :class="{ 'clickable': clickable }"
    @click="handleClick"
  >
    <div class="card-header">
      <div class="icon-container" :style="{ backgroundColor: iconColor }">
        <i :class="icon" class="card-icon"></i>
      </div>
      <div class="card-info">
        <h3 class="card-title">{{ title }}</h3>
        <p class="card-description">{{ description }}</p>
      </div>
    </div>
    
    <div class="card-content" v-if="$slots.default">
      <slot></slot>
    </div>
    
    <div class="card-stats" v-if="stats && stats.length > 0">
      <div 
        v-for="stat in stats" 
        :key="stat.label"
        class="stat-item"
      >
        <span class="stat-value">{{ stat.value }}</span>
        <span class="stat-label">{{ stat.label }}</span>
      </div>
    </div>
    
    <div class="card-footer" v-if="showFooter">
      <span class="footer-text">{{ footerText }}</span>
      <i class="fas fa-arrow-right" v-if="clickable"></i>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

interface Stat {
  label: string
  value: string | number
}

interface Props {
  title: string
  description: string
  icon: string
  iconColor?: string
  route?: string
  stats?: Stat[]
  footerText?: string
  showFooter?: boolean
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  iconColor: '#3B82F6',
  footerText: 'Ver más',
  showFooter: true,
  clickable: true
})

const router = useRouter()

const clickable = computed(() => props.clickable && !!props.route)

const handleClick = () => {
  if (clickable.value && props.route) {
    router.push(props.route)
  }
}
</script>

<style scoped>
.dashboard-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dashboard-card.clickable {
  cursor: pointer;
}

.dashboard-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  border-color: #d1d5db;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.icon-container {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon {
  color: white;
  font-size: 20px;
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px 0;
  line-height: 1.4;
}

.card-description {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

.card-content {
  flex: 1;
  margin-bottom: 16px;
}

.card-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-width: 60px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
  margin-top: auto;
}

.footer-text {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.card-footer i {
  color: #9ca3af;
  font-size: 14px;
  transition: transform 0.2s ease;
}

.dashboard-card.clickable:hover .card-footer i {
  transform: translateX(2px);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .dashboard-card {
    padding: 20px;
  }
  
  .card-header {
    gap: 12px;
  }
  
  .icon-container {
    width: 40px;
    height: 40px;
  }
  
  .card-icon {
    font-size: 18px;
  }
  
  .card-title {
    font-size: 16px;
  }
  
  .card-stats {
    gap: 16px;
  }
  
  .stat-value {
    font-size: 20px;
  }
}
</style>