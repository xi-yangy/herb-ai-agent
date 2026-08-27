import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from '@/views/HomeView.vue'
import HerbView from '@/views/HerbView.vue'
import HistoryView from '@/views/HistoryView.vue'
import MineView from '@/views/MineView.vue'
import ResultView from '@/views/ResultView.vue'
import HerbDetailView from '@/views/HerbDetailView.vue'
import FavoritesView from '@/views/FavoritesView.vue'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/home', name: 'home', component: HomeView },
  { path: '/herb', name: 'herb', component: HerbView },
  { path: '/history', name: 'history', component: HistoryView },
  { path: '/mine', name: 'mine', component: MineView },
  // 子页面（不在底部 Tabbar 中）
  { path: '/result', name: 'result', component: ResultView },
  { path: '/herb/:id', name: 'herb-detail', component: HerbDetailView, props: true },
  { path: '/favorites', name: 'favorites', component: FavoritesView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
