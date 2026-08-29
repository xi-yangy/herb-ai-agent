<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { listFavorites } from '@/api/herb'
import { listConsents, updateConsent } from '@/api/privacy'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const store = useAppStore()

const favoriteCount = ref(0)
// 授权状态：{ camera, album, microphone }
const consents = ref({})
const showPrivacySheet = ref(false)

// 授权项定义
const consentMeta = [
  { key: 'camera', title: '相机', desc: '用于拍摄识别中草药' },
  { key: 'album', title: '相册', desc: '用于选择图片识别' },
  { key: 'microphone', title: '麦克风', desc: '用于语音输入提问' },
]

onMounted(load)

async function load() {
  try {
    const favs = await listFavorites()
    favoriteCount.value = favs.length
  } catch (err) {
    console.error('[favorites]', err)
  }
}

/** 加载授权状态并打开管理面板。 */
async function openPrivacy() {
  try {
    const list = await listConsents()
    const map = {}
    for (const c of list) map[c.consent_type] = c.granted
    consents.value = map
  } catch (err) {
    console.error('[consents]', err)
  }
  showPrivacySheet.value = true
}

/** 切换某一项授权。 */
async function toggleConsent(key, value) {
  try {
    await updateConsent(key, value)
    consents.value[key] = value
    if (key === 'camera' && !value) {
      showToast('关闭相机后无法拍照识别，可随时重新开启')
    }
  } catch (err) {
    console.error('[update consent]', err)
    showToast('操作失败')
  }
}

/** 退出登录。 */
async function onLogout() {
  await showConfirmDialog({ title: '退出登录', message: '确定退出当前账号吗？' }).then(() => {
    store.logout()
    showToast('已退出登录')
  })
}
</script>

<template>
  <div class="page-container px-4 pb-28 pt-6">
    <header class="mb-5">
      <h1 class="section-title text-[22px] text-ink">我的</h1>
      <p class="mt-1 text-sm text-ink-secondary">收藏、账号与隐私设置</p>
    </header>

    <!-- 用户信息 / 登录入口 -->
    <section
      class="overflow-hidden rounded-xl p-4"
      :class="store.isLoggedIn ? 'brand-gradient' : 'bg-paper-card shadow-paper'"
    >
      <div class="flex items-center gap-3">
        <span
          class="flex h-11 w-11 items-center justify-center rounded-xl text-white"
          :class="store.isLoggedIn ? 'bg-white/20' : 'bg-primary/10'"
        >
          <van-icon name="user-o" size="22" :color="store.isLoggedIn ? '#fff' : '#2F9E6B'" />
        </span>
        <div v-if="store.isLoggedIn" class="flex-1">
          <p class="text-base font-semibold text-white">{{ store.user.username }}</p>
          <p class="mt-0.5 text-xs text-white/80">已登录，历史与收藏已同步</p>
        </div>
        <template v-else>
          <div class="flex-1">
            <p class="text-base font-semibold text-ink">未登录</p>
            <p class="mt-0.5 text-xs text-ink-secondary">登录后同步识别历史与收藏</p>
          </div>
          <button
            type="button"
            class="btn-outline h-9 rounded-full px-4 text-sm"
            @click="router.push({ name: 'login' })"
          >
            登录 / 注册
          </button>
        </template>
      </div>
    </section>

    <!-- 功能入口 -->
    <div class="mt-4 overflow-hidden rounded-xl bg-paper-card shadow-paper">
      <button
        type="button"
        class="flex w-full items-center gap-3 px-4 py-4 text-left transition active:bg-paper"
        @click="router.push({ name: 'favorites' })"
      >
        <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
          <van-icon name="like-o" size="20" color="#2F9E6B" />
        </span>
        <span class="flex-1 text-sm font-medium text-ink">我的收藏</span>
        <span class="text-sm text-ink-secondary">{{ favoriteCount }} 味</span>
        <van-icon name="arrow" color="#A8A39A" />
      </button>
      <button
        type="button"
        class="flex w-full items-center gap-3 border-t border-ink/10 px-4 py-4 text-left transition active:bg-paper"
        @click="openPrivacy"
      >
        <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-ochre/10">
          <van-icon name="shield-o" size="20" color="#C08A3E" />
        </span>
        <span class="flex-1 text-sm font-medium text-ink">隐私与授权</span>
        <van-icon name="arrow" color="#A8A39A" />
      </button>
      <button
        v-if="store.isLoggedIn"
        type="button"
        class="flex w-full items-center gap-3 border-t border-ink/10 px-4 py-4 text-left transition active:bg-paper"
        @click="onLogout"
      >
        <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-cinnabar/10">
          <van-icon name="sign" size="20" color="#C0392B" />
        </span>
        <span class="flex-1 text-sm font-medium text-cinnabar">退出登录</span>
      </button>
    </div>

    <p class="mt-6 text-center text-xs text-ink-secondary/70">灵草 · 中草药识别智能体</p>

    <!-- 隐私授权管理面板 -->
    <van-popup v-model:show="showPrivacySheet" position="bottom" round>
      <div class="px-6 pb-8 pt-6">
        <h2 class="text-center text-lg font-semibold text-ink">隐私与授权</h2>
        <p class="mt-2 text-center text-xs text-ink-secondary">
          管理本设备的功能权限，关闭后对应功能将受限
        </p>

        <div class="mt-5 space-y-3">
          <div
            v-for="item in consentMeta"
            :key="item.key"
            class="flex items-center justify-between rounded-xl bg-paper px-4 py-3.5"
          >
            <div>
              <p class="text-sm font-semibold text-ink">{{ item.title }}</p>
              <p class="mt-0.5 text-xs text-ink-secondary">{{ item.desc }}</p>
            </div>
            <van-switch
              :model-value="consents[item.key] !== false"
              size="24"
              active-color="#2F9E6B"
              @update:model-value="toggleConsent(item.key, $event)"
            />
          </div>
        </div>

        <p class="mt-4 text-center text-xs leading-relaxed text-ink-secondary/70">
          图片数据仅用于本次识别，前端完成后即清除。
        </p>
      </div>
    </van-popup>
  </div>
</template>
