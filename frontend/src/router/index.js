import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from '@/views/HomeView.vue'
import HerbView from '@/views/HerbView.vue'
import HistoryView from '@/views/HistoryView.vue'
import MineView from '@/views/MineView.vue'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/home', name: 'home', component: HomeView },
  { path: '/herb', name: 'herb', component: HerbView },
  { path: '/history', name: 'history', component: HistoryView },
  { path: '/mine', name: 'mine', component: MineView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
