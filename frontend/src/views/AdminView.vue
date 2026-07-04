<template>
  <div class="min-h-screen p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold mb-2 text-purple-400">Admin Panel</h1>
    <AdminNav />

    <!-- Stats row -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      <router-link
        to="/admin/questions"
        class="bg-gray-800 rounded-xl p-5 text-center hover:bg-gray-700 hover:ring-1 hover:ring-purple-500/50 transition-all block"
      >
        <div class="text-4xl font-extrabold text-blue-400">{{ questions.length }}</div>
        <div class="text-gray-400 text-sm mt-1">Total Questions</div>
        <div class="text-purple-400 text-xs mt-2">Manage questions →</div>
      </router-link>
      <div class="bg-gray-800 rounded-xl p-5 text-center">
        <div class="text-4xl font-extrabold text-green-400">
          {{ avgTimeLimit > 0 ? avgTimeLimit + 's' : '—' }}
        </div>
        <div class="text-gray-400 text-sm mt-1">Avg Time Limit</div>
      </div>
      <div class="bg-gray-800 rounded-xl p-5 text-center">
        <div class="text-4xl font-extrabold text-yellow-400">
          {{ questions.length > 0 ? Math.ceil(questions.length * avgTimeLimit / 60) + ' min' : '—' }}
        </div>
        <div class="text-gray-400 text-sm mt-1">Est. Quiz Duration</div>
      </div>
    </div>

    <!-- Account -->
    <div class="bg-gray-800 rounded-xl p-6 shadow-xl mb-8">
      <h2 class="font-semibold text-gray-200 mb-1">Account</h2>
      <p class="text-sm text-gray-500 mb-4">
        Change the password for your admin account.
      </p>
      <button
        v-if="!showPasswordForm"
        @click="openPasswordForm"
        class="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
      >Change Password</button>
      <form v-else @submit.prevent="changePassword" class="space-y-4 max-w-md">
        <div>
          <label class="block text-sm text-gray-400 mb-1">Current Password</label>
          <input
            v-model="passwordForm.current"
            type="password"
            autocomplete="current-password"
            required
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">New Password</label>
          <input
            v-model="passwordForm.new"
            type="password"
            autocomplete="new-password"
            required
            minlength="4"
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">Confirm New Password</label>
          <input
            v-model="passwordForm.confirm"
            type="password"
            autocomplete="new-password"
            required
            minlength="4"
            class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
        <div class="flex items-center gap-4">
          <button
            type="submit"
            :disabled="changingPassword"
            class="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
          >{{ changingPassword ? 'Saving…' : 'Update Password' }}</button>
          <button
            type="button"
            @click="closePasswordForm"
            class="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
          >Cancel</button>
          <span v-if="passwordSaved" class="text-green-400 text-sm">Password updated!</span>
          <span v-if="passwordError" class="text-red-400 text-sm">{{ passwordError }}</span>
        </div>
      </form>
    </div>

    <!-- Welcome text -->
    <div class="bg-gray-800 rounded-xl p-6 shadow-xl mb-8">
      <h2 class="font-semibold text-gray-200 mb-1">Quiz Welcome Screen</h2>
      <p class="text-sm text-gray-500 mb-4">
        This text is shown to participants before they press Start. The welcome screen has no timer.
      </p>
      <textarea
        v-model="welcomeText"
        rows="6"
        class="w-full bg-gray-700 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-y mb-4"
        placeholder="Enter welcome message for quiz participants…"
      ></textarea>
      <div class="flex items-center gap-4">
        <button
          @click="saveWelcomeText"
          :disabled="savingWelcome"
          class="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
        >{{ savingWelcome ? 'Saving…' : 'Save Welcome Text' }}</button>
        <span v-if="welcomeSaved" class="text-green-400 text-sm">Saved!</span>
        <span v-if="welcomeError" class="text-red-400 text-sm">{{ welcomeError }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import AdminNav from '../components/AdminNav.vue'

const questions = ref([])
const welcomeText = ref('')
const savingWelcome = ref(false)
const welcomeSaved = ref(false)
const welcomeError = ref('')

const showPasswordForm = ref(false)
const changingPassword = ref(false)
const passwordSaved = ref(false)
const passwordError = ref('')
const passwordForm = ref({ current: '', new: '', confirm: '' })

const avgTimeLimit = computed(() => {
  if (questions.value.length === 0) return 0
  const sum = questions.value.reduce((acc, q) => acc + q.time_limit, 0)
  return Math.round(sum / questions.value.length)
})

async function loadQuestions() {
  try {
    const res = await axios.get('/api/admin/questions')
    questions.value = res.data
  } catch (e) {
    console.error('Failed to load questions', e)
  }
}

async function loadSettings() {
  try {
    const res = await axios.get('/api/admin/settings')
    welcomeText.value = res.data.welcome_text || ''
  } catch (e) {
    console.error('Failed to load settings', e)
  }
}

async function saveWelcomeText() {
  welcomeError.value = ''
  welcomeSaved.value = false
  savingWelcome.value = true
  try {
    await axios.put('/api/admin/settings', { welcome_text: welcomeText.value })
    welcomeSaved.value = true
    setTimeout(() => { welcomeSaved.value = false }, 2000)
  } catch (e) {
    welcomeError.value = e.response?.data?.error || 'Failed to save welcome text.'
  } finally {
    savingWelcome.value = false
  }
}

function openPasswordForm() {
  passwordForm.value = { current: '', new: '', confirm: '' }
  passwordError.value = ''
  passwordSaved.value = false
  showPasswordForm.value = true
}

function closePasswordForm() {
  showPasswordForm.value = false
  passwordForm.value = { current: '', new: '', confirm: '' }
  passwordError.value = ''
}

async function changePassword() {
  passwordError.value = ''
  passwordSaved.value = false

  if (passwordForm.value.new !== passwordForm.value.confirm) {
    passwordError.value = 'New passwords do not match.'
    return
  }

  changingPassword.value = true
  try {
    await axios.put('/api/admin/password', {
      current_password: passwordForm.value.current,
      new_password: passwordForm.value.new,
    })
    passwordSaved.value = true
    passwordForm.value = { current: '', new: '', confirm: '' }
    setTimeout(() => {
      passwordSaved.value = false
      showPasswordForm.value = false
    }, 1500)
  } catch (e) {
    passwordError.value = e.response?.data?.error || 'Failed to update password.'
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  loadQuestions()
  loadSettings()
})
</script>
