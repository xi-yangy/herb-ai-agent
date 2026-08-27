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

// 初始化：识别进入优先读 store，否则按 herbId 从知识库取（简单场景从 store/query）
onMounted(async () => {
  const storeResult = store.lastRecognition?.result
  const storeImage = store.lastRecognition?.imageBase64

  if (storeResult) {
    result.value = storeResult
    image.value = storeImage || ''
    herbId.value = storeResult.herb?.id ?? null
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
              识别通道 {{ result?.channel || 'mock' }}
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

        <p class="mt-2 text-sm leading-relaxed text-[#5B6B62]">
          {{ herb?.description || result?.name + '：请以知识库详情为准。' }}
        </p>

        <button
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
