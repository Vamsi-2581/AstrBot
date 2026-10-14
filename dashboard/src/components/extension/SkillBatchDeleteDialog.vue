<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

const { tm } = useModuleI18n('features/extension');

defineProps<{
  show: boolean;
  targets: string[];
  deleting: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
  (e: 'confirm'): void;
}>();
</script>

<template>
  <v-dialog
    :model-value="show"
    max-width="520px"
    :persistent="deleting"
    :aria-label="tm('skills.batchDeleteTitle')"
    @update:model-value="emit('update:show', $event)"
  >
    <v-card>
      <v-card-title class="text-h3 pa-4 pb-0 pl-6">
        {{ tm('skills.batchDeleteTitle') }}
      </v-card-title>
      <v-card-text>
        <p>
          {{
            tm('skills.batchDeleteMessage', {
              count: targets.length,
            })
          }}
        </p>
        <v-list class="batch-delete-targets mt-3" density="compact">
          <v-list-item
            v-for="name in targets"
            :key="name"
            class="batch-delete-target"
            :title="name"
            prepend-icon="mdi-puzzle-outline"
          />
        </v-list>
      </v-card-text>
      <v-card-actions class="d-flex justify-end">
        <v-btn
          variant="text"
          :disabled="deleting"
          @click="emit('update:show', false)"
        >
          {{ tm('skills.cancel') }}
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          :loading="deleting"
          :disabled="targets.length === 0"
          @click="emit('confirm')"
        >
          {{
            tm('skills.batchDeleteConfirm', {
              count: targets.length,
            })
          }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.batch-delete-targets {
  background: transparent;
  max-height: 240px;
  overflow-y: auto;
  padding: 0;
}

.batch-delete-target {
  background: rgba(var(--v-theme-on-surface), 0.05);
  border-radius: 8px;
}

.batch-delete-target + .batch-delete-target {
  margin-top: 6px;
}
</style>
