import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import Import from './views/Import.vue'
import Search from './views/Search.vue'
import Detail from './views/Detail.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/import', name: 'Import', component: Import },
  { path: '/search', name: 'Search', component: Search },
  { path: '/photo/:id', name: 'Detail', component: Detail }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
