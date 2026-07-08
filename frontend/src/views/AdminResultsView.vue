<template>
  <div class="min-h-screen p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold mb-2 text-purple-400">Admin Panel</h1>
    <AdminNav />

    <div class="bg-gray-800 rounded-xl overflow-hidden shadow-xl">
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-700">
        <h2 class="font-semibold text-gray-200">Participant Results</h2>
        <div class="flex items-center gap-3">
          <button
            @click="openDeleteAllConfirm"
            :disabled="!hasAttempts || deletingAllResults"
            class="bg-red-800 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
          >Delete All Results</button>
          <button
            @click="exportCsv"
            :disabled="!hasAttempts || exporting"
            class="bg-green-700 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
          >{{ exporting ? 'Exporting…' : 'Export CSV' }}</button>
        </div>
      </div>

      <div v-if="resultsLoading" class="text-center text-gray-500 py-12">
        Loading results…
      </div>

      <div v-else-if="!hasAttempts" class="text-center text-gray-500 py-12">
        No quiz attempts yet.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-gray-400 bg-gray-700 text-xs uppercase tracking-wider">
            <tr>
              <th class="sticky left-0 z-20 bg-gray-700 px-4 py-3 text-left w-[150px] min-w-[150px]">Participant</th>
              <th class="sticky left-[150px] z-20 bg-gray-700 px-4 py-3 text-left w-[170px] min-w-[170px]">Date</th>
              <th class="sticky left-[320px] z-20 bg-gray-700 px-4 py-3 text-left w-[70px] min-w-[70px] border-r border-gray-600">Time</th>
              <th
                v-for="q in resultQuestions"
                :key="q.id"
                class="px-4 py-3 text-center min-w-[56px]"
                :title="q.question"
              >Q{{ q.id }}</th>
              <th class="sticky right-[168px] z-20 bg-gray-700 px-4 py-3 text-center w-[96px] min-w-[96px] border-l border-gray-600">Total</th>
              <th class="sticky right-0 z-20 bg-gray-700 px-4 py-3 text-left w-[168px] min-w-[168px]">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-700">
            <tr
              v-for="row in resultRows"
              :key="row.key"
              class="group hover:bg-gray-700/30 transition-colors"
            >
              <td class="sticky left-0 z-10 bg-gray-800 group-hover:bg-gray-700 px-4 py-3 text-gray-200 font-medium w-[150px] min-w-[150px]">
                <div>{{ row.displayName }}</div>
                <div class="text-xs text-gray-500 font-normal">{{ row.email }}</div>
              </td>
              <td class="sticky left-[150px] z-10 bg-gray-800 group-hover:bg-gray-700 px-4 py-3 text-gray-400 whitespace-nowrap w-[170px] min-w-[170px]">
                {{ row.abandoned ? 'Started (not completed)' : formatDate(row.date) }}
              </td>
              <td class="sticky left-[320px] z-10 bg-gray-800 group-hover:bg-gray-700 px-4 py-3 text-gray-400 w-[70px] min-w-[70px] border-r border-gray-700">{{ row.abandoned ? '—' : row.timeTaken + 's' }}</td>
              <td
                v-for="q in resultQuestions"
                :key="q.id"
                class="px-4 py-3 text-center min-w-[56px]"
              >
                <span v-if="row.abandoned" class="text-gray-600">—</span>
                <span
                  v-else-if="row.questionScores[q.id] === 1"
                  class="text-green-400 font-bold"
                >1</span>
                <span
                  v-else-if="row.questionScores[q.id] === 0"
                  class="text-red-400 font-bold"
                >0</span>
                <span v-else class="text-gray-600">—</span>
              </td>
              <td class="sticky right-[168px] z-10 bg-gray-800 group-hover:bg-gray-700 px-4 py-3 text-center font-bold text-yellow-400 w-[96px] min-w-[96px] border-l border-gray-700">
                <span v-if="row.abandoned" class="text-gray-500 text-sm font-normal">Abandoned</span>
                <span v-else>{{ row.score }}/{{ row.total }}</span>
              </td>
              <td class="sticky right-0 z-10 bg-gray-800 group-hover:bg-gray-700 px-4 py-3 w-[168px] min-w-[168px]">
                <div class="flex flex-wrap items-center gap-2">
                  <template v-if="!row.isAdmin">
                    <template v-if="passwordResetConfirm === row.userId">
                      <button
                        @click="resetUserPassword(row)"
                        class="text-amber-400 hover:text-amber-300 text-xs font-medium transition-colors"
                      >Confirm?</button>
                      <button
                        @click="passwordResetConfirm = null"
                        class="text-gray-400 hover:text-gray-300 text-xs transition-colors"
                      >Cancel</button>
                    </template>
                    <button
                      v-else
                      @click="passwordResetConfirm = row.userId"
                      class="text-amber-400 hover:text-amber-300 text-xs font-medium transition-colors"
                    >Reset pwd</button>
                  </template>
                  <template v-if="resultDeleteConfirm === row.key">
                    <button
                      @click="deleteResult(row)"
                      class="text-red-400 hover:text-red-300 text-xs font-medium transition-colors"
                    >Confirm?</button>
                    <button
                      @click="resultDeleteConfirm = null"
                      class="text-gray-400 hover:text-gray-300 text-xs transition-colors"
                    >Cancel</button>
                  </template>
                  <button
                    v-else
                    @click="resultDeleteConfirm = row.key"
                    class="text-red-400 hover:text-red-300 text-xs font-medium transition-colors"
                  >Delete</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Delete all results confirmation -->
    <div
      v-if="showDeleteAllConfirm"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div class="absolute inset-0 bg-black/60" @click="showDeleteAllConfirm = false"></div>
      <div class="relative bg-gray-800 rounded-xl shadow-2xl p-6 w-full max-w-md">
        <h3 class="text-lg font-bold text-red-400 mb-2">Delete All Participant Results?</h3>
        <p class="text-sm text-gray-300 mb-2">
          This will permanently delete every quiz attempt for all participants.
        </p>
        <p class="text-sm text-gray-500 mb-6">
          Abandoned attempts will also be cleared, and participants will be able to take the quiz again. This cannot be undone.
        </p>
        <p v-if="deleteAllError" class="text-red-400 text-sm mb-4">{{ deleteAllError }}</p>
        <div class="flex gap-3">
          <button
            @click="deleteAllResults"
            :disabled="deletingAllResults"
            class="flex-1 bg-red-700 hover:bg-red-600 disabled:opacity-50 py-2.5 rounded-xl font-semibold transition-colors"
          >{{ deletingAllResults ? 'Deleting…' : 'Delete All' }}</button>
          <button
            @click="showDeleteAllConfirm = false"
            :disabled="deletingAllResults"
            class="flex-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 py-2.5 rounded-xl font-semibold transition-colors"
          >Cancel</button>
        </div>
      </div>
    </div>

    <!-- Reset password result modal -->
    <div
      v-if="resetPasswordResult"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div class="absolute inset-0 bg-black/60" @click="resetPasswordResult = null"></div>
      <div class="relative bg-gray-800 rounded-xl shadow-2xl p-6 w-full max-w-sm">
        <h3 class="text-lg font-bold text-gray-100 mb-2">Password Reset</h3>
        <p class="text-sm text-gray-400 mb-4">
          Share this temporary password with the participant. They should change it after logging in.
        </p>
        <div class="bg-gray-900 rounded-lg px-4 py-3 mb-4">
          <div class="text-xs text-gray-500 mb-1">Email</div>
          <div class="text-gray-200 font-medium">{{ resetPasswordResult.email }}</div>
          <div class="text-xs text-gray-500 mt-3 mb-1">New Password</div>
          <div class="text-amber-400 font-mono font-bold select-all">{{ resetPasswordResult.password }}</div>
        </div>
        <button
          @click="resetPasswordResult = null"
          class="w-full bg-purple-600 hover:bg-purple-500 py-2.5 rounded-xl font-semibold transition-colors"
        >Done</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'
