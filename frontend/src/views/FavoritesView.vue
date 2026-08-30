<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { listFavorites, removeFavorite, getHerb } from '@/api/herb'

const router = useRouter()
const favorites = ref([])
const loading = ref(true)

const safetyColor = { 普通: '#4A7C59', 慎用: '#C08A3E', 毒性: '#C0392B' }

onMounted(load)

async function load() {
  loading.value = true
  try {
    const favs = await listFavorites()
    // 逐个取药材详情（收藏表只存 id）
    const herbs = await Promise.all(
      favs.map(async (f) => {
        try {
          const herb = await getHerb(f.herb_id)
          return { favoriteId: f.id, ...herb }
        } catch (err) {
          console.error('[get herb]', err)
          return null
        }
      })
    )
    favorites.value = herbs.filter(Boolean)
  } catch (err) {
    console.error('[favorites]', err)
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

async function onRemove(fav) {
  try {
    await removeFavorite(fav.id)
    favorites.value = favorites.value.filter((h) => h.id !== fav.id)
    showToast('已取消收藏')
  } catch (err) {
    console.error('[remove favorite]', err)
    showToast('操作失败')
  }
}
</script>

<template>
  <div class="page-container px-6 pb-12 pt-2">
    <div class="mb-4 flex items-center gap-3">
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full border-2 border-primary/70 bg-primary/10 shadow-md shadow-primary/25 transition-colors duration-200 hover:bg-primary/15 active:scale-90"
        @click="router.back()"
      >
        <van-icon name="arrow-left" size="18" color="#2D6B4F" />
      </button>
      <h1 class="section-title text-[22px] text-ink">我的收藏</h1>
    </div>

    <div v-if="loading" class="py-20 text-center text-sm text-ink-secondary">加载中…</div>

    <van-empty v-else-if="favorites.length === 0" description="还没有收藏，去识别并收藏药材吧" />

    <div v-else class="space-y-3">
      <div
        v-for="(h, idx) in favorites"
        :key="h.id"
        class="slide-in flex items-center gap-3 rounded-xl bg-paper-card px-5 py-4 shadow-paper"
        :style="{ animationDelay: idx * 0.05 + 's' }"
      >
        <button
          type="button"
          class="min-w-0 flex-1 text-left"
          @click="router.push({ name: 'herb-detail', params: { id: h.id } })"
        >
          <p class="text-base font-semibold text-ink">{{ h.name }}</p>
          <p class="mt-1 line-clamp-1 text-xs text-ink-secondary">{{ h.nature_flavor }}</p>
        </button>
        <span
          class="shrink-0 rounded-full px-2.5 py-1 text-xs font-medium"
          :style="{
            color: safetyColor[h.safety_level] || '#4A7C59',
            backgroundColor: (safetyColor[h.safety_level] || '#4A7C59') + '1A',
          }"
        >
          {{ h.safety_level }}
        </span>
        <button
          type="button"
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-cinnabar/10 active:scale-90"
          @click="onRemove(h)"
        >
          <van-icon name="like" size="18" color="#C0392B" />
        </button>
      </div>
    </div>
  </div>
</template>
