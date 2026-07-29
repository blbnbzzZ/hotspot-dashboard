<template>
  <div class="data-manage">
    <div class="section-title">⚙️ 设置</div>
    <div class="section-subtitle">管理本地存储的热点数据和采集配置</div>

    <!-- 主题切换 -->
    <div class="card" style="margin-bottom:16px;">
      <div style="font-weight:600;margin-bottom:8px;">🎨 主题</div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-sm" @click="setTheme('light')"
          :style="!isDark ? 'background:var(--accent);color:white;border:2px solid var(--accent);' : 'background:var(--bg-secondary);border:2px solid var(--border-color);'">
          ☀️ 亮色
        </button>
        <button class="btn btn-sm" @click="setTheme('dark')"
          :style="isDark ? 'background:var(--accent);color:white;border:2px solid var(--accent);' : 'background:var(--bg-secondary);border:2px solid var(--border-color);'">
          🌙 暗色
        </button>
      </div>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-top:6px;">
        主题设置自动保存在本地浏览器
      </div>
    </div>

    <!-- 存储概览 -->
    <div class="card" style="margin-bottom:16px;">
      <div style="font-weight:600;margin-bottom:8px;">💾 存储概览</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.82rem;">
        <div>
          <span style="color:var(--text-secondary)">总采集条目：</span>
          <strong>{{ store.stats?.total_raw_items || 0 }}</strong>
        </div>
        <div>
          <span style="color:var(--text-secondary)">总聚合热点：</span>
          <strong>{{ store.stats?.total_aggregated || 0 }}</strong>
        </div>
        <div>
          <span style="color:var(--text-secondary)">总批次数：</span>
          <strong>{{ store.stats?.total_batches || 0 }}</strong>
        </div>
        <div>
          <span style="color:var(--text-secondary)">数据库路径：</span>
          <strong style="font-size:0.7rem;">项目目录/data/hotspots.db</strong>
        </div>
      </div>
    </div>

    <!-- 平台统计 -->
    <div class="card" style="margin-bottom:16px;">
      <div style="font-weight:600;margin-bottom:8px;">📡 各平台数据统计</div>
      <div v-for="p in store.platformStats" :key="p.platform_key"
        style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-light);">
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="platform-badge" :class="'platform-' + p.platform_key">
            {{ p.platform_name }}
          </span>
          <span style="font-size:0.82rem;">累计 {{ p.total_items }} 条</span>
        </div>
        <span style="font-size:0.72rem;color:var(--text-secondary);">
          最近: {{ p.latest_count }} 条
        </span>
      </div>
      <div v-if="!store.platformStats.length" style="color:var(--text-muted);font-size:0.82rem;text-align:center;padding:12px;">
        暂无数据
      </div>
    </div>

    <!-- 操作 -->
    <div class="card" style="margin-bottom:16px;">
      <div style="font-weight:600;margin-bottom:12px;">🔧 数据操作</div>

      <button class="btn btn-primary btn-block" @click="handleCrawl" :disabled="store.loading"
        style="margin-bottom:8px;">
        🔄 立即采集热点
      </button>

      <button class="btn btn-secondary btn-block" @click="handleExport" style="margin-bottom:8px;">
        📥 导出最新数据 (JSON)
      </button>

      <div style="border-top:1px solid var(--border-color);margin:12px 0;"></div>

      <div style="display:flex;gap:8px;">
        <button class="btn btn-danger btn-sm" @click="confirmDelete = true">
          🗑️ 清除所有数据
        </button>
      </div>

      <div v-if="confirmDelete" style="margin-top:12px;padding:12px;background:rgba(239,68,68,0.1);border-radius:8px;border:1px solid rgba(239,68,68,0.3);">
        <div style="font-size:0.82rem;color:var(--danger);margin-bottom:8px;font-weight:600;">
          ⚠️ 此操作不可恢复！将删除所有采集和聚合数据。
        </div>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-danger btn-sm" @click="handleClear">确认清除</button>
          <button class="btn btn-secondary btn-sm" @click="confirmDelete = false">取消</button>
        </div>
      </div>
    </div>

    <!-- 采集调度信息 -->
    <div class="card" style="margin-bottom:16px;">
      <div style="font-weight:600;margin-bottom:8px;">⏰ 采集调度</div>
      <div style="font-size:0.82rem;color:var(--text-secondary);">
        <div>📅 频率：每 6 小时自动采集</div>
        <div>📡 数据源：微博热搜、澎湃新闻、百度热搜、B站热搜</div>
        <div style="margin-top:4px;font-size:0.72rem;color:var(--text-muted);">
          启动应用时自动执行首次采集，之后每6小时更新
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useHotspotStore } from '../stores/hotspot'

const store = useHotspotStore()
const showToast = inject('showToast', () => {})
const isDark = inject('isDark', ref(false))
const confirmDelete = ref(false)

// 主题切换
function setTheme(mode) {
  isDark.value = mode === 'dark'
  localStorage.setItem('theme', mode)
  document.documentElement.className = mode
  showToast(mode === 'dark' ? '已切换为暗色主题' : '已切换为亮色主题')
}

async function handleCrawl() {
  const result = await store.triggerCrawl()
  if (result?.status === 'success') {
    showToast('采集完成！')
  } else {
    showToast('采集失败，请检查网络')
  }
}

async function handleExport() {
  try {
    const { default: axios } = await import('axios')
    const { data } = await axios.get('/api/data/export')
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `hotspots-${data.batch_id || 'export'}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast('导出成功')
  } catch (e) {
    showToast('导出失败')
  }
}

async function handleClear() {
  confirmDelete.value = false
  await store.clearAllData()
  showToast('所有数据已清除')
}

onMounted(() => {
  store.fetchStats()
  store.fetchBatches()
})
</script>
