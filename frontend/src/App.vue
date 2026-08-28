<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import { updateConsent } from '@/api/privacy'
import PrivacyDialog from '@/components/PrivacyDialog.vue'

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

// 子页面（识别结果/详情/收藏/登录/警示）隐藏底部导航，获得全屏沉浸体验
const hideTabbar = computed(() => {
  return ['result', 'herb-detail', 'favorites', 'login', 'warning-gate'].includes(route.name)
})

// 首次隐私授权说明
const PRIVACY_ACK_KEY = 'herb_privacy_ack'
const showPrivacy = ref(false)

onMounted(async () => {
  // 每次启动将三项授权重置为默认开启：手动关闭仅当前会话生效，刷新/重启后恢复开启
  try {
    await Promise.all([
      updateConsent('camera', true),
      updateConsent('album', true),
      updateConsent('microphone', true),
    ])
  } catch (err) {
    console.error('[privacy reset]', err)
  }
  // 已确认过首次说明则不再弹出
  if (localStorage.getItem(PRIVACY_ACK_KEY) === '1') return
  showPrivacy.value = true
})

/** 处理首次授权结果：记录持久化状态 + 同步后端授权。 */
async function onPrivacyResult({ consent }) {
  localStorage.setItem(PRIVACY_ACK_KEY, '1')
  // 暂不授权也不写入拒绝态，拍照时仍放行交给浏览器 getUserMedia 判断，避免相机被误阻断
  if (!consent) {
    showToast('你已了解权限说明；需要时会在拍照/上传时自动请求对应权限')
    return
  }
  try {
    // 默认授予相机/相册/麦克风；关闭后对应入口将受限（在「我的-隐私与授权」可重新开启）
    await Promise.all([
      updateConsent('camera', true),
      updateConsent('album', true),
      updateConsent('microphone', true),
    ])
  } catch (err) {
    console.error('[privacy consent]', err)
  }
}
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

    <!-- 首次隐私授权说明弹窗 -->
    <PrivacyDialog v-model:show="showPrivacy" @result="onPrivacyResult" />
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
