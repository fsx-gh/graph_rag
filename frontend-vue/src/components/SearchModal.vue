<template>
  <BaseModal :show="show" title="🔍 搜索人物" @close="$emit('close')">
    <input v-model="keyword" type="text" placeholder="输入姓名" class="input-field">
    <select v-model="field" class="input-field">
      <option value="name">姓名</option>
      <option value="occupation">职业</option>
      <option value="description">描述</option>
    </select>
    <button @click="handleSearch" class="action-btn primary">搜索</button>
  </BaseModal>
</template>

<script setup>
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'

defineProps({
  show: Boolean
})

const emit = defineEmits(['close', 'search'])

const keyword = ref('')
const field = ref('name')

const handleSearch = () => {
  if (!keyword.value.trim()) {
    alert('请输入搜索关键词')
    return
  }
  
  emit('search', {
    keyword: keyword.value,
    field: field.value
  })
}
</script>
