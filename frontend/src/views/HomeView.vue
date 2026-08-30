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

const recognizing = ref(false)
const showCamera = ref(false)

onMounted(async () => {
  const online = await checkHealth()
  store.setBackendOnline(online)
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
  <div class="page-container px-6 pb-12">
    <!-- 桌面双栏：左品牌区 + 右识别主卡；整页对称垂直居中（扣除 Header/Footer 高度） -->
    <div class="flex min-h-[calc(100vh-240px)] items-center gap-16 pt-8">
      <!-- 品牌区 -->
      <header class="flex-1 text-left">
        <!-- 草本绿品牌印章 -->
        <div
          class="flex h-24 w-24 items-center justify-center rounded-xl"
          style="background-color: #2f9e6b; box-shadow: 0 8px 20px rgba(47, 158, 107, 0.3)"
        >
          <span class="section-title text-4xl leading-none text-white">灵</span>
        </div>
        <h1 class="section-title mt-7 text-[32px] leading-tight text-ink">灵草 · 中草药识别</h1>
        <p class="mt-3 text-base text-ink-secondary">拍照识别草药，详解功效、禁忌与安全提示</p>

        <!-- 技术亮点标签 -->
        <div class="mt-7 flex flex-wrap gap-3">
          <span class="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <van-icon name="chat-o" size="13" />
            AI 多模态对话
          </span>
          <span class="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <van-icon name="bookmark-o" size="13" />
            100+ 药典药材库
          </span>
          <span class="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <van-icon name="shield-o" size="13" />
            毒性与易混淆预警
          </span>
        </div>
      </header>

      <!-- 识别主卡 -->
      <section class="card-paper flex flex-1 flex-col items-center px-6 py-8">
        <p class="section-title text-3xl text-ink">识别一株草药</p>
        <p class="mt-3 text-lg text-ink-secondary">拍摄或上传清晰照片，马上得到结果</p>

        <div class="mt-6 grid w-full grid-cols-2 gap-4">
          <button
            type="button"
            class="btn-primary h-14 w-full gap-2 text-lg"
            :disabled="recognizing"
            @click="triggerCapture"
          >
            <van-icon name="photograph" size="22" />
            拍照识别
          </button>
          <button
            type="button"
            class="btn-primary h-14 w-full gap-2 text-lg"
            :disabled="recognizing"
            @click="triggerAlbum"
          >
            <van-icon name="photo" size="22" />
            相册上传
          </button>
        </div>

        <p class="mt-4 text-center text-sm leading-relaxed text-ink-secondary">
          💡 提示：上传照片后，可与 AI 助手语音/文字对话，解答禁忌与用药疑问。
        </p>

        <p v-if="recognizing" class="mt-4 text-sm text-ink-secondary">正在辨识这株草药…</p>

        <!-- 常驻小卡：安全三原则 + 拍摄小贴士 -->
        <div class="mt-5 grid w-full grid-cols-2 gap-4">
          <div class="card-paper flex flex-col gap-2 p-4 text-left">
            <div class="flex items-center gap-1.5">
              <van-icon name="shield-o" size="18" color="#2F9E6B" />
              <span class="section-title text-base text-ink">安全三原则</span>
            </div>
            <ol class="space-y-1.5 text-[15px] leading-relaxed text-ink-secondary">
              <li class="flex gap-1.5"><span class="shrink-0 font-semibold text-primary">①</span><span>结果仅供参考，不构成诊断或处方</span></li>
              <li class="flex gap-1.5"><span class="shrink-0 font-semibold text-primary">②</span><span>毒性药材务必遵医嘱，切勿自行服用</span></li>
              <li class="flex gap-1.5"><span class="shrink-0 font-semibold text-primary">③</span><span>如身体不适请及时就医</span></li>
            </ol>
          </div>
          <div class="card-paper flex flex-col gap-2 p-4 text-left">
            <div class="flex items-center gap-1.5">
              <van-icon name="photo-o" size="18" color="#2F9E6B" />
              <span class="section-title text-base text-ink">拍摄小贴士</span>
            </div>
            <ol class="space-y-1.5 text-[15px] leading-relaxed text-ink-secondary">
              <li class="flex gap-1.5"><span class="shrink-0 font-semibold text-primary">①</span><span>一次只拍一株，避免枝叶重叠</span></li>
              <li class="flex gap-1.5"><span class="shrink-0 font-semibold text-primary">②</span><span>光线充足、背景简洁</span></li>
              <li class="flex gap-1.5"><span class="shrink-0 font-semibold text-primary">③</span><span>对准叶片花果特写</span></li>
            </ol>
          </div>
        </div>
      </section>
    </div>

    <!-- 隐藏的相册 file 输入 -->
    <input id="album-input" type="file" accept="image/*" class="hidden" @change="handleFile" />

    <!-- 相机拍照弹层 -->
    <CameraCapture
      v-model:show="showCamera"
      @captured="onCaptured"
      @degrade="onCameraDegrade"
    />
  </div>
</template>
