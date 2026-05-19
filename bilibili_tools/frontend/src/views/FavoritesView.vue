<template>
  <div class="favorites-view">
    <!-- 顶部操作栏 -->
    <div class="fav-header">
      <h2>📁 收藏夹</h2>
      <div class="fav-header-actions">
        <button class="btn btn-primary" @click="showCreateDialog = true">+ 新建收藏夹</button>
        <span class="fav-count" v-if="store.folders.length">{{ store.folders.length }} 个收藏夹 · {{ store.totalItems }} 个视频</span>
      </div>
    </div>

    <!-- 创建/重命名对话框 -->
    <div v-if="showCreateDialog || showRenameDialog" class="modal-overlay" @click.self="closeDialogs">
      <div class="modal-card">
        <h3>{{ showRenameDialog ? '重命名收藏夹' : '新建收藏夹' }}</h3>
        <input
          v-model="dialogName"
          class="modal-input"
          placeholder="输入收藏夹名称..."
          maxlength="50"
          @keyup.enter="confirmDialog"
          ref="dialogInputRef"
        />
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeDialogs">取消</button>
          <button class="btn btn-primary" @click="confirmDialog" :disabled="!dialogName.trim()">
            {{ showRenameDialog ? '保存' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 收藏夹列表 -->
    <div v-if="store.loading" class="loading">加载中...</div>

    <div v-else-if="store.folders.length === 0" class="empty">
      <p>还没有收藏夹</p>
      <p class="empty-hint">在搜索结果中点击 ⭐ 即可收藏视频</p>
    </div>

    <div v-else class="folders-list">
      <div
        v-for="folder in store.folders"
        :key="folder.id"
        class="folder-card"
        :class="{ expanded: expandedFolders.has(folder.id) }"
      >
        <!-- 收藏夹头部 -->
        <div class="folder-header" @click="toggleFolder(folder.id)">
          <div class="folder-info">
            <span class="folder-icon">{{ expandedFolders.has(folder.id) ? '📂' : '📁' }}</span>
            <span class="folder-name">{{ folder.name }}</span>
            <span class="folder-count">{{ folder.items?.length || 0 }} 个视频</span>
          </div>
          <div class="folder-actions" @click.stop>
            <button
              class="btn-icon"
              title="下载全部"
              :disabled="downloadingFolder === folder.id || !folder.items?.length"
              @click="downloadAll(folder)"
            >
              {{ downloadingFolder === folder.id ? '⏳' : '📥' }}
            </button>
            <button class="btn-icon" title="重命名" @click="startRename(folder)">✏️</button>
            <button class="btn-icon btn-icon-danger" title="删除" @click="confirmDelete(folder)">🗑️</button>
          </div>
        </div>

        <!-- 展开的视频列表 -->
        <div v-if="expandedFolders.has(folder.id)" class="folder-body">
          <div v-if="!folder.items?.length" class="empty-small">收藏夹为空</div>
          <div v-else class="fav-items-grid">
            <div v-for="item in folder.items" :key="item.id" class="fav-item">
              <div class="fav-item-cover">
                <img
                  :src="proxyImageUrl(item.pic)"
                  :alt="item.title"
                  loading="lazy"
                />
                <button
                  class="fav-item-remove"
                  title="移除"
                  @click.stop="removeItem(folder.id, item.id)"
                >✕</button>
              </div>
              <div class="fav-item-info">
                <p class="fav-item-title" :title="item.title">{{ item.title }}</p>
                <p class="fav-item-bvid">{{ item.bvid }}</p>
              </div>
              <button
                class="fav-item-download"
                title="下载此视频"
                :disabled="downloadingItems.has(item.bvid)"
                @click.stop="downloadSingle(folder.id, item)"
              >
                {{ downloadingItems.has(item.bvid) ? '⏳' : '⬇' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 下载结果提示 -->
    <div v-if="downloadResult" class="toast" :class="downloadResult.type">
      {{ downloadResult.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useFavoritesStore } from '../stores/favorites'
import { useDownloadStore } from '../stores/download'
import { proxyImageUrl } from '../utils/api'

const store = useFavoritesStore()
const downloadStore = useDownloadStore()

const expandedFolders = ref(new Set())
const showCreateDialog = ref(false)
const showRenameDialog = ref(false)
const dialogName = ref('')
const renamingFolderId = ref(null)
const dialogInputRef = ref(null)

const downloadingFolder = ref(null)
const downloadingItems = ref(new Set())
const downloadResult = ref(null)

onMounted(() => {
  store.fetchFolders()
})

function toggleFolder(id) {
  const s = expandedFolders.value
  if (s.has(id)) s.delete(id); else s.add(id)
  // 触发响应式更新
  expandedFolders.value = new Set(s)
}

function closeDialogs() {
  showCreateDialog.value = false
  showRenameDialog.value = false
  dialogName.value = ''
  renamingFolderId.value = null
}

async function confirmDialog() {
  const name = dialogName.value.trim()
  if (!name) return
  try {
    if (showRenameDialog.value && renamingFolderId.value) {
      await store.renameFolder(renamingFolderId.value, name)
    } else {
      await store.createFolder(name)
    }
    closeDialogs()
  } catch (e) {
    showToast('操作失败: ' + (e.response?.data?.detail || e.message), 'error')
  }
}

function startRename(folder) {
  renamingFolderId.value = folder.id
  dialogName.value = folder.name
  showRenameDialog.value = true
  showCreateDialog.value = false
  nextTick(() => dialogInputRef.value?.focus())
}

async function confirmDelete(folder) {
  if (!confirm(`确定删除收藏夹「${folder.name}」？`)) return
  try {
    await store.deleteFolder(folder.id)
    expandedFolders.value.delete(folder.id)
    expandedFolders.value = new Set(expandedFolders.value)
    showToast('已删除')
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

async function removeItem(folderId, itemId) {
  try {
    await store.removeItem(folderId, itemId)
  } catch (e) {
    showToast('移除失败', 'error')
  }
}

async function downloadAll(folder) {
  if (!folder.items?.length) return
  downloadingFolder.value = folder.id
  try {
    const result = await store.downloadAll(folder.id)
    if (result.errors?.length) {
      showToast(`已提交 ${result.submitted} 个，跳过 ${result.skipped} 个，${result.errors.length} 个失败`, 'warning')
    } else if (result.submitted > 0) {
      showToast(`已提交 ${result.submitted} 个下载任务，跳过 ${result.skipped} 个已下载`)
    } else {
      showToast('所有视频均已下载或正在队列中')
    }
    // 同步服务端任务到本地并开始轮询
    await downloadStore.syncFromServer()
    downloadStore.startPolling()
  } catch (e) {
    showToast('批量下载失败: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    downloadingFolder.value = null
  }
}

async function downloadSingle(folderId, item) {
  downloadingItems.value.add(item.bvid)
  try {
    await downloadStore.addTask({
      bvid: item.bvid,
      title: item.title,
      pic: item.pic,
      cover: item.pic,
    })
    showToast(`已添加: ${item.title.slice(0, 20)}...`)
  } catch (e) {
    showToast('下载失败', 'error')
  } finally {
    downloadingItems.value.delete(item.bvid)
  }
}

function showToast(message, type = 'success') {
  downloadResult.value = { message, type }
  setTimeout(() => { downloadResult.value = null }, 3000)
}
</script>

<style scoped>
.favorites-view {
  max-width: 1100px;
  margin: 0 auto;
}

.fav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.fav-header h2 {
  font-size: 1.3rem;
  font-weight: 600;
}

.fav-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fav-count {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  width: 400px;
  max-width: 90vw;
}

.modal-card h3 {
  margin-bottom: 16px;
  font-size: 1.1rem;
}

.modal-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.95rem;
  outline: none;
}

.modal-input:focus {
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

/* ── 收藏夹卡片 ── */
.folders-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.folder-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color 0.2s;
}

.folder-card:hover {
  border-color: var(--accent);
}

.folder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  cursor: pointer;
  user-select: none;
}

.folder-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.folder-icon {
  font-size: 1.2rem;
}

.folder-name {
  font-size: 1.05rem;
  font-weight: 500;
}

.folder-count {
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 2px 10px;
  border-radius: 10px;
}

.folder-actions {
  display: flex;
  gap: 4px;
}

.btn-icon {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-icon:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-icon:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-icon-danger:hover:not(:disabled) {
  background: rgba(231,76,60,0.2);
  color: var(--danger);
}

/* ── 展开区域 ── */
.folder-body {
  padding: 0 18px 16px;
}

.empty-small {
  text-align: center;
  color: var(--text-secondary);
  padding: 24px 0;
  font-size: 0.9rem;
}

.fav-items-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

@media (max-width: 900px) {
  .fav-items-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 600px) {
  .fav-items-grid { grid-template-columns: repeat(2, 1fr); }
}

.fav-item {
  position: relative;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.fav-item:hover {
  border-color: var(--accent);
}

.fav-item-cover {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--bg-primary);
}

.fav-item-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.fav-item-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 50%;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 0.7rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.fav-item:hover .fav-item-remove {
  opacity: 1;
}

.fav-item-info {
  padding: 8px 10px;
}

.fav-item-title {
  font-size: 0.82rem;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.fav-item-bvid {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.fav-item-download {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translateY(2px);
  transition: all 0.15s;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}

.fav-item:hover .fav-item-download {
  opacity: 1;
  transform: translateY(0);
}

.fav-item-download:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* ── Toast 提示 ── */
.toast {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 0.9rem;
  z-index: 200;
  animation: toastIn 0.3s ease;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}

.toast.success { background: var(--success); color: #fff; }
.toast.error { background: var(--danger); color: #fff; }
.toast.warning { background: var(--warning); color: #000; }

@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* ── 通用 ── */
.btn {
  padding: 10px 18px;
  border: none;
  border-radius: var(--radius);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary { background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--bg-hover); }

.loading, .empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 0;
  font-size: 1.05rem;
}

.empty-hint {
  font-size: 0.9rem;
  margin-top: 8px;
  opacity: 0.7;
}
</style>
