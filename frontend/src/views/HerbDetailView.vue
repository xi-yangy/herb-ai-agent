<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getHerb, addFavorite, removeFavorite, listFavorites } from '@/api/herb'
import LayeredInfoCard from '@/components/LayeredInfoCard.vue'
import QaPanel from '@/components/QaPanel.vue'

const route = useRoute()
const router = useRouter()

const herb = ref(null)
const loading = ref(true)
const isFavorite = ref(false)

const safetyMeta = computed(() => {
  const map = {
    普通: { color: '#4A7C59', bg: '#EAF1EC', label: '普通药材' },
    慎用: { color: '#C08A3E', bg: '#F7EFDF', label: '慎用' },
    毒性: { color: '#C0392B', bg: '#FAE9E7', label: '毒性药材 · 高风险' },
  }
  return map[herb.value?.safety_level || ''] || map.普通
})

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    herb.value = await getHerb(id)
    await checkFavorite(id)
  } catch (err) {
    console.error('[herb detail]', err)
    showToast('药材不存在')
  } finally {
    loading.value = false
  }
})

async function checkFavorite(id) {
  try {
    const list = await listFavorites()
    isFavorite.value = list.some((f) => f.herb_id === id)
  } catch (err) {
    console.error('[favorites]', err)
  }
}

async function toggleFavorite() {
  if (!herb.value) return
  try {
    if (isFavorite.value) {
      await removeFavorite(herb.value.id)
      isFavorite.value = false
      showToast('已取消收藏')
    } else {
      await addFavorite(herb.value.id)
      isFavorite.value = true
      showToast('已收藏')
    }
  } catch (err) {
    console.error('[favorite toggle]', err)
    showToast('操作失败')
  }
}
</script>

<template>
  <div class="page-container px-6 pb-12 pt-4">
    <div class="mx-auto max-w-[860px]">
    <!-- 顶部返回 -->
    <div class="mb-4 flex items-center gap-3">
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full bg-paper-card shadow-paper active:scale-90"
        @click="router.back()"
      >
        <van-icon name="arrow-left" size="18" color="#2A2A28" />
      </button>
      <h1 class="section-title text-[22px] text-ink">药材详情</h1>
    </div>

    <div v-if="loading" class="py-20 text-center text-sm text-ink-secondary">加载中…</div>

    <template v-else-if="herb">
      <!-- 头部 -->
      <section
        class="flex items-center justify-between rounded-xl p-5"
        :style="{ backgroundColor: safetyMeta.bg }"
      >
        <div>
          <h2 class="text-2xl font-bold" :style="{ color: safetyMeta.color }">{{ herb.name }}</h2>
          <span
            class="mt-2 inline-block rounded-full px-3 py-1 text-xs font-medium text-white"
            :style="{ backgroundColor: safetyMeta.color }"
          >
            {{ safetyMeta.label }}
          </span>
        </div>
        <button
          type="button"
          class="flex h-10 w-10 items-center justify-center rounded-full bg-paper-card/70 active:scale-90"
          :class="isFavorite ? 'text-cinnabar' : 'text-ink-secondary'"
          @click="toggleFavorite"
        >
          <van-icon :name="isFavorite ? 'like' : 'like-o'" size="22" />
        </button>
      </section>

      <!-- 来源标注 -->
      <p class="mt-3 text-right text-xs text-ink-secondary/70">
        数据来源：{{ herb.source || '未标注' }}
      </p>

      <!-- 分层信息卡（F5：白话科普 + 专业药典折叠） -->
      <LayeredInfoCard :herb="herb" class="mt-3" />

      <!-- 多模态追问（F12/F13：常驻文本/语音问答 + 分组快捷词包，Qwen 真实调用 + 知识库降级） -->
      <QaPanel :herb="herb" :result-name="herb.name" class="mt-5" />

      <p class="mt-6 text-center text-xs leading-relaxed text-ink-secondary/70">
        本内容仅供参考，不构成医疗建议。用药请遵医嘱。
      </p>
    </template>
    </div>
  </div>
</template>