import AdminNav from '../components/AdminNav.vue'

const resultQuestions = ref([])
const participants = ref([])
const resultsLoading = ref(false)
const exporting = ref(false)
const deletingAllResults = ref(false)
const showDeleteAllConfirm = ref(false)
const deleteAllError = ref('')
const resultDeleteConfirm = ref(null)
const passwordResetConfirm = ref(null)
const resetPasswordResult = ref(null)

const hasAttempts = computed(() => resultRows.value.length > 0)

const resultRows = computed(() => {
  const rows = []
  for (const participant of participants.value) {
    const displayName = [participant.first_name, participant.last_name].filter(Boolean).join(' ')
      || participant.username
    const email = participant.username

    for (const [index, attempt] of (participant.results || []).entries()) {
      const questionScores = {}
      for (const q of attempt.questions || []) {
        questionScores[q.id] = q.is_correct ? 1 : 0
      }
      rows.push({
        key: `${participant.id}-${attempt.date || index}`,
        userId: participant.id,
        displayName,
        email,
        isAdmin: Boolean(participant.is_admin),
        date: attempt.date,
        timeTaken: attempt.time_taken ?? '—',
        score: attempt.score ?? 0,
        total: attempt.total ?? resultQuestions.value.length,
        questionScores,
        abandoned: false,
      })
    }

    if (participant.quiz_started && !(participant.results || []).length) {
      rows.push({
        key: `${participant.id}-__abandoned__`,
        userId: participant.id,
        displayName,
        email,
        isAdmin: Boolean(participant.is_admin),
        date: '__abandoned__',
        timeTaken: '—',
        score: '—',
        total: '—',
        questionScores: {},
        abandoned: true,
      })
    }
  }
  return rows.sort((a, b) => {
    if (a.abandoned && !b.abandoned) return -1
    if (!a.abandoned && b.abandoned) return 1
    return (b.date || '').localeCompare(a.date || '')
  })
})

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

