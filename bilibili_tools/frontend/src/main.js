import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import SearchView from './views/SearchView.vue'
import DownloadView from './views/DownloadView.vue'
import LlmAssistView from './views/LlmAssistView.vue'
import SettingsView from './views/SettingsView.vue'
import FavoritesView from './views/FavoritesView.vue'

const routes = [
  { path: '/', name: 'search', component: SearchView },
  { path: '/downloads', name: 'downloads', component: DownloadView },
  { path: '/favorites', name: 'favorites', component: FavoritesView },
  { path: '/llm', name: 'llm', component: LlmAssistView },
  { path: '/settings', name: 'settings', component: SettingsView },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
