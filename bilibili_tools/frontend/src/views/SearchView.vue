<template>
  <div class="search-page">
    <div class="search-header">
      <template v-if="searchOpts.upFilter">
        <input v-model="upQuery" class="search-input up-input" placeholder="UP主名/UID" @keyup.enter="doSearch" />
        <span class="sep">+</span>
      </template>
      <input v-model="inputQuery" class="search-input" placeholder="搜索B站视频..." @keyup.enter="doSearch" />
      <button class="btn btn-primary" @click="doSearch">搜索</button>
      <button class="btn btn-secondary" @click="$router.push('/llm')">🤖 AI辅助</button>
      <button class="btn btn-secondary" :class="{ active: showSettings }" @click="showSettings = !showSettings">⚙ 搜索设置</button>
    </div>

    <div v-if="showSettings" class="search-settings-panel">
      <div class="setting-row">
        <label>排序</label>
        <select v-model="searchOpts.sortBy">
          <option value="relevance">综合</option><option value="views">播放量</option>
          <option value="date">发布时间</option><option value="duration">时长</option>
        </select>
        <select v-model="searchOpts.order">
          <option value="desc">降序</option><option value="asc">升序</option>
        </select>
      </div>
      <div class="setting-row">
        <label><input type="checkbox" v-model="searchOpts.upFilter" /> 指定UP主</label>
        <span class="hint" v-if="searchOpts.upFilter">搜索框将分为 UP主 + 关键词 两段</span>
      </div>
    </div>

    <div v-if="store.results.length>0 && !store.loading" class="pager-row">
      <button class="btn btn-page" :disabled="store.page<=1" @click="store.goPage(store.page-1)">◀</button>
      <button v-for="p in pageButtons" :key="p" class="btn btn-page-num" :class="{current:p===store.page}" @click="store.goPage(p)">{{p}}</button>
      <button class="btn btn-page" :disabled="!store.hasMore" @click="store.goPage(store.page+1)">▶</button>
    </div>

    <!-- 多选工具栏 -->
    <div v-if="store.results.length>0 && !store.loading" class="multi-toolbar">
      <template v-if="!multiMode">
        <button class="btn btn-outline" @click="enterMultiMode">☑ 开启多选</button>
      </template>
      <template v-else>
        <span class="multi-count">已选 {{ selectedCount }} / {{ store.results.length }}</span>
        <button class="btn btn-sm" @click="selectAll">全选</button>
        <button class="btn btn-sm" @click="invertSelection">反选</button>
        <button class="btn btn-sm btn-download" @click="batchDownload" :disabled="selectedCount===0">⬇ 下载已选取</button>
        <button class="btn btn-sm btn-fav" @click="batchFavorite" :disabled="selectedCount===0">⭐ 收藏已选取</button>
        <button class="btn btn-sm btn-cancel" @click="exitMultiMode">✕ 取消</button>
      </template>
    </div>

    <div class="search-body">
      <div class="results-area">
        <div v-if="store.loading" class="loading">搜索中...</div>
        <div v-else-if="store.results.length>0" class="results-grid">
          <VideoCard
            v-for="v in store.results"
            :key="v.bvid"
            :video="v"
            :isFavorited="favStore.isBvidFavorited(v.bvid)"
            :showCheckbox="multiMode"
            :checked="selectedBvids.has(v.bvid)"
            @update:checked="(val) => toggleBvid(v.bvid, val)"
            @download="quickDownload"
            @favorite="openFavPicker"
          />
        </div>
        <div v-else-if="store.searched" class="empty">未找到相关结果</div>
      </div>
    </div>

    <div v-if="store.results.length>0 && !store.loading" class="pager-row">
      <button class="btn btn-page" :disabled="store.page<=1" @click="store.goPage(store.page-1)">◀</button>
      <button v-for="p in pageButtons" :key="p" class="btn btn-page-num" :class="{current:p===store.page}" @click="store.goPage(p)">{{p}}</button>
      <button class="btn btn-page" :disabled="!store.hasMore" @click="store.goPage(store.page+1)">▶</button>
    </div>

    <!-- 收藏夹选择弹窗 -->
    <div v-if="favPicker.visible" class="modal-overlay" @click.self="closeFavPicker">
      <div class="modal-card fav-picker-card">
        <h3>⭐ 收藏到...</h3>
        <p class="fav-picker-title">{{ favPicker.video?.title?.slice(0, 30) || '...' }}</p>

        <!-- 已有收藏夹列表 -->
        <div v-if="favStore.folders.length" class="fav-picker-list">
          <button
            v-for="f in favStore.folders"
            :key="f.id"
            class="fav-picker-folder"
            :disabled="favPicker.saving"
            @click="addToFolder(f.id)"
          >
            <span class="fp-name">📁 {{ f.name }}</span>
            <span class="fp-count">{{ f.items?.length || 0 }}</span>
          </button>
        </div>
        <div v-else class="fav-picker-empty">暂无收藏夹</div>

        <!-- 快速创建 -->
        <div class="fav-picker-create">
          <input
            v-model="favPicker.newName"
            class="modal-input"
            placeholder="新建收藏夹..."
            maxlength="50"
            @keyup.enter="createAndAdd"
          />
          <button class="btn btn-primary" :disabled="!favPicker.newName.trim() || favPicker.saving" @click="createAndAdd">
            新建并收藏
          </button>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" @click="closeFavPicker">取消</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="favToast" class="toast" :class="favToast.type">{{ favToast.message }}</div>

    <footer class="search-footer">
      <a href="https://space.bilibili.com/544689323" target="_blank">@九月沉</a><span class="sep">|</span>
      <a href="https://github.com/Cold-Dream-Dust/BiliBiliMusicLib" target="_blank">GitHub</a>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import VideoCard from '../components/VideoCard.vue'
