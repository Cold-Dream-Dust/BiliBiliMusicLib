/**
 * 设置状态管理（与后端 config 同步）
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getConfig, updateConfig } from '../utils/api'

export const useSettingsStore = defineStore('settings', () => {
  const downloadType = ref('audio')
  const audioFormat = ref('mp3')
  const videoFormat = ref('mp4')
  const maxConcurrent = ref(3)
  const downloadDir = ref('')
  const llmBaseUrl = ref('https://api.openai.com/v1')
  const llmApiKey = ref('')
  const llmModel = ref('gpt-4o-mini')
  const loaded = ref(false)

  /** 从后端加载配置 */
  async function load() {
    try {
      const cfg = await getConfig()
      downloadType.value = cfg.download_type || 'audio'
      audioFormat.value = cfg.audio_format || 'mp3'
      videoFormat.value = cfg.video_format || 'mp4'
      maxConcurrent.value = cfg.max_concurrent_downloads || 3
      downloadDir.value = cfg.download_dir || ''
      llmBaseUrl.value = cfg.llm_base_url || 'https://api.openai.com/v1'
      llmApiKey.value = cfg.llm_api_key || ''
      llmModel.value = cfg.llm_model || 'gpt-4o-mini'
      loaded.value = true
    } catch (e) {
      console.error('加载设置失败:', e)
    }
  }

  /** 保存到后端 */
  async function save(overrides = {}) {
    const payload = {
      download_type: downloadType.value,
      audio_format: audioFormat.value,
      video_format: videoFormat.value,
      max_concurrent_downloads: maxConcurrent.value,
      download_dir: downloadDir.value,
      llm_base_url: llmBaseUrl.value,
      llm_api_key: llmApiKey.value,
      llm_model: llmModel.value,
      ...overrides,
    }
    return await updateConfig(payload)
  }

  return {
    downloadType, audioFormat, videoFormat, maxConcurrent, downloadDir,
    llmBaseUrl, llmApiKey, llmModel, loaded,
    load, save,
  }
})
