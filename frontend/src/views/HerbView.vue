<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { listHerbs } from '@/api/herb'

const router = useRouter()
const herbs = ref([])
const loading = ref(true)

const safetyColor = { 普通: '#2E7D52', 慎用: '#F2A33C', 毒性: '#E5484D' }

onMounted(async () => {
  try {
    herbs.value = await listHerbs()
  } catch (err) {
    console.error('[herbs]', err)
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function goDetail(id) {
  router.push({ name: 'herb-detail', params: { id } })
}
</script>

<template>
  <div class="page-container px-4 pb-28 pt-6">
    <header class="mb-5">
      <h1 class="text-[22px] font-semibold text-[#1F2A24]">药材百科</h1>
      <p class="mt-1 text-sm text-[#5B6B62]">收录常见中草药，标注安全等级</p>
    </header>

    <div v-if="loading" class="py-20 text-center text-sm text-[#5B6B62]">加载中…</div>

    <van-empty v-else-if="herbs.length === 0" description="暂无药材数据" />

    <div v-else class="space-y-3">
      <button
        v-for="(h, idx) in herbs"
        :key="h.id"
        type="button"
        class="slide-in flex w-full items-center justify-between rounded-2xl bg-white p-4 text-left shadow-sm transition active:scale-95"
        :style="{ animationDelay: idx * 0.05 + 's' }"
        @click="goDetail(h.id)"
      >
        <div>
          <p class="text-base font-semibold text-[#1F2A24]">{{ h.name }}</p>
          <p class="mt-1 line-clamp-1 text-xs text-[#5B6B62]">{{ h.nature_flavor }}</p>
        </div>
        <span
          class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium"
          :style="{
            color: safetyColor[h.safety_level] || '#2E7D52',
            backgroundColor: (safetyColor[h.safety_level] || '#2E7D52') + '1A',
          }"
        >
          {{ h.safety_level }}
        </span>
      </button>
    </div>
  </div>
</template>
