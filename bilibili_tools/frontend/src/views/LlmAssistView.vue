<template>
  <div class="llm-view">
    <h2 class="view-title">🤖 LLM 智能识别</h2>
    <p class="view-desc">描述你想找的媒体内容，AI 会帮你找到精准的 B站 搜索关键词</p>

    <div class="chat-area">
      <div v-if="thinking" class="thinking">
        🤔 AI 正在思考并联网搜索...
      </div>

      <div v-if="result" class="result-card">
        <div class="result-keywords">
          <span class="label">🔑 搜索关键词：</span>
          <strong>{{ result.keywords }}</strong>
        </div>
        <div v-if="result.explanation" class="result-explanation">
          {{ result.explanation }}
        </div>
        <div v-if="result.suggestions?.length" class="result-suggestions">
          <span class="label">💡 备选搜索：</span>
          <button
            v-for="(s, i) in result.suggestions"
            :key="i"
            class="suggestion-btn"
            @click="searchWithKeyword(s)"
          >
            {{ s }}
          </button>
        </div>
        <button class="btn btn-primary" @click="searchWithKeyword(result.keywords)">
          🔍 用此关键词搜索
        </button>
      </div>
    </div>

    <div class="input-area">
      <input
        v-model="query"
        class="llm-input"
        placeholder="例：周杰伦一首和茶叶有关的歌"
        @keyup.enter="identify"
        :disabled="thinking"
      />
      <button class="btn btn-primary" @click="identify" :disabled="thinking || !query.trim()">
        识别
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { llmIdentify } from '../utils/api'

const router = useRouter()
const query = ref('')
const thinking = ref(false)
const result = ref(null)

async function identify() {
  if (!query.value.trim() || thinking.value) return
  thinking.value = true
  result.value = null
  try {
    result.value = await llmIdentify(query.value)
  } catch (e) {
    console.error('LLM 识别失败:', e)
    result.value = { keywords: query.value, explanation: '识别失败，请检查 LLM 配置' }
  } finally {
    thinking.value = false
  }
}

function searchWithKeyword(keyword) {
  router.push({ name: 'search', query: { q: keyword } })
}
</script>

<style scoped>
.llm-view {
  max-width: 700px;
  margin: 0 auto;
}

.view-title {
  font-size: 1.3rem;
  margin-bottom: 8px;
}

.view-desc {
  color: var(--text-secondary);
  margin-bottom: 24px;
  font-size: 0.95rem;
}

.chat-area {
  margin-bottom: 24px;
  min-height: 100px;
}

.thinking {
  text-align: center;
  color: var(--accent);
  padding: 30px;
  font-size: 1.05rem;
}

.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}

.result-keywords {
  font-size: 1.2rem;
  margin-bottom: 12px;
  color: var(--accent);
}

.result-keywords strong {
  color: var(--text-primary);
}

.result-explanation {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 14px;
  line-height: 1.6;
}

.result-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
}

.label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.suggestion-btn {
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.suggestion-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.input-area {
  display: flex;
  gap: 10px;
}

.llm-input {
  flex: 1;
  padding: 12px 18px;
  font-size: 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-secondary);
  color: var(--text-primary);
  outline: none;
}

.llm-input:focus {
  border-color: var(--accent);
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

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
