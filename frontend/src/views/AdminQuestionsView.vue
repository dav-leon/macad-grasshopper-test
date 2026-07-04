<template>
  <div class="min-h-screen p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold mb-2 text-purple-400">Admin Panel</h1>
    <AdminNav />

    <div class="bg-gray-800 rounded-xl overflow-hidden shadow-xl">
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-700">
        <h2 class="font-semibold text-gray-200">Questions</h2>
        <button
          @click="openAdd"
          class="bg-purple-600 hover:bg-purple-500 px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
        >+ Add Question</button>
      </div>

      <div v-if="questions.length === 0" class="text-center text-gray-500 py-12">
        No questions yet. Add your first one!
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="text-gray-400 bg-gray-700/50 text-xs uppercase tracking-wider">
            <tr>
              <th class="px-4 py-3 text-left">ID</th>
              <th class="px-4 py-3 text-left">Question</th>
              <th class="px-4 py-3 text-left">Options</th>
              <th class="px-4 py-3 text-left">Answer</th>
              <th class="px-4 py-3 text-left">Time</th>
              <th class="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-700">
            <tr v-for="q in questions" :key="q.id" class="hover:bg-gray-700/30 transition-colors">
              <td class="px-4 py-3 text-gray-500 font-mono">{{ q.id }}</td>
              <td class="px-4 py-3 text-gray-200 max-w-xs">
                <div class="flex items-start gap-2">
                  <img
                    v-if="q.image"
                    :src="q.image"
                    class="w-10 h-10 rounded object-cover shrink-0 bg-gray-900"
                    title="Question has image"
                  />
                  <span class="line-clamp-2">{{ q.question }}</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <div v-for="(opt, i) in q.options" :key="i" class="text-xs text-gray-400 leading-5">
                  <span class="font-bold text-gray-500">{{ String.fromCharCode(65 + i) }}.</span>
                  {{ opt }}
                </div>
              </td>
              <td class="px-4 py-3">
                <span class="bg-green-900/40 text-green-400 border border-green-700 px-2 py-0.5 rounded-md text-xs font-bold">
                  {{ String.fromCharCode(65 + q.answer) }}
                </span>
              </td>
              <td class="px-4 py-3">
                <template v-if="timeEdit.id === q.id">
                  <div class="flex items-center gap-1">
                    <input
                      ref="timeInput"
                      v-model.number="timeEdit.value"
                      type="number"
                      min="5"
                      max="300"
                      class="w-16 bg-gray-700 border border-purple-500 rounded px-2 py-0.5 text-gray-100 text-sm focus:outline-none"
                      @keyup.enter="saveTimeLimit(q)"
                      @keyup.escape="timeEdit.id = null"
                      @blur="saveTimeLimit(q)"
                    />
                    <span class="text-gray-500 text-xs">s</span>
                  </div>
                </template>
                <button
                  v-else
                  @click="startTimeEdit(q)"
                  class="text-gray-400 hover:text-white hover:bg-gray-700 px-2 py-0.5 rounded transition-colors text-sm"
                  title="Click to edit"
                >{{ q.time_limit }}s</button>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <button
                    @click="openEdit(q)"
                    class="text-blue-400 hover:text-blue-300 text-xs font-medium transition-colors"
                  >Edit</button>

                  <template v-if="deleteConfirm === q.id">
                    <button
                      @click="deleteQuestion(q.id)"
                      class="text-red-400 hover:text-red-300 text-xs font-medium transition-colors"
                    >Confirm?</button>
                    <button
                      @click="deleteConfirm = null"
                      class="text-gray-400 hover:text-gray-300 text-xs transition-colors"
                    >Cancel</button>
                  </template>
                  <button
                    v-else
                    @click="deleteConfirm = q.id"
                    class="text-red-400 hover:text-red-300 text-xs font-medium transition-colors"
                  >Delete</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Slide-in panel overlay -->
    <Transition name="slide">
      <div v-if="showForm" class="fixed inset-0 flex justify-end z-50">
        <div class="absolute inset-0 bg-black/60" @click="closeForm"></div>

        <div class="relative bg-gray-800 w-full max-w-md h-full overflow-y-auto shadow-2xl flex flex-col">
          <div class="flex items-center justify-between px-6 py-5 border-b border-gray-700">
            <h3 class="text-xl font-bold text-gray-100">
              {{ editingId ? 'Edit Question' : 'Add Question' }}
            </h3>
            <button @click="closeForm" class="text-gray-400 hover:text-gray-200 text-2xl leading-none">&times;</button>
          </div>

          <form @submit.prevent="saveQuestion" class="p-6 space-y-5 flex-1">
            <div>
              <label class="block text-sm text-gray-400 mb-1">Question</label>
              <textarea
                v-model="form.question"
                required
                rows="3"
                class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                placeholder="Enter question text…"
              ></textarea>
            </div>

            <div v-for="i in 4" :key="i">
              <label class="block text-sm text-gray-400 mb-1">
                Option {{ String.fromCharCode(64 + i) }}
              </label>
              <input
                v-model="form.options[i - 1]"
                required
                type="text"
                class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                :placeholder="`Option ${String.fromCharCode(64 + i)}`"
              />
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-2">Correct Answer</label>
              <div class="flex gap-4">
                <label
                  v-for="i in 4"
                  :key="i"
                  class="flex items-center gap-1.5 cursor-pointer"
                >
                  <input
                    type="radio"
                    :value="i - 1"
                    v-model="form.answer"
                    class="accent-purple-500 w-4 h-4"
                  />
                  <span class="text-sm font-semibold">{{ String.fromCharCode(64 + i) }}</span>
                </label>
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-2">Image <span class="text-gray-600">(optional)</span></label>

              <div v-if="form.image" class="relative mb-3 rounded-xl overflow-hidden bg-gray-900">
                <img :src="form.image" class="w-full max-h-48 object-contain" />
                <button
                  type="button"
                  @click="removeImage"
                  class="absolute top-2 right-2 bg-red-600 hover:bg-red-500 text-white rounded-full w-7 h-7 flex items-center justify-center text-base leading-none transition-colors"
                  title="Remove image"
                >&times;</button>
              </div>
              <div
                v-else
                class="mb-3 h-24 border-2 border-dashed border-gray-600 rounded-xl flex items-center justify-center text-gray-600 text-sm select-none"
              >No image</div>

              <label class="flex items-center justify-center gap-2 cursor-pointer bg-gray-700 hover:bg-gray-600 py-2 rounded-lg text-sm mb-3 transition-colors">
                <span>📁</span> Choose file
                <input type="file" accept="image/*" class="hidden" @change="onFileSelect" />
              </label>

              <input
                v-model="imageUrlInput"
                type="url"
                placeholder="…or paste an image URL"
                class="w-full bg-gray-700 rounded-lg px-4 py-2 text-gray-100 placeholder-gray-500 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                @input="onUrlInput"
              />
              <p v-if="imageError" class="text-red-400 text-xs mt-1">{{ imageError }}</p>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">Time Limit (seconds)</label>
              <input
                v-model.number="form.time_limit"
                type="number"
                min="5"
                max="300"
                required
                class="w-full bg-gray-700 rounded-lg px-4 py-2.5 text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <p v-if="formError" class="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
              {{ formError }}
            </p>

            <div class="flex gap-3 pt-2">
              <button
                type="submit"
                :disabled="saving"
                class="flex-1 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 py-2.5 rounded-xl font-semibold transition-colors"
              >{{ saving ? 'Saving…' : (editingId ? 'Update' : 'Add Question') }}</button>
              <button
                type="button"
                @click="closeForm"
                class="flex-1 bg-gray-700 hover:bg-gray-600 py-2.5 rounded-xl font-semibold transition-colors"
              >Cancel</button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import axios from 'axios'
