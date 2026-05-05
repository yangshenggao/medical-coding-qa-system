<template>
  <div class="login-container">
    <div class="login-shell">
      <div class="login-intro">
        <div class="eyebrow">Medical Coding Reference Desk</div>
        <h1>医学编码问答系统</h1>
        <p class="intro-text">
          为医学编码、术语检索与规则解释提供统一工作台，覆盖
          <span>WHODrug</span>
          与
          <span>MedDRA</span>
          的中英文编码支持。
        </p>
        <div class="intro-notes">
          <div class="note-card">
            <strong>词典检索</strong>
            <span>结构化检索优先，减少编码歧义。</span>
          </div>
          <div class="note-card">
            <strong>智能解释</strong>
            <span>结合规则文档与候选术语给出专业建议。</span>
          </div>
        </div>
      </div>

      <div class="login-card">
      <div class="login-header">
        <div class="icon-badge">
          <el-icon :size="34"><ChatDotSquare /></el-icon>
        </div>
        <h2>登录工作台</h2>
        <p class="subtitle">基于 WHODrug和MedDRA的智能医学编码检索平台</p>
      </div>
      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        Internal access for authorized coding staff.
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(loginForm)
    userStore.setLoginInfo(res.data)
    ElMessage.success('登录成功')
    // 管理员跳转数据概览，普通用户跳转智能问答
    if (res.data.user.role === 'admin') {
      router.push('/home')
    } else {
      router.push('/chat')
    }
  } catch (err) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  position: relative;
}

.login-container::before {
  content: '';
  position: absolute;
  inset: 24px;
  border: 1px solid rgba(80, 96, 88, 0.16);
  border-radius: 28px;
  pointer-events: none;
}

.login-shell {
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 420px);
  gap: 28px;
  align-items: stretch;
}

.login-intro,
.login-card {
  border-radius: 28px;
  border: 1px solid rgba(69, 85, 78, 0.16);
  box-shadow: var(--med-shadow);
  backdrop-filter: blur(12px);
}

.login-intro {
  position: relative;
  overflow: hidden;
  padding: 48px 44px;
  background:
    linear-gradient(145deg, rgba(255, 250, 243, 0.92), rgba(238, 229, 216, 0.9)),
    radial-gradient(circle at top right, rgba(139, 61, 47, 0.12), transparent 28%);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.login-intro::after {
  content: '';
  position: absolute;
  right: -40px;
  top: 38px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(210, 180, 134, 0.26), transparent 70%);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(139, 61, 47, 0.2);
  color: var(--med-accent);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  background: rgba(255, 251, 245, 0.72);
}

.login-intro h1 {
  margin-top: 22px;
  max-width: 480px;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: clamp(34px, 4vw, 52px);
  line-height: 1.06;
  letter-spacing: -0.03em;
  color: var(--med-ink);
}

.intro-text {
  margin-top: 18px;
  max-width: 520px;
  color: var(--med-ink-soft);
  font-size: 16px;
  line-height: 1.8;
}

.intro-text span {
  color: var(--med-accent);
  font-weight: 700;
}

.intro-notes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 36px;
}

.note-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px 18px 20px;
  border-radius: 18px;
  border: 1px solid rgba(69, 85, 78, 0.12);
  background: rgba(255, 252, 246, 0.72);
}

.note-card strong {
  color: var(--med-ink);
  font-size: 15px;
}

.note-card span {
  color: var(--med-ink-soft);
  font-size: 13px;
  line-height: 1.7;
}

.login-card {
  width: 100%;
  padding: 42px 36px;
  background: rgba(255, 252, 246, 0.9);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.icon-badge {
  width: 72px;
  height: 72px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  color: var(--med-accent);
  background: linear-gradient(145deg, rgba(255, 248, 238, 0.96), rgba(235, 221, 203, 0.88));
  border: 1px solid rgba(139, 61, 47, 0.16);
  box-shadow: 0 18px 32px rgba(68, 54, 43, 0.08);
}

.login-header h2 {
  margin: 0 0 10px;
  color: var(--med-ink);
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.subtitle {
  color: var(--med-ink-soft);
  font-size: 13px;
  line-height: 1.7;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 50px;
  padding: 0 16px;
  border-radius: 14px;
}

.login-form :deep(.el-input__inner) {
  color: var(--med-ink);
}

.login-btn {
  width: 100%;
  height: 48px;
  border-radius: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.login-footer {
  text-align: center;
  margin-top: 14px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(83, 101, 95, 0.72);
}

@media (max-width: 960px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .login-intro {
    min-height: 320px;
  }
}

@media (max-width: 640px) {
  .login-container {
    padding: 16px;
  }

  .login-container::before {
    inset: 12px;
    border-radius: 22px;
  }

  .login-intro,
  .login-card {
    padding: 28px 22px;
    border-radius: 22px;
  }

  .intro-notes {
    grid-template-columns: 1fr;
  }
}
</style>
