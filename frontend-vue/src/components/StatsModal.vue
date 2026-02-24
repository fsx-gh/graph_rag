<template>
  <BaseModal :show="show" title="📈 图谱总览" @close="$emit('close')" width="800px">
    <div class="stats-container">
      <div v-if="stats" class="content-wrapper">
        <!-- 统计概览 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">节点总数</div>
            <div class="stat-value">{{ stats.nodeCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">关系总数</div>
            <div class="stat-value">{{ stats.relationshipCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">连接分量</div>
            <div class="stat-value">{{ stats.componentCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">平均度数</div>
            <div class="stat-value">{{ stats.avgDegree.toFixed(2) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">网络密度</div>
            <div class="stat-value">{{ stats.density.toFixed(4) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">最大度数</div>
            <div class="stat-value">{{ stats.maxDegree }}</div>
          </div>
        </div>

        <!-- 连接分量详情 -->
        <div v-if="stats.components && stats.components.length > 0" class="components-section">
          <h3 class="section-title">连接分量详情</h3>
          <div class="components-list">
            <div v-for="component in stats.components" :key="component.id" class="component-card">
              <div class="component-header">
                <span class="component-title">分量 {{ component.id }}</span>
                <span class="component-size">{{ component.size }} 个节点</span>
              </div>
              <div class="component-nodes">
                <span 
                  v-for="node in component.nodes" 
                  :key="node.id" 
                  class="node-tag"
                  :title="node.occupation || ''"
                >
                  {{ node.name }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="loading">加载中...</div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import { API_BASE_URL } from '../services/api'

const props = defineProps({
  show: Boolean
})

defineEmits(['close'])

const stats = ref(null)

const loadStats = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/graph/stats`)
    if (!response.ok) throw new Error('Failed to load stats')
    stats.value = await response.json()
  } catch (error) {
    console.error('Error loading stats:', error)
    stats.value = null
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadStats()
  }
})
</script>

<style scoped>
.stats-container {
  padding: 20px;
  min-height: 300px;
  max-height: 70vh;
  overflow-y: auto;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  width: 100%;
}


.stat-card {
  background: linear-gradient(135deg, #67c6e7 0%, #50d29e 100%);
  border-radius: 10px;
  padding: 20px;
  color: #23436b;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 8px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
}

.components-section {
  margin-top: 10px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #667eea;
}

.components-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}


.component-card {
  background: #e3f2fd;
  border-radius: 8px;
  padding: 15px;
  border-left: 4px solid #67c6e7;
  transition: all 0.3s ease;
}

.component-card:hover {
  background: #b3e5fc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.component-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.component-title {
  font-size: 16px;
  font-weight: 600;
  color: #495057;
}

.component-size {
  font-size: 14px;
  color: #6c757d;
  background: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 500;
}

.component-nodes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}


.node-tag {
  background: #b3e5fc;
  color: #23436b;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid #67c6e7;
  transition: all 0.2s ease;
  cursor: default;
}

.node-tag:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
  transform: translateY(-1px);
}

.loading {
  text-align: center;
  color: #666;
  font-size: 14px;
  padding: 40px;
}
</style>
