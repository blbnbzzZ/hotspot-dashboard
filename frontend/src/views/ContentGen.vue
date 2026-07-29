<template>
  <div class="content-gen">
    <router-link to="/" class="back-btn">← 返回看板</router-link>

    <!-- 已选热点 -->
    <div v-if="selectedHot" class="card" style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:flex-start;">
      <div>
        <div style="font-size:0.72rem;color:var(--text-muted);">📌 当前热点</div>
        <div style="font-weight:700;font-size:0.95rem;margin-top:2px;">{{ selectedHot.display_title }}</div>
        <div style="font-size:0.72rem;color:var(--text-secondary);margin-top:2px;">
          权重 {{ Math.round(selectedHot.total_weight) }} · {{ selectedHot.category }}
        </div>
      </div>
      <button class="btn btn-secondary btn-sm" @click="selectedHot = null">更换</button>
    </div>

    <!-- Tips 教程 -->
    <div class="card" style="margin-bottom:12px;">
      <div style="font-weight:600;font-size:0.85rem;margin-bottom:6px;">💡 如何写好生成需求</div>
      <div style="font-size:0.78rem;color:var(--text-secondary);line-height:1.8;">
        <div>1. <strong>明确场景</strong> — 是公众号文章、短视频脚本还是朋友圈文案？</div>
        <div>2. <strong>指定风格</strong> — 专业严肃、轻松幽默、煽情催泪？</div>
        <div>3. <strong>提供素材</strong> — 热点标题、人物名称、关键数据</div>
        <div>4. <strong>控制篇幅</strong> — 比如"200字以内"、"写三段落"</div>
      </div>
    </div>

    <!-- 选择 AI -->
    <div class="card" style="margin-bottom:12px;">
      <div style="font-size:0.78rem;font-weight:600;margin-bottom:6px;">选择 AI 模型</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;">
        <button v-for="p in aiStatus.providers" :key="p.key"
          class="filter-chip" :class="{ active: selectedProvider === p.key }"
          :disabled="!p.configured"
          @click="selectedProvider = p.key"
          :style="{ fontSize: '0.72rem', padding: '4px 10px' }">
          {{ p.configured ? p.name : p.name + ' (未配置)' }}
        </button>
      </div>
    </div>

    <!-- 对话历史 -->
    <div v-if="messages.length" class="chat-history" ref="chatHistoryRef"
      @wheel="handleChatWheel" @touchmove="handleChatWheel">
      <div v-for="msg in messages" :key="msg.id || msg._tempId"
        class="chat-bubble" :class="msg.role">
        <div class="bubble-avatar">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
        <div class="bubble-content">
          <div v-if="msg.status === 'generating'" class="bubble-generating">
            <div class="spinner" style="width:14px;height:14px;"></div>
            <span>AI 思考中...</span>
          </div>
          <pre v-else>{{ msg.content }}</pre>
          <div v-if="msg.tokens" class="bubble-meta">{{ msg.tokens }} tokens</div>
        </div>
      </div>
    </div>

    <!-- 对话输入区 -->
    <div class="chat-input-card card">
      <div style="display:flex;gap:8px;">
        <textarea class="chat-textarea" v-model="promptInput"
          placeholder="写你的内容需求，越详细生成效果越好...&#10;&#10;例如：写一篇关于「南海Hero久竞」的300字电竞新闻，专业评论风格."
          @keydown.ctrl.enter="sendMessage" rows="3">
        </textarea>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;flex-wrap:wrap;gap:6px;">
        <div style="font-size:0.7rem;color:var(--text-muted);display:flex;gap:6px;">
          <span>{{ selectedProviderName || '请先选择 AI 模型' }}</span>
          <span v-if="convTotalTokens > 0">· 已用 {{ convTotalTokens }} tokens</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">
          <button class="btn btn-secondary btn-sm" @click="generateAIPrompt"
            :disabled="generating">
            🤖 AI 智能生成提示词
          </button>
          <button class="btn btn-secondary btn-sm" @click="generateFreeContent"
            :disabled="!selectedHot || generating"
            title="无需 API，使用本地模板快速生成内容">
            🪄 免费模板生成
          </button>
          <button class="btn btn-primary btn-sm" @click="sendMessage"
            :disabled="!canSend">
            {{ generating ? '⏳ 生成中...' : '🚀 发送' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 操作区 -->
    <div style="display:flex;gap:8px;margin-top:12px;">
      <button class="btn btn-secondary btn-sm" @click="newConversation" v-if="messages.length">
        🆕 新对话
      </button>
      <button class="btn btn-secondary btn-sm" @click="saveAsFile" v-if="messages.length">
        💾 保存到文件
      </button>
      <button class="btn btn-secondary btn-sm" @click="loadHistory">
        📋 历史对话
      </button>
    </div>

    <!-- 历史对话抽屉 -->
    <div v-if="showHistory" class="history-drawer card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <div style="font-weight:600;">📋 历史对话</div>
        <button class="btn btn-secondary btn-sm" @click="showHistory = false">关闭</button>
      </div>
      <div v-if="!conversations.length" style="text-align:center;padding:20px;color:var(--text-muted);">
        暂无历史对话
      </div>
      <div v-for="c in conversations" :key="c.id" class="conv-item"
        @click="loadConversation(c.id)">
        <div class="conv-title">{{ c.title }}</div>
        <div class="conv-meta">
          {{ formatTime(c.updated_at) }} · {{ c.message_count }} 条消息
          <span v-if="c.hotspot_title" class="conv-hotspot"> · {{ c.hotspot_title.slice(0,15) }}</span>
          <span v-if="c.total_tokens > 0" class="conv-tokens"> · {{ c.total_tokens }} tokens</span>
        </div>
        <button class="btn btn-danger btn-sm" @click.stop="deleteConversation(c.id)">🗑️</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useHotspotStore } from '../stores/hotspot'

const route = useRoute()
const store = useHotspotStore()
const showToast = inject('showToast', () => {})

// 状态
const selectedHot = ref(null)
const promptInput = ref('')
const generating = ref(false)
const aiStatus = ref({ enabled: false, current_name: '', providers: [] })
const selectedProvider = ref('')
const messages = ref([])  // 对话消息列表
const conversations = ref([])  // 历史对话列表
const showHistory = ref(false)
const currentConvId = ref(null)
const convTotalTokens = ref(0)
let pollTimer = null
const chatHistoryRef = ref(null)

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatHistoryRef.value) {
      chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
    }
  })
}

