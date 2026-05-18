/**
 * 搜索状态管理 — 跨路由保持搜索结果
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { searchBilibili } from '../utils/api'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const results = ref([])
  const loading = ref(false)
  const searched = ref(false)
  const page = ref(1)
  const total = ref(0)
  const hasMore = ref(false)

  const totalPages = computed(() => Math.ceil(total.value / 20))

  async function doSearch(q, p = 1) {
    if (!q?.trim()) return
    query.value = q
    loading.value = true
    searched.value = true
    page.value = p
    try {
      const data = await searchBilibili(q, p)
      results.value = data.items || []
      total.value = data.total || 0
      hasMore.value = data.has_more || false
    } catch (e) {
      console.error('搜索失败:', e)
      results.value = []
    } finally {
      loading.value = false
    }
  }

  async function goPage(p) {
    if (p < 1 || p > totalPages.value) return
    await doSearch(query.value, p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return { query, results, loading, searched, page, total, totalPages, hasMore, doSearch, goPage }
})
