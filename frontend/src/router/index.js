import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '热点看板' },
  },
  {
    path: '/trend/:id?',
    name: 'TrendDetail',
    component: () => import('../views/TrendDetail.vue'),
    meta: { title: '趋势分析' },
  },
  {
    path: '/generate/:id?',
    name: 'ContentGen',
    component: () => import('../views/ContentGen.vue'),
    meta: { title: '内容生成' },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { title: '历史数据' },
  },
  {
    path: '/manage',
    name: 'DataManage',
    component: () => import('../views/DataManage.vue'),
    meta: { title: '数据管理' },
  },
  {
    path: '/my',
    name: 'MyPage',
    component: () => import('../views/MyPage.vue'),
    meta: { title: '我的' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - 热点聚合工作台` : '热点聚合工作台'
})

export default router
