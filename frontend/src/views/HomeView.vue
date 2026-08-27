<script setup>
import { onMounted, ref } from 'vue'
import { checkHealth } from '@/api/health'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const checking = ref(true)

onMounted(async () => {
  const online = await checkHealth()
  store.setBackendOnline(online)
  checking.value = false
})
</script>

<template>
  <div class="page-container px-4 py-6">
    <!-- 顶部标题 -->
    <header class="mb-8 text-center">
      <h1 class="text-xl font-semibold text-primary">中草药图像识别</h1>
      <p class="mt-2 text-sm text-gray-500">拍照或上传图片，快速识别中草药</p>
    </header>

    <!-- 后端连通状态 -->
    <div class="mb-6 flex items-center justify-center gap-2 text-sm">
      <span
        class="inline-block h-2.5 w-2.5 rounded-full"
        :class="store.backendOnline ? 'bg-primary' : 'bg-danger'"
      ></span>
      <span class="text-gray-500">
        {{ checking ? '检测中…' : store.backendOnline ? '服务正常' : '服务未连接' }}
      </span>
    </div>

    <!-- 识别入口（占位，后续接入拍照/相册） -->
    <div class="grid grid-cols-2 gap-4">
      <button
        class="flex flex-col items-center justify-center gap-2 rounded-2xl bg-white py-8 shadow-sm transition active:scale-95"
        type="button"
      >
        <van-icon name="photograph" size="36" color="#2E7D32" />
        <span class="text-base font-medium">拍照识别</span>
        <span class="text-xs text-gray-400">即将上线</span>
      </button>
      <button
        class="flex flex-col items-center justify-center gap-2 rounded-2xl bg-white py-8 shadow-sm transition active:scale-95"
        type="button"
      >
        <van-icon name="photo" size="36" color="#2E7D32" />
        <span class="text-base font-medium">相册上传</span>
        <span class="text-xs text-gray-400">即将上线</span>
      </button>
    </div>

    <!-- 安全提示 -->
    <p class="mt-8 text-center text-xs text-gray-400">
      识别结果仅供参考，不构成诊断或处方建议
    </p>
  </div>
</template>
