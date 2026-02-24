<template>
  <BaseModal :show="show" title="🛤️ 查找最短路径" @close="$emit('close')">
    <div v-if="error" class="path-error">
      <span>⚠️ {{ error }}</span>
    </div>
    
    <select v-model="start" class="input-field">
      <option value="">选择起点</option>
      <option v-for="node in nodes" :key="node.id" :value="node.name">
        {{ node.name }}
      </option>
    </select>
    <select v-model="end" class="input-field">
      <option value="">选择终点</option>
      <option v-for="node in nodes" :key="node.id" :value="node.name">
        {{ node.name }}
      </option>
    </select>
    <button 
      @click="handleFindPath" 
      :disabled="!start || !end" 
      class="action-btn primary">
      查找
    </button>
    
    <div v-if="path.length > 0" class="path-result">
      <div class="path-header">
        <span>路径距离: {{ distance }} 步</span>
      </div>
      <div class="path-nodes">
        <div v-for="(nodeId, index) in path" :key="index" class="path-node-item">
          <span class="node-name">{{ getNodeName(nodeId) }}</span>
          <span v-if="index < path.length - 1" class="path-arrow">→</span>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'

const props = defineProps({
  show: Boolean,
  nodes: Array,
  path: Array,
  distance: Number,
  error: String
})

const emit = defineEmits(['close', 'find-path'])

const start = ref('')
const end = ref('')

const handleFindPath = () => {
  emit('find-path', {
    start: start.value,
    end: end.value
  })
}

const getNodeName = (nodeName) => {
  // 现在path中直接存储的就是节点名字，不是ID
  return nodeName || '未知'
}
</script>
