<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { showToast } from 'vant'

/**
 * 实时拍照组件：getUserMedia 取景 → 快门 canvas 抽帧转 base64 → 拍照预览确认 → emit captured。
 * - PC 与移动端均可真拍照；无摄像头 / 拒绝权限 / 不可用时内部降级信号 emit('degrade')，
 *   由父组件回落相册选图，不阻断主流程。
 * - 关闭 / 卸载时强制释放媒体流（stop tracks），避免摄像头灯常亮（合规 + 省电）。
 */
const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:show', 'captured', 'degrade'])

const videoRef = ref(null)
const canvasRef = ref(null)
const facingMode = ref('environment') // environment 后置 / user 前置
const stream = ref(null)
const shot = ref('') // 拍照后的 dataURL；空表示取景中
const starting = ref(false)

/** 打开指定 facingMode 的摄像头。 */
async function openCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    emit('degrade')
    return
  }
  stopStream()
  starting.value = true
  try {
    const s = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: facingMode.value } },
      audio: false,
    })
    stream.value = s
    if (videoRef.value) {
      videoRef.value.srcObject = s
      await videoRef.value.play().catch(() => {})
    }
  } catch (err) {
    // 权限拒绝 / 无摄像头 / 约束不满足 → 降级为相册选图
    showToast('未获得相机权限或无摄像头，已切换为从相册选择')
    emit('degrade')
  } finally {
    starting.value = false
  }
}

/** 停止并释放媒体流。 */
function stopStream() {
  if (stream.value) {
    stream.value.getTracks().forEach((t) => t.stop())
    stream.value = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
}

/** 切换前后摄像头。 */
function switchCamera() {
  facingMode.value = facingMode.value === 'environment' ? 'user' : 'environment'
  openCamera()
}

/** 压缩图片到 maxSide 以内并输出 dataURL（PRD：上传 ≤1MB）。 */
function compressDataUrl(dataUrl, maxSide = 1280) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      let { width, height } = img
      const ratio = Math.max(width, height) / maxSide
      if (ratio > 1) {
        width = Math.round(width / ratio)
        height = Math.round(height / ratio)
      }
      const c = document.createElement('canvas')
      c.width = width
      c.height = height
      c.getContext('2d').drawImage(img, 0, 0, width, height)
      // 先试 0.85，过大则逐步降低质量，保证 ≤1MB
      let quality = 0.85
      let out = c.toDataURL('image/jpeg', quality)
      while (out.length > 1.05 * 1024 * 1024 && quality > 0.3) {
        quality -= 0.15
        out = c.toDataURL('image/jpeg', quality)
      }
      resolve(out)
    }
    img.onerror = () => resolve(dataUrl)
    img.src = dataUrl
  })
}

/** 快门：抽帧 → 压缩 → 进入拍照预览。 */
async function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas || !video.videoWidth) return
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
  const raw = canvas.toDataURL('image/jpeg', 0.9)
  shot.value = await compressDataUrl(raw)
}

/** 重拍：回到取景状态。 */
function retake() {
  shot.value = ''
}

/** 确认识别：输出 base64 并关闭弹层。 */
function confirm() {
  if (!shot.value) return
  emit('captured', shot.value)
  shot.value = ''
  emit('update:show', false)
}

/** 关闭弹层（释放流 + 重置状态）。 */
function close() {
  shot.value = ''
  stopStream()
  emit('update:show', false)
}

// 打开弹层时启动摄像头
watch(
  () => props.show,
  (v) => {
    if (v) {
      shot.value = ''
      openCamera()
    } else {
      stopStream()
    }
  }
)

// 卸载兜底释放
onBeforeUnmount(stopStream)
</script>

<template>
  <van-popup
    :show="show"
    position="center"
    :close-on-click-overlay="false"
    class="camera-popup"
  >
    <div class="flex h-[520px] w-[640px] flex-col">
      <!-- 顶部操作栏 -->
      <div class="flex items-center justify-between px-4 py-3">
        <button
          type="button"
          class="flex h-9 w-9 items-center justify-center rounded-full bg-paper active:scale-90"
          @click="close"
        >
          <van-icon name="cross" size="18" color="#2A2A28" />
        </button>
        <span class="section-title text-[15px] text-ink">拍摄识别</span>
        <span class="w-9"></span>
      </div>

      <!-- 取景 / 预览区 -->
      <div class="relative flex-1 overflow-hidden bg-[#101613]">
        <!-- 实时取景 -->
        <video
          v-show="!shot"
          ref="videoRef"
          playsinline
          muted
          autoplay
          class="h-full w-full object-cover"
        ></video>
        <!-- 拍照预览 -->
        <img v-if="shot" :src="shot" alt="拍照预览" class="h-full w-full object-cover" />

        <!-- 取景提示 -->
        <div v-if="starting && !shot" class="absolute inset-0 flex items-center justify-center">
          <van-loading color="#fff" size="24">正在开启摄像头…</van-loading>
        </div>
      </div>

      <!-- 底部控制区 -->
      <div class="flex items-center justify-around px-6 py-5">
        <!-- 取景态：切换 + 快门 -->
        <template v-if="!shot">
          <button
            type="button"
            class="flex h-11 w-11 items-center justify-center rounded-full bg-paper transition active:scale-90"
            :disabled="starting"
            @click="switchCamera"
          >
            <van-icon name="replay" size="20" color="#2F9E6B" />
          </button>
          <button
            type="button"
            class="h-16 w-16 rounded-full border-4 border-paper-card bg-primary shadow-lg transition active:scale-95"
            :disabled="starting"
            @click="capture"
          ></button>
          <span class="w-11"></span>
        </template>
        <!-- 预览态：重拍 + 确认 -->
        <template v-else>
          <button
            type="button"
            class="h-12 rounded-xl border border-ink/20 bg-paper-card px-8 text-sm font-medium text-ink-secondary transition active:scale-95"
            @click="retake"
          >
            重拍
          </button>
          <button
            type="button"
            class="btn-primary h-12 px-8 text-sm"
            @click="confirm"
          >
            确认识别
          </button>
        </template>
      </div>

      <!-- 隐藏 canvas（抽帧用） -->
      <canvas ref="canvasRef" class="hidden"></canvas>
    </div>
  </van-popup>
</template>

<style scoped>
.camera-popup {
  border-radius: 16px;
  overflow: hidden;
}
</style>
