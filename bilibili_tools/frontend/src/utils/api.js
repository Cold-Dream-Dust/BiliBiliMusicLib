/**
 * API 工具 — axios 封装
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ── 搜索 ──────────────────────────────
export async function searchBilibili(q, page = 1, sortBy = 'relevance') {
  const { data } = await api.get('/search', {
    params: { q, page, sort_by: sortBy },
  })
  return data
}

export async function getVideoInfo(bvid) {
  const { data } = await api.get(`/video/${bvid}`)
  return data
}

// ── 下载 ──────────────────────────────
export async function submitDownload(bvid, type = null, format = null) {
  const body = { bvid }
  if (type) body.type = type
  if (format) body.format = format
  const { data } = await api.post('/download', body)
  return data
}

export async function getDownloadTasks() {
  const { data } = await api.get('/downloads')
  return data
}

export async function cancelDownload(taskId) {
  const { data } = await api.delete(`/downloads/${taskId}`)
  return data
}

// ── LLM ──────────────────────────────
export async function llmIdentify(query) {
  const { data } = await api.post('/llm/identify', { query })
  return data
}

// ── 配置 ──────────────────────────────
export async function getConfig() {
  const { data } = await api.get('/config')
  return data
}

export async function updateConfig(settings) {
  const { data } = await api.put('/config', settings)
  return data
}

export default api
export { api }

/** 将B站封面URL转为代理URL，绕过防盗链 */
export function proxyImageUrl(originalUrl) {
  if (!originalUrl) return ''
  // 处理协议相对 URL (//i0.hdslb.com/...)
  let url = originalUrl
  if (url.startsWith('//')) {
    url = 'https:' + url
  }
  return `/api/proxy/image?url=${encodeURIComponent(url)}`
}
