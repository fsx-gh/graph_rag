<template>
  <div v-if="selectedNode" class="left-panel">
    <div class="panel-content">
      <div class="panel-section">
        <div class="section-header">
          <span>✨ 人物详情</span>
        </div>
        <div class="section-body">
          <div class="detail-header">
            <strong>{{ selectedNode.name }}</strong>
          </div>
          <div class="detail-row">
            <span>年龄:</span>
            <span>{{ selectedNode.age || '未知' }}</span>
          </div>
          <div class="detail-row">
            <span>职业:</span>
            <span>{{ selectedNode.occupation || '未知' }}</span>
          </div>
          <div v-if="selectedNode.description" class="detail-row">
            <span>描述:</span>
            <span class="desc">{{ selectedNode.description }}</span>
          </div>

          <div v-if="relations.length > 0" class="relations-section">
            <div class="relations-header">关联关系 ({{ relations.length }})</div>
            <div class="relations-list">
              <div v-for="rel in relations" :key="rel.id" class="relation-item">
                <span class="relation-text">{{ formatRelation(rel) }}</span>
                <button class="delete-btn" @click="$emit('delete-relation', rel.id)">×</button>
              </div>
            </div>
          </div>

          <button class="delete-node-btn" @click="$emit('delete-person', selectedNode.id)">删除此节点</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  selectedNode: Object,
  allNodes: Array,
  allRelationships: Array
})

defineEmits(['delete-person', 'delete-relation'])

const relations = computed(() => {
  if (!props.selectedNode) return []
  return props.allRelationships.filter(r =>
    r.source === props.selectedNode.id || r.target === props.selectedNode.id
  )
})

const formatRelation = (rel) => {
  const source = props.allNodes.find(n => n.id === rel.source)
  const target = props.allNodes.find(n => n.id === rel.target)
  return source && target ? `${source.name} → ${target.name} (${rel.type})` : '未知'
}
</script>