// 监听对话区域滚轮 - 到底时透传到外层页面
function handleChatWheel(e) {
  const el = chatHistoryRef.value
  if (!el) return
  const delta = e.deltaY
  const isAtTop = el.scrollTop <= 0
  const isAtBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1
  // 滚到底（继续向下滚）或滚到顶（继续向上滚）→ 让外层滚动
  if ((delta > 0 && isAtBottom) || (delta < 0 && isAtTop)) {
    e.stopPropagation()
    // 不 preventDefault，让浏览器自然滚动外层
  }
}

// ============ AI 状态 ============
const selectedProviderName = computed(() => {
  const p = aiStatus.value.providers?.find(x => x.key === selectedProvider.value)
  return p?.name || ''
})

const canSend = computed(() =>
  promptInput.value.trim() && selectedProvider.value && !generating.value
)

async function fetchAIStatus() {
  try {
    const res = await fetch('/api/ai/status')
    aiStatus.value = await res.json()
    const firstConfigured = aiStatus.value.providers?.find(p => p.configured)
    if (firstConfigured && !selectedProvider.value) selectedProvider.value = firstConfigured.key
  } catch (e) {}
}

// ============ AI 智能生成提示词（先生成提示词模板）============
function generateAIPrompt() {
  if (!selectedHot.value) {
    showToast('请先选择热点')
    return
  }
  // 直接生成提示词模板填入输入框，用户可编辑后再点发送
  const hot = selectedHot.value
  const plats = Object.keys(hot.platforms || {}).map(k => ({ weibo: '微博', thepaper: '澎湃', baidu: '百度', bilibili: 'B站' })[k] || k).join('、')

  promptInput.value = `请基于以下热点话题创作一篇内容：

【热点信息】
- 标题：${hot.display_title}
- 类别：${hot.category || '综合'}
- 热度：${Math.round(hot.total_weight)}/100
- 覆盖平台：${plats}
- 摘要：${hot.summary}

【创作要求】
- 内容真实、专业、有吸引力
- 适合中文社交媒体传播
- 字数根据平台特性调整
- 直接输出最终内容，不要加说明`
  showToast('提示词已生成，可编辑后点发送')
}

