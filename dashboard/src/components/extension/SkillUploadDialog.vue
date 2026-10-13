<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import {
  STATUS_ERROR,
  STATUS_UPLOADING,
  STATUS_WAITING,
  formatFileSize,
  statusChipClass,
  type UploadItem,
  type UploadStatus,
} from './skillsHelpers';

const { t } = useI18n();
const { tm } = useModuleI18n('features/extension');

const props = defineProps<{
  show: boolean;
  uploading: boolean;
  items: UploadItem[];
}>();

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
  (e: 'close'): void;
  (e: 'addFiles', files: File[]): void;
  (e: 'remove', id: string): void;
  (e: 'confirm'): void;
}>();

const uploadInput = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);

const uploadStateCounts = computed(() =>
  props.items.reduce(
    (counts, item) => {
      counts.total += 1;
      counts[item.status] += 1;
      return counts;
    },
    {
      total: 0,
      waiting: 0,
      uploading: 0,
      success: 0,
      error: 0,
      skipped: 0,
    },
  ),
);

const hasUploadableItems = computed(() =>
  props.items.some(
    (item) => item.status === STATUS_WAITING || item.status === STATUS_ERROR,
  ),
);

function uploadStatusLabel(status: UploadStatus) {
  if (status === STATUS_UPLOADING) return tm('skills.statusUploading');
  if (status === 'success') return tm('skills.statusSuccess');
  if (status === STATUS_ERROR) return tm('skills.statusError');
  if (status === 'skipped') return tm('skills.statusSkipped');
  return tm('skills.statusWaiting');
}

function openPicker() {
  if (props.uploading) return;
  uploadInput.value?.click();
}

function onSelection(event: Event) {
  const input = event.target;
  const selected =
    input instanceof HTMLInputElement && input.files
      ? Array.from(input.files)
      : [];
  emit('addFiles', selected);
  if (uploadInput.value) {
    uploadInput.value.value = '';
  }
}

function onDrop(event: DragEvent) {
  isDragging.value = false;
  if (props.uploading) {
    return;
  }
  emit('addFiles', Array.from(event.dataTransfer?.files || []));
}

watch(
  () => props.show,
  (open) => {
    if (open) return;
    isDragging.value = false;
    if (uploadInput.value) {
      uploadInput.value.value = '';
    }
  },
);
</script>