import { useSearchStore } from '../stores/search'
import { useDownloadStore } from '../stores/download'
import { useFavoritesStore } from '../stores/favorites'

const store = useSearchStore()
const downloadStore = useDownloadStore()
const favStore = useFavoritesStore()
const inputQuery = ref(store.query||'')
const upQuery = ref('')
const showSettings = ref(false)
const multiMode = ref(false)
const selectedBvids = ref(new Set())
const batchSaving = ref(false)

const selectedCount = computed(() => selectedBvids.value.size)

const searchOpts = reactive({sortBy:store.sortBy||'relevance',order:store.order||'desc',upFilter:false})

const pageButtons = computed(()=>{
  const c=store.page, t=Math.max(store.totalPages,1)
  let s=Math.max(1,c-4), e=Math.min(t,c+4)
  const w=e-s+1
  if(w<9){if(s===1)e=Math.min(t,s+8);else s=Math.max(1,e-8)}
  const a=[];for(let i=s;i<=e;i++)a.push(i)
  return a
})

onMounted(()=>{
  if(store.query)inputQuery.value=store.query
  favStore.fetchFolders()  // 加载收藏状态用于标记已收藏视频
})

function doSearch(){
  let q=inputQuery.value.trim()
  if(searchOpts.upFilter&&upQuery.value.trim()) q=upQuery.value.trim()+' '+q
  store.sortBy=searchOpts.sortBy; store.order=searchOpts.order
  store.doSearch(q,1)
}

function quickDownload(video){downloadStore.addTask(video)}

// ── 多选逻辑 ──
function enterMultiMode() { multiMode.value = true; selectedBvids.value = new Set() }
function exitMultiMode() { multiMode.value = false; selectedBvids.value = new Set() }
function toggleBvid(bvid, val) {
  const s = new Set(selectedBvids.value)
  if (val) s.add(bvid); else s.delete(bvid)
  selectedBvids.value = s
}
function selectAll() {
  selectedBvids.value = new Set(store.results.map(v => v.bvid))
}
function invertSelection() {
  const all = new Set(store.results.map(v => v.bvid))
  const s = new Set()
  for (const bvid of all) { if (!selectedBvids.value.has(bvid)) s.add(bvid) }
  selectedBvids.value = s
}

