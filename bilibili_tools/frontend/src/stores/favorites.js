/**
 * 收藏夹状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getFavoriteFolders,
  createFavoriteFolder,
  renameFavoriteFolder,
  deleteFavoriteFolder,
  addFavoriteItem,
  removeFavoriteItem,
  downloadAllFavorites,
} from '../utils/api'

export const useFavoritesStore = defineStore('favorites', () => {
  const folders = ref([])
  const loading = ref(false)

  const totalItems = computed(() =>
    folders.value.reduce((sum, f) => sum + (f.items?.length || 0), 0)
  )

  /** 所有已收藏的 bvid 集合（用于搜索页标记已收藏） */
  const allFavoritedBvids = computed(() => {
    const set = new Set()
    for (const f of folders.value) {
      for (const item of (f.items || [])) {
        if (item.bvid) set.add(item.bvid)
      }
    }
    return set
  })

  async function fetchFolders() {
    loading.value = true
    try {
      const data = await getFavoriteFolders()
      folders.value = data.folders || []
    } catch (e) {
      console.error('获取收藏夹失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function createFolder(name) {
    try {
      const data = await createFavoriteFolder(name)
      if (data.folder) {
        folders.value.unshift(data.folder)
      }
      return data.folder
    } catch (e) {
      console.error('创建收藏夹失败:', e)
      throw e
    }
  }

  async function renameFolder(folderId, name) {
    try {
      const data = await renameFavoriteFolder(folderId, name)
      const idx = folders.value.findIndex(f => f.id === folderId)
      if (idx >= 0 && data.folder) {
        folders.value[idx] = data.folder
      }
    } catch (e) {
      console.error('重命名收藏夹失败:', e)
      throw e
    }
  }

  async function deleteFolder(folderId) {
    try {
      await deleteFavoriteFolder(folderId)
      folders.value = folders.value.filter(f => f.id !== folderId)
    } catch (e) {
      console.error('删除收藏夹失败:', e)
      throw e
    }
  }

  async function addItem(folderId, video) {
    try {
      const data = await addFavoriteItem(folderId, video.bvid, video.title, video.pic || video.cover || '')
      const idx = folders.value.findIndex(f => f.id === folderId)
      if (idx >= 0 && data.folder) {
        folders.value[idx] = data.folder
      }
      return true
    } catch (e) {
      console.error('添加收藏失败:', e)
      throw e
    }
  }

  async function removeItem(folderId, itemId) {
    try {
      const data = await removeFavoriteItem(folderId, itemId)
      const idx = folders.value.findIndex(f => f.id === folderId)
      if (idx >= 0 && data.folder) {
        folders.value[idx] = data.folder
      }
    } catch (e) {
      console.error('移除收藏失败:', e)
      throw e
    }
  }

  async function downloadAll(folderId) {
    try {
      const data = await downloadAllFavorites(folderId)
      return data
    } catch (e) {
      console.error('批量下载失败:', e)
      throw e
    }
  }

  /** 判断某个 bvid 是否已在某个收藏夹中 */
  function isInFolder(folderId, bvid) {
    const folder = folders.value.find(f => f.id === folderId)
    if (!folder) return false
    return folder.items?.some(item => item.bvid === bvid) || false
  }

  /** 判断某个 bvid 是否已在任意收藏夹中 */
  function isBvidFavorited(bvid) {
    return allFavoritedBvids.value.has(bvid)
  }

  return {
    folders,
    loading,
    totalItems,
    allFavoritedBvids,
    fetchFolders,
    createFolder,
    renameFolder,
    deleteFolder,
    addItem,
    removeItem,
    downloadAll,
    isInFolder,
    isBvidFavorited,
  }
})
