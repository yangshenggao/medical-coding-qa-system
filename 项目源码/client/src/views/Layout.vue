<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="24"><FirstAidKit /></el-icon>
        <span v-show="!isCollapse" class="logo-text">医学编码问答系统</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        :router="true"
        class="aside-menu"
      >
        <!-- 管理员菜单 -->
        <template v-if="userStore.isAdmin">
          <el-menu-item index="/home">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>数据概览</template>
          </el-menu-item>
          <el-menu-item index="/import">
            <el-icon><Upload /></el-icon>
            <template #title>数据导入</template>
          </el-menu-item>
          <el-menu-item index="/user-manage">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
        </template>
        
        <!-- 通用菜单 -->
        <el-menu-item index="/whodrug">
          <el-icon><Search /></el-icon>
          <template #title>WHODrug查询</template>
        </el-menu-item>
        <el-menu-item index="/meddra">
          <el-icon><Search /></el-icon>
          <template #title>MedDRA搜索</template>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能问答</template>
        </el-menu-item>
        <el-menu-item index="/chat-history">
          <el-icon><Clock /></el-icon>
          <template #title>对话历史</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span class="page-title">{{ $route.meta.title }}</span>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.userInfo?.nickname }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { UserFilled, FirstAidKit, DataAnalysis, Upload, Search, ChatDotRound, Clock, Fold, Expand, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)

function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  background: transparent;
}

.aside {
  margin: 18px 0 18px 18px;
  border-radius: 26px;
  border: 1px solid rgba(53, 67, 61, 0.2);
  background:
    linear-gradient(180deg, rgba(38, 53, 48, 0.97), rgba(29, 42, 38, 0.94));
  box-shadow: 0 24px 44px rgba(28, 38, 34, 0.16);
  transition: width 0.3s ease;
  overflow: hidden;
}

.logo {
  height: 78px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  color: #f8f2e8;
  gap: 12px;
  padding: 0 22px;
  border-bottom: 1px solid rgba(255, 245, 230, 0.09);
  letter-spacing: 0.04em;
}

.logo-text {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.aside-menu {
  border-right: none;
  background: transparent;
  padding: 14px 10px 18px;
}

.aside-menu :deep(.el-menu) {
  border-right: none;
  background: transparent;
}

.aside-menu :deep(.el-menu-item) {
  height: 48px;
  margin: 6px 8px;
  border-radius: 14px;
  color: rgba(247, 239, 227, 0.72);
  transition: all 0.24s ease;
}

.aside-menu :deep(.el-menu-item:hover) {
  background: rgba(238, 217, 186, 0.12);
  color: #fff8ef;
}

.aside-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(139, 61, 47, 0.72), rgba(176, 118, 84, 0.52));
  color: #fffaf4;
  box-shadow: inset 0 0 0 1px rgba(255, 238, 208, 0.08);
}

.aside-menu :deep(.el-menu-item .el-icon) {
  font-size: 16px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 18px 18px 0 18px;
  padding: 0 26px;
  height: 76px;
  border-radius: 24px;
  border: 1px solid rgba(64, 84, 77, 0.12);
  background: rgba(255, 251, 244, 0.82);
  box-shadow: var(--med-shadow-soft);
  backdrop-filter: blur(12px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--med-ink-soft);
  transition: color 0.2s ease, transform 0.2s ease;
}

.collapse-btn:hover {
  color: var(--med-accent);
  transform: translateX(-1px);
}

.page-title {
  font-size: 20px;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-weight: 600;
  color: var(--med-ink);
}

.header-right .user-info {
  padding: 8px 14px 8px 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  border-radius: 999px;
  background: rgba(243, 234, 220, 0.7);
  border: 1px solid rgba(64, 84, 77, 0.08);
}

.username {
  font-size: 14px;
  color: var(--med-ink-soft);
}

.main {
  background: transparent;
  padding: 18px;
  overflow-y: auto;
}
</style>
