import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import AtlasList from '@/views/AtlasList.vue'
import AtlasDetail from '@/views/AtlasDetail.vue'
import ModelList from '@/views/ModelList.vue'
import Training from '@/views/Training.vue'
import Launch from '@/views/Launch.vue'
import RuleEngine from '@/views/RuleEngine.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: Home },
    { path: '/atlas', name: 'atlas-list', component: AtlasList },
    { path: '/atlas/:id', name: 'atlas-detail', component: AtlasDetail },
    { path: '/annotate/:image_id', name: 'annotate', component: () => import('@/views/Annotate.vue') },
    { path: '/models', name: 'model-list', component: ModelList },
    { path: '/training', name: 'training', component: Training },
    { path: '/launch', name: 'launch', component: Launch },
    { path: '/rule-engine', name: 'rule-engine', component: RuleEngine },
  ],
})

export default router
