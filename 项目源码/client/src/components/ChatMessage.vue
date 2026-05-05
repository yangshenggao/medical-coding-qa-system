<template>
  <!-- 对话消息气泡组件 -->
  <div class="message-wrapper" :class="{ 'is-user': isUser }">
    <div class="avatar">
      <el-avatar :size="36" :icon="isUser ? UserFilled : Monitor" :style="avatarStyle" />
    </div>
    <div class="bubble" :class="{ 'user-bubble': isUser, 'ai-bubble': !isUser }">
      <div class="message-text">{{ message.content }}</div>
      <!-- AI回答时显示参考来源 -->
      <div v-if="!isUser && message.sources?.length" class="sources">
        <div class="sources-title">参考来源：</div>
        <el-tag
          v-for="(src, i) in message.sources"
          :key="i"
          size="small"
          type="info"
          class="source-tag"
        >
          {{ src.file_name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 对话消息气泡组件
 * 区分用户消息和AI回答，AI回答可展示参考来源
 */
import { computed } from 'vue'
import { UserFilled, Monitor } from '@element-plus/icons-vue'

const props = defineProps({
  /** 消息对象 { role: 'user'|'ai', content: string, sources?: array } */
  message: { type: Object, required: true }
})

/** 是否为用户消息 */
const isUser = computed(() => props.message.role === 'user')

/** 头像样式 */
const avatarStyle = computed(() => ({
  backgroundColor: isUser.value ? '#8b3d2f' : '#385149'
}))
</script>

<style scoped>
.message-wrapper {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message-wrapper.is-user {
  flex-direction: row-reverse;
}

.bubble {
  max-width: 70%;
  padding: 14px 18px;
  border-radius: 18px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
  box-shadow: var(--med-shadow-soft);
}

.user-bubble {
  background: linear-gradient(145deg, #8b3d2f, #b06550);
  color: #fff9f1;
  border-top-right-radius: 6px;
}

.ai-bubble {
  background: rgba(255, 251, 245, 0.95);
  color: var(--med-ink);
  border-top-left-radius: 6px;
  border: 1px solid rgba(64, 84, 77, 0.08);
}

.message-text {
  font-size: 14px;
  line-height: 1.8;
}

.sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(64, 84, 77, 0.08);
}

.sources-title {
  font-size: 12px;
  color: var(--med-ink-soft);
  margin-bottom: 6px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.source-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}
</style>
