<template>
  <BaseModal :show="show" title="👑 关键人物排序" @close="$emit('close')">
    <div class="ranking-container">
      <div v-if="ranking && ranking.length > 0" class="ranking-content">
        <div class="ranking-info">
          按中心性排序，显示对知识图谱最具影响力的人物
        </div>
        
        <div class="ranking-list">
          <div 
            v-for="(person, index) in ranking" 
            :key="person.id"
            class="ranking-item"
            @click="$emit('highlight-node', person.id)"
          >
            <div class="ranking-badge">
              <span v-if="index === 0" class="medal">🥇</span>
              <span v-else-if="index === 1" class="medal">🥈</span>
              <span v-else-if="index === 2" class="medal">🥉</span>
              <span v-else class="rank-number">{{ index + 1 }}</span>
            </div>
            
            <div class="ranking-info-detail">
              <div class="person-name">{{ person.name }}</div>
              <div class="person-properties">
                <span class="property">度数: {{ person.degree }}</span>
                <span class="property">中心性: {{ person.centrality.toFixed(4) }}</span>
              </div>
            </div>
            
            <div class="ranking-bar">
              <div 
                class="bar-fill" 
                :style="{ width: (person.centrality / maxCentrality * 100) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="loading">加载中...</div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import BaseModal from './BaseModal.vue'
import { API_BASE_URL } from '../services/api'

const props = defineProps({
  show: Boolean
})

defineEmits(['close', 'highlight-node'])

const ranking = ref([])
const maxCentrality = computed(() => {
  return ranking.value.length > 0 
    ? Math.max(...ranking.value.map(p => p.centrality))
    : 1
})

const loadRanking = async () => {
  try {
    // Directly load pre-calculated ranking from backend
    const response = await fetch(`${API_BASE_URL}/api/ranking/centrality?limit=20`)
    if (!response.ok) throw new Error('Failed to load ranking')
    ranking.value = await response.json()
  } catch (error) {
    console.error('Error loading ranking:', error)
    ranking.value = []
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadRanking()
  }
})
</script>

<style scoped>
.ranking-container {
  padding: 20px;
  max-height: 500px;
  overflow-y: auto;
}

.ranking-info {
  background: #f0f4ff;
  border-left: 3px solid #667eea;
  padding: 12px;
  border-radius: 4px;
  font-size: 13px;
  color: #555;
  margin-bottom: 15px;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ranking-item {
  display: grid;
  grid-template-columns: 50px 1fr 80px;
  gap: 12px;
  align-items: center;
  padding: 12px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.ranking-item:hover {
  background: #f9f9f9;
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
  transform: translateX(4px);
}

.ranking-badge {
  text-align: center;
  font-size: 20px;
  font-weight: bold;
}

.medal {
  font-size: 24px;
}

.rank-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: #f0f0f0;
  border-radius: 50%;
  color: #333;
  font-weight: 600;
}

.ranking-info-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.person-name {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.person-properties {
  display: flex;
  gap: 10px;
  font-size: 12px;
}

.property {
  color: #666;
}

.ranking-bar {
  display: flex;
  align-items: center;
  height: 24px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
  min-width: 20px;
}

.ranking-item:hover .bar-fill {
  background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
}

.loading {
  text-align: center;
  color: #666;
  font-size: 14px;
  padding: 40px 20px;
}
</style>
