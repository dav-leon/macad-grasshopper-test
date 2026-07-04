<template>
  <div class="flex gap-1 mb-6 border-b border-gray-700">
    <router-link
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors"
      :class="isActive(item.to)
        ? 'border-purple-500 text-purple-400'
        : 'border-transparent text-gray-400 hover:text-gray-200'"
    >{{ item.label }}</router-link>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const items = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/questions', label: 'Questions' },
  { to: '/admin/results', label: 'Results' },
]

const route = useRoute()

function isActive(path) {
  return route.path === path
}
</script>
