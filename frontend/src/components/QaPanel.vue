<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { showToast } from 'vant'
import { askQuestion } from '@/api/qa'
import { listConsents } from '@/api/privacy'

/**
 * 多模态问答追问组件（PRD F12/F13）。
 * - 常驻展示：底部直接暴露输入框 + 分组快捷词包（无需点击展开）；
 * - 文本/语音（Web Speech API）输入问题，Qwen 结合识别结果上下文回答；
 * - Qwen 不可用降级为知识库结构化展示（fallback 标记）；
 * - 快捷词包按药材属性动态选中最相关的 1-2 组（如毒性药材突出安全组）；
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

const input = ref('')
const sending = ref(false)
const listRef = ref(null)
// 根元素 ref：供父组件 scrollIntoView 平滑滚动到本问答面板
const panelRef = ref(null)

// 消息列表：{ role: 'user' | 'ai', text, fallback, disclaimer }
const messages = ref([])

/**
 * 分组快捷词包（多组按维度组织，每组若干词条，点击即发送）。
 * 展示时按当前药材属性动态选中与安全等级/分类最相关的组。
 */
const quickPacks = [
  {
    id: 'safety',
    title: '安全提示',
    icon: 'shield-o',
    questions: ['毒性如何', '会不会中毒', '有什么副作用', '哪些人不能用'],
  },
  {
    id: 'effect',
    title: '功效用法',
    icon: 'fire-o',
    questions: ['怎么用', '一次用多少', '能治什么', '适合哪些人'],
  },
  {
    id: 'caution',
    title: '禁忌慎用',
    icon: 'warning-o',
    questions: ['有什么禁忌', '孕妇能吃吗', '儿童能用吗', '和什么不能同服'],
  },
  {
    id: 'blend',
    title: '搭配炮制',
    icon: 'gold-coin-o',
    questions: ['能和什么一起吃', '怎么炮制', '怎么辨别正品'],
  },
]

/**
 * 当前页展示的快捷词包组（1-2 组）。
 * 规则：毒性 → 安全提示（+禁忌慎用）；慎用 → 安全提示 + 禁忌慎用；
 *       普通 → 功效用法（+搭配炮制）。优先级高的组排前。
 */
const selectedPacks = computed(() => {
  const level = props.herb?.safety_level || ''
  const byId = (id) => quickPacks.find((p) => p.id === id)
  if (level === '毒性') return [byId('safety'), byId('caution')].filter(Boolean)
  if (level === '慎用') return [byId('safety'), byId('caution')].filter(Boolean)
  return [byId('effect'), byId('blend')].filter(Boolean)
})

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
      vision: !!res.vision,
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

