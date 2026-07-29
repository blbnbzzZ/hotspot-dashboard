<template>
  <div class="history">
    <div class="section-title">📋 采集批次历史</div>

    <!-- 使用说明 -->
    <div class="card" style="font-size:0.78rem;color:var(--text-secondary);line-height:1.7;background:var(--accent-light);border-left:3px solid var(--accent);">
      💡 <strong>引用规则</strong>：系统默认引用最近 24 小时内最新的 <strong>3 批</strong>数据。
      点击「✓ 引用中」按钮可<strong>排除</strong>某批次（首页将不再展示该批次数据），点击「🚫 已排除」可恢复。
    </div>

    <!-- 趋势总览图 -->
    <div class="section-subtitle">近72小时热点趋势</div>
    <div class="chart-container" ref="overviewChartRef" style="height:250px;"></div>

    <!-- 批次列表 -->
    <div class="section-title" style="margin-top:16px;">📦 批次记录</div>

    <div v-if="store.loading" class="loading-spinner">
      <div class="spinner"></div>
    </div>

    <div v-else-if="!store.batches.length" class="empty-state">
      <div class="empty-state-icon">📭</div>
      <div class="empty-state-text">暂无批次记录</div>
    </div>

    <div v-else>
      <div v-for="batch in store.batches" :key="batch.batch_id"
        class="batch-list-item" @click="viewBatch(batch.batch_id)"
        style="cursor:pointer;">
        <div class="batch-info">
          <div class="batch-id">{{ batch.batch_id.slice(0, 12) }}</div>
          <div class="batch-meta">
            {{ formatTime(batch.completed_at) }}
            · 采集 {{ batch.total_items }} 条
            · 聚合 {{ batch.aggregated_items }} 个热点
            <span v-if="batch.common_items" style="color:#f59e0b;font-weight:600;">
              · {{ batch.common_items }}个共同热点
            </span>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <div :style="{ fontSize: '0.72rem', color: batch.status === 'completed' ? '#10b981' : '#f59e0b' }">
            {{ batch.status === 'completed' ? '✅ 完成' : '⏳ 进行中' }}
          </div>
          <button class="btn btn-sm" @click.stop="toggleBatchExclusion(batch.batch_id)"
            v-if="batch.status === 'completed'"
            :style="isExcluded(batch.batch_id) ? 'background:#ef4444;color:white;' : 'background:var(--bg-secondary);color:var(--text-secondary);'"
            :title="isExcluded(batch.batch_id) ? '点击恢复引用此批次' : '点击排除此批次（不在首页显示）'">
            {{ isExcluded(batch.batch_id) ? '🚫 已排除' : '✓ 引用中' }}
          </button>
          <button class="btn btn-danger btn-sm" @click.stop="confirmDelete(batch.batch_id)"
            :title="'删除批次 ' + batch.batch_id.slice(0,8)">
            🗑️
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, nextTick } from 'vue'
import { useHotspotStore } from '../stores/hotspot'
import * as echarts from 'echarts'

const store = useHotspotStore()
const overviewChartRef = ref(null)
const isDark = inject('isDark', ref(false))
const showToast = inject('showToast', () => {})
const deletingId = ref(null)

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

const excludedBatchIds = ref([])

async function fetchExcluded() {
  try {
    const res = await fetch('/api/batches/excluded')
    const data = await res.json()
    excludedBatchIds.value = data.excluded || []
  } catch (e) {}
}

async function toggleBatchExclusion(batchId) {
  const isExcluded = excludedBatchIds.value.includes(batchId)
  try {
    const res = await fetch('/api/batches/excluded/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ batch_id: batchId }),
    })
    const data = await res.json()
    if (data.status === 'success') {
      excludedBatchIds.value = data.excluded || []
      showToast(isExcluded ? `已恢复批次 ${batchId.slice(0, 8)}` : `已排除批次 ${batchId.slice(0, 8)}`)
    }
  } catch (e) {
    showToast('操作失败')
  }
}

function isExcluded(batchId) {
  return excludedBatchIds.value.includes(batchId)
}

function viewBatch(batchId) {
  store.currentBatchId = batchId
  store.fetchHotspots(1)
}

function confirmDelete(batchId) {
  if (confirm(`确定删除批次 ${batchId.slice(0, 12)} 的数据吗？此操作不可恢复。`)) {
    handleDelete(batchId)
  }
}

async function handleDelete(batchId) {
  showToast('正在删除...')
  await store.deleteBatch(batchId)
  showToast('已删除')
}

async function loadData() {
  await store.fetchTrends(72)
  await store.fetchBatches()
  nextTick(() => renderOverviewChart())
}

function renderOverviewChart() {
  if (!overviewChartRef.value) return
  const chart = echarts.init(overviewChartRef.value)

  const textColor = isDark.value ? '#a0a8b8' : '#636e72'

  let times = [], totalItems = [], commonItems = []
  if (store.trends.length > 0) {
    store.trends.forEach(t => {
      const d = new Date(t.time)
      times.push(`${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:00`)
      totalItems.push(t.total_items || 0)
      commonItems.push(t.common_items || 0)
    })
  } else {
    times = ['7/28 00:00', '7/28 06:00', '7/28 12:00', '7/28 18:00']
    totalItems = [85, 92, 78, 88]
    commonItems = [12, 18, 10, 15]
  }

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['聚合热点', '共同热点'],
      textStyle: { color: textColor, fontSize: 11 },
      bottom: 0,
    },
    grid: { left: '3%', right: '4%', top: '10%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { color: textColor, fontSize: 10, rotate: 30 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: textColor, fontSize: 11 },
      splitLine: { lineStyle: { color: isDark.value ? '#2a2a45' : '#f0f2f5' } },
    },
    series: [
      {
        name: '聚合热点',
        type: 'bar',
        data: totalItems,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#3b6df0' },
            { offset: 1, color: '#8b5cf6' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: '共同热点',
        type: 'line',
        data: commonItems,
        smooth: true,
        lineStyle: { color: '#f59e0b', width: 2 },
        itemStyle: { color: '#f59e0b' },
        symbol: 'circle',
        symbolSize: 8,
      },
    ],
  })
}

onMounted(() => {
  fetchExcluded()
  loadData()
})
</script>
