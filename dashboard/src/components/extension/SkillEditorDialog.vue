<script setup lang="ts">
import { computed } from 'vue';
import { LazyMonacoEditor as VueMonacoEditor } from '@/components/shared/LazyMonacoEditor';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import { useCustomizerStore } from '@/stores/customizer';
import type { SkillEntry } from './skillsHelpers';

const { t } = useI18n();
const { tm } = useModuleI18n('features/extension');
const customizer = useCustomizerStore();

const props = defineProps<{
  show: boolean;
  fullscreen: boolean;
  skillName: string;
  currentDir: string;
  entries: SkillEntry[];
  filePath: string;
  content: string;
  fileEditable: boolean;
  fileDirty: boolean;
  loadingFiles: boolean;
  loadingFile: boolean;
  saving: boolean;
  error: string;
}>();

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
  (e: 'update:content', value: string): void;
  (e: 'dirty'): void;
  (e: 'openEntry', entry: SkillEntry): void;
  (e: 'openParent'): void;
  (e: 'save'): void;
  (e: 'close'): void;
}>();

const editorLanguage = computed(() => {
  const path = props.filePath.toLowerCase();
  if (path.endsWith('.json')) return 'json';
  if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml';
  if (path.endsWith('.toml') || path.endsWith('.ini')) return 'ini';
  if (path.endsWith('.py')) return 'python';
  if (path.endsWith('.js')) return 'javascript';
  if (path.endsWith('.ts')) return 'typescript';
  if (path.endsWith('.html')) return 'html';
  if (path.endsWith('.css')) return 'css';
  if (path.endsWith('.sh')) return 'shell';
  if (path.endsWith('.md') || path.endsWith('.txt')) return 'markdown';
  return 'plaintext';
});

const editorTheme = computed(() =>
  customizer.uiTheme === 'AstrBotDark' ? 'vs-dark' : 'vs-light',
);

const editorOptions = computed(() => ({
  automaticLayout: true,
  fontSize: 13,
  lineNumbers: 'on',
  minimap: { enabled: false },
  readOnly: !props.fileEditable || props.loadingFile,
  scrollBeyondLastLine: false,
  tabSize: 2,
  wordWrap: 'on',
}));
</script>

<template>
  <v-dialog
    :model-value="show"
    max-width="1180px"
    scrollable
    :fullscreen="fullscreen"
    :persistent="saving"
    :aria-label="skillName"
    @update:model-value="emit('update:show', $event)"
  >
    <v-card class="skill-editor-dialog">
      <v-card-title class="skill-editor-dialog__header">
        <div>
          <div class="text-h3 font-weight-bold">
            {{ skillName }}
          </div>
        </div>
        <v-btn
          icon="mdi-close"
          variant="text"
          :aria-label="t('core.common.close')"
          :disabled="saving"
          @click="emit('close')"
        />
      </v-card-title>

      <v-card-text class="skill-editor-dialog__body">
        <div class="skill-editor">
          <div class="skill-editor__files">
            <div class="skill-editor__files-header">
              <v-btn
                icon="mdi-arrow-up"
                size="small"
                variant="text"
                :aria-label="tm('skills.openParentDir')"
                :disabled="!currentDir || loadingFiles"
                @click="emit('openParent')"
              />
              <span>{{ currentDir || '/' }}</span>
            </div>

            <v-progress-linear
              v-if="loadingFiles"
              indeterminate
              color="primary"
            />

            <div v-else class="skill-editor__file-list">
              <button
                v-for="entry in entries"
                :key="`${entry.type}:${entry.path}`"
                class="skill-editor__file-row"
                :class="{
                  'skill-editor__file-row--active': filePath === entry.path,
                }"
                type="button"
                @click="emit('openEntry', entry)"
              >
                <v-icon size="18">
                  {{
                    entry.type === 'directory'
                      ? 'mdi-folder-outline'
                      : 'mdi-file-document-outline'
                  }}
                </v-icon>
                <span>{{ entry.name }}</span>
                <v-chip
                  v-if="entry.type === 'file' && !entry.editable"
                  size="x-small"
                  variant="tonal"
                >
                  {{ tm('skills.readonly') }}
                </v-chip>
              </button>
            </div>
          </div>

          <div class="skill-editor__content">
            <div class="skill-editor__content-header">
              <div class="skill-editor__path">
                {{ filePath || tm('skills.noFileSelected') }}
              </div>
              <v-chip
                v-if="fileDirty"
                size="small"
                color="warning"
                variant="tonal"
              >
                {{ tm('skills.unsaved') }}
              </v-chip>
            </div>

            <v-alert
              v-if="error"
              type="error"
              variant="tonal"
              density="compact"
              class="mb-3"
            >
              {{ error }}
            </v-alert>

            <div class="skill-editor__monaco">
              <VueMonacoEditor
                :value="content"
                :theme="editorTheme"
                :language="editorLanguage"
                :options="editorOptions"
                class="skill-editor__monaco-editor"
                @update:value="emit('update:content', $event)"
                @change="emit('dirty')"
              />
            </div>
          </div>
        </div>
      </v-card-text>

      <v-card-actions class="skill-editor-dialog__actions">
        <v-spacer />
        <v-btn variant="text" :disabled="saving" @click="emit('close')">
          {{ tm('skills.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          :loading="saving"
          :disabled="!filePath || !fileEditable || !fileDirty"
          @click="emit('save')"
        >
          {{ tm('skills.saveFile') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.skill-editor__monaco-editor {
  width: 100%;
  height: 100%;
}

.skill-editor-dialog {
  display: flex;
  flex-direction: column;
  height: min(88vh, 980px);
  max-height: min(88vh, 980px);
  overflow: hidden;
}

.skill-editor-dialog__header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px 14px;
}

.skill-editor-dialog__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  padding: 16px 22px;
}

.skill-editor-dialog__actions {
  border-top: 1px solid var(--v-theme-border);
  padding: 12px 22px;
}

.skill-editor {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: 16px;
  height: 100%;
  min-height: 0;
}

.skill-editor__files {
  border: 1px solid rgba(128, 128, 128, 0.28);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.skill-editor__files-header {
  align-items: center;
  border-bottom: 1px solid rgba(128, 128, 128, 0.28);
  display: flex;
  gap: 8px;
  min-height: 44px;
  padding: 6px 10px;
}

.skill-editor__files-header span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-editor__file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  padding: 6px;
}

.skill-editor__file-row {
  align-items: center;
  border-radius: 8px;
  color: rgb(var(--v-theme-on-surface));
  display: grid;
  gap: 8px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  min-height: 34px;
  padding: 6px 8px;
  text-align: left;
}

.skill-editor__file-row:hover,
.skill-editor__file-row--active {
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.skill-editor__file-row--active {
  background: rgba(var(--v-theme-on-surface), 0.1);
}

.skill-editor__file-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-editor__content {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

.skill-editor__content-header {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  min-height: 34px;
}

.skill-editor__path {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-editor__monaco {
  border: 1px solid rgba(128, 128, 128, 0.28);
  border-radius: 10px;
  flex: 1 1 auto;
  margin-top: 12px;
  min-height: 520px;
  overflow: hidden;
  position: relative;
}
</style>
