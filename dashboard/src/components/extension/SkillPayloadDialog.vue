<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

const { tm } = useModuleI18n('features/extension');

defineProps<{
  show: boolean;
  content: string;
}>();

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
}>();
</script>

<template>
  <v-dialog
    :model-value="show"
    max-width="820px"
    scrollable
    :aria-label="tm('skills.neoPayloadTitle')"
    @update:model-value="emit('update:show', $event)"
  >
    <v-card class="payload-dialog">
      <v-card-title>{{ tm('skills.neoPayloadTitle') }}</v-card-title>
      <v-card-text class="payload-dialog__body">
        <pre class="payload-preview">{{ content }}</pre>
      </v-card-text>
      <v-card-actions class="payload-dialog__actions d-flex justify-end">
        <v-btn variant="text" @click="emit('update:show', false)">{{
          tm('skills.cancel')
        }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.payload-preview {
  margin: 0;
  min-height: 0;
  overflow: auto;
  background: rgb(var(--v-theme-code-surface));
  color: rgb(var(--v-theme-code-text));
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
}

.payload-dialog {
  display: flex;
  flex-direction: column;
  max-height: min(80vh, 760px);
  overflow: hidden;
}

.payload-dialog__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.payload-dialog__actions {
  flex: 0 0 auto;
}
</style>
