<script setup>
import { computed, ref } from 'vue'

/**
 * 分层信息卡（PRD F5）：
 * - 白话科普卡（默认展开）：由专业字段经规则模板生成通俗内容（它有什么用/该怎么用/哪些人要注意），
 *   并按安全等级显示色条与警示措辞。
 * - 专业药典卡（点击展开）：原样展示专业字段（性味归经/功效主治/用法用量/禁忌/毒性）。
 * - 合规：白话措辞统一用"传统上/常用于/建议"等限定词，避免"治疗/治愈/疗效"等诊断性表述；
 *   毒性药材白话卡顶部强制显示红色警示条（不可折叠隐藏）。
 */
const props = defineProps({
  herb: {
    type: Object,
    required: true,
  },
})

/** 专业卡是否展开。 */
const showPro = ref(false)

/** 安全等级映射（色条 + 图标 + 文案）。 */
const safetyMeta = computed(() => {
  const map = {
    普通: { color: '#4A7C59', bg: '#EAF1EC', label: '普通药材', icon: 'smile-o' },
    慎用: { color: '#C08A3E', bg: '#F7EFDF', label: '慎用', icon: 'warning-o' },
    毒性: { color: '#C0392B', bg: '#FAE9E7', label: '毒性药材 · 高风险', icon: 'warning-o' },
  }
  return map[props.herb.safety_level || ''] || map.普通
})

/** 安全提示措辞（按安全等级）。 */
function safetyTip(level) {
  const tips = {
    普通: '常规使用相对安全，仍建议按剂量服用，避免过量。',
    慎用: '需谨慎使用，特定人群（如孕妇、儿童、体质虚弱者）应避免或减量，建议先咨询医师。',
    毒性: '含毒性成分，使用不当可危及健康。务必经炮制、严格控量并遵医嘱，切勿自行服用。',
  }
  return tips[level] || tips.普通
}

