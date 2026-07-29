<template>
  <div class="dashboard">
    <!-- Stats Overview -->
    <div class="stats-grid" v-if="store.stats">
      <div class="stat-card">
        <div class="stat-value">{{ store.stats.latest_batch?.aggregated_items || 0 }}</div>
        <div class="stat-label">聚合热点</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: #f59e0b">{{ store.stats.latest_batch?.common_items || 0 }}</div>
        <div class="stat-label">共同热点</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ store.stats.total_raw_items || 0 }}</div>
        <div class="stat-label">累计采集</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ store.stats.total_batches || 0 }}</div>
        <div class="stat-label">采集批次</div>
      </div>
    </div>

    <!-- 手动刷新 & 筛选 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
      <button class="btn btn-secondary btn-sm" @click="refreshViewData" :disabled="refreshing"
        title="从数据库刷新最新热点（不触发爬取）">
        {{ refreshing ? '⏳ 更新中...' : '📊 更新数据' }}
      </button>
      <button class="btn btn-secondary btn-sm" @click="refreshData" :disabled="store.crawlProgress.active">
        {{ store.crawlProgress.active ? `⏳ ${store.crawlProgress.text}` : '🔄 立即采集' }}
      </button>
      <span style="font-size:0.72rem;color:var(--text-muted)">
        {{ store.currentBatchId ? '批次: ' + store.currentBatchId.slice(0,8) : '' }}
        {{ store.stats?.latest_batch?.completed_at ? '· 上次采集: ' + formatRelativeTime(store.stats.latest_batch.completed_at) : '' }}
      </span>
    </div>

    <!-- 爬取进度条 -->
    <div v-if="store.crawlProgress.active" class="crawl-progress">
      <div class="crawl-progress-text">
        <span>{{ store.crawlProgress.text }}</span>
        <span style="color:var(--text-muted)">{{ store.crawlProgress.percent }}%</span>
      </div>
      <div class="crawl-progress-bar">
        <div class="crawl-progress-fill" :style="{ width: store.crawlProgress.percent + '%' }"></div>
      </div>
      <div class="crawl-platforms">
        <span v-for="p in store.crawlProgress.platforms" :key="p.key"
          class="crawl-platform-chip"
          :class="{ done: p.status === 'done', running: p.status === 'running', pending: p.status === 'pending' }">
          <span class="crawl-platform-icon">
            {{ p.status === 'done' ? '✓' : p.status === 'running' ? '⏳' : '○' }}
          </span>
          {{ p.name }}
          <span style="font-size:0.65rem;opacity:0.7;">{{ p.count > 0 ? `(${p.count})` : '' }}</span>
        </span>
      </div>
    </div>

    <!-- Filter Chips -->
    <!-- 分类筛选 -->
    <div class="section-subtitle" style="font-size:0.78rem;margin-bottom:6px;">🏷️ 分类筛选</div>
    <div class="filter-bar">
      <button class="filter-chip" :class="{ active: !store.filters.isCommon && !store.filters.category }"
        @click="clearFilters">全部</button>
      <button class="filter-chip" :class="{ active: store.filters.isCommon === 1 }"
        @click="toggleCommon">🔥 所有数据源共同热点</button>
      <button v-for="cat in store.categories.filter(Boolean).slice(0, 5)" :key="cat"
        class="filter-chip" :class="{ active: store.filters.category === cat }"
        @click="toggleCategory(cat)">
        {{ cat }}
      </button>
    </div>

    <!-- Search -->
    <div class="search-bar">
      <span class="search-icon">🔍</span>
      <input class="search-input" v-model="searchText" placeholder="搜索热点关键词..."
        @input="onSearch" type="search" />
    </div>

    <!-- Platform Quick Filter -->
    <div style="display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;">
      <span v-for="p in platforms" :key="p.key"
        class="filter-chip"
        :class="{ active: store.filters.platform === p.key }"
        @click="togglePlatform(p.key)"
        :style="{ fontSize: '0.7rem', padding: '3px 10px' }">
        {{ p.name }}
      </span>
    </div>

    <!-- Loading Progress Bar -->
    <ProgressBar :loading="store.loading" :text="loadingText" />

    <!-- Hotspot List -->
    <div v-if="store.loading && !store.hotspots.length" class="loading-spinner">
      <div class="spinner"></div>
    </div>

    <div v-else-if="!store.hotspots.length" class="empty-state">
      <div class="empty-state-icon">📭</div>
      <div class="empty-state-text">暂无热点数据</div>
      <button class="btn btn-primary btn-sm" style="margin-top:12px" @click="refreshData">
        点击获取热点
      </button>
    </div>

    <template v-else>
      <div class="section-title">📊 热点榜单</div>

      <transition-group name="slide-up" tag="div">
        <div v-for="(hot, idx) in store.hotspots" :key="hot.id"
          class="hot-card" @click="goDetail(hot.id)">
          <div class="hot-card-rank" :class="{ top3: idx < 3 }">
            {{ idx + 1 }}
          </div>
          <div class="hot-card-body">
            <div class="hot-card-title">{{ hot.display_title }}</div>
            <div class="hot-card-meta">
              <span v-if="hot.is_common" class="common-badge">🔥 共同热点</span>
              <span v-for="(info, plat) in hot.platforms" :key="plat"
                class="platform-badge" :class="'platform-' + plat">
                {{ platformNames[plat] || plat }}
              </span>
              <span style="font-size:0.72rem;color:var(--text-muted)">
                {{ hot.category }}
              </span>
            </div>
            <div class="hot-card-summary">{{ hot.summary }}</div>
            <div class="hot-card-time">
              🕒 {{ formatRelativeTime(hot.created_at) }} 采集
            </div>
          </div>
          <div class="weight-display">
            <div class="weight-bar">
              <div class="weight-bar-fill"
                :style="{ width: hot.total_weight + '%', background: store.weightColor(hot.total_weight) }">
              </div>
            </div>
            <span class="weight-value" :style="{ color: store.weightColor(hot.total_weight) }">
              {{ Math.round(hot.total_weight) }}
            </span>
          </div>
        </div>
      </transition-group>

      <!-- Pagination -->
      <div v-if="store.totalItems > 30" style="text-align:center;padding:16px 0;">
        <button class="btn btn-secondary btn-sm" :disabled="store.currentPage <= 1"
          @click="store.fetchHotspots(store.currentPage - 1)">
          上一页
        </button>
        <span style="margin:0 12px;font-size:0.85rem;color:var(--text-secondary)">
          {{ store.currentPage }} / {{ Math.ceil(store.totalItems / 30) }}
        </span>
        <button class="btn btn-secondary btn-sm"
          :disabled="store.currentPage >= Math.ceil(store.totalItems / 30)"
          @click="store.fetchHotspots(store.currentPage + 1)">
          下一页
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHotspotStore } from '../stores/hotspot'
import ProgressBar from '../components/ProgressBar.vue'

