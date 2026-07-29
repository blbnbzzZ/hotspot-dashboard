<template>
  <div class="my-page">
    <div class="section-title">👤 我的</div>

    <!-- Tab 切换 -->
    <div class="filter-bar">
      <button class="filter-chip" :class="{ active: tab === 'history' }" @click="tab = 'history'">💬 对话历史</button>
      <button class="filter-chip" :class="{ active: tab === 'settings' }" @click="tab = 'settings'">🔑 API 设置</button>
    </div>

    <!-- =========== Tab: 对话历史 =========== -->
    <div v-if="tab === 'history'">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div class="section-title" style="margin-bottom:0;">💬 对话历史</div>
        <span style="font-size:0.78rem;color:var(--text-muted);">共 {{ conversations.length }} 条</span>
      </div>

      <div v-if="loadingConvs" class="loading-spinner"><div class="spinner"></div></div>
      <div v-else-if="!conversations.length" class="empty-state">
        <div class="empty-state-icon">💭</div>
        <div class="empty-state-text">暂无对话历史</div>
        <div style="font-size:0.78rem;color:var(--text-muted);margin-top:6px;">从热点详情进入「基于此热点生成内容」开始对话</div>
      </div>

      <div v-else>
        <div v-for="c in conversations" :key="c.id" class="conv-card card">
          <div class="conv-card-header">
            <div style="flex:1;min-width:0;">
              <div class="conv-card-title">{{ c.title || '(无标题)' }}</div>
              <div class="conv-card-meta">
                <span v-if="c.hotspot_title" class="meta-hotspot">🔥 {{ c.hotspot_title.slice(0, 25) }}</span>
                <span class="meta-time">⏱ {{ formatTime(c.updated_at) }}</span>
                <span class="meta-msgs">💬 {{ c.message_count }} 条</span>
                <span v-if="c.total_tokens" class="meta-tokens">🎯 {{ c.total_tokens }} tokens</span>
              </div>
            </div>
            <div style="display:flex;gap:4px;">
              <button class="btn btn-secondary btn-sm" @click="openConversation(c.id)">📂 打开</button>
              <button class="btn btn-danger btn-sm" @click="deleteConv(c.id)">🗑️</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- =========== Tab: 生成记录（已移除） =========== -->

    <!-- =========== Tab: API 设置 =========== -->
    <div v-if="tab === 'settings'">
      <div class="card" style="margin-bottom:16px;">
        <div style="font-weight:600;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;">
          <span>🔑 AI API 密钥管理</span>
          <span v-if="aiStatus.enabled" style="font-size:0.7rem;color:#10b981;font-weight:600;">✓ 已启用</span>
        </div>

        <div v-for="p in aiStatus.providers" :key="p.key" class="ai-provider-row">
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="font-weight:600;font-size:0.85rem;">{{ p.name }}</span>
              <span v-if="p.configured" style="font-size:0.65rem;background:#10b981;color:white;padding:1px 6px;border-radius:8px;">已配置</span>
            </div>
            <div style="font-size:0.7rem;color:var(--text-muted);margin-top:2px;">{{ p.docs }}</div>
          </div>
          <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
            <input v-model="keyInputs[p.env_key]" :type="showKeys[p.env_key] ? 'text' : 'password'"
              placeholder="输入 API Key" class="api-key-input" :disabled="loadingKey === p.env_key" />
            <button class="btn btn-secondary btn-sm" @click="toggleKeyShow(p.env_key)">
              {{ showKeys[p.env_key] ? '🙈' : '👁️' }}
            </button>
            <button class="btn btn-primary btn-sm" @click="saveKey(p)" :disabled="loadingKey === p.env_key || !keyInputs[p.env_key]">
              {{ loadingKey === p.env_key ? '...' : '保存' }}
            </button>
            <button v-if="p.configured" class="btn btn-danger btn-sm" @click="deleteKey(p.env_key)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- =========== Tab: 文件保存路径 =========== -->
    <!-- 已移除 - 改用浏览器默认下载目录 -->
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const showToast = inject('showToast', () => {})
const tab = ref('history')

