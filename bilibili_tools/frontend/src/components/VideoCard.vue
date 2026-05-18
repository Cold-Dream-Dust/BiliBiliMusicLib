<template>
  <div class="video-card">
    <div class="card-cover" @click="$emit('click')">
      <img
        :src="coverUrl"
        :alt="video.title"
        loading="lazy"
        class="cover-img"
      />
      <span class="duration" v-if="video.duration">{{ formatDuration(video.duration) }}</span>
    </div>
    <div class="card-body">
      <h4 class="card-title" :title="video.title">{{ video.title }}</h4>
      <div class="card-meta">
        <span v-if="video.author">👤 {{ video.author }}</span>
        <span v-if="video.play || video.view">{{ formatCount(video.play || video.view) }} 播放</span>
      </div>
    </div>
    <!-- 右下角一键下载按钮 -->
    <button
      :class="['download-btn', { clicked: btnClicked }]"
      @click.stop="handleDownload"
      title="一键下载"
    >
      {{ btnClicked ? '✓' : '⚡' }}
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { proxyImageUrl } from '../utils/api'

const props = defineProps({
  video: { type: Object, required: true },
})
const emit = defineEmits(['download', 'click'])

const coverUrl = computed(() => proxyImageUrl(props.video.pic || props.video.cover))
const btnClicked = ref(false)

function handleDownload() {
  if (btnClicked.value) return
  btnClicked.value = true
  emit('download', props.video)
  // 1秒后恢复
  setTimeout(() => { btnClicked.value = false }, 1200)
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatCount(n) {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  if (n >= 1000) return (n / 1000).toFixed(1) + '千'
  return String(n)
}
</script>

<style scoped>
.video-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: all 0.2s;
  cursor: pointer;
}

.video-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: var(--bg-secondary);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.video-card:hover .cover-img {
  transform: scale(1.05);
}

.duration {
  position: absolute;
  bottom: 6px;
  right: 6px;
  background: rgba(0,0,0,0.75);
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.78rem;
}

.card-body {
  padding: 10px 12px 14px;
}

.card-title {
  font-size: 0.92rem;
  font-weight: 500;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 6px;
}

.card-meta {
  display: flex;
  gap: 12px;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.download-btn {
  position: absolute;
  bottom: 10px;
  right: 10px;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translateY(4px);
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  z-index: 2;
}

.download-btn.clicked {
  background: var(--success);
  transform: scale(0.85);
  opacity: 1;
}

.video-card:hover .download-btn {
  opacity: 1;
  transform: translateY(0);
}

.download-btn:hover {
  background: var(--accent-hover);
  transform: scale(1.1);
}

.download-btn.clicked:hover {
  background: var(--success);
  transform: scale(0.85);
}
</style>
