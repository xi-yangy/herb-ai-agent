<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { createHistory, addFavorite, removeFavorite, listFavorites } from '@/api/herb'
import { useAppStore } from '@/stores/app'
import LayeredInfoCard from '@/components/LayeredInfoCard.vue'
import QaPanel from '@/components/QaPanel.vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

// 支持两种进入方式：识别后直接进入（读 store）或从历史/收藏点入（读 route.query 的 herbId）
const herbId = ref(null)
const image = ref('')
const result = ref(null)
const loading = ref(false)
const isFavorite = ref(false)

// 多模态问答面板 ref：供「你可能会关心」预设问题桥接调用
const qaPanelRef = ref(null)

// 安全等级样式映射
const safetyMeta = computed(() => {
  const map = {
    普通: { color: '#2E7D52', bg: '#E6F4EC', label: '普通药材', tip: '常规使用相对安全，仍建议按剂量服用' },
    慎用: { color: '#F2A33C', bg: '#FDF3E4', label: '慎用', tip: '需谨慎使用，特定人群应避免或减量' },
    毒性: { color: '#E5484D', bg: '#FDE9E9', label: '毒性药材 · 高风险', tip: '含有毒性成分，务必遵医嘱并严格按剂量使用' },
  }
  const level = result.value?.safety_level || ''
  return map[level] || map.普通
})

const herb = computed(() => result.value?.herb || null)

// 识别通道可读文案映射
const channelLabel = computed(() => {
  const map = {
    baidu: '百度识别',
    mock: '模拟识别',
  }
  return map[result.value?.channel] || result.value?.channel || '未知通道'
})

// 是否低置信度（后端判定：不直接给结论，改判相似品种 + 引导重拍）
const lowConfidence = computed(() => !!result.value?.low_confidence)
// 相似品种候选列表
const similarList = computed(() => result.value?.similar || [])

// 鉴别防雷警报：识别命中配置了防雷字段的药材时，顶部弹出防雷警报卡
// 仅当 herb 已收录知识库且 warning.label 非空时展示，避免低置信/未收录误触发
const warning = computed(() => {
  const w = result.value?.warning
  if (!result.value?.herb || !w || !w.label) return null
  return w
})

// 「重新拍摄」：清空当前识别并返回首页（相机/相册入口）
function retake() {
  store.clearRecognition()
  router.push({ name: 'home' })
}

/** 相似品种安全等级小标签样式。 */
function similarTagMeta(level) {
  const map = {
    普通: { color: '#2E7D52', bg: '#E6F4EC' },
    慎用: { color: '#F2A33C', bg: '#FDF3E4' },
    毒性: { color: '#E5484D', bg: '#FDE9E9' },
  }
  return map[level] || map.普通
}

// 是否未收录本地知识库（无本地详情）
const notInKb = computed(() => !!result.value && !result.value.herb)

// 初始化：识别进入优先读 store，否则按 herbId 从知识库取（简单场景从 store/query）
onMounted(async () => {
  const storeResult = store.lastRecognition?.result
  const storeImage = store.lastRecognition?.imageBase64

  if (storeResult) {
    result.value = storeResult
    image.value = storeImage || ''
    herbId.value = storeResult.herb?.id ?? null

    // F4 高危强制警示：毒性药材且未确认时，先路由到强制全屏警示页（不可跳过）
    if (storeResult.safety_level === '毒性' && route.query.confirmed !== '1') {
      router.replace({ name: 'warning-gate' })
      return
    }

    await writeHistory(storeResult)
    // 保留 store 供返回首页时复用，不主动清除
  }
})

watch(result, (val) => {
  if (val?.herb?.id) {
    herbId.value = val.herb.id
    checkFavorite(val.herb.id)
  }
})

/** 识别成功后写一条历史。 */
async function writeHistory(r) {
  if (!r) return
  try {
    await createHistory({
      result_name: r.name,
      confidence: r.confidence,
      channel: r.channel || 'mock',
      herb_id: r.herb?.id ?? null,
    })
  } catch (err) {
    console.error('[history]', err)
  }
}

/** 查询当前药材是否已收藏。 */
async function checkFavorite(id) {
  try {
    const list = await listFavorites()
    isFavorite.value = list.some((f) => f.herb_id === id)
  } catch (err) {
    console.error('[favorites]', err)
  }
}

async function toggleFavorite() {
  if (!herbId.value) return
  try {
    if (isFavorite.value) {
      await removeFavorite(herbId.value)
      isFavorite.value = false
      showToast('已取消收藏')
    } else {
      await addFavorite(herbId.value)
      isFavorite.value = true
      showToast('已收藏')
    }
  } catch (err) {
    console.error('[favorite toggle]', err)
    showToast('操作失败')
  }
}

function goDetail() {
  if (herb.value?.id) router.push({ name: 'herb-detail', params: { id: herb.value.id } })
}

