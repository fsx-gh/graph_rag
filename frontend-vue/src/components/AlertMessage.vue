<template>
  <transition name="fade">
    <div v-if="show" :class="['alert', type]">
      {{ message }}
    </div>
  </transition>
</template>

<script setup>
defineProps({
  show: Boolean,
  message: String,
  type: {
    type: String,
    default: 'success'
  }
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
