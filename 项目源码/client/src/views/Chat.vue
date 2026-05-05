<template>
  <div class="chat-page">
    <section class="chat-hero">
      <div class="chat-hero-copy">
        <div class="hero-kicker">Medical Coding Workspace</div>
        <h1>智能问答</h1>
        <p>围绕词典候选、规则文档与编码解释开展对话，适合做检索后的进一步判断。</p>
      </div>
      <div class="hero-metric">
        <div class="hero-metric-value">02</div>
        <div class="hero-metric-label">Conversation Panels</div>
      </div>
    </section>

    <div class="chat-shell">
      <aside class="chat-sidebar">
        <div class="sidebar-heading">
          <div class="sidebar-title">选择知识库</div>
          <p>优先在左侧固定当前词典，再在右侧完成检索后的判断与追问。</p>
        </div>

        <div class="kb-list" v-if="kbList.length">
          <div
            v-for="kb in kbList"
            :key="kb.id"
            class="kb-card"
            :class="{ active: selectedKb?.id === kb.id }"
            @click="selectKb(kb)"
          >
            <div class="kb-card-head">
              <div class="kb-card-name">{{ kb.kb_name }}</div>
              <span class="kb-card-badge">{{ selectedKb?.id === kb.id ? 'Active' : kb.doc_count + '篇' }}</span>
            </div>
            <div class="kb-card-desc">{{ getKbGuideDesc(kb) }}</div>
          </div>
        </div>

        <div v-else class="empty-tip">
          <el-empty description="暂无知识库" :image-size="60" />
        </div>
      </aside>

      <section class="chat-main">
        <div class="workspace-head">
          <div class="workspace-copy">
            <div class="workspace-title">对话工作区</div>
            <div class="workspace-status" v-if="selectedKb">当前知识库：{{ selectedKb.kb_name }}</div>
            <div class="workspace-status hint" v-else>请先从左侧选择一个知识库</div>
          </div>
          <div class="workspace-tags">
            <span class="workspace-tag">候选术语</span>
            <span class="workspace-tag">规则文档</span>
            <span class="workspace-tag">编码解释</span>
          </div>
        </div>

        <div v-if="selectedKb" class="question-brief">
          <div class="brief-label">{{ getKbGuideTitle(selectedKb) }}</div>
          <div class="brief-desc">{{ getKbGuideDesc(selectedKb) }}</div>
          <div class="guide-examples">
            <button
              v-for="example in getKbExamples(selectedKb)"
              :key="example"
              class="guide-tag"
              type="button"
              @click="useExample(example)"
            >
              {{ example }}
            </button>
          </div>
        </div>

        <div class="chat-messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="welcome">
            <el-icon :size="64" color="rgba(83, 101, 95, 0.4)"><ChatDotSquare /></el-icon>
            <h3>欢迎使用医学编码智能问答</h3>
            <p>请选择 WHODrug 或 MedDRA 词典知识库，然后输入待编码的问题或术语描述。</p>
          </div>
          <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />
          <div v-if="asking" class="loading-msg">
            <el-avatar :size="36" :icon="Monitor" style="background-color: #385149" />
            <div class="loading-bubble">
              <span class="loading-dot">思考中</span>
              <el-icon class="is-loading"><Loading /></el-icon>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            placeholder="继续追问编码依据、术语层级或规则差异..."
            :disabled="!selectedKb || asking"
            @keydown.enter.exact.prevent="sendQuestion"
            resize="none"
          />
          <div class="chat-actions">
            <div class="input-note">建议先固定知识库，再围绕候选术语和规则依据继续追问。</div>
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="asking"
              :disabled="!selectedKb || !question.trim()"
              @click="sendQuestion"
              class="send-btn"
            >
              发送问题
            </el-button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Loading, Monitor } from '@element-plus/icons-vue'
import { getAllKB } from '../api/knowledge'
import { askQuestion } from '../api/chat'
import ChatMessage from '../components/ChatMessage.vue'

const kbList = ref([])
const selectedKb = ref(null)
const messages = ref([])
const question = ref('')
const asking = ref(false)
const sessionId = ref('')
const messagesRef = ref(null)

async function loadKBList() {
  try {
    const res = await getAllKB()
    kbList.value = res.data
  } catch (err) {
    // 错误已在拦截器处理
  }
}

function selectKb(kb) {
  if (selectedKb.value?.id === kb.id) return
  selectedKb.value = kb
  messages.value = []
  sessionId.value = generateSessionId()
  question.value = ''
}

