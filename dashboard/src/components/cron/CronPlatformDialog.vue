<template>
  <v-dialog
    v-model="modelValue"
    max-width="520"
    scrollable
    :aria-label="tm('platformDialog.title')"
  >
    <v-card class="dashboard-dialog-card platform-dialog__card">
      <v-card-title class="text-h3 pt-5 px-5">
        {{ tm('platformDialog.title') }}
      </v-card-title>
      <v-card-text class="px-5 pb-2 platform-dialog__content">
        <p class="platform-dialog-description">
          {{ tm('platformDialog.description') }}
        </p>
        <div v-if="platforms.length" class="platform-list">
          <div
            v-for="platform in platforms"
            :key="platform.id"
            class="platform-list-item"
          >
            <div class="platform-name">
              {{ platform.display_name || platform.name }}
            </div>
            <div class="platform-id">{{ platform.id }}</div>
          </div>
        </div>
        <div v-else class="dashboard-empty platform-dialog-empty">
          {{ tm('page.proactive.unsupported') }}
        </div>
      </v-card-text>
      <v-card-actions class="justify-end px-5 pb-5 platform-dialog__actions">
        <v-btn variant="text" @click="modelValue = false">
          {{ tm('actions.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

const modelValue = defineModel<boolean>({ required: true });

withDefaults(
  defineProps<{
    platforms?: { id: string; name: string; display_name?: string }[];
  }>(),
  {
    platforms: () => [],
  },
);

const { tm } = useModuleI18n('features/cron');
</script>

<style scoped>
.platform-dialog-description {
  margin: 0 0 16px;
  color: var(--dashboard-muted);
  font-size: 14px;
  line-height: 1.7;
}

.platform-list {
  display: grid;
  gap: 10px;
  max-height: min(56dvh, 480px);
  overflow-y: auto;
  overscroll-behavior: contain;
}

.platform-list-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--dashboard-border);
  border-radius: 8px;
}

.platform-name {
  min-width: 0;
  color: var(--dashboard-text);
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.platform-id {
  color: var(--dashboard-muted);
  font-size: 12px;
}

.platform-dialog-empty {
  min-height: 120px;
}

.platform-dialog__card {
  display: flex;
  flex-direction: column;
  max-height: min(88dvh, 720px);
}

.platform-dialog__content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.platform-dialog__actions {
  flex-shrink: 0;
}
</style>
