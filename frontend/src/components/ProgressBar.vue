<template>
  <transition name="progress-fade">
    <div v-if="visible" class="progress-bar-container">
      <div class="progress-bar-track">
        <div class="progress-bar-fill" :style="{ width: percent + '%' }"></div>
      </div>
      <div class="progress-bar-text" v-if="showText">
        {{ text || `${Math.round(percent)}%` }}
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  loading: { type: Boolean, default: false },
  percent: { type: Number, default: 0 },
  indeterminate: { type: Boolean, default: true },
  text: { type: String, default: '' },
  showText: { type: Boolean, default: true },
})

const visible = computed(() => props.loading)
const percent = computed(() => {
  if (props.indeterminate) return 100
  return Math.min(100, Math.max(0, props.percent))
})
</script>

<style scoped>
.progress-bar-container {
  position: sticky;
  top: var(--navbar-height);
  z-index: 50;
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 10px 0;
  margin-bottom: 12px;
  border-radius: var(--radius-md);
}

.progress-bar-track {
  width: 100%;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #8b5cf6, var(--accent));
  background-size: 200% 100%;
  border-radius: 3px;
  transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  animation: shimmer 1.5s linear infinite;
  box-shadow: 0 0 10px rgba(59, 109, 240, 0.5);
}

@keyframes shimmer {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

.progress-bar-text {
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 4px;
  font-weight: 500;
}

.progress-fade-enter-active,
.progress-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.progress-fade-enter-from,
.progress-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>