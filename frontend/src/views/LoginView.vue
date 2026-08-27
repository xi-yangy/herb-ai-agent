<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { login, register, migrateHistory, migrateFavorites } from '@/api/auth'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

// 登录 / 注册 切换
const mode = ref('login')
const username = ref('')
const password = ref('')
const submitting = ref(false)

/** 登录或注册成功后：保存用户态、迁移匿名数据、返回来源页。 */
async function handleSubmit() {
  const name = username.value.trim()
  if (!name) {
    showToast('请输入用户名')
    return
  }
  if (password.value.length < 6) {
    showToast('密码至少 6 位')
    return
  }

  submitting.value = true
  try {
    const res = mode.value === 'login'
      ? await login(name, password.value)
      : await register(name, password.value)

    // 持久化登录态（token 由 http 拦截器统一注入）
    localStorage.setItem('herb_token', res.token)
    store.setUser(res.user)

    // 登录后合并匿名历史/收藏到当前用户（失败不阻断登录）
    try {
      await Promise.all([migrateHistory(), migrateFavorites()])
    } catch (err) {
      console.error('[migrate]', err)
    }

    showSuccessToast(mode.value === 'login' ? '登录成功' : '注册成功')
    const redirect = route.query.redirect
    router.replace(typeof redirect === 'string' && redirect ? redirect : '/mine')
  } catch (err) {
    console.error('[auth submit]', err)
    const msg = err?.response?.data?.detail
    showToast(typeof msg === 'string' ? msg : '操作失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

/** 切换登录/注册模式并清空输入。 */
function switchMode(next) {
  mode.value = next
  password.value = ''
}
</script>

<template>
  <div class="min-h-screen bg-[#F5F7F4] px-6 pt-14">
    <!-- 返回 -->
    <button
      type="button"
      class="flex h-9 w-9 items-center justify-center rounded-full bg-white shadow-sm active:scale-90"
      @click="router.back()"
    >
      <van-icon name="arrow-left" size="18" color="#1F2A24" />
    </button>

    <!-- 品牌区 -->
    <div class="mt-8 text-center">
      <div
        class="brand-gradient mx-auto flex h-16 w-16 items-center justify-center rounded-3xl shadow-lg"
      >
        <van-icon name="flower-o" size="32" color="#fff" />
      </div>
      <h1 class="mt-4 text-[22px] font-semibold text-[#1F2A24]">灵草 · 中草药识别</h1>
      <p class="mt-2 text-sm text-[#5B6B62]">登录后同步你的识别历史与收藏</p>
    </div>

    <!-- 登录/注册卡片 -->
    <section class="glass-card mx-auto mt-8 max-w-md p-6">
      <div class="mb-6 flex rounded-xl bg-[#EFF4F0] p-1">
        <button
          type="button"
          class="flex-1 rounded-lg py-2 text-sm font-medium transition"
          :class="mode === 'login' ? 'brand-gradient text-white shadow' : 'text-[#5B6B62]'"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          type="button"
          class="flex-1 rounded-lg py-2 text-sm font-medium transition"
          :class="mode === 'register' ? 'brand-gradient text-white shadow' : 'text-[#5B6B62]'"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <van-field
        v-model="username"
        label="用户名"
        placeholder="请输入用户名"
        clearable
        maxlength="64"
        class="rounded-xl bg-white"
      />
      <van-field
        v-model="password"
        type="password"
        label="密码"
        placeholder="请输入密码（至少 6 位）"
        clearable
        maxlength="128"
        class="mt-3 rounded-xl bg-white"
      />

      <button
        type="button"
        class="brand-gradient mt-6 w-full rounded-2xl py-3.5 text-sm font-semibold text-white shadow-lg transition active:scale-95"
        :disabled="submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '处理中…' : mode === 'login' ? '登 录' : '注 册' }}
      </button>

      <p class="mt-4 text-center text-xs leading-relaxed text-[#5B6B62]/70">
        登录后，匿名识别记录与收藏将同步到你的账号。
      </p>
    </section>
  </div>
</template>
