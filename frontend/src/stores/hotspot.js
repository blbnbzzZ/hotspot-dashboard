import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = axios.create({ baseURL: '/api' })

export const useHotspotStore = defineStore('hotspot', () => {
  // State
  const hotspots = ref([])
  const commonHotspots = ref([])
  const trends = ref([])
  const stats = ref(null)
  const batches = ref([])
  const platformStats = ref([])
  const loading = ref(false)
  const crawlProgress = ref({
    active: false,
    percent: 0,
    text: '',
    platforms: [],
  })
  const currentBatchId = ref(null)
  const currentPage = ref(1)
  const totalItems = ref(0)
  const filters = ref({
    category: '',
    isCommon: null,
    platform: '',
    keyword: '',
    sortBy: 'weight',
  })

  // Getters
  const categories = computed(() => {
    const cats = [...new Set(hotspots.value.map(h => h.category).filter(Boolean))]
    return ['', ...cats.sort()]
  })

  const weightColor = (weight) => {
    if (weight >= 80) return '#e74c3c'
    if (weight >= 60) return '#e67e22'
    if (weight >= 40) return '#f39c12'
    if (weight >= 20) return '#2ecc71'
    return '#95a5a6'
  }

  const platformColor = (platform) => {
    const colors = {
      weibo: '#e6162d',
      thepaper: '#e64a19',
      baidu: '#2932e1',
      bilibili: '#fb7299',
    }
    return colors[platform] || '#999'
  }

  // Actions
  async function fetchHotspots(page = 1) {
    loading.value = true
    try {
      const params = {
        page,
        page_size: 30,
        sort_by: filters.value.sortBy,
      }
      if (filters.value.category) params.category = filters.value.category
      if (filters.value.isCommon !== null) params.is_common = filters.value.isCommon
      if (filters.value.platform) params.platform = filters.value.platform
      if (filters.value.keyword) params.keyword = filters.value.keyword
      if (currentBatchId.value && filters.value.keyword) {
        // not setting batch_id when filtering lets the API pick latest
      }

      const { data } = await API.get('/hotspots', { params })
      hotspots.value = data.items
      totalItems.value = data.total
      currentPage.value = data.page
      if (data.batch_id) currentBatchId.value = data.batch_id
    } catch (e) {
      console.error('获取热点失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchCommonHotspots() {
    try {
      const { data } = await API.get('/hotspots/common', { params: { min_platforms: 2 } })
      commonHotspots.value = data.items
    } catch (e) {
      console.error('获取共同热点失败:', e)
    }
  }

  async function fetchTrends(hours = 24) {
    try {
      const { data } = await API.get('/trends', { params: { hours } })
      trends.value = data.trends
    } catch (e) {
      console.error('获取趋势失败:', e)
    }
  }

  async function fetchStats() {
    try {
      const { data } = await API.get('/stats')
      stats.value = data

      const platResp = await API.get('/stats/platforms')
      platformStats.value = platResp.data.platforms
    } catch (e) {
      console.error('获取统计失败:', e)
    }
  }

  async function fetchBatches(page = 1) {
    try {
      const { data } = await API.get('/stats/batches', { params: { page, page_size: 20 } })
      batches.value = data.items
    } catch (e) {
      console.error('获取批次失败:', e)
    }
  }

  async function getHotspotDetail(id) {
    try {
      const { data } = await API.get(`/hotspots/${id}`)
      return data
    } catch (e) {
      console.error('获取详情失败:', e)
      return null
    }
  }

  async function triggerCrawl() {
    loading.value = true
    // 启动爬取进度模拟 - 后端是顺序爬取 4 个平台
    startCrawlProgressSimulation()

    try {
      const { data } = await API.post('/crawl/trigger')
      await fetchHotspots()
      await fetchStats()
      await fetchCommonHotspots()
      return data
    } catch (e) {
      console.error('触发爬取失败:', e)
    } finally {
      loading.value = false
      // 让进度条显示完成态 1 秒后重置
      setTimeout(() => {
        crawlProgress.value = {
          active: false,
          percent: 0,
          text: '',
          platforms: [],
        }
      }, 1200)
    }
  }

  function startCrawlProgressSimulation() {
    const platformList = [
      { key: 'weibo', name: '微博' },
      { key: 'thepaper', name: '澎湃' },
      { key: 'baidu', name: '百度' },
      { key: 'bilibili', name: 'B站' },
    ]

    // 初始化所有平台为 pending
    crawlProgress.value = {
      active: true,
      percent: 0,
      text: '正在启动爬取...',
      platforms: platformList.map(p => ({
        ...p,
        status: 'pending',
        count: 0,
      })),
    }

    // 每个平台阶段约 3 秒（基于历史观察）
    const stageDuration = 3000
    platformList.forEach((p, idx) => {
      // 进入 running 状态
      setTimeout(() => {
        if (!crawlProgress.value.active) return
        crawlProgress.value.platforms[idx].status = 'running'
        crawlProgress.value.text = `正在爬取 ${p.name}...`
        crawlProgress.value.percent = Math.round((idx + 0.5) / platformList.length * 100)
      }, idx * stageDuration + 100)

      // 完成
      setTimeout(() => {
        if (!crawlProgress.value.active) return
        crawlProgress.value.platforms[idx].status = 'done'
        crawlProgress.value.platforms[idx].count = 50
        crawlProgress.value.percent = Math.round((idx + 1) / platformList.length * 100)

        if (idx === platformList.length - 1) {
          crawlProgress.value.text = '爬取完成！正在聚合...'
          crawlProgress.value.percent = 100
        }
      }, (idx + 1) * stageDuration)
    })
  }

  async function deleteBatch(batchId) {
    try {
      await API.delete(`/data/batches/${batchId}`)
      await fetchBatches()
      await fetchStats()
    } catch (e) {
      console.error('删除批次失败:', e)
    }
  }

  async function clearAllData() {
    try {
      await API.delete('/data/clear')
      hotspots.value = []
      commonHotspots.value = []
      await fetchStats()
      await fetchBatches()
    } catch (e) {
      console.error('清除数据失败:', e)
    }
  }

  function setFilter(key, value) {
    filters.value[key] = value
  }

  function resetFilters() {
    filters.value = { category: '', isCommon: null, platform: '', keyword: '', sortBy: 'weight' }
  }

  return {
    hotspots,
    commonHotspots,
    trends,
    stats,
    batches,
    platformStats,
    loading,
    crawlProgress,
    currentBatchId,
    currentPage,
    totalItems,
    filters,
    categories,
    weightColor,
    platformColor,
    fetchHotspots,
    fetchCommonHotspots,
    fetchTrends,
    fetchStats,
    fetchBatches,
    getHotspotDetail,
    triggerCrawl,
    deleteBatch,
    clearAllData,
    setFilter,
    resetFilters,
  }
})
