<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { updateConsent } from '@/api/privacy'
import { useAppStore } from '@/stores/app'
import PrivacyDialog from '@/components/PrivacyDialog.vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

// 顶部导航项
const tabs = [
  { name: 'home', label: '首页' },
  { name: 'herb', label: '百科' },
  { name: 'history', label: '历史' },
  { name: 'mine', label: '我的' },
]

// 当前激活导航（路由名）
const active = () => route.name

// 全屏沉浸页（识别结果/高危警示）隐藏 Header/Footer；警示页强制全屏无逃逸入口
const hideShell = computed(() => {
  return ['result', 'warning-gate'].includes(route.name)
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
    <!-- 顶部固定 Header（桌面全局导航） -->
    <header
      v-if="!hideShell"
      class="fixed inset-x-0 top-0 z-50 h-16 border-b border-ink/10 bg-paper-card"
    >
      <div class="mx-auto flex h-full max-w-[1200px] items-center gap-6 px-6">
        <!-- 品牌：点击回首页 -->
        <button
          type="button"
          class="flex items-center gap-2.5"
          @click="router.push({ name: 'home' })"
        >
          <span
            class="flex h-8 w-8 items-center justify-center rounded-lg"
            style="background-color: #2f9e6b"
          >
            <span class="section-title text-lg leading-none text-white">灵</span>
          </span>
          <span class="section-title text-[17px] text-ink">灵草 · 中草药识别</span>
        </button>

        <!-- 主导航 -->
        <nav class="flex items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.name"
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-medium transition"
            :class="
              active() === tab.name
                ? 'bg-primary/10 font-semibold text-primary'
                : 'text-ink-secondary hover:bg-primary/5 hover:text-primary'
            "
            @click="router.push({ name: tab.name })"
          >
            {{ tab.label }}
          </button>
        </nav>

        <!-- 连通状态 -->
        <div class="ml-auto flex items-center gap-1.5 text-xs text-ink-secondary">
          <span
            class="inline-block h-2 w-2 rounded-full"
            :class="store.backendOnline ? 'bg-primary' : 'bg-cinnabar'"
          ></span>
          {{ store.backendOnline ? '智能体系统已就绪' : '系统暂未连接' }}
        </div>
      </div>
    </header>

    <!-- 主内容区：为固定 Header 预留顶部空间（全屏页除外） -->
    <main class="app-main" :class="hideShell ? 'pb-6' : 'pt-16 pb-6'">
      <router-view />
    </main>

    <!-- 底部版权/免责 Footer（正规网页结构；全屏页隐藏） -->
    <footer v-if="!hideShell" class="border-t border-ink/10 py-5">
      <div class="mx-auto max-w-[1200px] px-6 text-center text-xs leading-relaxed text-ink-faint">
        灵草·中草药多模态识别智能体 | 基于大模型与中药典知识库构建 | 本系统结果仅供参考，不构成诊断或处方，如有不适请咨询执业医师/药师
      </div>
      <div class="mx-auto max-w-[1200px] px-6 pt-1 text-center text-[11px] text-ink-faint/70">
        本系统仅供学习与科研参考
      </div>
    </footer>

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
}
</style>