/** 将功效文本按顿号/逗号拆分为短语列表（用于生活化组织）。 */
function splitPhrases(text) {
  if (!text) return []
  return text
    .split(/[，,、。;；]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/** 分类的通俗描述（category → 生活化说明）。 */
const categoryDesc = computed(() => {
  const map = {
    根茎类: '入药部位多为根部或根状茎',
    花类: '入药部位多为花或花蕾',
    果实类: '入药部位多为果实或种子',
    全草类: '入药部位多为整株草本',
    树皮类: '入药部位多为树皮',
    叶类: '入药部位多为叶片',
    种子类: '入药部位多为种子',
    动物类: '来源于动物药材',
    矿物类: '来源于矿物药材',
  }
  return map[props.herb.category || ''] || '是一味常用的中药材'
})

/** 白话：它有什么用（生活化改写 + 通俗总结）。 */
const plainUse = computed(() => {
  const phrases = splitPhrases(props.herb.effects)
  if (!phrases.length) return '暂无通俗功效说明，可点击下方查看专业内容。'
  const main = phrases.slice(0, 4).join('、')
  return `传统上常与「${main}」等作用相关，${categoryDesc.value}，多用于特定体质的日常调养参考，并非人人适用。`
})

/** 白话：该怎么用（剂量 + 服法生活化）。 */
const plainUsage = computed(() => {
  const u = (props.herb.usage || '').trim()
  if (!u) return '暂无通俗用法说明，可点击下方查看专业内容。'
  const doseMatch = u.match(/(\d[\d.～~\-至]*\s*(?:g|克|枚|片|粒))/)
  const dose = doseMatch ? doseMatch[1] : ''
  const method = u
    .replace(/^\d[\d.～~\-至]*\s*(?:g|克|枚|片|粒)\s*/i, '')
    .replace(/[，,、。;；]|$/, '')
  const parts = []
  if (dose) parts.push(`常规参考用量约 ${dose}`)
  if (method) parts.push(`服用时${method}`)
  return `${parts.length ? parts.join('，') : u}。以上为常规参考，具体请按医嘱或药师建议调整，如有不适及时停用。`
})

/** 白话：适合哪些人（贴合画像，通俗表达）。 */
const plainFit = computed(() => {
  const phrases = splitPhrases(props.herb.effects)
  const hint = phrases.length
    ? `常用于需要「${phrases.slice(0, 3).join('、')}」等调养需求的场景`
    : '常用于特定体质的日常调养参考'
  const base = `是否适合需结合个人体质与医师建议判断，${hint}，但不能仅凭一句描述自行对号入座。`
  if (props.herb.safety_level === '普通') return `${base}健康人群一般可在专业人士指导下尝试。`
  if (props.herb.safety_level === '慎用') return `${base}体质敏感、孕妇儿童及慢性病患者尤其需先咨询医师。`
  return `${base}本品属高风险药材，务必先经执业医师评估，切勿自行尝试。`
})

/** 白话：哪些人要小心（禁忌生活化）。 */
const plainNotice = computed(() => {
  const c = (props.herb.contraindications || '').trim()
  if (!c) return '未标注特殊禁忌，但仍建议遵医嘱使用，不宜自行长期服用。'
  return `以下人群需特别留意：${c}。若不确属禁忌范围，也建议在医师指导下使用。`
})

/** 切换专业卡展开。 */
function togglePro() {
  showPro.value = !showPro.value
}
</script>

<template>
  <div class="space-y-3">
    <!-- 白话科普卡 -->
    <section
      class="overflow-hidden rounded-xl p-5"
      :style="{ backgroundColor: safetyMeta.bg }"
    >
      <!-- 安全等级色条 -->
      <div class="flex items-center gap-2">
        <span
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-white"
          :style="{ backgroundColor: safetyMeta.color }"
        >
          <van-icon :name="safetyMeta.icon" size="14" />
          {{ safetyMeta.label }}
        </span>
      </div>

      <!-- 毒性强制警示条（不可折叠隐藏） -->
      <div
        v-if="herb.safety_level === '毒性'"
        class="danger-breathe mt-3 rounded-xl border border-cinnabar/40 bg-paper-card/80 p-3.5"
      >
        <div class="flex items-center gap-2">
          <van-icon name="warning-o" size="18" color="#C0392B" />
          <p class="text-sm font-bold text-cinnabar">高风险警示</p>
        </div>
        <p class="mt-1.5 text-xs leading-relaxed text-ink">
          该药材含毒性成分，使用不当可能危及健康。请务必在专业医师指导下使用，严格控制剂量与煎煮方法，切勿自行服用。
        </p>
      </div>

      <!-- 白话内容 -->
      <div class="mt-4 space-y-3">
        <div class="flex items-start gap-2.5">
          <van-icon name="fire-o" size="18" color="#2D6B4F" class="mt-0.5 shrink-0" />
          <p class="text-sm leading-relaxed text-ink">
            <span class="font-semibold text-primary">它有什么用：</span>{{ plainUse }}
          </p>
        </div>
        <div class="flex items-start gap-2.5">
          <van-icon name="clock-o" size="18" color="#2D6B4F" class="mt-0.5 shrink-0" />
          <p class="text-sm leading-relaxed text-ink">
            <span class="font-semibold text-primary">该怎么用：</span>{{ plainUsage }}
          </p>
        </div>
        <div class="flex items-start gap-2.5">
          <van-icon name="like-o" size="18" color="#2D6B4F" class="mt-0.5 shrink-0" />
          <p class="text-sm leading-relaxed text-ink">
            <span class="font-semibold text-primary">适合哪些人：</span>{{ plainFit }}
          </p>
        </div>
        <div class="flex items-start gap-2.5">
          <van-icon name="friends-o" size="18" color="#2D6B4F" class="mt-0.5 shrink-0" />
          <p class="text-sm leading-relaxed text-ink">
            <span class="font-semibold text-primary">哪些人要小心：</span>{{ plainNotice }}
          </p>
        </div>
        <p class="pt-1 text-xs leading-relaxed text-ink-secondary/80">安全提示：{{ safetyTip(herb.safety_level) }}</p>
      </div>
    </section>

    <!-- 专业药典卡（点击展开/收起） -->
    <section class="overflow-hidden rounded-xl bg-paper-card shadow-paper">
      <button
        type="button"
        class="flex w-full items-center justify-between px-5 py-4 text-left transition active:bg-paper"
        @click="togglePro"
      >
        <span class="flex items-center gap-2">
          <van-icon name="bookmark-o" size="18" color="#2D6B4F" />
          <span class="text-sm font-semibold text-ink">查看专业内容（药典）</span>
        </span>
        <van-icon
          name="arrow-down"
          size="16"
          color="#4A4A4A"
          class="transition-transform duration-200"
          :class="{ 'rotate-180': showPro }"
        />
      </button>

      <transition
        enter-active-class="transition-[max-height,opacity] duration-300 ease-out"
        enter-from-class="max-h-0 opacity-0"
        enter-to-class="max-h-[2000px] opacity-100"
        leave-active-class="transition-[max-height,opacity] duration-200 ease-in"
        leave-from-class="max-h-[2000px] opacity-100"
        leave-to-class="max-h-0 opacity-0"
      >
        <div v-if="showPro" class="max-h-[2000px] space-y-3 px-5 pb-5">
          <div class="rounded-xl bg-paper p-3.5">
            <h4 class="mb-1 text-xs font-semibold text-primary">性味归经</h4>
            <p class="text-sm leading-relaxed text-ink">{{ herb.nature_flavor || '—' }}</p>
          </div>
          <div class="rounded-xl bg-paper p-3.5">
            <h4 class="mb-1 text-xs font-semibold text-primary">功效主治</h4>
            <p class="text-sm leading-relaxed text-ink">{{ herb.effects || '—' }}</p>
          </div>
          <div class="rounded-xl bg-paper p-3.5">
            <h4 class="mb-1 text-xs font-semibold text-primary">用法用量</h4>
            <p class="text-sm leading-relaxed text-ink">{{ herb.usage || '—' }}</p>
          </div>
          <div class="rounded-xl bg-paper p-3.5">
            <h4 class="mb-1 text-xs font-semibold text-primary">禁忌</h4>
            <p class="text-sm leading-relaxed text-ink">{{ herb.contraindications || '—' }}</p>
          </div>
          <div
            class="rounded-xl p-3.5"
            :class="herb.safety_level === '毒性' ? 'border border-cinnabar/40 bg-cinnabar/10' : 'bg-paper'"
          >
            <h4 class="mb-1 text-xs font-semibold" :class="herb.safety_level === '毒性' ? 'text-cinnabar' : 'text-primary'">
              毒性说明
            </h4>
            <p class="text-sm leading-relaxed text-ink">{{ herb.toxicity || '常规剂量下无毒。' }}</p>
          </div>
        </div>
      </transition>
    </section>
  </div>
</template>

<style scoped>
.danger-breathe {
  animation: danger-pulse 2s ease-in-out infinite;
}
@keyframes danger-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.18);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(229, 72, 77, 0.06);
  }
}
</style>