function generateSessionId() {
  return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function getKbGuideTitle(kb) {
  const name = (kb?.kb_name || '').toLowerCase()
  if (name.includes('whodrug')) return '当前为药物编码建议模式'
  if (name.includes('meddra')) return '当前为术语编码建议模式'
  return '当前为知识库问答模式'
}

function getKbGuideDesc(kb) {
  const name = (kb?.kb_name || '').toLowerCase()
  if (name.includes('whodrug')) {
    return '适合输入药品名、商品名、活性成分、Drug Code 或 MPID，系统会返回候选药物编码记录。'
  }
  if (name.includes('meddra')) {
    return '适合输入症状、诊断、检查描述或不良事件表达，系统会返回候选 MedDRA 术语与层级。'
  }
  return '可以直接输入问题，系统会结合所选知识库内容回答。'
}

function getKbExamples(kb) {
  const name = (kb?.kb_name || '').toLowerCase()
  if (name.includes('whodrug')) {
    return [
      '查询甲基多巴对应的 WHODrug 编码',
      '帮我查找含地塞米松的候选药物记录',
      'Drug Code 000001-01-001 对应什么药品'
    ]
  }
  if (name.includes('meddra')) {
    return [
      '请推荐与胸闷气短相关的 MedDRA 术语',
      '搜索咳嗽伴发热的候选编码',
      '帮我查找与影像异常描述相关的 MedDRA 术语'
    ]
  }
  return ['这个知识库可以回答什么问题？']
}

function useExample(example) {
  question.value = example
}

async function sendQuestion() {
  const q = question.value.trim()
  if (!q || !selectedKb.value || asking.value) return

  messages.value.push({ role: 'user', content: q })
  question.value = ''
  asking.value = true
  scrollToBottom()

  try {
    const res = await askQuestion({
      question: q,
      kb_id: selectedKb.value.id,
      session_id: sessionId.value
    })

    messages.value.push({
      role: 'ai',
      content: res.data.answer,
      sources: res.data.source_docs
    })
  } catch (err) {
    messages.value.push({
      role: 'ai',
      content: '抱歉，服务出现异常，请稍后重试。'
    })
  } finally {
    asking.value = false
    scrollToBottom()
  }
}

onMounted(() => loadKBList())
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: calc(100vh - 130px);
}

.chat-hero,
.chat-shell {
  border-radius: 32px;
  border: 1px solid rgba(153, 132, 99, 0.28);
  background: rgba(252, 247, 238, 0.88);
  box-shadow: 0 24px 56px rgba(78, 66, 42, 0.08);
}

.chat-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 28px;
  padding: 30px 34px;
}

.chat-hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-kicker {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--med-accent);
}

.chat-hero h1 {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 34px;
  line-height: 1.2;
  color: var(--med-ink);
}

.chat-hero p {
  max-width: 760px;
  color: var(--med-ink-soft);
  line-height: 1.8;
}

