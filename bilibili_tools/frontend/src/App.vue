<template>
  <div id="app-container">
    <!-- 顶部导航 -->
    <nav class="nav-bar">
      <div class="nav-brand">🎵 Bilibili Tools</div>
      <div class="nav-tabs">
        <router-link to="/" class="nav-tab">🔍 搜索</router-link>
        <router-link to="/downloads" class="nav-tab">📥 下载管理</router-link>
        <router-link to="/llm" class="nav-tab">🤖 LLM 助手</router-link>
        <router-link to="/settings" class="nav-tab">⚙️ 设置</router-link>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 右侧浮动下载栏 -->
    <div :class="['float-downloads',{show:floatVisible}]" @mouseenter="floatVisible=true" @mouseleave="floatVisible=false">
      <router-link to="/downloads" class="float-btn" title="下载管理">📥</router-link>
      <div class="float-panel">
        <div class="float-list">
          <div v-for="t in activeDownloadItems" :key="t.id" class="float-item">
            <span class="float-title">{{t.title?.slice(0,10)||'...'}}</span>
            <div class="float-bar"><div class="float-fill" :style="{width:t.progress+'%'}"></div></div>
            <span class="float-pct">{{t.progress}}%</span>
          </div>
          <div v-if="activeDownloadItems.length===0" class="float-empty">空闲</div>
        </div>
        <router-link to="/downloads" class="float-link">全部 →</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDownloadStore } from './stores/download'

const downloadStore = useDownloadStore()
const floatVisible = ref(false)
let hideTimer = null

const activeDownloadItems = computed(() =>
  downloadStore.tasks.filter(t => t.status === 'active')
)

// 新下载开始时自动弹出3秒
watch(() => downloadStore.activeTasks.length, (now, old) => {
  if (now > old) {
    floatVisible.value = true
    clearTimeout(hideTimer)
    hideTimer = setTimeout(() => { floatVisible.value = false }, 3000)
  }
})
</script>

<style>
/* ── 全局基础样式 ── */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-primary: #0f0f0f;
  --bg-secondary: #1a1a1a;
  --bg-card: #222222;
  --bg-hover: #2a2a2a;
  --text-primary: #f1f1f1;
  --text-secondary: #aaaaaa;
  --accent: #00a1d6;
  --accent-hover: #00b5e5;
  --danger: #e74c3c;
  --success: #2ecc71;
  --warning: #f39c12;
  --border: #333333;
  --radius: 8px;
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
}

#app-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 16px;
}

/* ── 导航栏 ── */
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.nav-brand {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
}

.nav-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.nav-tab {
  padding: 8px 16px;
  border-radius: var(--radius);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.nav-tab:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-tab.router-link-active {
  background: var(--accent);
  color: #fff;
}

/* ── 主内容 ── */
.main-content {
  padding-bottom: 40px;
}

/* ── 滚动条 ── */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-primary);
}
::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

/* ── 右侧浮动下载栏 ── */
.float-downloads{position:fixed;right:0;top:50%;transform:translate(0,-50%);display:flex;align-items:stretch;z-index:100}
.float-btn{display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:var(--radius) 0 0 var(--radius);background:var(--accent);color:#fff;text-decoration:none;font-size:1.2rem;cursor:pointer;box-shadow:-2px 0 8px rgba(0,0,0,.5);flex-shrink:0}
.float-btn:hover{background:var(--accent-hover)}
.float-panel{width:0;overflow:hidden;background:var(--bg-card);border:1px solid var(--border);border-left:none;border-radius:0 var(--radius) var(--radius) 0;transition:width .25s ease;white-space:nowrap}
.float-downloads.show .float-panel{width:160px}
.float-list{display:flex;flex-direction:column;gap:6px;padding:8px 10px;max-height:260px;overflow-y:auto;width:160px}
.float-item{display:flex;flex-direction:column;gap:2px;font-size:.7rem}
.float-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-primary)}
.float-bar{height:3px;background:var(--bg-secondary);border-radius:2px;overflow:hidden}
.float-fill{height:100%;background:var(--accent);border-radius:2px;transition:width .3s}
.float-pct{font-size:.65rem;color:var(--text-secondary);text-align:right}
.float-empty{font-size:.7rem;color:var(--text-secondary);text-align:center;padding:4px 0}
.float-link{display:block;padding:4px 10px 8px;font-size:.7rem;color:var(--accent);text-decoration:none;text-align:center;width:160px}
.float-link:hover{text-decoration:underline}
</style>
