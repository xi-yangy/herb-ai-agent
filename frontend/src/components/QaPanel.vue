<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { showToast } from 'vant'
import { askQuestion } from '@/api/qa'
import { listConsents } from '@/api/privacy'

/**
 * 多模态问答追问组件（PRD F12/F13）。
 * - 追问卡片入口 → 展开聊天气泡问答区；
 * - 文本/语音（Web Speech API）输入问题，Qwen 结合识别结果上下文回答；
 * - Qwen 不可用降级为知识库结构化展示（fallback 标记）；
 * - 五态覆盖：空态 / 加载态 / 成功态 / 降级态 / 语音失败态；
 * - 每条 AI 回答底部附免责声明，遵循非诊断/非处方合规红线。
 */
const props = defineProps({
  herb: {
    type: Object,
    default: null,
  },
  resultName: {
    type: String,
    default: '',
  },
  // 识别原图（base64，可含 data:image 前缀）。有图时携带到后端走视觉图文问答
  image: {
    type: String,
    default: '',
  },
})

const expanded = ref(false)
const input = ref('')
const sending = ref(false)
const listRef = ref(null)

// 消息列表：{ role: 'user' | 'ai', text, fallback, disclaimer }
const messages = ref([])

// 常见问题快捷标签（空态展示，点击即发送）
const quickQuestions = ['怎么用', '有什么禁忌', '毒性如何']

// 是否支持语音输入（Chrome 系浏览器 + 联网）
const speechSupported = computed(() => {
  return typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition)
})

// 语音识别实例
let recognition = null
const listening = ref(false)

// ---- 语音朗读（TTS，Web Speech API）----

// 是否支持语音朗读
const ttsSupported = computed(() => typeof window !== 'undefined' && 'speechSynthesis' in window)

// 当前正在朗读的消息下标（-1 表示无）
const speakingIdx = ref(-1)

/** 选择中文语音，找不到则用默认。 */
function pickZhVoice() {
  const voices = window.speechSynthesis.getVoices()
  return voices.find((v) => v.lang.toLowerCase().startsWith('zh')) || null
}

/** 切换朗读/停止指定下标的消息。 */
function toggleSpeak(idx) {
  if (!ttsSupported.value) {
    showToast('当前浏览器不支持语音朗读')
    return
  }
  const msg = messages.value[idx]
  if (!msg || msg.role !== 'ai') return

  // 若已正在朗读该条 → 停止
  if (speakingIdx.value === idx) {
    stopSpeak()
    return
  }

  // 先取消当前朗读，再朗读新内容
  stopSpeak(true)

  const utter = new SpeechSynthesisUtterance(msg.text)
  utter.lang = 'zh-CN'
  const zh = pickZhVoice()
  if (zh) utter.voice = zh
  utter.rate = 1
  utter.onend = () => {
    speakingIdx.value = -1
  }
  utter.onerror = () => {
    speakingIdx.value = -1
  }
  speakingIdx.value = idx
  window.speechSynthesis.speak(utter)
}

/** 停止当前朗读并复位状态（silent 表示不弹提示）。 */
function stopSpeak(silent) {
  if (ttsSupported.value) window.speechSynthesis.cancel()
  speakingIdx.value = -1
  if (!silent) {
    showToast('已停止朗读')
  }
}

/** 组装知识库上下文透传给后端。 */
function buildContext() {
  const h = props.herb || {}
  return {
    effects: h.effects || '',
    usage: h.usage || '',
    contraindications: h.contraindications || '',
    toxicity: h.toxicity || '',
    nature_flavor: h.nature_flavor || '',
    safety_level: h.safety_level || '',
  }
}

/**
 * 压缩图片到 maxSide 以内并输出 dataURL（视觉问答用，省额度、防超时）。
 * 复用识别链路的 canvas 压缩思路；结果页传入的 image 通常已 ≤1MB，
 * 这里再压到 512px 以适配视觉 API 体积限制与降低额度消耗。
 */
function compressImage(dataUrl, maxSide = 512) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      let { width, height } = img
      if (width > maxSide || height > maxSide) {
        const ratio = Math.min(maxSide / width, maxSide / height)
        width = Math.round(width * ratio)
        height = Math.round(height * ratio)
      }
      const c = document.createElement('canvas')
      c.width = width
      c.height = height
      c.getContext('2d').drawImage(img, 0, 0, width, height)
      resolve(c.toDataURL('image/jpeg', 0.8))
    }
    img.onerror = () => resolve(dataUrl)
    img.src = dataUrl
  })
}

