<template>
  <nav class="top-navbar">
    <router-link to="/" class="navbar-brand">
      <div class="brand-icon">🔥</div>
      <span>热点聚合</span>
    </router-link>
    <div class="navbar-actions">
      <button class="theme-toggle" @click="$emit('toggleTheme')" :title="isDark ? '切换亮色' : '切换暗色'">
        {{ isDark ? '☀️' : '🌙' }}
      </button>
    </div>
  </nav>
</template>

<script setup>
defineProps({ isDark: Boolean })
defineEmits(['toggleTheme'])
</script>
