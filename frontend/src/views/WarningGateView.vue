<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const store = useAppStore()

// 读取待确认的危险药材信息（识别结果）
const danger = computed(() => {
  const result = store.lastRecognition?.result
  if (!result) return null
  return {
    name: result.name,
    safety_level: result.safety_level,
    toxicity: result.herb?.toxicity || '',
    contraindications: result.herb?.contraindications || '',
  }
})

/** 用户确认了解风险后，携带确认标记进入结果页（避免再次触发警示）。 */
function confirm() {
  router.replace({ name: 'result', query: { confirmed: '1' } })
}
</script>

<template>
  <!-- 强制全屏警示：无关闭、无返回、无跳过入口 -->
  <div class="warning-screen flex min-h-screen flex-col items-center justify-center px-6 py-12">
    <!-- 顶部警示标题 -->
    <div class="mb-6 flex flex-col items-center">
      <div class="danger-halo relative flex h-24 w-24 items-center justify-center rounded-full">
        <van-icon name="warning-o" size="52" color="#FFF" />
      </div>
      <h1 class="mt-6 text-center text-[24px] font-bold leading-tight text-white">
        高危药材警示
      </h1>
      <p class="mt-2 text-center text-sm text-white/80">识别到高风险药材，请务必谨慎对待</p>
    </div>

    <!-- 危险信息面板（玻璃拟态） -->
    <section class="danger-glass w-full max-w-md rounded-3xl p-6">
      <div class="flex items-center justify-between">
        <span class="rounded-full bg-[#E5484D]/90 px-3 py-1 text-xs font-semibold text-white">
          毒性药材 · 高风险
        </span>
        <span class="text-lg font-bold text-[#FFD7D9]">{{ danger?.name || '未知药材' }}</span>
      </div>

      <div class="mt-4 space-y-4">
        <div v-if="danger?.toxicity" class="rounded-2xl bg-black/15 p-4">
          <h2 class="text-sm font-bold text-[#FFD7D9]">毒性说明</h2>
          <p class="mt-1.5 text-sm leading-relaxed text-white/95">{{ danger.toxicity }}</p>
        </div>
        <div v-if="danger?.contraindications" class="rounded-2xl bg-black/15 p-4">
          <h2 class="text-sm font-bold text-[#FFD7D9]">禁忌提示</h2>
          <p class="mt-1.5 text-sm leading-relaxed text-white/95">{{ danger.contraindications }}</p>
        </div>
        <div class="rounded-2xl bg-black/15 p-4">
          <h2 class="text-sm font-bold text-[#FFD7D9]">特别提醒</h2>
          <p class="mt-1.5 text-sm leading-relaxed text-white/95">
            该药材可能含有毒性成分，使用不当可危及健康。切勿自行采摘、服用或加工。如已接触，请立即寻求专业医疗帮助。
          </p>
        </div>
      </div>
    </section>

    <!-- 唯一确认按钮（无关闭/跳过入口） -->
    <button
      type="button"
      class="danger-confirm mt-8 w-full max-w-md rounded-xl py-4 text-base font-bold text-[#7A0C12] transition active:scale-95"
      @click="confirm"
    >
      我已了解风险
    </button>

    <!-- 底部免责声明 -->
    <p class="mt-6 text-center text-xs leading-relaxed text-white/60">
      本识别结果仅供参考，不构成诊断或处方，如有不适请咨询执业医师/药师。
    </p>
  </div>
</template>

<style scoped>
/* 沉浸式深红警示背景 + 呼吸辉光 */
.warning-screen {
  background: radial-gradient(circle at 50% 30%, #7a1620 0%, #2a0e10 75%);
}

.danger-halo {
  background: #e5484d;
  box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.6);
  animation: halo-breathe 1.6s ease-in-out infinite;
}

@keyframes halo-breathe {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.55);
  }
  50% {
    box-shadow: 0 0 0 18px rgba(229, 72, 77, 0);
  }
}

.danger-glass {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(12px);
}

.danger-confirm {
  background: linear-gradient(180deg, #ffd7d9 0%, #ff9aa0 100%);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}
</style>