// AI 设置
const aiStatus = ref({ enabled: false, current_name: '', providers: [] })
const keyInputs = reactive({})
const showKeys = reactive({})
const loadingKey = ref(null)

async function fetchAIStatus() {
  try {
    const res = await fetch('/api/ai/status')
    aiStatus.value = await res.json()
    aiStatus.value.providers?.forEach(p => {
      if (!(p.env_key in keyInputs)) keyInputs[p.env_key] = ''
      if (!(p.env_key in showKeys)) showKeys[p.env_key] = false
    })
  } catch (e) {}
}

async function saveKey(provider) {
  const value = keyInputs[provider.env_key]?.trim()
  if (!value) { showToast('请输入 API Key'); return }
  loadingKey.value = provider.env_key
  try {
    const res = await fetch('/api/settings/ai/save', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ env_key: provider.env_key, value }) })
    const data = await res.json()
    if (data.status === 'success') {
      showToast('已保存')
      keyInputs[provider.env_key] = ''
      await fetchAIStatus()
    } else showToast('保存失败')
  } catch (e) { showToast('网络错误') }
  finally { loadingKey.value = null }
}

async function deleteKey(env_key) {
  if (!confirm('确认删除？')) return
  const res = await fetch('/api/settings/ai/delete', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ env_key }) })
  const data = await res.json()
  if (data.status === 'success') { showToast('已删除'); await fetchAIStatus() }
}

function toggleKeyShow(key) { showKeys[key] = !showKeys[key] }

// ============ 对话历史 ============
const conversations = ref([])
const loadingConvs = ref(false)

async function fetchConversations() {
  loadingConvs.value = true
  try {
    const res = await fetch('/api/conversations')
    const data = await res.json()
    conversations.value = data.items
  } catch (e) {}
  finally { loadingConvs.value = false }
}

function openConversation(id) {
  // 跳转到 ContentGen 并加载该对话
  router.push({ path: '/generate', query: { convId: id } })
}

async function deleteConv(id) {
  if (!confirm('确认删除此对话？')) return
  await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
  conversations.value = conversations.value.filter(c => c.id !== id)
  showToast('已删除')
}

// ============ 工具 ============
function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t), now = new Date()
  const diff = Math.floor((now - d) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff/60)}小时前`
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

function providerName(key) {
  return aiStatus.value.providers?.find(p => p.key === key)?.name || key
}

onMounted(() => {
  fetchAIStatus()
  fetchConversations()
})
</script>

<style scoped>
.conv-card {
  margin-bottom: 8px;
  padding: 12px 14px;
}
.conv-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.conv-card-title {
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-primary);
}
.conv-card-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 0.7rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
}
.meta-hotspot { color: var(--accent); }
.meta-time { color: var(--text-muted); }
.meta-msgs { color: var(--text-secondary); }
.meta-tokens { color: #10b981; }
.history-card {
  margin-bottom: 8px;
  padding: 12px 14px;
}
.history-card.history-expanded {
  border-left: 4px solid var(--accent);
}
.history-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.history-prompt {
  font-size: 0.85rem;
  font-weight: 500;
  line-height: 1.4;
}
.history-meta {
  font-size: 0.72rem;
  color: var(--text-secondary);
  margin-top: 3px;
}
.history-body {
  margin-top: 10px;
  border-top: 1px solid var(--border-light);
  padding-top: 10px;
}
.history-content pre {
  white-space: pre-wrap;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  line-height: 1.6;
  background: var(--bg-hover);
  padding: 10px;
  border-radius: var(--radius-sm);
  max-height: 400px;
  overflow-y: auto;
}
.gen-status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  vertical-align: middle;
  margin-right: 4px;
}
.dot-generating { background: #f59e0b; }
.dot-completed { background: #10b981; }
.dot-failed { background: #ef4444; }
.gen-error {
  font-size: 0.82rem;
  color: var(--danger);
  padding: 8px 0;
}
</style>