async function loadResults() {
  resultsLoading.value = true
  try {
    const res = await api.get('/api/admin/results')
    resultQuestions.value = res.data.questions || []
    participants.value = res.data.participants || []
  } catch (e) {
    console.error('Failed to load results', e)
  } finally {
    resultsLoading.value = false
  }
}

function openDeleteAllConfirm() {
  deleteAllError.value = ''
  showDeleteAllConfirm.value = true
}

async function exportCsv() {
  exporting.value = true
  try {
    const res = await api.get('/api/admin/results/export', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'quiz-results.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Failed to export results', e)
  } finally {
    exporting.value = false
  }
}

async function deleteAllResults() {
  deleteAllError.value = ''
  deletingAllResults.value = true
  try {
    await api.delete('/api/admin/results/all')
    showDeleteAllConfirm.value = false
    await loadResults()
  } catch (e) {
    deleteAllError.value = e.response?.data?.error || 'Failed to delete all results.'
    console.error('Failed to delete all results', e)
  } finally {
    deletingAllResults.value = false
  }
}

async function deleteResult(row) {
  if (!row.userId || !row.date) return
  try {
    await api.delete('/api/admin/results', {
      data: { user_id: row.userId, date: row.date },
    })
    resultDeleteConfirm.value = null
    await loadResults()
  } catch (e) {
    console.error('Failed to delete result', e)
  }
}

async function resetUserPassword(row) {
  if (!row.userId || row.isAdmin) return
  try {
    const res = await api.put(`/api/admin/users/${row.userId}/password`, {})
    passwordResetConfirm.value = null
    resetPasswordResult.value = {
      email: res.data.username,
      password: res.data.password,
    }
  } catch (e) {
    passwordResetConfirm.value = null
    console.error('Failed to reset password', e)
    alert(e.response?.data?.error || 'Failed to reset password.')
  }
}

onMounted(() => {
  loadResults()
})
</script>