// ============ 免费模板生成（不调用API，本地模板）============
function generateFreeContent() {
  if (!selectedHot.value) {
    showToast('请先选择热点')
    return
  }
  const hot = selectedHot.value
  const plats = Object.keys(hot.platforms || {}).map(k => ({ weibo: '微博', thepaper: '澎湃', baidu: '百度', bilibili: 'B站' })[k] || k).join('、')

  const templates = {
    article: `【${hot.display_title}】\n\n` +
`近日，"${hot.display_title}" 成为全网热议话题，在 ${plats} 等多个平台引发广泛讨论，综合热度权重高达 ${Math.round(hot.total_weight)} 分。\n\n` +
`一、事件概述\n${hot.display_title} 相关话题近期持续升温。从各平台数据来看，微博热搜榜一度跃居前列，知乎社区讨论热度持续高涨，B站相关视频内容也获得了大量播放和互动。\n\n` +
`二、多维度分析\n1. 舆论反响：各大社交平台上，网友对此话题态度分化明显，支持和质疑声音并存，形成了热烈的讨论氛围。\n2. 深层解读：${hot.display_title} 所反映的不仅仅是表面现象，更深层次地揭示了当前 ${hot.category || '社会'} 领域的某些趋势和变化。\n3. 未来展望：随着话题的持续发酵，预计将会有更多的信息和观点涌现，值得持续关注。\n\n` +
`三、总结\n"${hot.display_title}" 作为近期热点，已经超越了简单的娱乐话题范畴，成为观察当前舆论生态和公众情绪的重要窗口。\n\n` +
`---\n本文由热点聚合工作台自动生成`,

    news: `【热点速递】${hot.display_title}\n\n` +
`据热点聚合平台监测数据显示，"${hot.display_title}" 在全网引发广泛关注，综合热度评分达到 ${Math.round(hot.total_weight)} 分（满分100），在 ${plats} 等平台均登上热榜。\n\n` +
`据悉，该话题最初在微博平台引发讨论，随后迅速蔓延至知乎、B站等平台，形成跨平台传播态势。截至目前，相关话题累计讨论量持续攀升。\n\n` +
`业内分析人士指出，${hot.display_title} 之所以能获得如此高的关注度，与其所涉及的 ${hot.category || '综合'} 议题密切相关。\n\n` +
`编辑：热点聚合工作台 | 数据来源：微博/知乎/百度/B站`,

    short: `【短视频口播文案 - "${hot.display_title}"】\n\n` +
`🎬 时长：60秒\n\n` +
`[开场] 家人们！今天聊一个全网都在关注的事——${hot.display_title}\n\n` +
`[事件] 这事儿现在已经冲上了 ${plats} 的热搜，热度直接拉到 ${Math.round(hot.total_weight)} 分！到底发生了什么？一分钟给你说明白。\n\n` +
`[观点] 我个人觉得，${hot.display_title} 这个事情，反映了一个更深层次的问题。大家的关注是好事，但更重要的是……\n\n` +
`[收尾] 对这个事儿你怎么看？评论区聊聊！记得点赞关注！`,

    social: `📢 ${hot.display_title}\n\n` +
`今天热搜又被这事儿刷屏了！在 ${plats} 上热度直接飙到 ${Math.round(hot.total_weight)} 分 🔥\n\n` +
`简单来说就是……\n\n` +
`评论区说说你的看法？👇\n\n` +
`#热点速递 #今日热议`
  }

  const content = templates.article  // 默认用 article 模板
  // 添加为系统消息
  const sysMsg = { _tempId: Date.now(), role: 'assistant', content, status: 'completed', isTemplate: true }
  messages.value.push(sysMsg)
  scrollToBottom()
  showToast('免费模板已生成（本地生成，无需 API）')
}

