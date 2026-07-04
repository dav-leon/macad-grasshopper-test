<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="bg-gray-800 rounded-2xl shadow-2xl p-8 w-full max-w-md">
      <h1 class="text-3xl font-bold text-center mb-2 text-blue-400">MACAD GH-Quiz</h1>
      <p class="text-center text-gray-400 text-sm mb-8">Create a new account</p>

      <form @submit.prevent="handleRegister" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">First Name</label>
          <input
            v-model="firstName"
            type="text"
            autocomplete="given-name"
            required
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter first name"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Last Name</label>
          <input
            v-model="lastName"
            type="text"
            autocomplete="family-name"
            required
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter last name"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">Email</label>
          <input
            v-model="email"
            type="email"
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
            autocomplete="new-password"
            required
            minlength="4"
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="At least 4 characters"
          />
        </div>

        <p v-if="error" class="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
          {{ error }}
        </p>
        <p v-if="success" class="text-green-400 text-sm bg-green-900/20 border border-green-800 rounded-lg px-3 py-2">
          {{ success }}
        </p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg py-2.5 font-semibold transition-colors mt-2"
        >
          {{ loading ? 'Registering…' : 'Create Account' }}
        </button>
      </form>

      <p class="text-center text-gray-400 text-sm mt-6">
        Already have an account?
        <router-link to="/login" class="text-blue-400 hover:text-blue-300 ml-1">Sign In</router-link>
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

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

async function handleRegister() {
  error.value = ''
  success.value = ''

  if (!EMAIL_REGEX.test(email.value.trim())) {
    error.value = 'Please enter a valid email address.'
    return
  }

  loading.value = true
  try {
    const data = await auth.register(
      firstName.value,
      lastName.value,
      email.value,
      password.value,
    )
    success.value = data.is_admin
      ? 'Account created! You are the first user — admin role granted. Redirecting…'
      : 'Account created! Redirecting to login…'
    setTimeout(() => router.push('/login'), 1500)
  } catch (e) {
    error.value = e.response?.data?.error || 'Registration failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>
