<template>
  <div class="min-h-screen flex flex-col items-center justify-center p-4">
    <!-- No data guard -->
    <div v-if="!result" class="text-center">
      <p class="text-gray-400 text-lg mb-4">No results to display.</p>
      <router-link to="/login" class="text-blue-400 hover:text-blue-300">Go to login</router-link>
    </div>

    <div v-else class="w-full max-w-2xl">
      <!-- Score card -->
      <div class="bg-gray-800 rounded-2xl p-8 shadow-2xl text-center mb-6">
        <div class="text-6xl font-extrabold mb-3" :class="scoreColorClass">
          {{ result.score }} / {{ result.total }}
        </div>
        <p class="text-xl text-gray-300 mb-1">{{ scoreMessage }}</p>
        <p class="text-sm text-gray-500">
          {{ Math.round((result.score / result.total) * 100) }}% correct
        </p>
      </div>

      <!-- Breakdown -->
      <h2 class="text-lg font-semibold text-gray-300 mb-3">Answer Breakdown</h2>
      <div class="space-y-3">
        <div
          v-for="(item, idx) in result.results"
          :key="item.id"
          :class="item.is_correct
            ? 'border-green-600/60 bg-green-900/20'
            : 'border-red-600/60 bg-red-900/20'"
          class="rounded-xl border-2 p-4"
        >
          <div class="flex items-start gap-3 mb-3">
            <span
              class="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
              :class="item.is_correct ? 'bg-green-600 text-white' : 'bg-red-600 text-white'"
            >{{ item.is_correct ? '✓' : '✗' }}</span>
            <p class="font-medium leading-snug">{{ idx + 1 }}. {{ item.question }}</p>
          </div>

          <div class="ml-10 grid sm:grid-cols-2 gap-2 text-sm">
            <div class="bg-gray-800/60 rounded-lg px-3 py-2">
              <span class="text-gray-400 text-xs block mb-0.5">Your answer</span>
              <span :class="item.is_correct ? 'text-green-400' : 'text-red-400'" class="font-medium">
                {{
                  item.user_answer !== null && item.user_answer !== undefined
                    ? item.options[item.user_answer]
                    : 'No answer'
                }}
              </span>
            </div>
            <div class="bg-gray-800/60 rounded-lg px-3 py-2">
              <span class="text-gray-400 text-xs block mb-0.5">Correct answer</span>
              <span class="text-green-400 font-medium">{{ item.options[item.correct_answer] }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const raw = sessionStorage.getItem('quizResult')
const result = raw ? JSON.parse(raw) : null

const scoreColorClass = computed(() => {
  if (!result) return ''
  const pct = result.score / result.total
  if (pct >= 0.8) return 'text-green-400'
  if (pct >= 0.5) return 'text-yellow-400'
  return 'text-red-400'
})

const scoreMessage = computed(() => {
  if (!result) return ''
  const pct = result.score / result.total
  if (pct === 1) return 'Perfect score! Flawless!'
  if (pct >= 0.8) return 'Great job!'
  if (pct >= 0.5) return 'Good effort — keep it up!'
  return 'Keep practicing, you\'ll get there!'
})
</script>