import AdminNav from '../components/AdminNav.vue'

const questions = ref([])
const showForm = ref(false)
const editingId = ref(null)
const deleteConfirm = ref(null)
const saving = ref(false)
const formError = ref('')

const timeInput = ref(null)
const timeEdit = ref({ id: null, value: null })

const imageUrlInput = ref('')
const imageError = ref('')

function defaultForm() {
  return { question: '', options: ['', '', '', ''], answer: 0, time_limit: 30, image: null }
}
const form = ref(defaultForm())

function onFileSelect(e) {
  const file = e.target.files[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    imageError.value = 'File must be under 2 MB'
    e.target.value = ''
    return
  }
  imageError.value = ''
  const reader = new FileReader()
  reader.onload = () => {
    form.value.image = reader.result
    imageUrlInput.value = ''
  }
  reader.readAsDataURL(file)
}

function onUrlInput() {
  form.value.image = imageUrlInput.value || null
  imageError.value = ''
}

function removeImage() {
  form.value.image = null
  imageUrlInput.value = ''
  imageError.value = ''
}

function startTimeEdit(q) {
  timeEdit.value = { id: q.id, value: q.time_limit }
  nextTick(() => timeInput.value?.focus())
}

async function saveTimeLimit(q) {
  const newVal = timeEdit.value.value
  timeEdit.value = { id: null, value: null }
  if (!newVal || newVal === q.time_limit) return
  try {
    await axios.put(`/api/admin/questions/${q.id}`, { ...q, time_limit: newVal })
    q.time_limit = newVal
  } catch (e) {
    console.error('Failed to update time limit', e)
  }
}

async function loadQuestions() {
  try {
    const res = await axios.get('/api/admin/questions')
    questions.value = res.data
  } catch (e) {
    console.error('Failed to load questions', e)
  }
}

function openAdd() {
  editingId.value = null
  form.value = defaultForm()
  formError.value = ''
  imageUrlInput.value = ''
  imageError.value = ''
  showForm.value = true
}

function openEdit(q) {
  editingId.value = q.id
  form.value = {
    question: q.question,
    options: [...q.options],
    answer: q.answer,
    time_limit: q.time_limit,
    image: q.image || null,
  }
  imageUrlInput.value = q.image && !q.image.startsWith('data:') ? q.image : ''
  formError.value = ''
  imageError.value = ''
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  imageUrlInput.value = ''
  imageError.value = ''
}

async function saveQuestion() {
  formError.value = ''
  saving.value = true
  try {
    if (editingId.value) {
      await axios.put(`/api/admin/questions/${editingId.value}`, form.value)
    } else {
      await axios.post('/api/admin/questions', form.value)
    }
    await loadQuestions()
    closeForm()
  } catch (e) {
    formError.value = e.response?.data?.error || 'Failed to save question.'
  } finally {
    saving.value = false
  }
}

async function deleteQuestion(id) {
  try {
    await axios.delete(`/api/admin/questions/${id}`)
    deleteConfirm.value = null
    await loadQuestions()
  } catch (e) {
    console.error('Delete failed', e)
  }
}

onMounted(() => {
  loadQuestions()
})
</script>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: opacity 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}
.slide-enter-active .relative,
.slide-leave-active .relative {
  transition: transform 0.3s ease;
}
.slide-enter-from .relative,
.slide-leave-to .relative {
  transform: translateX(100%);
}
</style>