/** 展开问答区并滚动到底部。 */
function toggleExpand() {
  expanded.value = !expanded.value
  if (expanded.value) {
    scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

/** 发送问题（文本或快捷标签）。 */
async function send(text) {
  const q = (text ?? input.value).trim()
  if (!q || sending.value) return
  input.value = ''
  messages.value.push({ role: 'user', text: q })
  sending.value = true
  scrollToBottom()

  // 有识别原图时压缩后携带，供后端视觉图文问答（无图则后端走纯文本）
  let imageBase64 = props.image || ''
  if (imageBase64) {
    imageBase64 = await compressImage(imageBase64)
  }

  try {
    const res = await askQuestion({
      question: q,
      herb_name: props.resultName || props.herb?.name || '该药材',
      herb_context: buildContext(),
      image_base64: imageBase64 || undefined,
    })
    messages.value.push({
      role: 'ai',
      text: res.answer,
      fallback: !!res.fallback,
      disclaimer: res.disclaimer,
    })
  } catch (err) {
    console.error('[qa]', err)
    messages.value.push({
      role: 'ai',
      text: '抱歉，暂时无法获取回答，请稍后重试。',
      fallback: true,
      disclaimer: '以上内容仅供参考，不构成诊断或处方，如有不适请咨询执业医师/药师。',
    })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

/** 处理输入框回车发送。 */
function onKeyup(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

// ---- 语音输入（Web Speech API）----

/**
 * 启动语音识别，识别结果填充输入框。
 * 仅当麦克风授权记录明确拒绝（granted=false）时拦截并提示；
 * 记录缺失 / 后端不可用默认放行，交由浏览器真实权限把关。
 */
async function startVoice() {
  if (!speechSupported.value) {
    showToast('当前浏览器不支持语音输入，请使用文本')
    return
  }
  let consented = true
  try {
    const consents = await listConsents()
    const mic = (consents || []).find((c) => c.consent_type === 'microphone')
    // 记录缺失（undefined）默认放行，避免产品层授权记录与浏览器真实权限强耦合导致语音被误禁
    consented = mic ? !!mic.granted : true
  } catch (err) {
    console.error('[consents]', err)
    consented = true
  }
  if (!consented) {
    showToast('未获得麦克风授权，可在「我的-隐私与授权」中开启')
    return
  }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  recognition = new SR()
  recognition.lang = 'zh-CN'
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  recognition.onstart = () => {
    listening.value = true
  }
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript
    input.value = transcript
    showToast('语音已识别，可直接发送')
  }
  recognition.onerror = () => {
    showToast('语音识别失败，请改用文本输入')
  }
  recognition.onend = () => {
    listening.value = false
    recognition = null
  }

  try {
    recognition.start()
  } catch (err) {
    console.error('[voice]', err)
    listening.value = false
    showToast('语音识别失败，请改用文本输入')
  }
}

/** 组件卸载时停止语音识别与朗读。 */
onBeforeUnmount(() => {
  if (recognition) {
    recognition.onend = null
    recognition.stop()
  }
  if (ttsSupported.value) {
    window.speechSynthesis.cancel()
  }
})
</script>

<template>
  <section class="mt-5 overflow-hidden rounded-3xl bg-white shadow-sm">
    <!-- 追问卡片入口 -->
    <button
      type="button"
      class="flex w-full items-center justify-between px-5 py-4 text-left transition active:bg-[#F4F8F5]"
      @click="toggleExpand"
    >
      <div class="flex items-center gap-3">
        <span class="brand-gradient flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl">
          <van-icon name="chat-o" size="20" color="#fff" />
        </span>
        <div>
          <p class="text-sm font-semibold text-[#1F2A24]">对这味药还有什么想了解？</p>
          <p class="mt-0.5 text-xs text-[#5B6B62]">如「它有什么禁忌？」点击即可追问</p>
        </div>
      </div>
      <van-icon
        name="arrow-down"
        size="16"
        color="#5B6B62"
        class="shrink-0 transition-transform duration-200"
        :class="{ 'rotate-180': expanded }"
      />
    </button>

    <!-- 问答区 -->
    <transition
      enter-active-class="transition-[max-height,opacity] duration-300 ease-out"
      enter-from-class="max-h-0 opacity-0"
      enter-to-class="max-h-[800px] opacity-100"
      leave-active-class="transition-[max-height,opacity] duration-200 ease-in"
      leave-from-class="max-h-[800px] opacity-100"
      leave-to-class="max-h-0 opacity-0"
    >
      <div v-if="expanded" class="max-h-[800px] border-t border-[#F0F3F1]">
        <!-- 消息列表 -->
        <div ref="listRef" class="max-h-[360px] space-y-3 overflow-y-auto bg-[#F8FAF8] px-4 py-4">
          <!-- 空态：快捷标签 -->
          <div v-if="messages.length === 0" class="py-2 text-center">
            <p class="text-xs text-[#5B6B62]">你可以这样问我：</p>
            <div class="mt-3 flex flex-wrap justify-center gap-2">
              <button
                v-for="q in quickQuestions"
                :key="q"
                type="button"
                class="rounded-full border border-[#2E7D52]/30 bg-white px-4 py-1.5 text-xs font-medium text-[#2E7D52] transition hover:bg-[#E6F4EC] active:scale-95"
                @click="send(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <!-- 聊天气泡 -->
          <template v-else>
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="flex"
              :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
            >
              <div
                class="max-w-[82%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed"
                :class="
                  msg.role === 'user'
                    ? 'rounded-br-sm bg-[#2E7D52] text-white'
                    : 'rounded-bl-sm border border-[#E4EAE6] bg-white text-[#1F2A24]'
                "
              >
                <!-- 降级态标注 -->
                <p
                  v-if="msg.role === 'ai' && msg.fallback"
                  class="mb-1 flex items-center gap-1 text-[11px] font-medium text-[#B45309]"
                >
                  <van-icon name="info-o" size="12" />
                  已切换至本地知识库展示
                </p>
                <p class="whitespace-pre-line">{{ msg.text }}</p>

                <!-- 朗读按钮（仅 AI 回答，点击朗读/停止） -->
                <button
                  v-if="msg.role === 'ai' && ttsSupported"
                  type="button"
                  class="mt-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition active:scale-95"
                  :class="
                    speakingIdx === idx
                      ? 'bg-[#E5484D]/10 text-[#E5484D]'
                      : 'bg-[#E6F4EC] text-[#2E7D52] hover:bg-[#D9EEE1]'
                  "
                  :aria-label="speakingIdx === idx ? '停止朗读' : '朗读该回答'"
                  @click="toggleSpeak(idx)"
                >
                  <van-icon :name="speakingIdx === idx ? 'stop' : 'volume-o'" size="14" />
                  {{ speakingIdx === idx ? '停止朗读' : '朗读' }}
                </button>
                <p
                  v-if="msg.role === 'ai' && msg.disclaimer"
                  class="mt-1.5 border-t border-[#F0F3F1] pt-1.5 text-[11px] leading-relaxed text-[#5B6B62]/80"
                >
                  {{ msg.disclaimer }}
                </p>
              </div>
            </div>

            <!-- 加载态：思考中占位气泡 -->
            <div v-if="sending" class="flex justify-start">
              <div class="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-[#E4EAE6] bg-white px-4 py-3">
                <span class="dot-pulse flex gap-1">
                  <span class="h-1.5 w-1.5 rounded-full bg-[#2E7D52]"></span>
                  <span class="h-1.5 w-1.5 rounded-full bg-[#2E7D52]"></span>
                  <span class="h-1.5 w-1.5 rounded-full bg-[#2E7D52]"></span>
                </span>
                <span class="text-xs text-[#5B6B62]">思考中…</span>
              </div>
            </div>
          </template>
        </div>

        <!-- 底部输入栏 -->
        <div class="flex items-end gap-2 bg-white px-3 py-3">
          <input
            v-model="input"
            type="text"
            placeholder="输入你的问题…"
            class="min-w-0 flex-1 rounded-2xl border border-[#E4EAE6] bg-[#F8FAF8] px-3.5 py-2.5 text-sm text-[#1F2A24] outline-none transition focus:border-[#2E7D52]"
            @keyup="onKeyup"
          />
          <!-- 语音按钮 -->
          <button
            type="button"
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition active:scale-90"
            :class="listening ? 'voice-pulse bg-[#E5484D] text-white' : 'bg-[#E6F4EC] text-[#2E7D52]'"
            @click="startVoice"
          >
            <van-icon name="microphone" size="18" />
          </button>
          <!-- 发送按钮 -->
          <button
            type="button"
            class="brand-gradient flex h-10 w-16 shrink-0 items-center justify-center rounded-2xl text-sm font-medium text-white transition active:scale-95 disabled:opacity-50"
            :disabled="sending || !input.trim()"
            @click="send()"
          >
            发送
          </button>
        </div>
      </div>
    </transition>
  </section>
</template>

<style scoped>
.dot-pulse span {
  animation: dot-bounce 1.2s infinite ease-in-out;
}
.dot-pulse span:nth-child(2) {
  animation-delay: 0.15s;
}
.dot-pulse span:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes dot-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-3px);
    opacity: 1;
  }
}

.voice-pulse {
  animation: voice-ring 1.2s infinite ease-in-out;
}
@keyframes voice-ring {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(229, 72, 77, 0);
  }
}
</style>
