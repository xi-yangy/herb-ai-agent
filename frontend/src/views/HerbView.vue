<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { listHerbs } from '@/api/herb'

const router = useRouter()
const herbs = ref([])
const loading = ref(true)

/** 安全等级配色（普通/慎用/毒性，全站统一语义色）。 */
const safetyColor = { 普通: '#4A7C59', 慎用: '#C08A3E', 毒性: '#C0392B' }

/**
 * 分类聚合映射：把数据库里 22 种细碎 category 归并为有序大类。
 * 展示顺序即数组顺序，营造秩序感；未匹配的归入「其他」。
 */
const CATEGORIES = [
  { key: 'root', label: '根茎类', match: ['根茎类', '鳞茎类'] },
  { key: 'fruit', label: '果实种子类', match: ['果实类', '种子类', '果皮类'] },
  { key: 'herb', label: '花叶全草类', match: ['花类', '花粉类', '叶类', '全草类'] },
  { key: 'bark', label: '皮木树脂类', match: ['皮类', '树皮类', '茎类', '茎木类', '藤茎类', '藤木类', '树脂类'] },
  { key: 'animal', label: '动物矿物类', match: ['动物类', '矿物类', '虫瘿类'] },
  { key: 'fungus', label: '菌藻类', match: ['菌类', '菌核类'] },
]

/** 取药材所属大类 key，未匹配返回 'other'。 */
function groupOf(category) {
  const cat = (category || '').trim()
  const hit = CATEGORIES.find((g) => g.match.includes(cat))
  return hit ? hit.key : 'other'
}

const OTHER_GROUP = { key: 'other', label: '其他' }
const ALL_KEY = 'all'

const keyword = ref('')
const activeGroup = ref(ALL_KEY)

/** 搜索框防抖计时器。 */
let searchTimer = null
function onInput(value) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    keyword.value = value.trim()
  }, 180)
}

function clearSearch() {
  clearTimeout(searchTimer)
  keyword.value = ''
}

/** 各分类数量统计（用于导航角标）。 */
const groupStats = computed(() => {
  const stats = {}
  for (const h of herbs.value) {
    const key = groupOf(h.category)
    stats[key] = (stats[key] || 0) + 1
  }
  return stats
})

/** 按关键词过滤后的药材。 */
const searchedHerbs = computed(() => {
  const kw = keyword.value.toLowerCase()
  if (!kw) return herbs.value
  return herbs.value.filter((h) =>
    [h.name, h.nature_flavor, h.effects].some((t) => (t || '').toLowerCase().includes(kw)),
  )
})

/** 是否处于「分组视图」（未搜索 + 选中某分类）。 */
const inGroupView = computed(() => !keyword.value && activeGroup.value !== ALL_KEY)

/** 分组视图下，当前分类的药材列表。 */
const groupHerbs = computed(() => {
  if (!inGroupView.value) return []
  return searchedHerbs.value.filter((h) => groupOf(h.category) === activeGroup.value)
})

/** 分组视图标题：如「根茎类 · 62 味」。 */
const activeGroupLabel = computed(() => {
  const g = CATEGORIES.find((c) => c.key === activeGroup.value)
  return g ? g.label : OTHER_GROUP.label
})

/** 当前正在展示的药材（搜索平铺 or 分组过滤）。 */
const displayedHerbs = computed(() => (inGroupView.value ? groupHerbs.value : searchedHerbs.value))

/** 关键词命中高亮：把匹配片段包一层高亮（返回 [前, 命中, 后] 或原文字符串）。 */
function highlightText(text) {
  if (!keyword.value || !text) return text
  const kw = keyword.value.toLowerCase()
  const lower = String(text).toLowerCase()
  const idx = lower.indexOf(kw)
  if (idx < 0) return text
  return [text.slice(0, idx), text.slice(idx, idx + keyword.value.length), text.slice(idx + keyword.value.length)]
}

onMounted(async () => {
  try {
    herbs.value = await listHerbs()
  } catch (err) {
    console.error('[herbs]', err)
    showToast('加载失败')
  } finally {
    loading.value = false
  }
})

function goDetail(id) {
  router.push({ name: 'herb-detail', params: { id } })
}
</script>

