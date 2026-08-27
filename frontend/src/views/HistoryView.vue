<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { listHistory, clearHistory } from '@/api/herb'

const router = useRouter()
const history = ref([])
const loading = ref(true)

onMounted(load)

async function load() {
  loading.value = true
  try {
    history.value = await listHistory()
  } catch (err) {
    console.error('[history]', err)
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

async function onClear() {
  if (history.value.length === 0) return
  await showConfirmDialog({ title: '清空历史', message: '确定清空全部识别历史吗？' }).then(
    async () => {
      try {
        await clearHistory()
        history.value = []
        showToast('已清空')
      } catch (err) {
        console.error('[clear history]', err)
        showToast('操作失败')
      }
    }
  )
}
</script>

<template>
  <div class="page-container px-4 pb-28 pt-6">
    <header class="mb-5 flex items-center justify-between">
      <div>
        <h1 class="text-[22px] font-semibold text-[#1F2A24]">识别历史</h1>
        <p class="mt-1 text-sm text-[#5B6B62]">记录你的每一次识别</p>
      </div>
      <button
        v-if="history.length > 0"
        type="button"
        class="flex items-center gap-1 rounded-full bg-white px-3 py-1.5 text-xs text-[#5B6B62] shadow-sm active:scale-95"
        @click="onClear"
      >
        <van-icon name="delete-o" size="14" />
        清空
      </button>
    </header>

    <div v-if="loading" class="py-20 text-center text-sm text-[#5B6B62]">加载中…</div>

    <van-empty v-else-if="history.length === 0" description="暂无识别记录，去识别一株草药吧" />

    <div v-else class="space-y-3">
      <div
        v-for="(item, idx) in history"
        :key="item.id"
        class="slide-in flex items-center gap-3 rounded-2xl bg-white p-4 shadow-sm"
        :style="{ animationDelay: idx * 0.05 + 's' }"
      >
        <div
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
          :class="item.safety_level === '毒性' ? 'bg-[#FDE9E9]' : 'bg-[#E6F4EC]'"
        >
          <van-icon name="medal-o" size="22" :color="item.safety_level === '毒性' ? '#E5484D' : '#2E7D52'" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-base font-semibold text-[#1F2A24]">{{ item.result_name }}</p>
          <p class="mt-0.5 text-xs text-[#5B6B62]">
            {{ formatTime(item.created_at) }} · 置信度
            {{ ((item.confidence || 0) * 100).toFixed(0) }}%
          </p>
        </div>
        <van-icon name="arrow" color="#C0C8C3" />
      </div>
    </div>
  </div>
</template>