function getSelectedVideos() {
  return store.results.filter(v => selectedBvids.value.has(v.bvid))
}

async function batchDownload() {
  const vids = getSelectedVideos()
  if (!vids.length) return
  for (const v of vids) {
    await downloadStore.addTask(v)
    await new Promise(r => setTimeout(r, 200)) // 小延迟避免请求过快
  }
  showFavToast(`已提交 ${vids.length} 个下载任务`)
  exitMultiMode()
}

async function batchFavorite() {
  const vids = getSelectedVideos()
  if (!vids.length || batchSaving.value) return
  batchSaving.value = true
  favStore.fetchFolders()
  try {
    // 尝试收藏到已有收藏夹，如果没有则创建
    let targetFolder = favStore.folders[0]
    if (!targetFolder) {
      targetFolder = await favStore.createFolder('默认收藏')
    }
    for (const v of vids) {
      try { await favStore.addItem(targetFolder.id, v) } catch(e) { /* skip dupes */ }
    }
    showFavToast(`已收藏 ${vids.length} 个视频到「${targetFolder.name}」`)
  } catch (e) {
    showFavToast('批量收藏失败', 'error')
  } finally {
    batchSaving.value = false
    exitMultiMode()
  }
}

// ── 收藏夹选择 ──
const favPicker = reactive({
  visible: false,
  video: null,
  newName: '',
  saving: false,
})
const favToast = ref(null)

function openFavPicker(video) {
  favStore.fetchFolders()
  favPicker.video = video
  favPicker.newName = ''
  favPicker.visible = true
}

function closeFavPicker() {
  favPicker.visible = false
  favPicker.video = null
}

async function addToFolder(folderId) {
  if (favPicker.saving) return
  favPicker.saving = true
  try {
    await favStore.addItem(folderId, favPicker.video)
    showFavToast('已收藏 ✅')
    closeFavPicker()
  } catch (e) {
    showFavToast(e.response?.data?.detail || '收藏失败', 'error')
  } finally {
    favPicker.saving = false
  }
}

async function createAndAdd() {
  const name = favPicker.newName.trim()
  if (!name || favPicker.saving) return
  favPicker.saving = true
  try {
    const folder = await favStore.createFolder(name)
    await favStore.addItem(folder.id, favPicker.video)
    showFavToast('已收藏 ✅')
    closeFavPicker()
  } catch (e) {
    showFavToast(e.response?.data?.detail || '操作失败', 'error')
  } finally {
    favPicker.saving = false
  }
}

function showFavToast(msg, type = 'success') {
  favToast.value = { message: msg, type }
  setTimeout(() => { favToast.value = null }, 2500)
}
</script>

<style scoped>
.search-page{max-width:1400px;margin:0 auto}
.search-header{display:flex;gap:8px;margin-bottom:12px;align-items:center;flex-wrap:wrap}
.search-input{flex:1;min-width:180px;padding:10px 14px;font-size:.95rem;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-secondary);color:var(--text-primary);outline:none}
.search-input:focus{border-color:var(--accent)}
.up-input{flex:0 0 180px;min-width:120px}
.sep{color:var(--text-secondary);font-weight:700}
.search-settings-panel{display:flex;gap:24px;padding:10px 16px;margin-bottom:10px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);flex-wrap:wrap}
.setting-row{display:flex;align-items:center;gap:8px}
.setting-row label{font-size:.9rem;color:var(--text-secondary);white-space:nowrap;cursor:pointer}
.setting-row select{padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-secondary);color:var(--text-primary);font-size:.85rem}
.hint{font-size:.8rem;color:var(--text-secondary)}
.pager-row{display:flex;align-items:center;justify-content:center;gap:4px;padding:10px 0}
.btn-page,.btn-page-num{padding:6px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg-card);color:var(--text-primary);font-size:.85rem;cursor:pointer;transition:all .15s}
.btn-page:hover:not(:disabled),.btn-page-num:hover{background:var(--bg-hover)}
.btn-page-num.current{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-page:disabled{opacity:.3;cursor:not-allowed}
.search-body{display:flex;gap:16px}
.results-area{flex:1;min-width:0}
.results-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
@media(max-width:1200px){.results-grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:900px){.results-grid{grid-template-columns:repeat(3,1fr)}}
.loading,.empty{text-align:center;color:var(--text-secondary);padding:60px 0;font-size:1.1rem}
.search-footer{display:flex;justify-content:center;gap:10px;padding:20px 0 10px;font-size:.85rem;color:var(--text-secondary);border-top:1px solid var(--border);margin-top:20px}
.search-footer a{color:var(--accent);text-decoration:none}
.search-footer a:hover{text-decoration:underline}
.btn{padding:10px 18px;border:none;border-radius:var(--radius);font-size:.9rem;cursor:pointer;transition:all .2s;white-space:nowrap}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:var(--accent-hover)}
.btn-secondary{background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border)}
.btn-secondary:hover{background:var(--bg-hover)}
.btn-secondary.active{border-color:var(--accent);color:var(--accent)}

