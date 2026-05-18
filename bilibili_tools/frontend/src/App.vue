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
  </div>
</template>

<script setup>
// App root — 导航 + 路由出口
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
</style>
