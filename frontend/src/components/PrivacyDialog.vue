<script setup>
defineProps({
  show: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:show', 'result'])

/** 权限用途条目。 */
const items = [
  {
    icon: 'photograph',
    title: '相机',
    desc: '用于拍摄并识别中草药，仅在你主动拍摄时调用。',
  },
  {
    icon: 'photo',
    title: '相册',
    desc: '用于选择已保存的图片进行识别。',
  },
  {
    icon: 'mic',
    title: '麦克风',
    desc: '用于语音输入提问，仅在你主动点击语音按钮时调用。',
  },
]

/** 同意授权：全部授权为 true。 */
function agree() {
  emit('result', { consent: true })
  emit('update:show', false)
}

/** 暂不使用：全部授权为 false，进入降级模式。 */
function decline() {
  emit('result', { consent: false })
  emit('update:show', false)
}
</script>

<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    closeable
    :close-on-click-overlay="false"
    class="privacy-popup"
  >
    <div class="px-6 pb-8 pt-6">
      <h2 class="text-center text-lg font-semibold text-[#1F2A24]">隐私与权限说明</h2>
      <p class="mt-2 text-center text-xs leading-relaxed text-[#5B6B62]">
        为了正常使用拍照识别功能，我们需要你了解以下权限用途与数据规则
      </p>

      <!-- 权限条目 -->
      <div class="mt-5 space-y-3">
        <div
          v-for="item in items"
          :key="item.title"
          class="flex items-start gap-3 rounded-2xl bg-[#F4F8F5] p-3.5"
        >
          <span class="brand-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
            <van-icon :name="item.icon" size="18" color="#fff" />
          </span>
          <div>
            <p class="text-sm font-semibold text-[#1F2A24]">{{ item.title }}</p>
            <p class="mt-0.5 text-xs leading-relaxed text-[#5B6B62]">{{ item.desc }}</p>
          </div>
        </div>
      </div>

      <!-- 数据规则 -->
      <div class="mt-4 rounded-2xl border border-[#2E7D52]/20 bg-[#E6F4EC] p-3.5">
        <p class="text-xs font-semibold text-[#2E7D52]">图片数据使用规则</p>
        <p class="mt-1 text-xs leading-relaxed text-[#5B6B62]">
          你上传的图片仅用于本次识别，前端处理完成后即清除，服务端不持久化原始图片；不用于模型训练。
        </p>
      </div>

      <button
        type="button"
        class="brand-gradient mt-6 w-full rounded-2xl py-3.5 text-sm font-semibold text-white shadow-lg transition active:scale-95"
        @click="agree"
      >
        同意并继续
      </button>
      <button
        type="button"
        class="mt-3 w-full rounded-2xl border border-[#5B6B62]/20 bg-white py-3 text-sm font-medium text-[#5B6B62] transition active:scale-95"
        @click="decline"
      >
        暂不使用（降级模式）
      </button>
    </div>
  </van-popup>
</template>

<style scoped>
.privacy-popup {
  width: 100%;
  max-height: 82vh;
  overflow-y: auto;
}
</style>
