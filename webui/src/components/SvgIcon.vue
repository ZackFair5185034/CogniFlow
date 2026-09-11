<script setup lang="ts">
defineProps({
  name: {
    type: String,
    required: true,
    default: ''
  },
  size: {
    type: [Number, String],
    default: 24
  }
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="inline-block align-middle"
  >
    <use :xlink:href="'#icon-' + name" />
  </svg>
</template>
