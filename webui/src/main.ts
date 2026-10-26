import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'virtual:svg-icons-register'
import 'nprogress/nprogress.css'
import App from './App.vue'
import SvgIcon from './components/SvgIcon.vue'
import router from './router'
import { useRulePortsStore } from './stores/ruleEngine/ports'
import 'virtual:uno.css'
import '@/style/index.scss'

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)

// 注册 click-outside 指令
app.directive('click-outside', {
  mounted(el, binding) {
    el._clickOutside = (event: MouseEvent) => {
      if (!(el === event.target || el.contains(event.target as Node))) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el) {
    document.removeEventListener('click', el._clickOutside)
  }
})

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(ElementPlus)
app.component('SvgIcon', SvgIcon)

/**
 * 启动流程: 先预载端口兼容矩阵, 再挂载应用。
 *
 * 端口矩阵是前端连线校验的唯一依据。若不在挂载前加载完, 画布初始化瞬间的
 * 连线会因矩阵未就绪而被判为不兼容(旧实现把这类边静默丢弃)。
 * 加载失败不阻断启动 —— ports store 会保持 loaded=false, 连线校验走 fail-loud
 * 分支并提示用户刷新页面。
 */
async function bootstrap(): Promise<void> {
  const portsStore = useRulePortsStore()
  try {
    await portsStore.loadPorts()
  } catch (error) {
    console.error('[CogniFlow] 端口兼容矩阵加载失败, 连线校验将拒绝所有连接:', error)
  }
  app.mount('#app')
}

void bootstrap()