<template>
  <v-dialog
    :model-value="show"
    max-width="880px"
    scrollable
    :persistent="uploading"
    :aria-label="tm('skills.uploadDialogTitle')"
    @update:model-value="emit('update:show', $event)"
  >
    <v-card class="skills-upload-dialog">
      <v-card-title class="skills-upload-dialog__header px-6 pt-6 pb-2">
        <div class="skills-upload-dialog__heading">
          <div class="text-h4 font-weight-medium">
            {{ tm('skills.uploadDialogTitle') }}
          </div>
        </div>
        <v-btn
          class="skills-upload-dialog__close"
          icon="mdi-close"
          variant="text"
          :aria-label="t('core.common.close')"
          :disabled="uploading"
          @click="emit('close')"
        />
      </v-card-title>

      <v-card-text class="skills-upload-dialog__body px-6 pb-5 pt-2">
        <p
          class="skills-upload-dialog__description skills-upload-dialog__description--body"
        >
          {{ tm('skills.uploadHint') }}
        </p>

        <div class="skills-upload-structure-note">
          <v-icon size="18">mdi-information-outline</v-icon>
          <span>{{ tm('skills.structureRequirement') }}</span>
        </div>

        <div class="skills-upload-capabilities">
          <div class="skills-upload-capability">
            <div class="skills-upload-capability__icon">
              <v-icon size="18">mdi-layers-outline</v-icon>
            </div>
            <span>{{ tm('skills.abilityMultiple') }}</span>
          </div>
          <div class="skills-upload-capability">
            <div class="skills-upload-capability__icon">
              <v-icon size="18">mdi-shield-check-outline</v-icon>
            </div>
            <span>{{ tm('skills.abilityValidate') }}</span>
          </div>
          <div class="skills-upload-capability">
            <div class="skills-upload-capability__icon">
              <v-icon size="18">mdi-skip-next-circle-outline</v-icon>
            </div>
            <span>{{ tm('skills.abilitySkip') }}</span>
          </div>
        </div>

        <div
          class="skills-dropzone"
          :class="{ 'skills-dropzone--dragover': isDragging }"
          role="button"
          tabindex="0"
          :aria-label="tm('skills.dropzoneTitle')"
          @click="openPicker"
          @keydown.enter="openPicker"
          @keydown.space.prevent="openPicker"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
        >
          <div class="skills-dropzone__icon">
            <v-icon size="34">mdi-folder-zip-outline</v-icon>
          </div>
          <div class="text-h6 font-weight-medium">
            {{ tm('skills.dropzoneTitle') }}
          </div>
          <div class="skills-dropzone__subtitle">
            {{ tm('skills.dropzoneAction') }}
          </div>
          <div class="skills-dropzone__hint">
            {{ tm('skills.dropzoneHint') }}
          </div>
          <input
            ref="uploadInput"
            type="file"
            multiple
            hidden
            accept=".zip"
            @change="onSelection"
          />
        </div>

        <div v-if="items.length > 0" class="skills-upload-summary">
          <v-chip
            size="small"
            variant="flat"
            class="skills-upload-summary__chip"
          >
            {{ tm('skills.summaryTotal', { count: uploadStateCounts.total }) }}
          </v-chip>
          <v-chip
            size="small"
            variant="flat"
            class="skills-upload-summary__chip"
          >
            {{
              tm('skills.summaryReady', {
                count: uploadStateCounts.waiting + uploadStateCounts.uploading,
              })
            }}
          </v-chip>
          <v-chip
            size="small"
            variant="flat"
            class="skills-upload-summary__chip skills-upload-summary__chip--success"
          >
            {{
              tm('skills.summarySuccess', {
                count: uploadStateCounts.success,
              })
            }}
          </v-chip>
          <v-chip
            size="small"
            variant="flat"
            class="skills-upload-summary__chip skills-upload-summary__chip--error"
          >
            {{ tm('skills.summaryFailed', { count: uploadStateCounts.error }) }}
          </v-chip>
          <v-chip
            size="small"
            variant="flat"
            class="skills-upload-summary__chip"
          >
            {{
              tm('skills.summarySkipped', {
                count: uploadStateCounts.skipped,
              })
            }}
          </v-chip>
        </div>

        <div v-if="items.length > 0" class="skills-upload-list">
          <div class="skills-upload-list__header">
            <span>{{ tm('skills.fileListTitle') }}</span>
          </div>
          <div v-for="item in items" :key="item.id" class="skills-upload-row">
            <div class="skills-upload-row__meta">
              <div class="skills-upload-row__name">{{ item.name }}</div>
              <div class="skills-upload-row__size">
                {{ formatFileSize(item.size) }}
              </div>
              <div class="skills-upload-row__message">
                {{ item.validationMessage }}
              </div>
            </div>
            <div class="skills-upload-row__actions">
              <v-chip
                size="small"
                variant="flat"
                :class="statusChipClass(item.status)"
              >
                {{ uploadStatusLabel(item.status) }}
              </v-chip>
              <v-btn
                icon="mdi-close"
                size="small"
                variant="text"
                :aria-label="t('core.actions.delete')"
                :disabled="uploading || item.status === 'uploading'"
                @click="emit('remove', item.id)"
              />
            </div>
          </div>
        </div>
        <div v-else class="skills-upload-empty">
          {{ tm('skills.fileListEmpty') }}
        </div>
      </v-card-text>

      <v-card-actions
        class="skills-upload-dialog__actions justify-end px-6 pb-3 pt-2"
      >
        <v-btn
          class="skills-upload-dialog__action-btn"
          variant="tonal"
          color="secondary"
          :disabled="uploading"
          @click="emit('close')"
        >
          {{ tm('skills.cancel') }}
        </v-btn>
        <v-btn
          class="skills-upload-dialog__action-btn"
          variant="flat"
          color="primary"
          :loading="uploading"
          :disabled="!hasUploadableItems"
          @click="emit('confirm')"
        >
          {{ tm('skills.confirmUpload') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.skills-upload-dialog {
  display: flex;
  flex-direction: column;
  max-height: min(88vh, 960px);
  border-radius: 24px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid var(--v-theme-border);
  outline: 1px solid rgba(var(--v-theme-primary), 0.1);
  outline-offset: -1px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}

.skills-upload-dialog__header {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: flex-start;
  gap: 16px;
  white-space: normal;
  overflow: visible;
}

.skills-upload-dialog__heading {
  min-width: 0;
  padding-right: 0;
  white-space: normal;
}

.skills-upload-dialog__description {
  max-width: 100%;
  color: var(--v-theme-on-surface-variant);
  line-height: 1.7;
  word-break: break-word;
  white-space: normal;
  overflow-wrap: anywhere;
}

.skills-upload-dialog__description--body {
  margin: 0 0 14px;
  font-size: 15px;
  line-height: 1.6;
}

.skills-upload-dialog__close {
  align-self: flex-start;
}

.skills-upload-dialog__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.skills-upload-dialog__actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  border-top: 1px solid var(--v-theme-border);
  background: rgba(var(--v-theme-surface), 0.98);
}

.skills-upload-dialog__action-btn {
  min-width: 96px;
  height: 38px;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
}

.skills-upload-structure-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-primary), 0.18);
  background: rgba(var(--v-theme-surface), 0.96);
  color: var(--v-theme-on-surface-variant);
  line-height: 1.6;
}

