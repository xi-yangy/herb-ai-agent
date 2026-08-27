<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listFavorites } from '@/api/herb'

const router = useRouter()
const favoriteCount = ref(0)

onMounted(async () => {
  try {
    const favs = await listFavorites()
    favoriteCount.value = favs.length
  } catch (err) {
    console.error('[favorites]', err)
  }
})
</script>

<template>
  <div class="page-container px-4 pb-28 pt-6">
    <header class="mb-5">
      <h1 class="text-[22px] font-semibold text-[#1F2A24]">我的</h1>
      <p class="mt-1 text-sm text-[#5B6B62]">收藏与隐私设置</p>
    </header>

    <div class="overflow-hidden rounded-2xl bg-white shadow-sm">
      <button
        type="button"
        class="flex w-full items-center gap-3 px-4 py-4 text-left transition active:bg-[#F4F8F5]"
        @click="router.push({ name: 'favorites' })"
      >
        <span class="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#E6F4EC]">
          <van-icon name="like-o" size="20" color="#2E7D52" />
        </span>
        <span class="flex-1 text-sm font-medium text-[#1F2A24]">我的收藏</span>
        <span class="text-sm text-[#5B6B62]">{{ favoriteCount }} 味</span>
        <van-icon name="arrow" color="#C0C8C3" />
      </button>
    </div>

    <!-- 占位提示：登录/隐私第二批 -->
    <div class="mt-5 overflow-hidden rounded-2xl bg-white shadow-sm">
      <van-cell-group :border="false">
        <van-cell title="登录 / 注册" value="第二批" is-link />
        <van-cell title="隐私与授权" value="第二批" is-link />
      </van-cell-group>
    </div>

    <p class="mt-6 text-center text-xs text-[#5B6B62]/70">灵草 · 中草药识别智能体</p>
  </div>
</template>
