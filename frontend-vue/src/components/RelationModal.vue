<template>
  <BaseModal :show="show" title="🔗 添加关系" @close="$emit('close')">
    <select v-model="form.source" class="input-field">
      <option value="">选择起始人物</option>
      <option v-for="node in nodes" :key="node.id" :value="node.id">
        {{ node.name }}
      </option>
    </select>
    <select v-model="form.type" class="input-field">
      <option value="父子">父子</option>
      <option value="母子">母子</option>
      <option value="夫妻">夫妻</option>
      <option value="兄弟">兄弟</option>
      <option value="姐妹">姐妹</option>
      <option value="朋友">朋友</option>
      <option value="同事">同事</option>
      <option value="师生">师生</option>
      <option value="君臣">君臣</option>
    </select>
    <select v-model="form.target" class="input-field">
      <option value="">选择目标人物</option>
      <option v-for="node in nodes" :key="node.id" :value="node.id">
        {{ node.name }}
      </option>
    </select>
    <button @click="handleSubmit" class="action-btn primary">建立关系</button>
  </BaseModal>
</template>

<script setup>
import { reactive } from 'vue'
import BaseModal from './BaseModal.vue'

defineProps({
  show: Boolean,
  nodes: Array
})

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  source: '',
  target: '',
  type: '朋友'
})

const handleSubmit = () => {
  if (!form.source || !form.target) {
    alert('请选择人物')
    return
  }
  
  if (form.source === form.target) {
    alert('不能与自己建立关系')
    return
  }
  
  emit('submit', {
    source: form.source,
    target: form.target,
    type: form.type
  })
  
  // 重置表单
  form.source = ''
  form.target = ''
  form.type = '朋友'
}
</script>
