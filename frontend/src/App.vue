<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 底部导航项
const tabs = [
  { name: 'home', label: '首页', icon: 'home-o' },
  { name: 'herb', label: '百科', icon: 'search' },
  { name: 'history', label: '历史', icon: 'clock-o' },
  { name: 'mine', label: '我的', icon: 'user-o' },
]

// 当前激活 tab（路由名）
const active = () => route.name

// 子页面（识别结果/详情/收藏）隐藏底部导航，获得全屏沉浸体验
const hideTabbar = computed(() => {
  return ['result', 'herb-detail', 'favorites'].includes(route.name)
})
</script>

<template>
  <div class="app-layout">
    <main class="app-main">
      <router-view />
    </main>

    <!-- 底部导航（子页面隐藏） -->
    <van-tabbar v-if="!hideTabbar" :model-value="active()" route>
      <van-tabbar-item
        v-for="tab in tabs"
        :key="tab.name"
        :to="{ name: tab.name }"
        :icon="tab.icon"
      >
        {{ tab.label }}
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  /* 为底部 tabbar 预留空间 */
  padding-bottom: 50px;
}
</style>
