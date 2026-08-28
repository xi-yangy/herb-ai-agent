<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showLoadingToast, showToast } from 'vant'
import { checkHealth } from '@/api/health'
import { recognize } from '@/api/herb'
import { listConsents } from '@/api/privacy'
import { useAppStore } from '@/stores/app'
import CameraCapture from '@/components/CameraCapture.vue'

const router = useRouter()
const store = useAppStore()

const checking = ref(true)
const recognizing = ref(false)
const showCamera = ref(false)

onMounted(async () => {
  const online = await checkHealth()
  store.setBackendOnline(online)
  checking.value = false
})

/** 读取文件为 base64（剥离 data:image 前缀，保持接口契约简单）。 */
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.readAsDataURL(file)
  })
}

/** 统一识别入口：收到 base64 与通道后发起识别并跳转结果页。 */
async function handleRecognize(base64, channel) {
  recognizing.value = true
  showLoadingToast({ message: '识别中…', forbidClick: true, duration: 0 })
  try {
    const result = await recognize(base64, channel)
    store.setLastRecognition(base64, result)
    router.push({ name: 'result' })
  } catch (err) {
    console.error('[recognize]', err)
    showToast('识别失败，请稍后重试')
  } finally {
    recognizing.value = false
    showToast()
  }
}

/** 相册上传：选择图片 → 识别（channel=album）。 */
async function handleFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  // 重置，便于重复选择同一文件
  event.target.value = ''
  try {
    const base64 = await fileToBase64(file)
    await handleRecognize(base64, 'album')
  } catch (err) {
    console.error('[read file]', err)
    showToast('读取图片失败，请重试')
  }
}

/**
 * 点「拍照识别」：仅当授权记录明确拒绝（granted=false）时才降级相册；
 * 记录缺失 / 后端不可用默认放行，交由 CameraCapture 内部 getUserMedia 做真实相机校验。
 */
async function triggerCapture() {
  let consented = true
  try {
    const consents = await listConsents()
    const camera = (consents || []).find((c) => c.consent_type === 'camera')
    // 记录缺失（undefined）默认放行，避免产品层授权记录与浏览器真实权限强耦合导致相机被误判
    consented = camera ? !!camera.granted : true
  } catch (err) {
    console.error('[consents]', err)
    consented = true
  }

  if (!consented) {
    showToast('未获得相机授权，已切换为从相册选择')
    triggerAlbum()
    return
  }
  showCamera.value = true
}

/** 相机拍照成功：channel=camera。 */
function onCaptured(base64) {
  handleRecognize(base64, 'camera')
}

/** 相机不可用降级：回落相册选图。 */
function onCameraDegrade() {
  showCamera.value = false
  triggerAlbum()
}

/**
 * 触发相册：仅当相册授权记录明确拒绝（granted=false）时拦截并提示；
 * 记录缺失 / 后端不可用默认放行，交由浏览器文件选择器做真实校验。
 */
async function triggerAlbum() {
  let consented = true
  try {
    const consents = await listConsents()
    const album = (consents || []).find((c) => c.consent_type === 'album')
    // 记录缺失（undefined）默认放行，避免产品层授权记录与浏览器真实权限强耦合导致相册被误判
    consented = album ? !!album.granted : true
  } catch (err) {
    console.error('[consents]', err)
    consented = true
  }

  if (!consented) {
    showToast('未获得相册授权，可在「我的-隐私与授权」中开启')
    return
  }
  document.getElementById('album-input')?.click()
}
</script>

<template>
  <div class="page-container px-4 pb-28 pt-10">
    <!-- 品牌区 -->
    <header class="mb-10 text-center">
      <div
        class="brand-gradient mx-auto flex h-16 w-16 items-center justify-center rounded-3xl shadow-lg"
      >
        <van-icon name="flower-o" size="32" color="#fff" />
      </div>
      <h1 class="mt-4 text-[22px] font-semibold text-[#1F2A24]">灵草 · 中草药识别</h1>
      <p class="mt-2 text-sm text-[#5B6B62]">拍照识别草药，详解功效、禁忌与安全提示</p>
      <!-- 连通状态 -->
      <div class="mt-3 inline-flex items-center gap-1.5 text-xs">
        <span
          class="inline-block h-2 w-2 rounded-full"
          :class="store.backendOnline ? 'bg-[#2E7D52]' : 'bg-[#E5484D]'"
        ></span>
        <span class="text-[#5B6B62]">
          {{ checking ? '检测中…' : store.backendOnline ? '服务正常' : '服务未连接' }}
        </span>
      </div>
    </header>

    <!-- 大尺寸识别入口 -->
    <section class="glass-card flex flex-col items-center px-6 py-10">
      <button
        type="button"
        class="brand-gradient flex h-24 w-24 items-center justify-center rounded-full shadow-xl transition active:scale-95"
        :disabled="recognizing"
        @click="triggerCapture"
      >
        <van-icon name="photograph" size="40" color="#fff" />
      </button>
      <p class="mt-5 text-base font-medium text-[#1F2A24]">点击拍摄，识别中草药</p>

      <div class="mt-6 grid w-full grid-cols-2 gap-4">
        <button
          type="button"
          class="flex items-center justify-center gap-2 rounded-2xl border border-[#2E7D52]/20 bg-white/80 py-3.5 text-sm font-medium text-[#2E7D52] transition active:scale-95"
          :disabled="recognizing"
          @click="triggerCapture"
        >
          <van-icon name="photograph" size="20" />
          拍照识别
        </button>
        <button
          type="button"
          class="flex items-center justify-center gap-2 rounded-2xl border border-[#2E7D52]/20 bg-white/80 py-3.5 text-sm font-medium text-[#2E7D52] transition active:scale-95"
          :disabled="recognizing"
          @click="triggerAlbum"
        >
          <van-icon name="photo" size="20" />
          相册上传
        </button>
      </div>

      <p v-if="recognizing" class="mt-4 text-xs text-[#5B6B62]">正在分析图片特征…</p>
    </section>

    <!-- 隐藏的相册 file 输入 -->
    <input id="album-input" type="file" accept="image/*" class="hidden" @change="handleFile" />

    <!-- 相机拍照弹层 -->
    <CameraCapture
      v-model:show="showCamera"
      @captured="onCaptured"
      @degrade="onCameraDegrade"
    />

    <!-- 安全提示 -->
    <p class="mt-8 text-center text-xs leading-relaxed text-[#5B6B62]/70">
      识别结果仅供参考，不构成诊断或处方建议。<br />
      有毒草药请务必遵医嘱使用。
    </p>
  </div>
</template>
