<template>
  <!-- 顶部用户头像（仅在抽屉关闭时显示） -->
  <button v-if="!drawerOpen" class="avatar-trigger" @click="toggleDrawer" title="展开菜单">
    <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
      <path d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"/>
    </svg>
  </button>

  <!-- 抽屉遮罩 -->
  <transition name="drawer-fade">
    <div v-if="drawerOpen" class="drawer-backdrop" @click="closeDrawer"></div>
  </transition>

  <!-- 抽屉菜单 -->
  <transition name="drawer-slide">
    <nav v-if="drawerOpen" class="side-drawer">
      <div class="drawer-header">
        <div class="drawer-avatar">
          <svg viewBox="0 0 24 24" width="40" height="40" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
        </div>
        <div>
          <div style="font-weight:600;font-size:0.95rem;">访客用户</div>
          <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px;">本地数据存储</div>
        </div>
      </div>

      <div class="drawer-divider"></div>

      <div class="drawer-nav">
        <router-link to="/" class="drawer-link" @click="closeDrawer">
          <span class="link-icon">📊</span>
          <span class="link-text">热点看板</span>
        </router-link>
        <router-link to="/my" class="drawer-link" @click="closeDrawer">
          <span class="link-icon">👤</span>
          <span class="link-text">我的</span>
          <span v-if="myUnseen > 0" class="red-dot-badge">{{ myUnseen > 99 ? '99+' : myUnseen }}</span>
        </router-link>
        <router-link to="/history" class="drawer-link" @click="closeDrawer">
          <span class="link-icon">📋</span>
          <span class="link-text">采集历史</span>
        </router-link>
        <router-link to="/manage" class="drawer-link" @click="closeDrawer">
          <span class="link-icon">⚙️</span>
          <span class="link-text">设置</span>
        </router-link>
      </div>

      <div class="drawer-divider"></div>

      <div style="flex:1;"></div>

      <div style="padding:12px;font-size:0.7rem;color:var(--text-muted);text-align:center;">
        热点聚合工作台 v1.0
      </div>
    </nav>
  </transition>
</template>

<script setup>
import { ref, inject, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const drawerOpen = ref(false)
const showToast = inject('showToast', () => {})
const myUnseen = ref(0)
let unseenTimer = null

async function fetchUnseen() {
  try {
    const res = await fetch('/api/my/unseen')
    const data = await res.json()
    myUnseen.value = data.unseen || 0
  } catch (e) {}
}

function toggleDrawer() {
  drawerOpen.value = !drawerOpen.value
}

function closeDrawer() {
  drawerOpen.value = false
}

// 主题切换
const isDark = ref(false)
function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  document.documentElement.className = isDark.value ? 'dark' : ''
}

// 监听路由变化自动关闭抽屉
import { watch } from 'vue'
watch(() => router.currentRoute.value.path, () => {
  drawerOpen.value = false
})

onMounted(() => {
  // 读取主题
  const saved = localStorage.getItem('theme')
  isDark.value = saved === 'dark'

  // 启动红点轮询
  fetchUnseen()
  unseenTimer = setInterval(fetchUnseen, 5000)

  // 进入 /my 路由时清除红点
  router.afterEach((to) => {
    if (to.path === '/my') {
      fetch('/api/my/seen', { method: 'POST' }).catch(() => {})
      myUnseen.value = 0
    }
  })
})

onBeforeUnmount(() => {
  if (unseenTimer) clearInterval(unseenTimer)
})
</script>

<style scoped>
.avatar-trigger {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 200;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  background: linear-gradient(135deg, #8b5cf6, #ec4899);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-md);
  transition: transform 0.2s;
}
.avatar-trigger:hover {
  transform: scale(1.08);
}
.avatar-trigger:active {
  transform: scale(0.95);
}
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  z-index: 150;
}
.side-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  max-width: 80vw;
  background: var(--bg-card);
  border-right: 1px solid var(--border-color);
  z-index: 160;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 20px rgba(0,0,0,0.15);
}
.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
}
.drawer-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6, #ec4899);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}
.drawer-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}
.drawer-nav {
  padding: 8px 0;
}
.drawer-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: var(--text-primary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s;
}
.drawer-link:hover {
  background: var(--bg-hover);
}
.drawer-link.router-link-active {
  background: var(--accent-light);
  color: var(--accent);
  border-left: 3px solid var(--accent);
}
.drawer-exit {
  color: var(--danger);
}
.drawer-exit:hover {
  background: rgba(239, 68, 68, 0.1);
}
.link-icon {
  font-size: 1.1rem;
  width: 24px;
  text-align: center;
}
.link-text {
  flex: 1;
}
.red-dot-badge {
  background: #ef4444;
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  margin-left: auto;
}

.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.25s ease;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}
.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(-100%);
}
</style>