/** 停止语音识别：recognition.stop() 会触发 onend 自动复位 listening，兼容现有生命周期。 */
function stopVoice() {
  if (recognition) {
    recognition.stop()
  } else {
    listening.value = false
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

/**
 * 对外暴露：接收预设问题（兼容「你可能会关心」外部 prompt 桥接）。
 * 常驻面板无需展开，直接发送问题（走 send() 链路，Qwen 一次返回），再滚动定位。
 */
async function askPreset(question) {
  const q = (question || '').trim()
  if (!q) return
  await nextTick()
  send(q)
  // 发送后滚动到底部，让用户看到「思考中…」与后续回答
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

/** 对外暴露方法，供父组件（ResultView）桥接调用。 */
defineExpose({ askPreset, panelRef })
</script>

<template>
  <section ref="panelRef" class="card-paper mt-5 overflow-hidden">
    <!-- 常驻面板头部 -->
    <div class="flex items-center gap-3 px-5 pt-4">
      <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary">
        <van-icon name="chat-o" size="20" color="#fff" />
      </span>
      <div>
        <p class="section-title text-sm text-ink">对这味药还有什么想了解？</p>
        <p class="mt-0.5 text-xs text-ink-secondary">对这味药有疑问？直接提问，或点击下方快捷词条</p>
      </div>
    </div>

    <div class="border-t border-ink/10">
      <!-- 消息列表 -->
      <div ref="listRef" class="max-h-[420px] space-y-3 overflow-y-auto bg-paper/60 px-4 py-4">
        <!-- 空态引导文案 -->
        <p v-if="messages.length === 0" class="text-center text-xs text-ink-secondary">
          你可以问我关于本药材的功效、用法、禁忌或安全性等问题
        </p>

        <!-- 聊天气泡 -->
        <template v-else>
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[82%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed"
              :class="
                msg.role === 'user'
                  ? 'rounded-br-sm bg-primary text-white'
                  : 'rounded-bl-sm border border-ink/10 bg-white text-ink'
              "
            >
              <!-- 视觉图文模式标注（结合上传图片作答） -->
              <p
                v-if="msg.role === 'ai' && msg.vision"
                class="mb-1 flex items-center gap-1 text-[11px] font-semibold text-primary"
              >
                <van-icon name="photograph" size="13" />
                已结合你所拍的图片回答
              </p>
              <!-- 视觉问答证据：识别图片缩略图预览 -->
              <img
                v-if="msg.role === 'ai' && msg.vision && props.image"
                :src="props.image"
                alt="识别图片"
                class="mb-1.5 mt-0.5 h-14 w-14 rounded-lg border border-primary/30 object-cover"
              />
              <!-- 降级态标注 -->
              <p
                v-if="msg.role === 'ai' && msg.fallback"
                class="mb-1 flex items-center gap-1 text-[11px] font-medium text-ochre"
              >
                <van-icon name="info-o" size="12" />
                已根据药典资料为你整理
              </p>
              <p class="whitespace-pre-line">{{ msg.text }}</p>

              <!-- 朗读按钮（仅 AI 回答，点击朗读/停止） -->
              <button
                v-if="msg.role === 'ai' && ttsSupported"
                type="button"
                class="mt-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition active:scale-95"
                :class="
                  speakingIdx === idx
                    ? 'bg-cinnabar/10 text-cinnabar'
                    : 'bg-primary/10 text-primary hover:bg-primary/15'
                "
                :aria-label="speakingIdx === idx ? '停止朗读' : '朗读该回答'"
                @click="toggleSpeak(idx)"
              >
                <van-icon :name="speakingIdx === idx ? 'stop' : 'volume-o'" size="14" />
                {{ speakingIdx === idx ? '停止朗读' : '朗读' }}
              </button>
              <p
                v-if="msg.role === 'ai' && msg.disclaimer"
                class="mt-1.5 border-t border-ink/10 pt-1.5 text-[11px] leading-relaxed text-ink-secondary/80"
              >
                {{ msg.disclaimer }}
              </p>
            </div>
          </div>

          <!-- 加载态：思考中占位气泡 -->
          <div v-if="sending" class="flex justify-start">
            <div class="flex items-center gap-2 rounded-xl rounded-bl-sm border border-ink/10 bg-white px-4 py-3">
              <span class="flex gap-1">
                <span class="h-1.5 w-1.5 rounded-full bg-primary/40"></span>
                <span class="h-1.5 w-1.5 rounded-full bg-primary/60"></span>
                <span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
              </span>
              <span class="text-xs text-ink-secondary">思考中…</span>
            </div>
          </div>
        </template>
      </div>

      <!-- 分组快捷词包（按药材动态选中 1-2 组，点击即发送） -->
      <div class="space-y-3.5 border-t border-ink/10 bg-paper/60 px-4 py-3.5">
        <div v-for="pack in selectedPacks" :key="pack.id">
          <p class="mb-2 flex items-center gap-1.5 text-xs font-semibold text-primary">
            <van-icon :name="pack.icon" size="14" />
            {{ pack.title }}
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="q in pack.questions"
              :key="q"
              type="button"
              class="h-8 rounded-full border border-primary/30 bg-white px-3.5 text-xs font-medium text-primary transition hover:border-primary/50 hover:bg-primary/10 active:scale-95 disabled:opacity-50"
              :disabled="sending"
              @click="send(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>
      </div>

      <!-- 底部输入栏 -->
      <div class="flex items-center gap-2 border-t border-ink/10 bg-white px-3 py-3">
        <input
          v-model="input"
          type="text"
          placeholder="输入你的问题…"
          class="h-11 min-w-0 flex-1 rounded-xl border border-ink/10 bg-paper px-3.5 text-sm text-ink outline-none transition placeholder:text-ink-faint focus:border-primary"
          @keyup="onKeyup"
        />
        <!-- 语音按钮：话筒图标 + 文字，实心主色；录音中红色 + 脉冲，点击停止 -->
        <button
          type="button"
          :aria-label="listening ? '停止语音输入' : '语音输入'"
          :aria-pressed="listening ? 'true' : 'false'"
          class="flex h-11 shrink-0 items-center gap-1.5 rounded-full px-4 shadow-md transition active:scale-95"
          :class="listening ? 'voice-pulse bg-cinnabar text-white' : 'bg-primary text-white shadow-primary/25 hover:bg-primary-light'"
          @click="listening ? stopVoice() : startVoice()"
        >
          <van-icon name="microphone" size="18" />
          <span class="text-sm font-medium">{{ listening ? '停止' : '语音' }}</span>
        </button>
        <!-- 发送按钮 -->
        <button
          type="button"
          class="btn-primary h-11 shrink-0 px-5 text-sm"
          :disabled="sending || !input.trim()"
          @click="send()"
        >
          发送
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 语音收听态红色呼吸脉冲（box-shadow 扩散）；其余场景保持静态 */
.voice-pulse {
  animation: voice-pulse 1.6s ease-in-out infinite;
}

@keyframes voice-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(192, 57, 43, 0.45);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(192, 57, 43, 0);
  }
}
</style>
