<template>
  <div class="trend-detail">
    <!-- 返回 -->
    <router-link to="/" class="back-btn">← 返回看板</router-link>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-spinner"><div class="spinner"></div></div>

    <template v-else-if="detail">
      <!-- 热点详情 -->
      <div class="detail-header card">
        <div class="detail-title">{{ detail.display_title }}</div>
        <div class="detail-platforms">
          <span v-for="(info, plat) in detail.platforms" :key="plat"
            class="platform-badge" :class="'platform-' + plat">
            {{ platformNames[plat] }} #{{ info.rank }}
          </span>
          <span v-if="detail.is_common" class="common-badge">🔥 共同热点</span>
          <span style="font-size:0.75rem;color:var(--text-secondary)">
            {{ detail.category }}
          </span>
        </div>
        <div class="detail-weight">
          <span class="detail-weight-label">综合权重</span>
          <div class="weight-display" style="flex:1;max-width:200px;">
            <div class="weight-bar">
              <div class="weight-bar-fill"
                :style="{ width: detail.total_weight + '%', background: store.weightColor(detail.total_weight) }">
              </div>
            </div>
            <span class="weight-value" :style="{ color: store.weightColor(detail.total_weight) }">
              {{ Math.round(detail.total_weight) }}
            </span>
          </div>
        </div>
        <div style="font-size:0.82rem;color:var(--text-secondary);margin-top:8px;">
          {{ detail.summary }}
        </div>
      </div>

      <!-- 各平台详情 -->
      <div class="section-title">📡 各平台表现</div>
      <div v-for="(info, plat) in detail.platforms" :key="plat"
        class="card plat-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
              <span class="platform-badge" :class="'platform-' + plat">
                {{ platformNames[plat] }}
              </span>
              <span v-if="info.url && isRealUrl(info.url)" style="display:flex;align-items:center;gap:4px;">
                <button @click.stop="openArticle(info.url, plat)"
                  style="font-size:0.72rem;color:var(--accent);background:none;border:none;cursor:pointer;padding:0;">
                  🔗 查看文章
                </button>
              </span>
              <span v-else-if="info.url" style="font-size:0.7rem;color:var(--text-muted);">
                🔍 搜索结果
              </span>
            </div>
            <div style="font-size:0.85rem;line-height:1.4;">{{ info.title }}</div>
          </div>
          <div style="font-size:0.75rem;color:var(--text-secondary);text-align:right;flex-shrink:0;">
            <div>排名 <strong>#{{ info.rank }}</strong></div>
            <div v-if="info.hot_score">热度 {{ formatNumber(info.hot_score) }}</div>
          </div>
        </div>
      </div>

      <!-- 趋势图 -->
      <div class="section-title" style="margin-top:16px;">📈 热度趋势</div>
      <div class="chart-container" ref="chartRef"></div>

      <!-- 操作按钮 -->
      <div style="display:flex;gap:8px;margin-top:12px;">
        <button class="btn btn-primary btn-block" @click="goGenerate">
          ✍️ 基于此热点生成文章
        </button>
      </div>
    </template>

    <div v-else class="empty-state">
      <div class="empty-state-icon">🔍</div>
      <div class="empty-state-text">热点数据不存在或已过期</div>
    </div>

    <!-- 文章查看弹窗 -->
    <transition name="fade">
      <div v-if="articleModal.show" class="article-backdrop" @click="closeArticle">
        <div class="article-modal card" @click.stop>
          <div class="article-header">
            <div class="article-title">{{ articleModal.title || '加载中...' }}</div>
            <button class="btn btn-danger btn-sm" @click="closeArticle">✕</button>
          </div>
          <div class="article-body">
            <div v-if="articleModal.loading" class="loading-spinner">
              <div class="spinner"></div>
              <div style="margin-top:8px;color:var(--text-muted);font-size:0.85rem;">正在抓取文章内容...</div>
            </div>
            <template v-else>
              <div v-if="articleModal.summary" class="article-summary">
                <div style="font-weight:600;margin-bottom:6px;">🤖 AI 摘要</div>
                <div style="font-size:0.85rem;line-height:1.7;">{{ articleModal.summary }}</div>
              </div>
              <div class="article-text">
                <pre>{{ articleModal.text || '无法获取正文内容' }}</pre>
              </div>
              <div v-if="articleModal.url" style="margin-top:12px;text-align:center;">
                <a :href="articleModal.url" target="_blank" class="btn btn-secondary btn-sm"
                  style="text-decoration:none;">
                  🔗 在新窗口打开原文
                </a>
              </div>
              <div v-if="articleModal.error" class="article-error">⚠️ {{ articleModal.error }}</div>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHotspotStore } from '../stores/hotspot'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const store = useHotspotStore()