.skills-upload-capabilities {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.skills-upload-capability {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 52px;
  padding: 0 14px;
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  background: rgba(var(--v-theme-surface), 0.96);
  color: var(--v-theme-on-surface-variant);
}

.skills-upload-capability__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: rgba(var(--v-theme-primary), 0.16);
  color: rgba(var(--v-theme-primary), 0.95);
}

.skills-dropzone {
  padding: 36px 24px;
  border-radius: 22px;
  border: 1.5px dashed rgba(var(--v-theme-primary), 0.24);
  background: rgba(var(--v-theme-surface), 0.94);
  text-align: center;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease,
    background-color 0.2s ease;
}

.skills-dropzone:hover,
.skills-dropzone--dragover {
  border-color: rgba(var(--v-theme-primary), 0.52);
  background: rgba(var(--v-theme-primary), 0.05);
  transform: translateY(-1px);
}

.skills-dropzone__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 66px;
  height: 66px;
  margin: 0 auto 18px;
  border-radius: 20px;
  background: rgba(var(--v-theme-primary), 0.15);
  color: rgba(var(--v-theme-primary), 0.96);
}

.skills-dropzone__subtitle {
  margin-top: 10px;
  color: var(--v-theme-on-surface-variant);
}

.skills-dropzone__hint {
  margin-top: 8px;
  font-size: 13px;
  color: var(--v-theme-on-surface-variant);
  opacity: 0.82;
}

.skills-upload-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.skills-upload-summary__chip {
  background: rgba(var(--v-theme-surface), 0.96);
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  color: var(--v-theme-on-surface-variant);
}

.skills-upload-summary__chip--success {
  background: rgba(var(--v-theme-primary), 0.18);
  color: var(--v-theme-on-surface);
}

.skills-upload-summary__chip--error {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-error));
}

.skills-upload-list {
  margin-top: 16px;
  border-radius: 8px;
  border: 1px solid rgba(var(--v-theme-primary), 0.2);
  background: rgba(var(--v-theme-surface), 0.94);
  overflow: hidden;
}

.skills-upload-list__header {
  padding: 14px 18px;
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.14);
  color: var(--v-theme-on-surface);
  font-weight: 600;
}

.skills-upload-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
}

.skills-upload-row + .skills-upload-row {
  border-top: 1px solid rgba(var(--v-theme-primary), 0.12);
}

.skills-upload-row__meta {
  min-width: 0;
  flex: 1;
}

.skills-upload-row__name {
  font-weight: 600;
  color: var(--v-theme-on-surface);
  word-break: break-all;
}

.skills-upload-row__size {
  margin-top: 4px;
  font-size: 12px;
  color: var(--v-theme-on-surface-variant);
  opacity: 0.82;
}

.skills-upload-row__message {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--v-theme-on-surface-variant);
}

.skills-upload-row__actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.skills-status-chip {
  min-width: 74px;
  justify-content: center;
  font-weight: 600;
}

.skills-status-chip--waiting {
  background: rgba(var(--v-theme-surface), 0.96);
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  color: var(--v-theme-on-surface-variant);
}

.skills-status-chip--uploading {
  background: rgba(var(--v-theme-primary), 0.14);
  color: var(--v-theme-on-surface);
}

.skills-status-chip--success {
  background: rgba(var(--v-theme-primary), 0.2);
  color: var(--v-theme-on-surface);
}

.skills-status-chip--error {
  background: rgb(var(--v-theme-surface-variant));
  color: rgb(var(--v-theme-error));
}

.skills-status-chip--skipped {
  background: rgba(var(--v-theme-surface), 0.96);
  border: 1px solid rgba(var(--v-theme-primary), 0.16);
  color: var(--v-theme-on-surface-variant);
}

.skills-upload-empty {
  margin-top: 16px;
  padding: 20px 18px;
  border-radius: 8px;
  border: 1px dashed rgba(var(--v-theme-primary), 0.24);
  background: rgba(var(--v-theme-surface), 0.94);
  text-align: center;
  color: var(--v-theme-on-surface-variant);
}

@media (max-width: 860px) {
  .skills-upload-capabilities {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .skills-upload-dialog {
    max-height: 92vh;
  }

  .skills-upload-dialog__header {
    gap: 12px;
  }

  .skills-upload-dialog__heading {
    padding-right: 0;
  }

  .skills-upload-row {
    flex-direction: column;
  }

  .skills-upload-row__actions {
    justify-content: space-between;
    align-items: center;
  }

  .skills-upload-dialog__description--body {
    font-size: 14px;
  }
}
</style>
