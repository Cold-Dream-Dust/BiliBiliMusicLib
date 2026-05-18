<template>
  <div class="search-view">
    <div class="search-header">
      <input
        v-model="inputQuery"
        class="search-input"
        placeholder="搜索B站视频..."
        @keyup.enter="doSearch"
      />
      <button class="btn btn-primary" @click="doSearch">搜索</button>
      <button class="btn btn-secondary" @click="$router.push('/llm')">🤖 LLM 辅助</button>
    </div>

    <!-- 加载中 / 结果 / 空状态 -->
    <div v-if="store.loading" class="loading">搜索中...</div>
    <div v-else-if="store.results.length > 0" class="results-grid">
      <VideoCard
        v-for="video in store.results"
        :key="video.bvid"
        :video="video"
        @download="quickDownload"
      />
    </div>

    <div v-else-if="store.searched" class="empty">未找到相关结果</div>

    <!-- 翻页：底部 -->
    <div v-if="store.results.length > 0" class="pager bottom-pager">
      <button class="btn btn-page" :disabled="store.page <= 1" @click="store.goPage(store.page - 1)">
        ◀ 上一页
      </button>
      <span class="page-info">{{ store.page }} / {{ store.totalPages || 1 }}</span>
      <button class="btn btn-page" :disabled="!store.hasMore" @click="store.goPage(store.page + 1)">
        下一页 ▶
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import VideoCard from '../components/VideoCard.vue'
import { useSearchStore } from '../stores/search'
import { useDownloadStore } from '../stores/download'

const store = useSearchStore()
const downloadStore = useDownloadStore()
const inputQuery = ref(store.query || '')

// 如果已有搜索结果，恢复输入框
onMounted(() => {
  if (store.query) inputQuery.value = store.query
})

function doSearch() {
  store.doSearch(inputQuery.value)
}

function quickDownload(video) {
  downloadStore.addTask(video)
}
</script>

<style scoped>
.search-view {
  max-width: 1200px;
  margin: 0 auto;
}

.search-header {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
}

.search-input {
  flex: 1;
  padding: 12px 18px;
  font-size: 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-secondary);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--accent);
}

/* ── 翻页 ── */
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px 0;
}

.top-pager {
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.bottom-pager {
  margin-top: 24px;
  border-top: 1px solid var(--border);
}

.page-info {
  color: var(--text-secondary);
  font-size: 0.9rem;
  min-width: 60px;
  text-align: center;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.loading, .empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 0;
  font-size: 1.1rem;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-primary {
  background: var(--accent);
  color: #fff;
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-page {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border);
  padding: 8px 18px;
  border-radius: var(--radius);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-page:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--accent);
}

.btn-page:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
