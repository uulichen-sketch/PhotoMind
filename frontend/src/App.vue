<template>
  <div id="app">
    <nav class="app-nav">
      <div class="nav-brand">
        <div class="logo">
          <span class="logo-icon">📷</span>
          <span class="logo-text">PhotoMind</span>
        </div>
      </div>
      <div class="nav-menu">
        <router-link 
          v-for="item in menuItems" 
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { active: route.path === item.path }]"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </div>
    </nav>
    
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = [
  { path: '/', label: '首页', icon: '🏠' },
  { path: '/import', label: '导入', icon: '📥' },
  { path: '/search', label: '搜索', icon: '🔍' },
  { path: '/faces', label: '人物', icon: '👤' },
]
</script>

<style scoped>
#app {
  min-height: 100vh;
  display: flex;
}

.app-nav {
  width: 240px;
  background: var(--card-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
}

.nav-brand {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 32px;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-menu {
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  color: var(--text-secondary);
  text-decoration: none;
  font-weight: 500;
  transition: var(--transition);
}

.nav-item:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

.nav-item.active {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  color: white;
  box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
}

.nav-icon {
  font-size: 20px;
}

.nav-label {
  font-size: 16px;
}

.app-main {
  flex: 1;
  margin-left: 240px;
  padding: 32px;
  min-height: 100vh;
}

/* 响应式 */
@media (max-width: 768px) {
  .app-nav {
    width: 100%;
    height: auto;
    position: fixed;
    bottom: 0;
    top: auto;
    border-right: none;
    border-top: 1px solid var(--border-color);
    flex-direction: row;
    justify-content: space-around;
  }
  
  .nav-brand {
    display: none;
  }
  
  .nav-menu {
    flex-direction: row;
    justify-content: space-around;
    width: 100%;
    padding: 8px;
  }
  
  .nav-item {
    flex-direction: column;
    padding: 8px 16px;
    gap: 4px;
  }
  
  .nav-icon {
    font-size: 24px;
  }
  
  .nav-label {
    font-size: 12px;
  }
  
  .app-main {
    margin-left: 0;
    margin-bottom: 80px;
    padding: 20px;
  }
}
</style>
