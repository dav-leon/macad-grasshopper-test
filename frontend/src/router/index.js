import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/login' },
  {
    path: '/login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/quiz',
    component: () => import('../views/QuizView.vue'),
    meta: { auth: true },
  },
  {
    path: '/result',
    component: () => import('../views/ResultView.vue'),
    meta: { auth: true },
  },
  {
    path: '/admin',
    component: () => import('../views/AdminView.vue'),
    meta: { admin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.guest && auth.token) return '/quiz'
  if ((to.meta.auth || to.meta.admin) && !auth.token) return '/login'
  if (to.meta.admin && !auth.isAdmin) return '/quiz'
})

export default router
