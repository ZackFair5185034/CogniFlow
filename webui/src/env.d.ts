/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

// Vite virtual modules (unplugin-vue-components svg icons)
declare module 'virtual:svg-icons-register' {
  // side-effect import, no exports
}

declare module 'vue-virtual-scroller' {
  // 第三方无类型, 业务层只用到 RecycleScroller 组件
  // 实际 prop 走运行时校验, 这里 any 兜底
  const RecycleScroller: any
  export { RecycleScroller }
}
