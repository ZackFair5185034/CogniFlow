<script setup lang="ts">
defineProps({
  prefix: {
    type: String,
    default: 'icon'
  },
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

const symbolId = computed(() => `#${props.prefix}-${props.name}`)
</script>

<script lang="ts">
const props = defineProps<{
  prefix?: string
  name: string
  size?: number | string
}>()

export default {
  name: 'SvgIcon'
}
</script>

<template>
  <svg aria-hidden="true" class="svg-icon" :width="size" :height="size">
    <use :xlink:href="symbolId" fill="currentColor" />
  </svg>
</template>

<style scoped>
.svg-icon {
  display: inline-block;
  width: 1em;
  height: 1em;
  overflow: hidden;
  vertical-align: -0.15em;
  outline: none;
  fill: currentColor;
}
</style>
