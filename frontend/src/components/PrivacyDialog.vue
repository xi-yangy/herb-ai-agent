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

/** 暂不授权：不写入拒绝态，拍照时放行交给浏览器按需请求权限。 */
function decline() {
  emit('result', { consent: false })
  emit('update:show', false)
}
</script>

<template>
  <van-popup
    :show="show"
    position="center"
    closeable
    :close-on-click-overlay="false"
    class="privacy-popup"
  >
    <div class="px-6 pb-8 pt-6">
      <h2 class="section-title text-center text-lg text-ink">隐私与权限说明</h2>
      <p class="mt-2 text-center text-xs leading-relaxed text-ink-secondary">
        为了正常使用拍照识别功能，我们需要你了解以下权限用途与数据规则
      </p>

      <!-- 权限条目 -->
      <div class="mt-5 space-y-3">
        <div
          v-for="item in items"
          :key="item.title"
          class="flex items-start gap-3 rounded-xl bg-paper p-3.5"
        >
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary">
            <van-icon :name="item.icon" size="18" color="#fff" />
          </span>
          <div>
            <p class="text-sm font-semibold text-ink">{{ item.title }}</p>
            <p class="mt-0.5 text-xs leading-relaxed text-ink-secondary">{{ item.desc }}</p>
          </div>
        </div>
      </div>

      <!-- 数据规则 -->
      <div class="mt-4 rounded-xl border border-primary/20 bg-primary/10 p-3.5">
        <p class="text-xs font-semibold text-primary">图片数据使用规则</p>
        <p class="mt-1 text-xs leading-relaxed text-ink-secondary">
          你上传的图片仅用于本次识别与历史记录回看：图片保存在你本机浏览器中，清空历史或清除浏览器数据即删除；服务端不持久化原始图片，不用于模型训练。
        </p>
      </div>

      <button
        type="button"
        class="btn-primary mt-6 w-full"
        @click="agree"
      >
        同意并继续
      </button>
      <button
        type="button"
        class="btn-outline mt-3 w-full"
        @click="decline"
      >
        暂不授权，稍后需要时再开启
      </button>
    </div>
  </van-popup>
</template>

<style scoped>
.privacy-popup {
  width: 480px;
  max-width: 90vw;
  border-radius: 16px;
  max-height: 82vh;
  overflow-y: auto;
}
</style>