/* ── 多选工具栏 ── */
.multi-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  margin-bottom: 10px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  flex-wrap: wrap;
}
.multi-count { font-size: .85rem; color: var(--accent); font-weight: 500; margin-right: 4px; }
.btn-sm {
  padding: 6px 14px;
  font-size: .82rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
  background: var(--bg-secondary);
  color: var(--text-primary);
}
.btn-sm:hover:not(:disabled) { background: var(--bg-hover); }
.btn-sm:disabled { opacity: .4; cursor: not-allowed; }
.btn-outline {
  padding: 6px 16px;
  font-size: .85rem;
  border: 1px dashed var(--accent);
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
  color: var(--accent);
  transition: all .15s;
}
.btn-outline:hover { background: rgba(0,161,214,0.1); }
.btn-sm.btn-download { background: var(--accent); color: #fff; }
.btn-sm.btn-download:hover:not(:disabled) { background: var(--accent-hover); }
.btn-sm.btn-fav { background: #ffc107; color: #000; }
.btn-sm.btn-fav:hover:not(:disabled) { background: #e6a800; }
.btn-sm.btn-cancel { color: var(--danger); }

/* ── 收藏弹窗 ── */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:100}
.modal-card{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;width:420px;max-width:90vw}
.modal-card h3{margin-bottom:8px;font-size:1.1rem}
.modal-input{width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:6px;background:var(--bg-secondary);color:var(--text-primary);font-size:.9rem;outline:none;box-sizing:border-box}
.modal-input:focus{border-color:var(--accent)}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
.fav-picker-title{font-size:.82rem;color:var(--text-secondary);margin-bottom:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fav-picker-list{display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto;margin-bottom:12px}
.fav-picker-folder{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border:1px solid var(--border);border-radius:6px;background:var(--bg-secondary);color:var(--text-primary);font-size:.9rem;cursor:pointer;transition:all .15s;width:100%}
.fav-picker-folder:hover:not(:disabled){border-color:var(--accent);background:var(--bg-hover)}
.fav-picker-folder:disabled{opacity:.5;cursor:not-allowed}
.fp-count{font-size:.78rem;color:var(--text-secondary);background:var(--bg-card);padding:2px 8px;border-radius:8px}
.fav-picker-empty{text-align:center;color:var(--text-secondary);padding:16px 0;font-size:.88rem}
.fav-picker-create{display:flex;gap:8px;margin-bottom:8px}
.fav-picker-create .modal-input{flex:1}
.fav-picker-create .btn{white-space:nowrap}

/* ── Toast ── */
.toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%);padding:10px 22px;border-radius:8px;font-size:.9rem;z-index:200;animation:toastIn .3s ease;box-shadow:0 4px 16px rgba(0,0,0,0.4)}
.toast.success{background:var(--success);color:#fff}
.toast.error{background:var(--danger);color:#fff}
@keyframes toastIn{from{opacity:0;transform:translateX(-50%) translateY(10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
</style>
