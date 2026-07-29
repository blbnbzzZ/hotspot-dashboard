<template>
  <nav class="bottom-nav">
    <router-link to="/" class="nav-item" exact-active-class="router-link-active">
      <span class="nav-icon">📊</span>
      <span>看板</span>
    </router-link>
    <router-link to="/my" class="nav-item" active-class="router-link-active">
      <span class="nav-icon">👤</span>
      <span>我的</span>
    </router-link>
    <router-link to="/history" class="nav-item" active-class="router-link-active">
      <span class="nav-icon">📋</span>
      <span>历史</span>
    </router-link>
    <router-link to="/manage" class="nav-item" active-class="router-link-active">
      <span class="nav-icon">⚙️</span>
      <span>管理</span>
    </router-link>
  </nav>
</template>