// ============ 发送消息 ============
async function sendMessage() {
  if (!canSend.value) return
  const prompt = promptInput.value.trim()

  // 用户消息先显示
  const userMsg = { _tempId: Date.now(), role: 'user', content: prompt, status: 'completed' }
  messages.value.push(userMsg)
  promptInput.value = ''
  scrollToBottom()

  generating.value = true
  // 助手占位
  const aiMsgPlaceholder = { _tempId: Date.now() + 1, role: 'assistant', content: '', status: 'generating' }
  messages.value.push(aiMsgPlaceholder)
  scrollToBottom()

  try {
    let resp
    if (currentConvId.value) {
      // 追加消息
      resp = await fetch(`/api/conversations/${currentConvId.value}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
    } else {
      // 新建对话
      resp = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          hotspot_title: selectedHot.value?.display_title || '',
          hotspot_id: selectedHot.value?.id,
        }),
      })
    }

    const data = await resp.json()
    if (resp.ok) {
      currentConvId.value = data.id || currentConvId.value
      const aiMsgId = data.ai_msg_id
      startPolling(aiMsgId, aiMsgPlaceholder._tempId)
    } else {
      aiMsgPlaceholder.status = 'failed'
      aiMsgPlaceholder.content = `[错误] ${data.detail || '发送失败'}`
      generating.value = false
    }
  } catch (e) {
    aiMsgPlaceholder.status = 'failed'
    aiMsgPlaceholder.content = `[错误] ${e.message}`
    generating.value = false
  }
}

function startPolling(aiMsgId, tempId) {
  let attempts = 0
  const maxAttempts = 90  // 最多 90 秒
  if (pollTimer) clearInterval(pollTimer)

  pollTimer = setInterval(async () => {
    attempts++
    if (attempts > maxAttempts) {
      clearInterval(pollTimer)
      generating.value = false
      const placeholder = messages.value.find(m => m._tempId === tempId)
      if (placeholder) placeholder.content = '[超时] AI 响应超时（90秒），请重试'
      showToast('生成超时')
      return
    }
    try {
      const res = await fetch(`/api/conversations/${currentConvId.value}`)
      if (!res.ok) {
        clearInterval(pollTimer)
        generating.value = false
        return
      }
      const data = await res.json()
      if (data.messages) {
        // 找到占位对应的真实消息（兼容 aiMsgId 缺失情况）
        let realAiMsg = null
        if (aiMsgId) {
          realAiMsg = data.messages.find(m => m.id === aiMsgId)
        }
        // 如果没有指定 aiMsgId，找最后一条 assistant 消息
        if (!realAiMsg) {
          const assistants = data.messages.filter(m => m.role === 'assistant')
          realAiMsg = assistants[assistants.length - 1]
        }

        if (realAiMsg) {
          const placeholder = messages.value.find(m => m._tempId === tempId)
          if (placeholder) {
            placeholder.content = realAiMsg.content
            placeholder.tokens = realAiMsg.tokens
            placeholder.status = realAiMsg.status
            if (realAiMsg.id) placeholder.id = realAiMsg.id
            scrollToBottom()
          }
          convTotalTokens.value = data.total_tokens || 0
        }

        // 检查是否还在生成
        const stillGenerating = data.messages.some(m => m.status === 'generating')
        if (!stillGenerating) {
          generating.value = false
          clearInterval(pollTimer)
          const failed = data.messages.find(m => m.status === 'failed')
          if (failed) {
            showToast('生成失败：' + (failed.content?.slice(0, 50) || '未知'))
          } else {
            showToast('AI 已回复')
          }
        }
      }
    } catch (e) { /* ignore */ }
  }, 1000)
}

async function newConversation() {
  if (messages.value.length && !confirm('开始新对话？当前对话已保存到历史，可继续查看。')) return
  currentConvId.value = null
  messages.value = []
  convTotalTokens.value = 0
  showToast('已开始新对话')
}

// ============ 历史对话 ============
async function loadHistory() {
  try {
    const res = await fetch('/api/conversations')
    const data = await res.json()
    conversations.value = data.items
    showHistory.value = true
  } catch (e) {}
}

async function loadConversation(id) {
  try {
    const res = await fetch(`/api/conversations/${id}`)
    const data = await res.json()
    if (data.messages) {
      currentConvId.value = id
      messages.value = data.messages
      convTotalTokens.value = data.total_tokens || 0
      // 同步热点信息
      if (data.hotspot_title && !selectedHot.value) {
        selectedHot.value = { display_title: data.hotspot_title }
      }
      showHistory.value = false
      scrollToBottom()
      showToast(`已加载对话 #${id}`)
    }
  } catch (e) { showToast('加载失败') }
}

async function deleteConversation(id) {
  if (!confirm('确认删除此对话？')) return
  await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
  conversations.value = conversations.value.filter(c => c.id !== id)
  if (currentConvId.value === id) {
    currentConvId.value = null
    messages.value = []
  }
  showToast('已删除')
}

// ============ 保存到文件 ============
async function saveAsFile() {
  if (!messages.value.length) return
  const path = await getSavePath()
  const content = messages.value.map(m =>
    `【${m.role === 'user' ? '你' : 'AI'}】\n${m.content}\n\n---\n\n`
  ).join('')

  try {
    // 让后端保存（这样能跨平台）
    const filename = `conversation_${currentConvId.value || Date.now()}.md`
    const res = await fetch('/api/conversations/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, filename, path, conversation_id: currentConvId.value }),
    })
    const data = await res.json()
    if (data.status === 'success') {
      showToast(`已保存: ${data.full_path}`)
    } else {
      // 退化为浏览器下载
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
      showToast('已下载到浏览器默认目录')
    }
  } catch (e) {
    // 退化为下载
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `conversation_${Date.now()}.md`; a.click()
    URL.revokeObjectURL(url)
  }
}

