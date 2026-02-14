<template>
  <div id="app">
    <el-container>
      <el-header class="app-header">
        <h1>📷 PhotoMind 照片管理</h1>
        <el-menu mode="horizontal" :default-active="activeMenu" router>
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/import">导入</el-menu-item>
          <el-menu-item index="/search">搜索</el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 20px;
  background: #409EFF;
  color: white;
  padding: 0 20px;
}

.app-header h1 {
  font-size: 24px;
  margin: 0;
}

.app-header .el-menu {
  background: transparent;
  border: none;
}

.app-header .el-menu-item {
  color: white !important;
  font-size: 18px;
}

.app-header .el-menu-item:hover,
.app-header .el-menu-item.is-active {
  background: rgba(255, 255, 255, 0.2) !important;
}
</style>
