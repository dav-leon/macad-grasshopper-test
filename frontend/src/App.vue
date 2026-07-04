<template>
  <div class="min-h-screen bg-gray-900 text-gray-100">
    <nav
      v-if="auth.token"
      class="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center justify-between"
    >
      <span class="font-bold text-blue-400 text-lg tracking-wide">MACAD GH-Quiz</span>
      <div class="flex items-center gap-5 text-sm">
        <span class="text-gray-400">{{ displayName }}</span>
        <router-link
          v-if="auth.isAdmin"
          to="/admin"
          class="text-purple-400 hover:text-purple-300 transition-colors"
        >Admin</router-link>
        <router-link
          to="/quiz"
          class="text-blue-400 hover:text-blue-300 transition-colors"
        >Quiz</router-link>
        <button
          @click="handleLogout"
          class="text-red-400 hover:text-red-300 transition-colors"
        >Logout</button>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const auth = useAuthStore()

const displayName = computed(() => {
  const u = auth.user
  if (!u) return ''
  const name = [u.first_name, u.last_name].filter(Boolean).join(' ')
  return name || u.email || u.username
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
