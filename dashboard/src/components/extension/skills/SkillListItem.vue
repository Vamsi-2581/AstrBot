<script setup lang="ts">
import { computed } from 'vue';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import OutlinedActionListItem from '@/components/shared/OutlinedActionListItem.vue';

const props = defineProps<{
  name: string;
  description: string;
  path: string;
  active: boolean;
  sourceColor: string;
  sourceLabel: string;
  readOnly: boolean;
  inactivePlugin: boolean;
  loading: boolean;
  batchSelectionEnabled: boolean;
  batchDeleting: boolean;
  selectedNames: string[];
  clickable: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:selectedNames', value: string[]): void;
  (e: 'open'): void;
  (e: 'download'): void;
  (e: 'delete'): void;
  (e: 'toggle'): void;
}>();

const { t } = useI18n();
const { tm } = useModuleI18n('features/extension');

const selectedModel = computed<string[]>({
  get: () => props.selectedNames,
  set: (value) => {
    emit('update:selectedNames', value);
  },
});
</script>

<template>
  <OutlinedActionListItem
    :title="name"
    :clickable="clickable"
    @click="emit('open')"
  >
    <template #title-prepend>
      <v-checkbox-btn
        v-if="batchSelectionEnabled && !readOnly"
        v-model="selectedModel"
        :value="name"
        density="compact"
        hide-details
        :disabled="batchDeleting"
        :aria-label="
          tm('skills.selectSkill', {
            name,
          })
        "
        @click.stop
      />
    </template>
    <template #title-extra>
      <v-chip size="x-small" variant="tonal" :color="sourceColor">
        {{ sourceLabel }}
      </v-chip>
      <v-chip
        v-if="inactivePlugin"
        size="x-small"
        color="warning"
        variant="tonal"
      >
        {{ tm('skills.pluginDisabled') }}
      </v-chip>
    </template>

    <div class="skill-description text-body-2 text-medium-emphasis">
      {{ description || tm('skills.noDescription') }}
    </div>

    <div class="skill-path text-caption text-medium-emphasis">
      <v-icon size="small" class="me-1">mdi-file-document</v-icon>
      {{ tm('skills.path') }}: {{ path }}
    </div>

    <template v-if="!batchSelectionEnabled" #actions>
      <v-tooltip :text="tm('skills.download')" location="top">
        <template #activator="{ props: activatorProps }">
          <v-btn
            v-bind="activatorProps"
            icon="mdi-download-outline"
            variant="text"
            size="small"
            class="list-action-icon-btn"
            :aria-label="tm('skills.download')"
            :disabled="loading || readOnly"
            @click.stop="emit('download')"
          />
        </template>
      </v-tooltip>

      <v-tooltip :text="t('core.common.itemCard.delete')" location="top">
        <template #activator="{ props: activatorProps }">
          <v-btn
            v-bind="activatorProps"
            icon="mdi-delete-outline"
            variant="text"
            size="small"
            class="list-action-icon-btn"
            :aria-label="t('core.common.itemCard.delete')"
            :disabled="loading || readOnly"
            @click.stop="emit('delete')"
          />
        </template>
      </v-tooltip>
    </template>

    <template v-if="!batchSelectionEnabled" #control>
      <v-tooltip location="top">
        <template #activator="{ props: activatorProps }">
          <v-switch
            v-bind="activatorProps"
            color="primary"
            density="compact"
            hide-details
            inset
            :aria-label="
              active
                ? t('core.common.itemCard.enabled')
                : t('core.common.itemCard.disabled')
            "
            :model-value="active && !inactivePlugin"
            :loading="loading"
            :disabled="loading || readOnly || inactivePlugin"
            @click.stop
            @update:model-value="emit('toggle')"
          />
        </template>
        <span>{{
          active
            ? t('core.common.itemCard.enabled')
            : t('core.common.itemCard.disabled')
        }}</span>
      </v-tooltip>
    </template>
  </OutlinedActionListItem>
</template>

<style scoped>
.list-action-icon-btn {
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.list-action-icon-btn:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: rgb(var(--v-theme-on-surface));
}

.skill-description {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skill-path {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  margin-top: 6px;
  overflow: hidden;
  word-break: break-all;
}
</style>
