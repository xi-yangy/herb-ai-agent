<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { createHistory, addFavorite, removeFavorite, listFavorites, listHistory, getHerb } from '@/api/herb'
import { saveImage, getImage } from '@/utils/imageStore'
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

// 安全等级样式映射（国风语义色）
const safetyMeta = computed(() => {
  const map = {
    普通: { color: '#4A7C59', bg: '#EAF1EC', label: '普通药材', tip: '常规使用相对安全，仍建议按剂量服用' },
    慎用: { color: '#C08A3E', bg: '#F7EFDF', label: '慎用', tip: '需谨慎使用，特定人群应避免或减量' },
    毒性: { color: '#C0392B', bg: '#FAE9E7', label: '毒性药材 · 高风险', tip: '含有毒性成分，务必遵医嘱并严格按剂量使用' },
  }
  const level = result.value?.safety_level || ''
  return map[level] || map.普通
})

const herb = computed(() => result.value?.herb || null)

// 识别通道可读文案映射
const channelLabel = computed(() => {
  const map = {
    local: '本地识别',
    baidu: '百度识别',
    mock: '演示数据',
  }
  return map[result.value?.channel] || '未知通道'
})

// 是否低置信度（后端判定：不直接给结论，改判相似品种 + 引导重拍）
const lowConfidence = computed(() => !!result.value?.low_confidence)
// 相似品种候选列表
const similarList = computed(() => result.value?.similar || [])
// 是否未识别（本地拒识回退百度后仍无植物结果：展示"未识别/疑似非药材"引导，不呈现药材信息）
const unrecognized = computed(() => !!result.value?.unrecognized)

// 鉴别防雷警报：识别命中配置了防雷字段的药材时，顶部弹出防雷警报卡
// 仅当 herb 已收录知识库且 warning.label 非空时展示，避免低置信/未收录误触发
const warning = computed(() => {
  const w = result.value?.warning
  if (!result.value?.herb || !w || !w.label) return null
  return w
})

// 从防雷标签（如"易与枯矾混淆"）中提取混淆品种名，用于放大高亮展示
const confusionName = computed(() => warning.value?.label?.match(/易与(.+)混淆/)?.[1] || '')

// 「重新拍摄」：清空当前识别并返回首页（相机/相册入口）
function retake() {
  store.clearRecognition()
  router.push({ name: 'home' })
}

/** 相似品种安全等级小标签样式。 */
function similarTagMeta(level) {
  const map = {
    普通: { color: '#4A7C59', bg: '#EAF1EC' },
    慎用: { color: '#C08A3E', bg: '#F7EFDF' },
    毒性: { color: '#C0392B', bg: '#FAE9E7' },
  }
  return map[level] || map.普通
}

// 是否未收录本地知识库（无本地详情）
const notInKb = computed(() => !!result.value && !result.value.herb)