async function onClearRecognition() {
  await showConfirmDialog({
    title: '返回首页',
    message: '识别结果已写入历史，确定返回首页吗？',
  }).then(() => {
    store.clearRecognition()
    router.push({ name: 'home' })
  })
}

/**
 * 「你可能会关心」预设问题（prompt 按钮）→ 智能问答。
 * 先调用 QaPanel 的 askPreset 展开问答区并自动发送，
 * 再平滑滚动到问答面板顶部，让用户看到回答过程。
 */
function onPresetAsk(question) {
  if (!qaPanelRef.value) return
  // askPreset 内部先展开问答区（含过渡），再发送
  qaPanelRef.value.askPreset(question)
  // 展开动画约 300ms，待其展开后滚动定位到面板顶部
  setTimeout(() => {
    const el = qaPanelRef.value?.panelRef || null
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, 340)
}
</script>

<template>
  <div class="page-container px-4 pb-28 pt-6">
    <!-- 鉴别防雷警报：识别命中易混淆高危药材时，顶部内嵌醒目警报卡 -->
    <section
      v-if="warning"
      class="anti-deception-card mt-1 overflow-hidden rounded-3xl border border-[#E5484D]/30 bg-gradient-to-br from-[#7A0C12] via-[#B4330F] to-[#E5484D] p-5 shadow-lg shadow-[#E5484D]/20"
    >
      <!-- 头部：警示图标 + 标题 -->
      <div class="flex items-center gap-3">
        <div class="deception-halo relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/15">
          <van-icon name="shield-o" size="26" color="#FFF" />
        </div>
        <div>
          <h2 class="text-lg font-bold leading-tight text-white">鉴别防雷警报</h2>
          <p class="mt-0.5 text-xs text-white/75">该药材易与高危品种混淆，务必辨认后再使用</p>
        </div>
      </div>

      <!-- 药材辨析区：本药材 vs 易混淆高危品种 -->
      <div class="mt-4 space-y-2.5">
        <div class="flex items-center justify-between rounded-xl bg-white/10 px-3.5 py-2.5">
          <span class="text-xs text-white/70">本药材</span>
          <span class="rounded-full bg-white/20 px-2.5 py-0.5 text-sm font-semibold text-white">
            {{ warning.herb_name || result?.name }}
          </span>
        </div>
        <div class="rounded-xl bg-white/10 px-3.5 py-2.5">
          <div class="flex items-center justify-between">
            <span class="text-xs text-white/70">易混淆高危品种</span>
            <span class="rounded-full bg-[#E5484D] px-2.5 py-0.5 text-sm font-semibold text-white">
              {{ warning.label }}
            </span>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-white/95">{{ warning.message }}</p>
        </div>
      </div>

      <!-- 安全提示区 -->
      <div class="mt-3 rounded-xl border border-[#F2A33C]/40 bg-[#FDF3E4]/90 px-3.5 py-3">
        <p class="text-xs leading-relaxed text-[#B45309]">
          <van-icon name="warning-o" size="14" class="mr-1 align-[-2px]" />
          高危易混淆，宁严勿松。切勿仅凭外观自行采摘、辨认或服用，请交由专业药师/医师核对。
        </p>
      </div>

      <!-- 免责声明 -->
      <p class="mt-3 text-center text-[11px] leading-relaxed text-white/55">
        本辨析信息仅供参考，不构成诊断或处方，如有不适请咨询执业医师/药师。
      </p>
    </section>

    <!-- 顶部安全等级色条 -->
    <div
      class="flex items-center gap-3 rounded-2xl px-4 py-3.5"
      :style="{ backgroundColor: safetyMeta.bg }"
    >
      <span
        class="inline-block h-3 w-3 shrink-0 rounded-full"
        :style="{ backgroundColor: safetyMeta.color }"
      ></span>
      <div>
        <p class="text-sm font-semibold" :style="{ color: safetyMeta.color }">
          {{ safetyMeta.label }}
        </p>
        <p class="mt-0.5 text-xs" style="color: #5b6b62">{{ safetyMeta.tip }}</p>
      </div>
    </div>

    <!-- 低置信度降级：相似品种 + 引导重拍（PRD 硬性要求：低于阈值不直接给结论） -->
    <section
      v-if="lowConfidence"
      class="mt-5 rounded-2xl border border-[#F2A33C]/40 bg-[#FDF3E4] p-4"
    >
      <div class="flex items-center gap-2">
        <van-icon name="warning-o" size="20" color="#F2A33C" />
        <h2 class="text-sm font-bold text-[#B45309]">识别置信度较低，请核对</h2>
      </div>
      <p class="mt-2 text-xs leading-relaxed text-[#5B6B62]">
        系统未能高置信度确认该药材，以下为相似品种候选，请对照实物或调整拍摄后重试。
      </p>

      <ul v-if="similarList.length" class="mt-3 space-y-2">
        <li
          v-for="(item, idx) in similarList"
          :key="idx"
          class="flex items-center justify-between rounded-xl bg-white/80 px-3 py-2.5"
        >
          <span class="text-sm font-medium text-[#1F2A24]">{{ item.name }}</span>
          <span class="flex items-center gap-2">
            <span
              class="rounded px-1.5 py-0.5 text-[11px]"
              :style="{ color: similarTagMeta(item.safety_level).color, backgroundColor: similarTagMeta(item.safety_level).bg }"
            >
              {{ item.safety_level }}
            </span>
            <span class="text-xs text-[#5B6B62]">
              {{ ((item.confidence || 0) * 100).toFixed(0) }}%
            </span>
          </span>
        </li>
      </ul>

      <button
        type="button"
        class="mt-4 w-full rounded-2xl bg-[#2E7D52] py-3 text-sm font-medium text-white transition active:scale-95"
        @click="retake"
      >
        <van-icon name="photograph" size="16" class="mr-1 align-[-2px]" />
        重新拍摄
      </button>
      <p class="mt-3 text-center text-xs leading-relaxed text-[#5B6B62]/70">
        本结果为软件自动识别，仅供参考，不构成诊断或处方建议。
      </p>
    </section>

    <!-- 药材主体 -->
    <section class="mt-5 overflow-hidden rounded-3xl bg-white shadow-sm">
      <!-- 图片预览 -->
      <div v-if="image" class="flex h-52 items-center justify-center bg-[#F4F8F5]">
        <img :src="image" alt="识别图片" class="h-full w-full object-cover" />
      </div>

      <div class="p-5">
        <div class="flex items-start justify-between">
          <div>
            <h1 class="text-[22px] font-semibold text-[#1F2A24]">{{ result?.name || '识别中…' }}</h1>
            <p class="mt-1 text-xs text-[#5B6B62]">
              置信度 {{ ((result?.confidence || 0) * 100).toFixed(0) }}% ·
              识别通道 {{ channelLabel }}
            </p>
          </div>
          <button
            type="button"
            class="flex h-10 w-10 items-center justify-center rounded-full transition active:scale-90"
            :class="isFavorite ? 'text-[#E5484D]' : 'text-[#5B6B62]'"
            @click="toggleFavorite"
          >
            <van-icon :name="isFavorite ? 'like' : 'like-o'" size="22" />
          </button>
        </div>

        <!-- 已收录：展示描述；未收录：降级提示 -->
        <p v-if="herb" class="mt-2 text-sm leading-relaxed text-[#5B6B62]">
          {{ herb.description || result.name + '：请以知识库详情为准。' }}
        </p>
        <div v-else-if="notInKb" class="mt-3 rounded-xl bg-[#FDF3E4] p-3 text-xs leading-relaxed text-[#B45309]">
          识别到「{{ result?.name }}」，但该品种暂未收录本地知识库。识别结果仅供参考，请勿作为用药依据。
        </div>

        <button
          v-if="herb"
          type="button"
          class="mt-4 w-full rounded-2xl border border-[#2E7D52]/20 bg-white py-3 text-sm font-medium text-[#2E7D52] transition active:scale-95"
          @click="goDetail"
        >
          查看完整药材详情
        </button>
      </div>
    </section>

    <!-- 分层信息卡（F5：白话科普 + 专业药典折叠） -->
    <!-- @ask：「你可能会关心」预设问题 → 触发底部智能问答面板自动发送 -->
    <LayeredInfoCard v-if="herb" :herb="herb" class="mt-5" @ask="onPresetAsk" />

    <!-- 多模态追问（F12/F13：文本/语音问答，Qwen 真实调用 + 知识库降级；带图时走视觉图文问答） -->
    <QaPanel ref="qaPanelRef" :herb="herb" :result-name="result?.name" :image="image" class="mt-5" />

    <!-- 医疗免责声明 -->
    <p class="mt-6 text-center text-xs leading-relaxed text-[#5B6B62]/70">
      本结果为软件自动识别，仅供参考，不构成医疗建议。<br />
      如身体不适请及时就医，遵医嘱用药。
    </p>

    <!-- 返回 -->
    <button
      type="button"
      class="mt-6 w-full rounded-2xl bg-white py-3.5 text-sm font-medium text-[#2E7D52] shadow-sm transition active:scale-95"
      @click="onClearRecognition"
    >
      返回首页
    </button>
  </div>
</template>

<style scoped>
/* 鉴别防雷警报卡：进入动画（淡入 + 上移） */
.anti-deception-card {
  animation: deception-fade-in 0.5s ease-out both;
}

@keyframes deception-fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 警示图标呼吸辉光 */
.deception-halo {
  box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.45);
  animation: deception-halo-breathe 1.8s ease-in-out infinite;
}

@keyframes deception-halo-breathe {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.4);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(255, 255, 255, 0);
  }
}
</style>
