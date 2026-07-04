<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="bg-gray-800 rounded-2xl shadow-2xl p-8 w-full max-w-md">
      <h1 class="text-3xl font-bold text-center mb-2 text-blue-400">MACAD GH-Quiz</h1>
      <p class="text-center text-gray-400 text-sm mb-8">Sign in to your account</p>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">Email</label>
          <input
            v-model="email"
            type="text"
            autocomplete="email"
            required
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter email address"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Password</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter password"
          />
        </div>

        <p v-if="error" class="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
          {{ error }}
        </p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg py-2.5 font-semibold transition-colors mt-2"
        >
          {{ loading ? 'Signing in…' : 'Sign In' }}
        </button>
      </form>

      <p class="text-center text-gray-400 text-sm mt-6">
        Don't have an account?
        <router-link to="/register" class="text-blue-400 hover:text-blue-300 ml-1">Register</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/quiz')
  } catch (e) {
    error.value = e.response?.data?.error || 'Login failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>