// 初始化：识别进入优先读 store，否则按 herbId 从知识库取（简单场景从 store/query）
onMounted(async () => {
  // 从历史记录回看：按 historyId 取本地原图 + 历史结果组装展示（不重复写历史）
  if (route.query.historyId) {
    await loadFromHistory(Number(route.query.historyId))
    return
  }

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

/** 识别成功后写一条历史，并把原图存入本机 IndexedDB 供历史页回看；未识别结果不写历史。 */
async function writeHistory(r) {
  if (!r || r.unrecognized) return
  try {
    const record = await createHistory({
      result_name: r.name,
      confidence: r.confidence,
      channel: r.channel || 'mock',
      herb_id: r.herb?.id ?? null,
    })
    // 识别原图仅保存在本机浏览器（服务端不保存图片）；失败静默降级，不影响历史写入
    if (record?.id) saveImage(record.id, image.value)
  } catch (err) {
    console.error('[history]', err)
  }
}

/** 从历史记录回看：取本地原图（IndexedDB）+ 历史结果 + 药材详情组装展示。 */
async function loadFromHistory(historyId) {
  try {
    const list = await listHistory()
    const item = list.find((h) => h.id === historyId)
    if (!item) {
      showToast('未找到该条识别记录')
      return
    }
    image.value = (await getImage(item.id)) || ''
    let herb = null
    if (item.herb_id) {
      try {
        herb = await getHerb(item.herb_id)
      } catch (err) {
        console.warn('[history replay] 药材详情加载失败', err)
      }
    }
    result.value = {
      name: item.result_name,
      confidence: item.confidence,
      safety_level: herb?.safety_level || '普通',
      channel: item.channel || 'mock',
      similar: [],
      low_confidence: (item.confidence ?? 0) < 0.6,
      unrecognized: false,
      herb,
    }
    // 收藏态由 watch(result) 自动同步
  } catch (err) {
    console.error('[history replay]', err)
    showToast('历史记录加载失败')
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

/** 返回首页：清除识别状态后直接跳转（顶部悬浮按钮与底部按钮共用，不弹确认框）。 */
function onClearRecognition() {
  store.clearRecognition()
  router.push({ name: 'home' })
}

</script>

<template>
  <div class="page-container px-6 pb-12 pt-4">
    <div class="mx-auto max-w-[860px]">
    <!-- 固定悬浮返回按钮：滑动时始终可见，点击直接返回首页（清除识别状态）；绿色系描边跟随主色，提升可发现性 -->
    <button
      type="button"
      aria-label="返回首页"
      class="fixed left-4 top-3 z-50 flex h-9 w-9 items-center justify-center rounded-full border-2 border-primary/70 bg-primary/10 shadow-md shadow-primary/25 transition-colors duration-200 hover:bg-primary/15 active:scale-90"
      @click="onClearRecognition"
    >
      <van-icon name="arrow-left" size="18" color="#2D6B4F" />
    </button>

    <!-- 鉴别防雷警报：识别命中易混淆高危药材时，顶部内嵌醒目警报卡 -->
    <section
      v-if="warning"
      class="anti-deception-card mt-1 overflow-hidden rounded-2xl border border-cinnabar/30 bg-gradient-to-br from-[#7A0C12] via-[#B4330F] to-[#E5484D] p-5 shadow-lg shadow-cinnabar/20"
    >
      <!-- 头部：警示图标 + 标题 -->
      <div class="flex items-center gap-3">
        <div class="deception-halo relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-white/15">
          <van-icon name="shield-o" size="26" color="#FFF" />
        </div>
        <div>
          <h2 class="section-title text-lg leading-tight text-white">鉴别防雷警报</h2>
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
          <span class="text-xs text-white/70">易混淆高危品种</span>
          <!-- 混淆提醒：居中焦点 -->
          <div class="mt-2 text-center">
            <span
              v-if="confusionName"
              class="confusion-badge inline-flex items-center gap-1 rounded-full bg-cinnabar px-4 py-1.5 text-lg font-bold text-white"
            >
              <van-icon name="warning-o" size="18" />
              易与「<span class="text-[22px] text-amber-300">{{ confusionName }}</span>」混淆
            </span>
            <span
              v-else
              class="confusion-badge inline-flex items-center rounded-full bg-cinnabar px-4 py-1.5 text-lg font-bold text-white"
            >
              {{ warning.label }}
            </span>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-white/95">{{ warning.message }}</p>
        </div>
      </div>

      <!-- 安全提示区 -->
      <div class="mt-3 rounded-xl border border-amber-300/60 bg-amber-100/95 px-3.5 py-3">
        <p class="text-xs leading-relaxed text-amber-900">
          <van-icon name="warning-o" size="14" class="mr-1 align-[-2px]" />
          高危易混淆，宁严勿松。切勿仅凭外观自行采摘、辨认或服用，请交由专业药师/医师核对。
        </p>
      </div>

      <!-- 免责声明 -->
      <p class="mt-3 text-center text-[11px] leading-relaxed text-white/55">
        本辨析信息仅供参考，不构成诊断或处方，如有不适请咨询执业医师/药师。
      </p>
    </section>

    <!-- 未识别 / 疑似非药材：本地拒识回退百度后仍无植物结果时展示，不呈现任何药材信息 -->
    <section
      v-if="unrecognized"
      class="mt-1 overflow-hidden rounded-2xl border border-ochre/40 bg-ochre/10 p-5"
    >
      <div class="flex items-center gap-3">
        <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-ochre/15">
          <van-icon name="question-o" size="26" color="#C08A3E" />
        </div>
        <div>
          <h2 class="section-title text-lg leading-tight text-ochre">未能识别出药材</h2>
          <p class="mt-0.5 text-xs text-ink-secondary">该图片可能不是中草药，或拍摄效果不佳</p>
        </div>
      </div>

      <p class="mt-4 text-xs leading-relaxed text-ink-secondary">
        系统未能在图片中确认到可信的中草药品种。请确认拍摄对象为药材本身，并保证光线充足、
        主体清晰、避开杂物；若非药材图片，可忽略本结果。
      </p>

      <button type="button" class="btn-primary mt-4 w-full" @click="retake">
        <van-icon name="photograph" size="16" class="align-[-2px]" />
        重新拍摄
      </button>

      <p class="mt-3 text-center text-xs leading-relaxed text-ink-secondary/70">
        本结果为软件自动识别，仅供参考，不构成诊断或处方建议。
      </p>
    </section>

    <!-- 顶部安全等级色条（未识别时不展示） -->
    <div
      v-if="!unrecognized"
      class="flex items-center gap-3 rounded-xl px-4 py-3.5"
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
        <p class="mt-0.5 text-xs text-ink-secondary">{{ safetyMeta.tip }}</p>
      </div>
    </div>

    <!-- 低置信度降级：相似品种 + 引导重拍（PRD 硬性要求：低于阈值不直接给结论） -->
    <section
      v-if="lowConfidence && !unrecognized"
      class="mt-5 rounded-xl border border-ochre/40 bg-ochre/10 p-4"
    >
      <div class="flex items-center gap-2">
        <van-icon name="warning-o" size="20" color="#C08A3E" />
        <h2 class="text-sm font-bold text-ochre">识别置信度较低，请核对</h2>
      </div>
      <p class="mt-2 text-xs leading-relaxed text-ink-secondary">
        系统未能高置信度确认该药材，以下为相似品种候选，请对照实物或调整拍摄后重试。
      </p>

      <ul v-if="similarList.length" class="mt-3 space-y-2">
        <li
          v-for="(item, idx) in similarList"
          :key="idx"
          class="flex items-center justify-between rounded-xl bg-paper-card px-3 py-2.5"
        >
          <span class="text-sm font-medium text-ink">{{ item.name }}</span>
          <span class="flex items-center gap-2">
            <span
              class="rounded px-1.5 py-0.5 text-[11px]"
              :style="{ color: similarTagMeta(item.safety_level).color, backgroundColor: similarTagMeta(item.safety_level).bg }"
            >
              {{ item.safety_level }}
            </span>
            <span class="text-xs text-ink-secondary">
              {{ ((item.confidence || 0) * 100).toFixed(0) }}%
            </span>
          </span>
        </li>
      </ul>

      <button
        type="button"
        class="btn-primary mt-4 w-full"
        @click="retake"
      >
        <van-icon name="photograph" size="16" class="align-[-2px]" />
        重新拍摄
      </button>
      <p class="mt-3 text-center text-xs leading-relaxed text-ink-secondary/70">
        本结果为软件自动识别，仅供参考，不构成诊断或处方建议。
      </p>
    </section>

    <!-- 药材主体（未识别时不展示） -->
    <section v-if="!unrecognized" class="card-paper mt-5 overflow-hidden">
      <!-- 图片预览 -->
      <div v-if="image" class="flex h-52 items-center justify-center bg-paper">
        <img :src="image" alt="识别图片" class="h-full w-full object-cover" />
      </div>

      <div class="p-5">
        <div class="flex items-start justify-between">
          <div>
            <h1 class="section-title text-[22px] text-ink">{{ result?.name || '识别中…' }}</h1>
            <p class="mt-1 text-xs text-ink-secondary">
              置信度 {{ ((result?.confidence || 0) * 100).toFixed(0) }}% ·
              识别通道 {{ channelLabel }}
            </p>
          </div>
          <button
            type="button"
            class="flex h-10 w-10 items-center justify-center rounded-full transition active:scale-90"
            :class="isFavorite ? 'text-cinnabar' : 'text-ink-faint'"
            @click="toggleFavorite"
          >
            <van-icon :name="isFavorite ? 'like' : 'like-o'" size="22" />
          </button>
        </div>

        <!-- 已收录：展示描述；未收录：降级提示 -->
        <p v-if="herb" class="mt-2 text-sm leading-relaxed text-ink-secondary">
          {{ herb.description || result.name + '：请以知识库详情为准。' }}
        </p>
        <div v-else-if="notInKb" class="mt-3 rounded-xl bg-ochre/10 p-3 text-xs leading-relaxed text-ochre">
          识别到「{{ result?.name }}」，但该品种暂未收录本地知识库。识别结果仅供参考，请勿作为用药依据。
        </div>

        <button
          v-if="herb"
          type="button"
          class="btn-outline mt-4 w-full"
          @click="goDetail"
        >
          查看完整药材详情
        </button>
      </div>
    </section>

    <!-- 分层信息卡（F5：白话科普 + 专业药典折叠） -->
    <LayeredInfoCard v-if="herb && !unrecognized" :herb="herb" class="mt-5" />

    <!-- 多模态追问（F12/F13：常驻文本/语音问答 + 分组快捷词包，Qwen 真实调用 + 知识库降级；带图时走视觉图文问答） -->
    <QaPanel v-if="!unrecognized" :herb="herb" :result-name="result?.name" :image="image" class="mt-5" />

    <!-- 医疗免责声明 -->
    <p class="mt-6 text-center text-xs leading-relaxed text-ink-secondary/70">
      本结果为软件自动识别，仅供参考，不构成医疗建议。<br />
      如身体不适请及时就医，遵医嘱用药。
    </p>

    <!-- 返回 -->
    <button
      type="button"
      class="btn-outline mt-6 w-full"
      @click="onClearRecognition"
    >
      返回首页
    </button>
    </div>
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

/* 警示图标呼吸辉光（高危场景保留） */
.deception-halo {
  box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.45);
  animation: deception-halo-breathe 1.8s ease-in-out infinite;
}

/* 混淆提醒徽标：轻微泛光提升视觉权重 */
.confusion-badge {
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  box-shadow: 0 0 14px rgba(229, 72, 77, 0.55);
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
