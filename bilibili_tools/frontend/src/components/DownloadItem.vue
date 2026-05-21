<template>
  <div :class="['download-item', `status-${task.status}`]">
    <!-- 缩略图 -->
    <img
      :src="thumbUrl"
      class="item-thumb"
      :alt="task.title"
    />

    <!-- 信息区 -->
    <div class="item-info">
      <div class="item-title" :title="task.title">{{ task.title }}</div>
      <div class="item-meta">
        <!-- 进度条（下载中） -->
        <template v-if="task.status === 'active'">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
          </div>
          <span class="progress-text">{{ task.progress }}%</span>
          <span v-if="task.speed" class="speed-text">{{ task.speed }}</span>
        </template>
        <!-- 提交中 -->
        <span v-else-if="task.status === 'submitting'" class="submitting-text">提交中...</span>
        <!-- 排队序号 -->
        <span v-else-if="task.status === 'pending'" class="queue-num">
          排队中 #{{ task.queuePosition }}
        </span>
        <!-- 完成标记 -->
        <span v-else-if="task.status === 'done'" class="done-mark">✓ 已完成</span>
        <!-- 失败 -->
        <span v-else-if="task.status === 'failed'" class="fail-mark">✕ {{ task.error || '下载失败' }}</span>
      </div>
    </div>

    <!-- 操作按钮区 -->
    <div class="item-actions">
      <!-- 下载中 -->
      <template v-if="task.status === 'active'">
        <button class="action-btn" @click="$emit(task.paused ? 'resume' : 'pause')" :title="task.paused ? '继续' : '暂停'">
          {{ task.paused ? '▶' : '⏸' }}
        </button>
        <button class="action-btn danger" @click="$emit('cancel')" title="取消">✕</button>
      </template>

      <!-- 等待中 -->
      <template v-else-if="task.status === 'pending'">
        <button class="action-btn" @click="$emit('cancel')" title="取消">✕</button>
        <button class="action-btn" @click="$emit('prioritize')" title="优先下载">⬆</button>
      </template>

      <!-- 已完成 -->
      <template v-else-if="task.status === 'done'">
        <button class="action-btn" @click="$emit('open-file')" title="打开文件">📁</button>
        <button class="action-btn danger" @click="$emit('remove')" title="删除">🗑</button>
      </template>

      <!-- 失败 -->
      <template v-else-if="task.status === 'failed'">
        <button class="action-btn retry-btn" @click="$emit('retry')" title="仍要下载（删除本地文件后重新下载）">↻ 仍要下载</button>
        <button class="action-btn danger" @click="$emit('remove')" title="删除">🗑</button>
      </template>

      <!-- 提交中 — 仅显示加载状态 -->
      <template v-else-if="task.status === 'submitting'">
        <span class="submitting-text">...</span>
      </template>

      <!-- 统一：打开所在文件夹 -->
      <button class="action-btn" @click="$emit('open-folder')" title="打开文件夹">📂</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { proxyImageUrl } from '../utils/api'

const props = defineProps({
  task: { type: Object, required: true },
})
defineEmits(['pause', 'resume', 'cancel', 'prioritize', 'remove', 'open-file', 'open-folder', 'retry'])

const thumbUrl = computed(() => proxyImageUrl(props.task.thumbnail || props.task.pic))
</script>

<style scoped>
.download-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: border-color 0.2s;
}

.download-item.status-active {
  border-color: var(--accent);
}

.download-item.status-done {
  border-color: var(--success);
  opacity: 0.85;
}

.download-item.status-failed {
  border-color: var(--danger);
}

.item-thumb {
  width: 56px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
  background: var(--bg-secondary);
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  flex: 1;
  max-width: 200px;
  height: 6px;
  background: var(--bg-secondary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
  min-width: 38px;
}

.speed-text {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.queue-num {
  font-size: 0.8rem;
  color: var(--warning);
}

.done-mark {
  font-size: 0.8rem;
  color: var(--success);
}

.fail-mark {
  font-size: 0.8rem;
  color: var(--danger);
}

.submitting-text {
  font-size: 0.8rem;
  color: var(--accent);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.action-btn:hover {
  background: var(--bg-hover);
  border-color: var(--text-secondary);
}

.action-btn.danger:hover {
  background: var(--danger);
  border-color: var(--danger);
  color: #fff;
}

.retry-btn {
  width: auto;
  padding: 0 10px;
  font-size: 0.78rem;
  background: var(--warning);
  color: #000;
  white-space: nowrap;
  gap: 4px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.retry-btn:hover { background: #e6a800; }
</style>
