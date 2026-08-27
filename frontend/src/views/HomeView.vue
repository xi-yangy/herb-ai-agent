<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showLoadingToast, showToast } from 'vant'
import { checkHealth } from '@/api/health'
import { recognize } from '@/api/herb'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const store = useAppStore()

const checking = ref(true)
const recognizing = ref(false)

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

/** 拍照或相册上传后统一处理。 */
async function handleFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  // 重置，便于重复选择同一文件
  event.target.value = ''
  const channel = file.type.startsWith('image/') ? 'album' : 'album'

  recognizing.value = true
  showLoadingToast({ message: '识别中…', forbidClick: true, duration: 0 })
  try {
    const base64 = await fileToBase64(file)
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

/** 触发拍照（capture 优先相机）。 */
function triggerCapture() {
  document.getElementById('capture-input')?.click()
}

/** 触发相册。 */
function triggerAlbum() {
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

    <!-- 隐藏的 file 输入 -->
    <input id="capture-input" type="file" accept="image/*" capture="environment" class="hidden" @change="handleFile" />
    <input id="album-input" type="file" accept="image/*" class="hidden" @change="handleFile" />

    <!-- 安全提示 -->
    <p class="mt-8 text-center text-xs leading-relaxed text-[#5B6B62]/70">
      识别结果仅供参考，不构成诊断或处方建议。<br />
      有毒草药请务必遵医嘱使用。
    </p>
  </div>
</template>
