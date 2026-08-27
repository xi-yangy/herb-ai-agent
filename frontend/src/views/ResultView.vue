<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { createHistory, addFavorite, removeFavorite, listFavorites } from '@/api/herb'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

// 支持两种进入方式：识别后直接进入（读 store）或从历史/收藏点入（读 route.query 的 herbId）
const herbId = ref(null)
const image = ref('')
const result = ref(null)
const loading = ref(false)
const isFavorite = ref(false)

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

const safetyLevel = computed(() => result.value?.safety_level || '')
const herb = computed(() => result.value?.herb || null)

// 识别通道可读文案映射
const channelLabel = computed(() => {
  const map = {
    local: '本地模型识别',
    baidu: '百度识别',
    mock: '模拟识别',
  }
  return map[result.value?.channel] || result.value?.channel || '未知通道'
})

// 是否低置信度（后端判定：不直接给结论，改判相似品种 + 引导重拍）
const lowConfidence = computed(() => !!result.value?.low_confidence)
// 相似品种候选列表
const similarList = computed(() => result.value?.similar || [])

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
</script>

<template>
  <div class="page-container px-4 pb-28 pt-6">
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

    <!-- 知识卡片 -->
    <section v-if="herb" class="mt-5 space-y-3">
      <div class="rounded-2xl bg-white p-4 shadow-sm">
        <h2 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">性味归经</h2>
        <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.nature_flavor }}</p>
      </div>
      <div class="rounded-2xl bg-white p-4 shadow-sm">
        <h2 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">功效主治</h2>
        <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.effects }}</p>
      </div>
      <div class="rounded-2xl bg-white p-4 shadow-sm">
        <h2 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">用法用量</h2>
        <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.usage }}</p>
      </div>
    </section>

    <!-- 高危警示（毒性药材） -->
    <section
      v-if="safetyLevel === '毒性'"
      class="danger-breathe mt-5 rounded-2xl border border-[#E5484D]/40 bg-[#FDE9E9] p-4"
    >
      <div class="flex items-center gap-2">
        <van-icon name="warning-o" size="20" color="#E5484D" />
        <h2 class="text-sm font-bold text-[#E5484D]">高风险警示</h2>
      </div>
      <p class="mt-2 text-sm leading-relaxed text-[#1F2A24]">
        该药材含毒性成分，使用不当可能危及健康。请务必在专业医师指导下使用，严格控制剂量与煎煮方法，切勿自行服用。
      </p>
      <p class="mt-2 rounded-xl bg-white/70 p-2.5 text-xs leading-relaxed text-[#5B6B62]">
        {{ herb?.toxicity || '毒性信息详见详情页。' }}
      </p>
    </section>

    <!-- 慎用警示 -->
    <section
      v-else-if="safetyLevel === '慎用'"
      class="mt-5 rounded-2xl border border-[#F2A33C]/40 bg-[#FDF3E4] p-4"
    >
      <div class="flex items-center gap-2">
        <van-icon name="info-o" size="20" color="#F2A33C" />
        <h2 class="text-sm font-bold text-[#E08600]">谨慎使用</h2>
      </div>
      <p class="mt-2 text-sm leading-relaxed text-[#1F2A24]">{{ herb?.contraindications }}</p>
    </section>

    <!-- 禁忌与毒性 -->
    <section v-if="herb" class="mt-5 rounded-2xl bg-white p-4 shadow-sm">
      <h2 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">禁忌</h2>
      <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.contraindications }}</p>
    </section>

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
