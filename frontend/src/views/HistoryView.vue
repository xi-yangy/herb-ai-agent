<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'

import { listHistory, clearHistory } from '@/api/herb'
import { getImage, clearImages } from '@/utils/imageStore'

const router = useRouter()
const history = ref([])
// 历史记录 id -> 本地识别图（IndexedDB 读取；无图时为 null，回落图标展示）
const imageMap = ref({})
const loading = ref(true)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const list = await listHistory()
    history.value = list
    // 并行读取每条记录的本地原图，避免串行阻塞；无图返回 null 不影响列表
    const pairs = await Promise.all(list.map(async (item) => [item.id, await getImage(item.id)]))
    imageMap.value = Object.fromEntries(pairs)
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

/** 是否非植物（百度返回的非植物名称，严重度更高）。 */
function isNonPlant(item) {
  return (item.result_name || '').includes('非植物')
}

/**
 * 是否识别受限：非植物名称 / 低置信度（<0.6，与后端阈值一致）/ 未收录知识库。
 * 受限结果打上「识别受限」标记，提示用户谨慎采信，体现识别严谨度。
 */
function isLimited(item) {
  return isNonPlant(item) || (item.confidence ?? 0) < 0.6 || !item.herb_id
}

/** 点击历史条目：跳转结果页，展示当初上传的原图与识别结果回看。 */
function goReplay(item) {
  router.push({ name: 'result', query: { historyId: item.id } })
}

async function onClear() {
  if (history.value.length === 0) return
  await showConfirmDialog({ title: '清空历史', message: '确定清空全部识别历史吗？' }).then(
    async () => {
      try {
        await clearHistory()
        // 同步清除本机保存的识别图（IndexedDB），保证图片数据随历史一并删除
        await clearImages()
        history.value = []
        imageMap.value = {}
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
  <div class="page-container px-6 pb-12 pt-2" style="max-width: 900px; margin: 0 auto;">
    <header class="mb-5 flex items-center justify-between">
      <div>
        <h1 class="section-title text-[22px] text-ink">识别历史</h1>
        <p class="mt-1 text-sm text-ink-secondary">记录你的每一次识别</p>
      </div>
      <button
        v-if="history.length > 0"
        type="button"
        class="btn-ghost gap-1 text-xs"
        @click="onClear"
      >
        <van-icon name="delete-o" size="14" />
        清空
      </button>
    </header>

    <div v-if="loading" class="py-20 text-center text-sm text-ink-secondary">加载中…</div>

    <van-empty v-else-if="history.length === 0" description="暂无识别记录，去识别一株草药吧" />

    <div v-else class="space-y-3">
      <div
        v-for="(item, idx) in history"
        :key="item.id"
        class="slide-in flex cursor-pointer items-center gap-3 rounded-xl bg-paper-card px-5 py-4 shadow-paper transition active:bg-paper"
        :style="{ animationDelay: idx * 0.05 + 's' }"
        @click="goReplay(item)"
      >
        <!-- 实时上传识别图缩略图（本机 IndexedDB）；无图时回落图标 -->
        <img
          v-if="imageMap[item.id]"
          :src="imageMap[item.id]"
          :alt="item.result_name"
          loading="lazy"
          class="h-11 w-11 shrink-0 rounded-xl object-cover"
        />
        <div
          v-else
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
          :class="item.safety_level === '毒性' ? 'bg-cinnabar/10' : 'bg-primary/10'"
        >
          <van-icon name="medal-o" size="22" :color="item.safety_level === '毒性' ? '#C0392B' : '#2D6B4F'" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="flex flex-wrap items-center gap-x-2 text-base font-semibold text-ink">
            <span>{{ item.result_name }}</span>
            <span
              v-if="isLimited(item)"
              class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs leading-none"
              :class="isNonPlant(item) ? 'border-cinnabar/40 bg-cinnabar/10 text-cinnabar' : 'border-ochre/40 bg-ochre/10 text-ochre'"
            >
              <van-icon name="warning-o" size="11" />
              识别受限
            </span>
          </p>
          <p class="mt-0.5 text-xs text-ink-secondary">
            {{ formatTime(item.created_at) }} · 置信度
            {{ ((item.confidence || 0) * 100).toFixed(0) }}%
          </p>
        </div>
        <van-icon name="arrow" color="#8C8C8C" />
      </div>
    </div>
  </div>
</template>
