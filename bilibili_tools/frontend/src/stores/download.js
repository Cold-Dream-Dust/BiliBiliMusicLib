/**
 * 下载任务状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { submitDownload, api } from '../utils/api'

let taskIdCounter = 0
let pollTimer = null

export const useDownloadStore = defineStore('download', () => {
  const tasks = ref([])

  const submittingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'submitting')
  )
  const pendingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'pending')
  )
  const activeTasks = computed(() =>
    tasks.value.filter(t => t.status === 'active')
  )
  const doneTasks = computed(() =>
    tasks.value.filter(t => t.status === 'done')
  )
  const failedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'failed')
  )

  /** 从 VideoCard 一键添加下载 */
  async function addTask(video) {
    const id = ++taskIdCounter
    const task = {
      id,
      bvid: video.bvid,
      title: video.title,
      thumbnail: video.pic || video.cover,
      status: 'submitting',
      progress: 0,
      speed: null,
      queuePosition: pendingTasks.value.length + 1,
      paused: false,
      serverId: null,
    }
    tasks.value.push(task)

    // 调用后端提交下载
    try {
      const result = await submitDownload(video.bvid)
      task.serverId = result.task_id
      task.status = 'active'
      startPolling()
    } catch (e) {
      task.status = 'failed'
      task.error = e.response?.data?.detail || '提交下载失败'
      // 如果是 Cookie 相关错误，提示用户去设置
      if (task.error.includes('Cookie') || task.error.includes('cookie')) {
        task.error += ' — 点击上方「设置」填写 B站 Cookie'
      }
    }
  }

  /** 轮询后端获取进度 */
  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(async () => {
      const hasActive = activeTasks.value.length > 0
      if (!hasActive && pendingTasks.value.length === 0) {
        stopPolling()
        return
      }
      try {
        const { data } = await api.get('/downloads/poll')
        if (data?.tasks) {
          for (const remote of data.tasks) {
            const local = tasks.value.find(t => t.serverId === remote.id)
            if (local) {
              local.status = remote.status
              local.progress = remote.progress
              local.speed = remote.speed || ''
              local.error = remote.error || ''
              local.file_path = remote.file_path || ''
              local.paused = remote.paused || false
            }
          }
        }
      } catch (e) {
        // 轮询失败静默处理
      }
    }, 1000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  /** 从服务端同步所有任务到本地 store（用于收藏夹批量下载后刷新） */
  async function syncFromServer() {
    try {
      const { data } = await api.get('/downloads')
      const serverTasks = data?.tasks || []
      for (const st of serverTasks) {
        const exists = tasks.value.find(t => t.serverId === st.id)
        if (!exists) {
          tasks.value.push({
            id: ++taskIdCounter,
            bvid: st.bvid || '',
            title: st.title || st.bvid || '',
            thumbnail: st.thumbnail || '',
            status: st.status,
            progress: st.progress || 0,
            speed: st.speed || '',
            error: st.error || '',
            file_path: st.file_path || '',
            paused: st.paused || false,
            serverId: st.id,
          })
        }
      }
    } catch (e) {
      console.error('同步任务列表失败:', e)
    }
  }

  function pauseTask(id) {
    const t = tasks.value.find(t => t.id === id)
    if (t) t.paused = true
  }

  function resumeTask(id) {
    const t = tasks.value.find(t => t.id === id)
    if (t) t.paused = false
  }

  function cancelTask(id) {
    const t = tasks.value.find(t => t.id === id)
    if (t) t.status = 'failed'
  }

  function prioritizeTask(id) {
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx > 0) {
      const [item] = tasks.value.splice(idx, 1)
      // 移到第一个 pending 之后
      const firstPending = tasks.value.findIndex(t => t.status === 'pending')
      tasks.value.splice(firstPending >= 0 ? firstPending : 0, 0, item)
    }
  }

  function removeTask(id) {
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  function openFile(task) {
    if (task.serverId) {
      fetch(`/api/file/${task.serverId}`).catch(()=>{})
    }
  }

  function openFolder(task) {
    if (task.serverId) {
      // 后端端点会直接打开系统文件夹
      fetch(`/api/downloads/${task.serverId}/open-folder`)
        .then(r => r.json())
        .then(d => { if (d.status !== 'opened') alert('无法打开文件夹: ' + (d.detail || '')) })
        .catch(() => alert('无法打开文件夹'))
    }
  }

  return {
    tasks,
    submittingTasks,
    pendingTasks,
    activeTasks,
    doneTasks,
    failedTasks,
    addTask,
    pauseTask,
    resumeTask,
    cancelTask,
    prioritizeTask,
    removeTask,
    openFile,
    openFolder,
    startPolling,
    stopPolling,
    syncFromServer,
  }
})