.hero-metric {
  flex: 0 0 164px;
  min-height: 88px;
  border-radius: 24px;
  border: 1px solid rgba(153, 132, 99, 0.22);
  background: linear-gradient(180deg, rgba(236, 228, 210, 0.96), rgba(230, 219, 195, 0.86));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.hero-metric-value {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 34px;
  color: var(--med-ink);
}

.hero-metric-label {
  font-size: 12px;
  color: var(--med-ink-soft);
}

.chat-shell {
  display: grid;
  grid-template-columns: 294px minmax(0, 1fr);
  gap: 24px;
  padding: 24px;
  min-height: 680px;
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  border-radius: 28px;
  border: 1px solid rgba(153, 132, 99, 0.24);
  background: rgba(255, 252, 246, 0.78);
  padding: 28px 22px;
  min-width: 0;
}

.sidebar-heading {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 18px;
}

.sidebar-title {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-weight: 600;
  font-size: 24px;
  color: var(--med-ink);
}

.sidebar-heading p {
  color: var(--med-ink-soft);
  font-size: 13px;
  line-height: 1.7;
}

.kb-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.kb-card {
  border-radius: 22px;
  border: 1px solid rgba(176, 152, 113, 0.34);
  background: linear-gradient(180deg, rgba(255, 249, 240, 0.96), rgba(247, 240, 229, 0.82));
  padding: 18px;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
  color: var(--med-ink-soft);
}

.kb-card:hover {
  transform: translateY(-1px);
  border-color: rgba(139, 61, 47, 0.38);
}

.kb-card.active {
  background: linear-gradient(180deg, rgba(30, 58, 52, 0.96), rgba(45, 78, 70, 0.92));
  border-color: transparent;
  color: #fffaf3;
}

.kb-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.kb-card-name {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.35;
}

.kb-card-badge {
  flex-shrink: 0;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1;
  color: var(--med-accent);
  background: rgba(213, 184, 146, 0.26);
}

.kb-card.active .kb-card-badge {
  color: #fffaf3;
  background: rgba(196, 126, 92, 0.84);
}

.kb-card-desc {
  font-size: 12px;
  line-height: 1.75;
  color: inherit;
  opacity: 0.86;
}

.empty-tip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-main {
  display: flex;
  flex-direction: column;
  border-radius: 28px;
  border: 1px solid rgba(153, 132, 99, 0.24);
  background: rgba(255, 252, 247, 0.88);
  min-width: 0;
  padding: 24px;
  overflow: hidden;
}

.workspace-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.workspace-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.workspace-title {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 30px;
  color: var(--med-ink);
}

.workspace-status {
  color: var(--med-ink-soft);
  font-size: 13px;
}

.workspace-status.hint {
  opacity: 0.9;
}

.workspace-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workspace-tag {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(153, 132, 99, 0.22);
  background: rgba(244, 236, 220, 0.78);
  color: var(--med-ink-soft);
  font-size: 12px;
  font-weight: 600;
}

.question-brief {
  border-radius: 22px;
  border: 1px solid rgba(181, 157, 119, 0.22);
  background: linear-gradient(180deg, rgba(252, 247, 239, 0.96), rgba(246, 238, 225, 0.86));
  padding: 18px 20px;
  margin-bottom: 18px;
}

.brief-label {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--med-accent);
  margin-bottom: 8px;
}

.brief-desc {
  font-size: 14px;
  color: var(--med-ink-soft);
  line-height: 1.75;
  margin-bottom: 12px;
}

.guide-examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.guide-tag {
  appearance: none;
  border: 1px solid rgba(176, 152, 113, 0.26);
  background: rgba(255, 251, 244, 0.92);
  color: var(--med-ink-soft);
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.guide-tag:hover {
  border-color: rgba(139, 61, 47, 0.34);
  color: var(--med-ink);
  transform: translateY(-1px);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px 4px 18px;
  min-height: 350px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: rgba(83, 101, 95, 0.56);
  gap: 12px;
}

.welcome h3 {
  color: var(--med-ink-soft);
  font-size: 20px;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
}

.welcome p {
  font-size: 14px;
  color: rgba(83, 101, 95, 0.72);
}

.loading-msg {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.loading-bubble {
  background: rgba(255, 248, 239, 0.95);
  border-radius: 16px;
  padding: 12px 15px;
  border: 1px solid rgba(64, 84, 77, 0.08);
}

.loading-dot {
  margin-right: 8px;
}

.chat-input {
  border-radius: 24px;
  border: 1px solid rgba(181, 157, 119, 0.22);
  background: rgba(255, 251, 246, 0.92);
  padding: 16px 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chat-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.input-note {
  color: var(--med-ink-soft);
  font-size: 12px;
  line-height: 1.7;
}

.send-btn {
  height: 42px;
  border-radius: 999px;
  min-width: 112px;
  letter-spacing: 0.04em;
  padding: 0 20px;
}

.chat-main :deep(.el-textarea__inner) {
  min-height: 64px !important;
  border-radius: 18px;
  padding: 14px 16px;
  line-height: 1.7;
  background: rgba(253, 249, 241, 0.96);
  border-color: rgba(181, 157, 119, 0.22);
}

@media (max-width: 1180px) {
  .chat-hero,
  .chat-shell {
    grid-template-columns: 1fr;
  }

  .chat-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-metric {
    width: 100%;
    max-width: 220px;
  }

  .chat-sidebar {
    width: 100%;
  }
}

@media (max-width: 760px) {
  .chat-page {
    gap: 18px;
  }

  .chat-hero {
    padding: 22px 20px;
  }

  .chat-hero h1,
  .workspace-title,
  .sidebar-title {
    font-size: 26px;
  }

  .chat-shell,
  .chat-main {
    padding: 18px;
  }

  .chat-actions,
  .workspace-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .send-btn {
    width: 100%;
  }
}
</style>
