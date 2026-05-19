<template>
  <div class="settings-view">
    <h2 class="view-title">⚙️ 设置</h2>

    <!-- 下载设置 -->
    <div class="settings-section">
      <h3 class="section-header" @click="showDownload=!showDownload">下载设置 {{showDownload?'▾':'▸'}}</h3>
      <div v-show="showDownload">
        <div class="form-group">
          <label>下载类型</label>
          <select v-model="settings.download_type">
            <option value="audio">纯音频</option>
            <option value="video">视频</option>
          </select>
        </div>
        <div class="form-group">
          <label>音频格式</label>
          <select v-model="settings.audio_format">
            <option value="mp3">MP3</option>
            <option value="m4a">M4A / AAC</option>
            <option value="flac">FLAC 无损</option>
          </select>
        </div>
        <div class="form-group">
          <label>视频格式</label>
          <select v-model="settings.video_format">
            <option value="mp4">MP4</option>
            <option value="webm">WebM</option>
            <option value="mkv">MKV</option>
          </select>
        </div>
        <div class="form-group">
          <label>最大并行下载数：{{ settings.max_concurrent_downloads }}</label>
          <input type="range" v-model.number="settings.max_concurrent_downloads" min="1" max="10" step="1" />
        </div>
        <div class="form-group">
          <label>下载目录</label>
          <div class="dir-input-row">
            <input v-model="settings.download_dir" class="dir-input" />
            <button class="btn btn-secondary" @click="selectDir">选择...</button>
          </div>
        </div>
      </div>
    </div>

    <!-- B站 登录设置 -->
    <div class="settings-section">
      <h3 class="section-header" @click="showBili=!showBili">B站 登录设置 {{showBili?'▾':'▸'}}</h3>
      <div v-show="showBili">
        <p v-if="browserOk" class="cookie-ok">✅ 已从浏览器自动读取到 B站 Cookie</p>
        <div v-if="!browserOk" class="cookie-manual">
          <p class="cookie-hint">⚠️ 未检测到浏览器 Cookie。请填写三个关键字段。</p>
          <div class="form-group">
            <label>SESSDATA（登录令牌）</label>
            <input v-model="settings.bili_sessdata" placeholder="从浏览器 Cookie 中复制" />
          </div>
          <div class="form-group">
            <label>bili_jct（CSRF 令牌）</label>
            <input v-model="settings.bili_jct" placeholder="从浏览器 Cookie 中复制" />
          </div>
          <div class="form-group">
            <label>DedeUserID（用户ID，可选）</label>
            <input v-model="settings.bili_dedeuserid" placeholder="从浏览器 Cookie 中复制" />
          </div>
          <p class="cookie-hint">获取方式：浏览器登录 B站 → F12 → Application → Cookies → bilibili.com → 复制对应值</p>
        </div>
      </div>
    </div>

    <!-- LLM 设置 -->
    <div class="settings-section">
      <h3 class="section-header" @click="showLlm=!showLlm">LLM 设置 {{showLlm?'▾':'▸'}}</h3>
      <div v-show="showLlm">
        <div class="form-group">
          <label>API 地址 (base_url)</label>
          <input v-model="settings.llm_base_url" placeholder="https://api.deepseek.com/v1" />
        </div>
        <div class="form-group">
          <label>API Key</label>
          <input v-model="settings.llm_api_key" type="password" placeholder="sk-..." />
        </div>
        <div class="form-group">
          <label>模型</label>
          <input v-model="settings.llm_model" placeholder="deepseek-chat" />
        </div>
      </div>
    </div>

    <div class="settings-actions">
      <button class="btn btn-primary" @click="saveSettings" :disabled="saving">{{ saving ? '保存中...' : '保存设置' }}</button>
      <span v-if="saved" class="saved-hint">✓ 已保存</span>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { getConfig, updateConfig } from '../utils/api'

const settings = reactive({
  download_type: 'audio', audio_format: 'mp3', video_format: 'mp4',
  max_concurrent_downloads: 3, download_dir: '',
  bili_sessdata: '', bili_jct: '', bili_dedeuserid: '', browser_cookies_available: false,
  llm_base_url: 'https://api.deepseek.com/v1', llm_api_key: '', llm_model: 'deepseek-chat',
})

const showDownload = ref(true)
const showBili = ref(true)
const showLlm = ref(false)
const browserOk = ref(false)
const saving = ref(false)
const saved = ref(false)

onMounted(async () => {
  try {
    const cfg = await getConfig()
    Object.assign(settings, cfg)
    browserOk.value = cfg.browser_cookies_available || false
  } catch (e) { console.error('加载配置失败:', e) }
})

async function saveSettings() {
  saving.value = true; saved.value = false
  try { await updateConfig({ ...settings }); saved.value = true; setTimeout(()=>saved.value=false, 2000) }
  catch (e) { console.error('保存失败:', e) }
  finally { saving.value = false }
}

async function selectDir() {
  try {
    const h = await window.showDirectoryPicker()
    alert(`已选择: ${h.name}\n请将完整路径粘贴到输入框，例如:\nC:\\Users\\xxx\\Downloads\\${h.name}`)
  } catch (e) {
    if (e.name !== 'AbortError') alert('请直接在输入框中输入目录路径\n例如: C:\\Users\\你的用户名\\Downloads')
  }
}
</script>

<style scoped>
.settings-view{max-width:600px;margin:0 auto}
.view-title{font-size:1.3rem;margin-bottom:24px}
.settings-section{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px;margin-bottom:14px}
.section-header{cursor:pointer;user-select:none;font-size:1.05rem;color:var(--accent);margin-bottom:12px;transition:color .2s}
.section-header:hover{color:var(--accent-hover)}
.form-group{margin-bottom:14px}
.form-group:last-child{margin-bottom:0}
.form-group label{display:block;margin-bottom:6px;color:var(--text-secondary);font-size:.9rem}
input,select{width:100%;padding:10px 14px;font-size:.95rem;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-secondary);color:var(--text-primary);outline:none}
input:focus,select:focus{border-color:var(--accent)}
input[type="range"]{padding:0;accent-color:var(--accent)}
.dir-input-row{display:flex;gap:8px}
.dir-input{flex:1}
.settings-actions{display:flex;align-items:center;gap:14px;padding:10px 0}
.saved-hint{color:var(--success);font-size:.9rem}
.cookie-ok{color:var(--success);font-size:.95rem;padding:8px 0}
.cookie-hint{color:var(--text-secondary);font-size:.82rem;line-height:1.6;margin-bottom:10px}
.btn{padding:10px 20px;border:none;border-radius:var(--radius);font-size:.95rem;cursor:pointer;transition:all .2s}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:var(--accent-hover)}
.btn-primary:disabled{opacity:.5;cursor:not-allowed}
.btn-secondary{background:var(--bg-hover);color:var(--text-primary);border:1px solid var(--border)}
.btn-secondary:hover{background:var(--border)}
</style>