const router = useRouter()
const store = useHotspotStore()
const searchText = ref('')
const refreshing = ref(false)

const platforms = [
  { key: 'weibo', name: '微博' },
  { key: 'thepaper', name: '澎湃' },
  { key: 'baidu', name: '百度' },
  { key: 'bilibili', name: 'B站' },
]
const platformNames = {
  weibo: '微博', thepaper: '澎湃', baidu: '百度', bilibili: 'B站',
}

// 进度条文字：根据当前筛选条件动态显示
const loadingText = computed(() => {
  if (!store.loading) return ''
  const f = store.filters
  const parts = []
  if (f.platform) parts.push(platformNames[f.platform] || f.platform)
  else parts.push('全部平台')
  if (f.isCommon === 1) parts.push('共同热点')
  if (f.category) parts.push(f.category)
  if (f.keyword) parts.push(`关键词"${f.keyword}"`)
  return `正在加载${parts.join('·')}热点...`
})

let searchTimer = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.setFilter('keyword', searchText.value)
    store.fetchHotspots(1)
  }, 400)
}

function toggleCommon() {
  store.setFilter('isCommon', store.filters.isCommon === 1 ? null : 1)
  store.fetchHotspots(1)
}

function toggleCategory(cat) {
  store.setFilter('category', store.filters.category === cat ? '' : cat)
  store.fetchHotspots(1)
}

function togglePlatform(key) {
  store.setFilter('platform', store.filters.platform === key ? '' : key)
  store.fetchHotspots(1)
}

function clearFilters() {
  store.resetFilters()
  searchText.value = ''
  store.fetchHotspots(1)
}

function refreshData() {
  store.triggerCrawl()
}

async function refreshViewData() {
  refreshing.value = true
  try {
    await Promise.all([
      store.fetchHotspots(1),
      store.fetchStats(),
      store.fetchCommonHotspots(),
    ])
  } finally {
    refreshing.value = false
  }
}

function goDetail(id) {
  router.push(`/trend/${id}`)
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  if (diffHour < 24) return `${diffHour}小时前`
  if (diffDay < 7) return `${diffDay}天前`
  return `${date.getMonth() + 1}/${date.getDate()}`
}

// 进入首页时刷新一次（满足「回到首页自动更新」需求）
onMounted(() => {
  refreshViewData()
})
</script>
