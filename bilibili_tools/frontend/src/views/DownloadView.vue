<template>
  <div class="download-view">
    <!-- Tab 切换栏 -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span v-if="tab.count > 0" class="tab-count">{{ tab.count }}</span>
      </button>
    </div>

    <!-- 列表 -->
    <div v-if="filteredList.length === 0" class="empty">
      暂无{{ tabs.find(t => t.key === activeTab)?.label }}的下载任务
    </div>

    <div v-else class="download-list">
      <DownloadItem
        v-for="task in filteredList"
        :key="task.id"
        :task="task"
        @pause="downloadStore.pauseTask(task.id)"
        @resume="downloadStore.resumeTask(task.id)"
        @cancel="downloadStore.cancelTask(task.id)"
        @prioritize="downloadStore.prioritizeTask(task.id)"
        @remove="downloadStore.removeTask(task.id)"
        @open-file="downloadStore.openFile(task)"
        @open-folder="downloadStore.openFolder(task)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import DownloadItem from '../components/DownloadItem.vue'
import { useDownloadStore } from '../stores/download'

const downloadStore = useDownloadStore()

const activeTab = ref('active') // 默认「下载中」

const tabs = computed(() => [
  { key: 'active', label: '下载中', count: downloadStore.activeTasks.length },
  { key: 'pending', label: '等待中', count: downloadStore.pendingTasks.length + downloadStore.submittingTasks.length },
  { key: 'done', label: '已完成', count: downloadStore.doneTasks.length },
  { key: 'failed', label: '失败', count: downloadStore.failedTasks.length },
])

const filteredList = computed(() => {
  switch (activeTab.value) {
    case 'active': return downloadStore.activeTasks
    case 'pending': return [...downloadStore.submittingTasks, ...downloadStore.pendingTasks]
    case 'done': return downloadStore.doneTasks
    case 'failed': return downloadStore.failedTasks
    default: return []
  }
})
</script>

<style scoped>
.download-view {
  max-width: 900px;
  margin: 0 auto;
}

.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius);
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--accent);
  color: #fff;
}

.tab-count {
  background: rgba(255,255,255,0.25);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.8rem;
}

.download-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 0;
  font-size: 1.05rem;
}
</style>