const detail = ref(null)
const loading = ref(true)
const chartRef = ref(null)
const showToast = inject('showToast', () => {})

// 文章查看弹窗
const articleModal = ref({
  show: false,
  loading: false,
  title: '',
  text: '',
  summary: '',
  url: '',
  error: '',
})

async function openArticle(url, platform) {
  articleModal.value = {
    show: true, loading: true, title: '加载中...',
    text: '', summary: '', url, error: '',
  }
  try {
    const res = await fetch('/api/content/fetch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    const data = await res.json()
    if (res.ok) {
      articleModal.value.title = data.title || '无标题'
      articleModal.value.text = data.text || '（正文为空）'
      articleModal.value.summary = data.summary || ''
    } else {
      articleModal.value.error = data.detail || '加载失败'
    }
  } catch (e) {
    articleModal.value.error = e.message
  } finally {
    articleModal.value.loading = false
  }
}

function closeArticle() {
  articleModal.value.show = false
}
const isDark = inject('isDark', ref(false))

const platformNames = { weibo: '微博', thepaper: '澎湃', baidu: '百度', bilibili: 'B站' }

function formatNumber(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toLocaleString()
}

function isRealUrl(url) {
  // 检测是不是真正的文章/视频链接，不是搜索页
  const searchPatterns = [
    's.weibo.com/weibo',
    'baidu.com/s?',
    'thepaper.cn/search',
    'search.bilibili.com',
  ]
  return !searchPatterns.some(p => url.includes(p))
}

function goGenerate() {
  // AI 生成功能已移至「我的」页面（底部导航→我的）
  router.push(`/generate/${route.params.id}`)
}

async function loadDetail() {
  loading.value = true
  const id = route.params.id
  if (!id) {
    // 没有ID时显示趋势总览
    await store.fetchTrends(72)
    loading.value = false
    nextTick(() => renderTrendChart())
    return
  }
  detail.value = await store.getHotspotDetail(parseInt(id))
  loading.value = false
  if (detail.value) {
    nextTick(() => renderTrendChart())
  }
}

function renderTrendChart() {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)

  const textColor = isDark.value ? '#a0a8b8' : '#636e72'
  const bgColor = isDark.value ? '#1e1e36' : '#ffffff'

  // 如果有趋势数据就绘制，否则绘制示例数据
  let times = [], values = []
  if (store.trends.length > 0) {
    store.trends.forEach((t, i) => {
      const d = new Date(t.time)
      times.push(`${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`)
      const found = t.top_items?.find(item => detail.value && item.keyword === detail.value.keyword)
      values.push(found ? found.total_weight : detail.value ? detail.value.total_weight * (0.7 + Math.random() * 0.3) : 30 + Math.random() * 40)
    })
  } else if (detail.value) {
    // 模拟趋势
    const now = new Date()
    for (let i = 23; i >= 0; i--) {
      const t = new Date(now - i * 3600000)
      times.push(`${t.getHours().toString().padStart(2, '0')}:00`)
      const base = detail.value.total_weight
      const variation = Math.sin(i / 4) * 15 + (Math.random() - 0.5) * 10
      values.push(Math.max(0, Math.round(base + variation)))
    }
  } else {
    times = ['00:00', '06:00', '12:00', '18:00']
    values = [45, 52, 68, 60]
  }

  chart.setOption({
    backgroundColor: bgColor,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.7)',
      borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 12 },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: 'var(--border-color)' } },
      axisLabel: { color: textColor, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: isDark.value ? '#2a2a45' : '#f0f2f5' } },
      axisLabel: { color: textColor, fontSize: 11 },
    },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#3b6df0', width: 3 },
      itemStyle: { color: '#3b6df0' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,109,240,0.25)' },
          { offset: 1, color: 'rgba(59,109,240,0.02)' },
        ]),
      },
    }],
  })

  // 响应暗色模式
  watch(isDark, () => {
    chart.dispose()
    nextTick(() => renderTrendChart())
  }, { once: true })
}

onMounted(loadDetail)
watch(() => route.params.id, loadDetail)
</script>

<style scoped>
.article-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(3px);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.article-modal {
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 501;
}
.article-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}
.article-title {
  font-weight: 600;
  font-size: 1rem;
  line-height: 1.4;
  flex: 1;
  min-width: 0;
  max-height: 3em;
  overflow: hidden;
}
.article-body {
  flex: 1;
  overflow-y: auto;
  margin-top: 12px;
  min-height: 200px;
}
.article-summary {
  background: var(--accent-light);
  padding: 12px;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  border-left: 3px solid var(--accent);
}
.article-text pre {
  white-space: pre-wrap;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  line-height: 1.7;
  margin: 0;
}
.article-error {
  color: var(--danger);
  font-size: 0.85rem;
  padding: 12px;
  text-align: center;
}
</style>
