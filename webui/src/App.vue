<template>
  <div id="app">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>VisionGame WebUI</h1>
          <el-menu mode="horizontal" :default-active="route.path" router>
            <el-menu-item index="/">首页</el-menu-item>
            <el-menu-item index="/atlas">图集管理</el-menu-item>
            <el-menu-item index="/models">模型管理</el-menu-item>
            <el-menu-item index="/training">训练监控</el-menu-item>
            <el-menu-item index="/launch">模型启动</el-menu-item>
          </el-menu>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}
#app {
  height: 100vh;
}
.el-header {
  background-color: #545c64;
  color: white;
  padding: 0;
}
.header-content {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 20px;
}
.header-content h1 {
  font-size: 20px;
  margin-right: 40px;
  color: white;
}
.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
