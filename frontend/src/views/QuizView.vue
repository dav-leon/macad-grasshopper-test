<template>
  <div class="min-h-screen flex flex-col items-center justify-center p-4">
    <!-- Loading -->
    <div v-if="loading" class="text-gray-400 text-lg">Loading…</div>

    <!-- Welcome screen -->
    <div v-else-if="phase === 'welcome'" class="w-full max-w-2xl">
      <div class="bg-gray-800 rounded-2xl p-8 shadow-2xl">
        <h1 class="text-2xl font-bold text-white mb-6 text-center">Welcome</h1>
        <div
          class="text-gray-300 leading-relaxed whitespace-pre-wrap mb-8"
        >{{ welcomeText || 'Welcome to the quiz. Press Start when you are ready.' }}</div>
        <p class="text-sm text-amber-400/90 bg-amber-900/20 border border-amber-700/50 rounded-lg px-4 py-3 mb-8">
          Once you press Start, you cannot leave and come back later. Make sure you are ready before continuing.
        </p>
        <button
          @click="startQuiz"
          :disabled="starting || questionCount === 0"
          class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed py-4 rounded-xl text-lg font-bold transition-colors"
        >
          {{ starting ? 'Starting…' : 'Start Quiz' }}
        </button>
        <p v-if="questionCount === 0" class="text-red-400 text-sm text-center mt-4">
          No questions are available yet. Please check back later.
        </p>
        <p v-if="startError" class="text-red-400 text-sm text-center mt-4">{{ startError }}</p>
      </div>
    </div>

    <!-- Already taken -->
    <div v-else-if="phase === 'locked'" class="w-full max-w-2xl text-center">
      <div class="bg-gray-800 rounded-2xl p-8 shadow-2xl">
        <div class="text-5xl mb-4">🔒</div>
        <h1 class="text-2xl font-bold text-white mb-3">Quiz Already Taken</h1>
        <p class="text-gray-400 mb-2">
          {{ hasResult
            ? 'You have already completed this quiz.'
            : 'You started this quiz but did not finish. You cannot take it again.' }}
        </p>
        <p class="text-sm text-gray-500">
          Contact an administrator if you need to retake the quiz.
        </p>
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="questions.length === 0" class="text-center">
      <p class="text-gray-400 text-lg mb-4">No questions available yet.</p>
      <router-link to="/" class="text-blue-400 hover:text-blue-300">Go home</router-link>
    </div>

    <!-- Quiz -->
    <div v-else class="w-full max-w-2xl">
      <!-- Top progress bar -->
      <div class="mb-6">
        <div class="flex justify-between text-sm text-gray-400 mb-2">
          <span>Question <span class="text-white font-semibold">{{ currentIndex + 1 }}</span> / {{ questions.length }}</span>
          <span>{{ answeredCount }} answered</span>
        </div>
        <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 rounded-full transition-all duration-300"
            :style="{ width: `${(currentIndex / questions.length) * 100}%` }"
          ></div>
        </div>
      </div>

      <!-- Question card -->
      <div class="bg-gray-800 rounded-2xl p-6 shadow-2xl">
        <!-- Timer ring -->
        <div class="flex items-center justify-between mb-5">
          <span class="text-sm text-gray-400 font-medium">Time remaining</span>
          <div class="relative w-14 h-14">
            <svg class="-rotate-90 w-14 h-14" viewBox="0 0 56 56">
              <circle cx="28" cy="28" r="24" fill="none" stroke="#374151" stroke-width="4" />
              <circle
                cx="28" cy="28" r="24"
                fill="none"
                :stroke="timerStroke"
                stroke-width="4"
                stroke-linecap="round"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="dashOffset"
                style="transition: stroke-dashoffset 1s linear, stroke 0.5s ease;"
              />
            </svg>
            <span
              class="absolute inset-0 flex items-center justify-center text-sm font-bold"
              :class="timerTextClass"
            >{{ timeLeft }}</span>
          </div>
        </div>

        <!-- Question image -->
        <div v-if="currentQuestion.image" class="mb-5 rounded-xl overflow-hidden bg-gray-900">
          <img
            :src="currentQuestion.image"
            alt="Question image"
            class="w-full max-h-56 object-contain"
          />
        </div>

        <!-- Question text -->
        <h2 class="text-xl font-semibold mb-6 leading-snug">{{ currentQuestion.question }}</h2>

        <!-- Options -->
        <div class="space-y-3">
          <button
            v-for="(option, idx) in currentQuestion.options"
            :key="idx"
            @click="selectAnswer(idx)"
            :class="optionClass(idx)"
            class="w-full text-left px-4 py-3 rounded-xl border-2 transition-all duration-150 font-medium flex items-center gap-3"
          >
            <span
              class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              :class="optionBadgeClass(idx)"
            >{{ String.fromCharCode(65 + idx) }}</span>
            <span>{{ option }}</span>
          </button>
        </div>

        <!-- Navigation -->
        <div class="mt-7 flex justify-between items-center">
          <span class="text-xs text-gray-500">Click an option, then press Next</span>
          <button
            @click="nextQuestion"
            class="bg-blue-600 hover:bg-blue-500 px-6 py-2.5 rounded-xl font-semibold transition-colors"
          >
            {{ currentIndex === questions.length - 1 ? 'Submit Quiz' : 'Next →' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const phase = ref('loading') // loading | welcome | quiz | locked
const welcomeText = ref('')
const hasResult = ref(false)
const questionCount = ref(0)
const starting = ref(false)
const startError = ref('')
const loading = ref(true)

const questions = ref([])
const currentIndex = ref(0)
const answers = ref({})
const timeLeft = ref(0)
const startTime = ref(0)

let timerInterval = null
const circumference = 2 * Math.PI * 24

const currentQuestion = computed(() => questions.value[currentIndex.value])

const answeredCount = computed(() =>
  Object.keys(answers.value).length
)

const dashOffset = computed(() => {
  if (!currentQuestion.value) return circumference
  return circumference * (1 - timeLeft.value / currentQuestion.value.time_limit)
})

const timerStroke = computed(() => {
  if (!currentQuestion.value) return '#6b7280'
  const ratio = timeLeft.value / currentQuestion.value.time_limit
  if (ratio > 0.5) return '#22c55e'
  if (ratio > 0.25) return '#f59e0b'
  return '#ef4444'
})

const timerTextClass = computed(() => {
  if (!currentQuestion.value) return 'text-gray-400'
  const ratio = timeLeft.value / currentQuestion.value.time_limit
  if (ratio > 0.5) return 'text-green-400'
  if (ratio > 0.25) return 'text-yellow-400'
  return 'text-red-400'
})

function isSelected(idx) {
  return answers.value[currentQuestion.value?.id] === idx
}

function optionClass(idx) {
  if (isSelected(idx)) {
    return 'border-blue-500 bg-blue-900/40 text-blue-100'
  }
  return 'border-gray-600 bg-gray-700/40 hover:border-gray-400 text-gray-200 hover:bg-gray-700/70'
}

function optionBadgeClass(idx) {
  if (isSelected(idx)) return 'bg-blue-500 text-white'
  return 'bg-gray-600 text-gray-300'
}

function selectAnswer(idx) {
  answers.value[currentQuestion.value.id] = idx
}

function startTimer() {
  clearInterval(timerInterval)
  timeLeft.value = currentQuestion.value.time_limit
  timerInterval = setInterval(() => {
    timeLeft.value--
    if (timeLeft.value <= 0) {
      clearInterval(timerInterval)
      nextQuestion()
    }
  }, 1000)
}

async function nextQuestion() {
  clearInterval(timerInterval)
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
    startTimer()
  } else {
    await submitQuiz()
  }
}

async function submitQuiz() {
  const timeTaken = Math.floor((Date.now() - startTime.value) / 1000)

  const payload = {}
  for (const q of questions.value) {
    const ans = answers.value[q.id]
    payload[String(q.id)] = ans !== undefined ? ans : null
  }

  try {
    const res = await axios.post('/api/quiz/submit', {
      answers: payload,
      time_taken: timeTaken,
    })
    sessionStorage.setItem('quizResult', JSON.stringify(res.data))
    router.push('/result')
  } catch (e) {
    console.error('Submit failed', e)
    if (e.response?.status === 403) {
      phase.value = 'locked'
      hasResult.value = true
    }
  }
}

async function startQuiz() {
  startError.value = ''
  starting.value = true
  try {
    const res = await axios.post('/api/quiz/start')
    questions.value = res.data.questions || []
    if (questions.value.length === 0) {
      startError.value = 'No questions are available.'
      return
    }
    phase.value = 'quiz'
    startTime.value = Date.now()
    startTimer()
  } catch (e) {
    startError.value = e.response?.data?.error || 'Failed to start quiz.'
    if (e.response?.status === 403) {
      phase.value = 'locked'
    }
  } finally {
    starting.value = false
  }
}

onMounted(async () => {
  try {
    const statusRes = await axios.get('/api/quiz/status')

    welcomeText.value = statusRes.data.welcome_text || ''
    hasResult.value = statusRes.data.has_result
    questionCount.value = statusRes.data.question_count || 0

    if (!statusRes.data.can_take_quiz) {
      phase.value = 'locked'
    } else {
      phase.value = 'welcome'
    }
  } catch (e) {
    console.error('Failed to load quiz status', e)
    phase.value = 'welcome'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  clearInterval(timerInterval)
})
</script>
