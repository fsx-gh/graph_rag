<template>
  <BaseModal :show="show" title="📚 图谱导览" :large="true" @close="$emit('close')">
    <div class="overview-container">
      <div v-if="overview" class="overview-content">
        <!-- 节点列表 -->
        <div class="section">
          <h3>🧑 人物列表 ({{ nodes.length }})</h3>
          <div class="items-list">
            <div 
              v-for="node in nodes" 
              :key="node.id"
              class="item"
              @click="$emit('highlight-node', node.id)"
            >
              <span class="item-name">{{ node.name }}</span>
              <span class="item-degree">度数: {{ node.degree }}</span>
            </div>
          </div>
        </div>

        <!-- 关系列表 -->
        <div class="section">
          <h3>� 关系列表 ({{ relationships.length }})</h3>
          <div class="items-list relationships-list">
            <div 
              v-for="rel in relationships" 
              :key="rel.id"
              class="item"
            >
              <span class="item-relation">{{ rel.sourceName }} → {{ rel.targetName }}</span>
              <span class="item-type">{{ rel.type }}</span>
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

const overview = ref(null)
const nodes = ref([])
const relationships = ref([])

const loadOverview = async () => {
  try {
    // Load nodes
    const nodesResponse = await fetch(`${API_BASE_URL}/api/nodes`)
    if (!nodesResponse.ok) throw new Error('Failed to load nodes')
    const nodesData = await nodesResponse.json()

    // Load relationships
    const relsResponse = await fetch(`${API_BASE_URL}/api/relationships`)
    if (!relsResponse.ok) throw new Error('Failed to load relationships')
    const relsData = await relsResponse.json()
    
    // Calculate degrees from relationships using person names as key
    const degreeMap = {}
    relsData.forEach(rel => {
      const sourceName = rel.source  // 人物名字
      const targetName = rel.target  // 人物名字
      degreeMap[sourceName] = (degreeMap[sourceName] || 0) + 1
      degreeMap[targetName] = (degreeMap[targetName] || 0) + 1
    })
    
    // Add degrees to nodes using person name as key
    nodes.value = nodesData.map(node => ({
      ...node,
      degree: degreeMap[node.name] || 0
    }))
    
    // Format relationships to use names
    relationships.value = relsData.map(rel => ({
      ...rel,
      id: `${rel.source}-${rel.target}`,
      sourceName: rel.source,
      targetName: rel.target
    }))

    overview.value = { nodes: nodes.value, relationships: relationships.value }
  } catch (error) {
    console.error('Error loading overview:', error)
    overview.value = null
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadOverview()
  }
})
</script>

<style scoped>
.overview-container {
  padding: 20px;
  max-height: 500px;
  overflow-y: auto;
}

.section {
  margin-bottom: 20px;
}

.section h3 {
  color: #e0bbbb;
  margin: 0 0 10px 0;
  font-size: 14px;
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}

.items-list {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.relationships-list {
  grid-template-columns: repeat(5, 1fr);
}

.item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 6px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 12px;
  color: white;
  text-align: center;
  min-height: 80px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.item:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.item-name {
  font-weight: 600;
  color: white;
  margin-bottom: 6px;
  word-break: break-word;
  font-size: 13px;
}

.item-degree {
  font-size: 11px;
  color: rgba(255,255,255,0.8);
  background: rgba(255,255,255,0.2);
  padding: 2px 6px;
  border-radius: 2px;
}

.item-relation {
  color: white;
  font-size: 14px;
  line-height: 1.3;
  margin-bottom: 4px;
  word-break: break-word;
}

.item-type {
  font-size: 10px;
  color: white;
  background: rgba(255,255,255,0.3);
  padding: 2px 6px;
  border-radius: 2px;
  margin-top: 4px;
}

.loading {
  text-align: center;
  color: #666;
  font-size: 14px;
  padding: 40px 20px;
}
</style>
