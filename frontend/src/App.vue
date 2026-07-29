<template>
  <div class="app-layout" :class="{ dark: isDark }">
    <SideNav />
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <transition name="slide-up">
      <div v-if="toast.show" class="toast">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import SideNav from './components/SideNav.vue'
import { useHotspotStore } from './stores/hotspot'

const store = useHotspotStore()
const isDark = ref(false)
const toast = ref({ show: false, message: '' })

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  document.documentElement.className = isDark.value ? 'dark' : ''
}

function showToast(msg, duration = 2500) {
  toast.value = { show: true, message: msg }
  setTimeout(() => { toast.value.show = false }, duration)
}

provide('showToast', showToast)
provide('isDark', isDark)
provide('toggleTheme', toggleTheme)

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    isDark.value = true
    document.documentElement.className = 'dark'
  }

  store.fetchHotspots()
  store.fetchStats()
  store.fetchCommonHotspots()
})
</script>