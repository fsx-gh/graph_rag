<template>
  <BaseModal :show="show" title="➕ 添加人物" @close="$emit('close')">
    <input v-model="form.name" type="text" placeholder="姓名" class="input-field">
    <input v-model.number="form.age" type="number" placeholder="年龄" class="input-field">
    <input v-model="form.occupation" type="text" placeholder="职业" class="input-field">
    <input v-model="form.description" type="text" placeholder="描述" class="input-field">
    <button @click="handleSubmit" class="action-btn primary">添加</button>
  </BaseModal>
</template>

<script setup>
import { reactive } from 'vue'
import BaseModal from './BaseModal.vue'

defineProps({
  show: Boolean
})

const emit = defineEmits(['close', 'submit'])

const form = reactive({
  name: '',
  age: null,
  occupation: '',
  description: ''
})

const handleSubmit = () => {
  if (!form.name.trim()) {
    alert('请输入姓名')
    return
  }
  
  emit('submit', {
    name: form.name,
    age: form.age || null,
    occupation: form.occupation || null,
    description: form.description || null
  })
  
  // 重置表单
  form.name = ''
  form.age = null
  form.occupation = ''
  form.description = ''
}
</script>