async function getSavePath() {
  try {
    const res = await fetch('/api/settings/storage')
    const data = await res.json()
    return data.path || ''
  } catch { return '' }
}

// ============ 工具 ============
function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  const now = new Date()
  const diff = Math.floor((now - d) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff/60)}小时前`
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

onMounted(async () => {
  await fetchAIStatus()
  if (route.params.id) {
    const hot = await store.getHotspotDetail(parseInt(route.params.id))
    if (hot) selectedHot.value = hot
  } else if (!store.hotspots.length) {
    await store.fetchHotspots()
  }
  // 如果带 convId 参数（从我的→历史对话点击而来），自动加载对话
  if (route.query.convId) {
    await loadConversation(parseInt(route.query.convId))
    // 自动滚动到底部
    scrollToBottom()
  }
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.chat-history {
  max-height: 500px;
  overflow-y: auto;
  margin-bottom: 12px;
  padding: 8px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
  /* 当内滚动到底时允许外层滚动接续 */
  overscroll-behavior-y: auto;
}
.chat-bubble {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.chat-bubble.user {
  flex-direction: row-reverse;
}
.bubble-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: white;
}
.chat-bubble.user .bubble-avatar { background: var(--accent); }
.chat-bubble.assistant .bubble-avatar { background: linear-gradient(135deg, #8b5cf6, #ec4899); }
.bubble-content {
  flex: 1;
  min-width: 0;
  background: var(--bg-card);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}
.chat-bubble.user .bubble-content {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
.chat-bubble.user .bubble-content pre { color: white; margin: 0; }
.bubble-content pre {
  white-space: pre-wrap;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0;
}
.bubble-meta {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-top: 6px;
}
.bubble-generating {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.chat-input-card {
  border-left: 4px solid var(--accent);
}
.chat-textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 0.88rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 80px;
}
.chat-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}
.history-drawer {
  margin-top: 16px;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background 0.2s;
}
.conv-item:hover {
  background: var(--bg-hover);
}
.conv-title {
  flex: 1;
  font-size: 0.85rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.conv-meta {
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 2px;
}
.conv-hotspot {
  color: var(--accent);
}
.conv-tokens {
  color: #10b981;
}
</style>