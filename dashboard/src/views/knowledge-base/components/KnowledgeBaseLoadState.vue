<template>
  <div v-if="loading" class="loading-container">
    <v-progress-circular indeterminate color="primary" size="64" />
  </div>

  <div v-else-if="loadError" class="loading-container">
    <v-icon size="72" color="error">mdi-alert-circle-outline</v-icon>
    <p class="mt-4 text-medium-emphasis">{{ t('states.loadError') }}</p>
    <v-btn
      class="mt-4"
      prepend-icon="mdi-refresh"
      color="primary"
      variant="tonal"
      @click="emit('retry')"
    >
      {{ t('states.retry') }}
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';

defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
  loadError: {
    type: Boolean,
    default: false,
  },
  t: {
    type: Function as PropType<
      (key: string, params?: Record<string, string | number>) => string
    >,
    required: true,
  },
});

const emit = defineEmits(['retry']);
</script>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
