<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div :class="['modal-dialog', { 'modal-large': large }]" :style="width ? { width: width, maxWidth: width } : {}">
      <div class="modal-header">
        <span>{{ title }}</span>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>
      <div class="modal-body">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  show: Boolean,
  title: String,
  large: Boolean,
  width: String
})

defineEmits(['close'])
</script>