<template>
  <div class="page-container px-6 pb-12">
    <!-- 标题区 -->
    <header class="mb-5">
      <h1 class="section-title text-[26px] text-ink">药材百科</h1>
      <p class="mt-1 text-base text-ink-secondary">收录常见中草药，按部位分类 · 标注安全等级</p>
    </header>

    <!-- 搜索区 -->
    <div
      class="flex items-center gap-2 rounded-xl border border-ink/10 bg-paper-card px-3.5 py-2.5 transition focus-within:border-primary focus-within:shadow-paper"
    >
      <van-icon name="search" size="16" color="#4A4A4A" />
      <input
        type="text"
        class="min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint"
        placeholder="搜索药材名 / 性味 / 功效"
        :value="keyword"
        @input="onInput($event.target.value)"
      />
      <button
        v-if="keyword"
        type="button"
        class="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 active:scale-90"
        @click="clearSearch"
      >
        <van-icon name="cross" size="11" color="#4A4A4A" />
      </button>
    </div>

    <!-- 分类胶囊导航（横向可滚动） -->
    <nav class="mt-4 flex flex-wrap gap-2 pb-1">
      <button
        type="button"
        class="flex shrink-0 items-center gap-1 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition active:scale-95"
        :class="activeGroup === ALL_KEY ? 'bg-primary text-white' : 'bg-paper-card text-ink-secondary'"
        @click="activeGroup = ALL_KEY"
      >
        全部
        <span
          class="rounded-full px-1.5 text-[11px]"
          :class="activeGroup === ALL_KEY ? 'bg-white/25' : 'bg-primary/10 text-ink-secondary'"
        >{{ herbs.length }}</span>
      </button>

      <button
        v-for="g in CATEGORIES"
        :key="g.key"
        type="button"
        class="flex shrink-0 items-center gap-1 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition active:scale-95"
        :class="activeGroup === g.key ? 'bg-primary text-white' : 'bg-paper-card text-ink-secondary'"
        @click="activeGroup = g.key"
      >
        {{ g.label }}
        <span
          class="rounded-full px-1.5 text-[11px]"
          :class="activeGroup === g.key ? 'bg-white/25' : 'bg-primary/10 text-ink-secondary'"
        >{{ groupStats[g.key] || 0 }}</span>
      </button>

      <button
        v-if="groupStats['other'] > 0"
        type="button"
        class="flex shrink-0 items-center gap-1 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition active:scale-95"
        :class="activeGroup === OTHER_GROUP.key ? 'bg-primary text-white' : 'bg-paper-card text-ink-secondary'"
        @click="activeGroup = OTHER_GROUP.key"
      >
        其他
        <span
          class="rounded-full px-1.5 text-[11px]"
          :class="activeGroup === OTHER_GROUP.key ? 'bg-white/25' : 'bg-primary/10 text-ink-secondary'"
        >{{ groupStats['other'] || 0 }}</span>
      </button>
    </nav>

    <!-- 加载态 -->
    <div v-if="loading" class="py-20 text-center text-sm text-ink-secondary">加载中…</div>

    <!-- 数据空态 -->
    <van-empty v-else-if="herbs.length === 0" description="暂无药材数据" />

    <!-- 搜索空态 -->
    <van-empty v-else-if="keyword && searchedHerbs.length === 0" description="未找到相关药材">
      <van-button size="small" round class="mt-2" @click="clearSearch">清除搜索</van-button>
    </van-empty>

    <template v-else>
      <!-- 分组标题 -->
      <div v-if="inGroupView" class="mt-6 mb-3 flex items-end justify-between">
        <h2 class="section-title text-lg text-ink">{{ activeGroupLabel }}</h2>
        <span class="text-xs text-ink-secondary">{{ displayedHerbs.length }} 味药材</span>
      </div>
      <p v-else-if="keyword" class="mt-6 mb-3 text-xs text-ink-secondary">
        找到 {{ displayedHerbs.length }} 味相关药材
      </p>

      <!-- 卡片网格 -->
      <div class="grid grid-cols-4 gap-4">
        <button
          v-for="(h, idx) in displayedHerbs"
          :key="h.id"
          type="button"
          class="slide-in group flex flex-col rounded-xl bg-paper-card p-4 text-left shadow-paper transition hover:-translate-y-0.5 hover:shadow-card active:scale-95"
          :style="{ animationDelay: idx * 0.04 + 's' }"
          @click="goDetail(h.id)"
        >
          <div class="flex items-start justify-between gap-2">
            <p class="text-base font-semibold leading-snug text-ink">
              <template v-if="keyword && typeof highlightText(h.name) !== 'string'">
                <span v-for="(part, i) in highlightText(h.name)" :key="i">
                  <mark v-if="i === 1" class="rounded bg-amber-200/80 px-0.5 font-semibold text-amber-900">{{ part }}</mark>
                  <template v-else>{{ part }}</template>
                </span>
              </template>
              <template v-else>{{ h.name }}</template>
            </p>
            <span
              class="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium"
              :style="{
                color: safetyColor[h.safety_level] || '#4A7C59',
                backgroundColor: (safetyColor[h.safety_level] || '#4A7C59') + '1A',
              }"
            >
              {{ h.safety_level }}
            </span>
          </div>
          <p class="mt-2 line-clamp-2 min-h-[2.5rem] text-xs leading-5 text-ink-secondary">
            <template v-if="keyword && typeof highlightText(h.nature_flavor) !== 'string'">
              <span v-for="(part, i) in highlightText(h.nature_flavor)" :key="i">
                <mark v-if="i === 1" class="rounded bg-amber-200/80 px-0.5 font-semibold text-amber-900">{{ part }}</mark>
                <template v-else>{{ part }}</template>
              </span>
            </template>
            <template v-else>{{ h.nature_flavor || '—' }}</template>
          </p>
          <div class="mt-3 flex items-center gap-1 text-[11px] text-ink-faint transition group-hover:text-primary">
            <van-icon name="arrow" size="12" />
            查看详情
          </div>
        </button>
      </div>
    </template>
  </div>
</template>
