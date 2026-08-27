<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { getHerb, addFavorite, removeFavorite, listFavorites } from '@/api/herb'

const route = useRoute()
const router = useRouter()

const herb = ref(null)
const loading = ref(true)
const isFavorite = ref(false)

const safetyMeta = computed(() => {
  const map = {
    普通: { color: '#2E7D52', bg: '#E6F4EC', label: '普通药材' },
    慎用: { color: '#F2A33C', bg: '#FDF3E4', label: '慎用' },
    毒性: { color: '#E5484D', bg: '#FDE9E9', label: '毒性药材 · 高风险' },
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
  <div class="page-container px-4 pb-28 pt-6">
    <!-- 顶部返回 -->
    <div class="mb-4 flex items-center gap-3">
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full bg-white shadow-sm active:scale-90"
        @click="router.back()"
      >
        <van-icon name="arrow-left" size="18" color="#1F2A24" />
      </button>
      <h1 class="text-[22px] font-semibold text-[#1F2A24]">药材详情</h1>
    </div>

    <div v-if="loading" class="py-20 text-center text-sm text-[#5B6B62]">加载中…</div>

    <template v-else-if="herb">
      <!-- 头部 -->
      <section
        class="flex items-center justify-between rounded-3xl p-5"
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
          class="flex h-10 w-10 items-center justify-center rounded-full bg-white/70 active:scale-90"
          :class="isFavorite ? 'text-[#E5484D]' : 'text-[#5B6B62]'"
          @click="toggleFavorite"
        >
          <van-icon :name="isFavorite ? 'like' : 'like-o'" size="22" />
        </button>
      </section>

      <!-- 来源标注 -->
      <p class="mt-3 text-right text-xs text-[#5B6B62]/70">
        数据来源：{{ herb.source || '未标注' }}
      </p>

      <!-- 知识卡片 -->
      <section class="mt-3 space-y-3">
        <div class="rounded-2xl bg-white p-4 shadow-sm">
          <h3 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">性味归经</h3>
          <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.nature_flavor }}</p>
        </div>
        <div class="rounded-2xl bg-white p-4 shadow-sm">
          <h3 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">功效主治</h3>
          <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.effects }}</p>
        </div>
        <div class="rounded-2xl bg-white p-4 shadow-sm">
          <h3 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">用法用量</h3>
          <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.usage }}</p>
        </div>
        <div class="rounded-2xl bg-white p-4 shadow-sm">
          <h3 class="mb-1.5 text-sm font-semibold text-[#2E7D52]">禁忌</h3>
          <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.contraindications }}</p>
        </div>
        <div
          class="rounded-2xl p-4 shadow-sm"
          :class="herb.safety_level === '毒性' ? 'border border-[#E5484D]/40 bg-[#FDE9E9]' : 'bg-white'"
        >
          <h3 class="mb-1.5 text-sm font-semibold" :class="herb.safety_level === '毒性' ? 'text-[#E5484D]' : 'text-[#2E7D52]'">
            毒性说明
          </h3>
          <p class="text-sm leading-relaxed text-[#1F2A24]">{{ herb.toxicity || '常规剂量下无毒。' }}</p>
        </div>
      </section>

      <p class="mt-6 text-center text-xs leading-relaxed text-[#5B6B62]/70">
        本内容仅供参考，不构成医疗建议。用药请遵医嘱。
      </p>
    </template>
  </div>
</template>
