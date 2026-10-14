<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

const { tm } = useModuleI18n('features/extension');

defineProps<{
  loading: boolean;
  totalSkills: number;
  resultCount: number;
  search: string;
}>();

const emit = defineEmits<{
  (e: 'update:search', value: string): void;
}>();

function onSearchUpdate(value: string | null) {
  emit('update:search', value ?? '');
}
</script>

<template>
  <div class="pb-3">
    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
    ></v-progress-linear>

    <div v-else-if="totalSkills === 0" class="text-center pa-8">
      <v-icon size="64" color="on-surface-variant">mdi-folder-open</v-icon>
      <p class="text-medium-emphasis mt-4">{{ tm('skills.empty') }}</p>
      <small class="text-medium-emphasis">{{ tm('skills.emptyHint') }}</small>
    </div>

    <template v-else>
      <div class="skills-list-header">
        <h3 class="skills-list-title text-h3">
          {{ tm('status.installed') }}
        </h3>
        <div class="skills-search-wrap">
          <v-text-field
            :model-value="search"
            :label="tm('skills.searchPlaceholder')"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="solo-filled"
            flat
            clearable
            hide-details
            single-line
            class="skills-search-field"
            @update:model-value="onSearchUpdate"
          />
        </div>
        <div class="skills-list-actions">
          <slot name="actions" />
        </div>
      </div>

      <div v-if="resultCount === 0" class="text-center pa-8">
        <v-icon size="64" color="on-surface-variant">mdi-magnify</v-icon>
        <p class="text-medium-emphasis mt-4">
          {{ tm('skills.noSearchResult') }}
        </p>
      </div>

      <div v-else class="skills-list">
        <slot />
      </div>
    </template>
  </div>
</template>

<style scoped>
.skills-list-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.skills-list-title {
  margin: 0 auto 0 0;
}

.skills-list-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skills-search-wrap {
  flex: 0 1 300px;
  min-width: 200px;
}

.skills-search-field {
  width: 100%;
}

.skills-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 640px) {
  .skills-list-header {
    align-items: stretch;
  }

  .skills-search-wrap {
    flex: 1 1 100%;
  }

  .skills-list-actions {
    margin-left: 0;
    width: 100%;
  }
}
</style>
