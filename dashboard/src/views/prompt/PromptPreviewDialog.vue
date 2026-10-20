<template>
  <v-dialog
    v-model="visible"
    max-width="700px"
    scrollable
    :aria-label="displayName"
  >
    <v-card v-if="prompt" class="app-dialog prompt-preview">
      <v-card-title
        class="app-dialog__title prompt-preview__head d-flex justify-space-between align-center"
      >
        <span class="text-title-small">{{ displayName }}</span>
        <div class="d-flex align-center ga-1">
          <v-btn
            color="primary"
            variant="tonal"
            size="small"
            prepend-icon="mdi-pencil"
            @click="emit('edit')"
          >
            {{ tm('buttons.edit') }}
          </v-btn>
          <v-btn
            icon="mdi-close"
            variant="text"
            :aria-label="tm('buttons.close')"
            @click="visible = false"
          />
        </div>
      </v-card-title>

      <v-card-text class="prompt-preview__content">
        <div class="prompt-preview__block">
          <h4 class="prompt-preview__label">{{ tm('form.systemPrompt') }}</h4>
          <pre class="prompt-preview__code">{{ prompt.system_prompt }}</pre>
        </div>

        <div v-if="prompt.custom_error_message" class="prompt-preview__block">
          <h4 class="prompt-preview__label">
            {{ tm('form.customErrorMessage') }}
          </h4>
          <pre class="prompt-preview__code">{{
            prompt.custom_error_message
          }}</pre>
        </div>

        <div
          v-if="prompt.begin_dialogs && prompt.begin_dialogs.length > 0"
          class="prompt-preview__block"
        >
          <h4 class="prompt-preview__label">{{ tm('form.presetDialogs') }}</h4>
          <div
            v-for="(dialog, index) in prompt.begin_dialogs"
            :key="index"
            class="prompt-preview__dialog"
          >
            <v-chip
              :color="index % 2 === 0 ? 'primary' : 'secondary'"
              variant="tonal"
              size="small"
              class="mb-1"
            >
              {{
                index % 2 === 0
                  ? tm('form.userMessage')
                  : tm('form.assistantMessage')
              }}
            </v-chip>
            <div class="prompt-preview__dialog-text">{{ dialog }}</div>
          </div>
        </div>

        <div class="prompt-preview__block">
          <h4 class="prompt-preview__label">{{ tm('form.tools') }}</h4>
          <v-chip
            v-if="prompt.tools === null"
            size="small"
            color="success"
            variant="tonal"
            prepend-icon="mdi-check-all"
          >
            {{ tm('form.allToolsAvailable') }}
          </v-chip>
          <div
            v-else-if="prompt.tools && prompt.tools.length > 0"
            class="d-flex flex-wrap ga-1"
          >
            <v-chip
              v-for="toolName in prompt.tools"
              :key="toolName"
              size="small"
              color="primary"
              variant="tonal"
            >
              {{ toolName }}
            </v-chip>
          </div>
          <div v-else class="text-body-2 text-medium-emphasis">
            {{ tm('form.noToolsSelected') }}
          </div>
        </div>

        <div class="prompt-preview__block">
          <h4 class="prompt-preview__label">{{ tm('form.skills') }}</h4>
          <v-chip
            v-if="prompt.skills === null"
            size="small"
            color="success"
            variant="tonal"
            prepend-icon="mdi-check-all"
          >
            {{ tm('form.allSkillsAvailable') }}
          </v-chip>
          <div
            v-else-if="prompt.skills && prompt.skills.length > 0"
            class="d-flex flex-wrap ga-1"
          >
            <v-chip
              v-for="skillName in prompt.skills"
              :key="skillName"
              size="small"
              color="primary"
              variant="tonal"
            >
              {{ skillName }}
            </v-chip>
          </div>
          <div v-else class="text-body-2 text-medium-emphasis">
            {{ tm('form.noSkillsSelected') }}
          </div>
        </div>

        <div class="text-caption text-medium-emphasis">
          <div>
            {{ tm('labels.createdAt') }}:
            {{ formatDate(prompt.created_at) }}
          </div>
          <div v-if="prompt.updated_at">
            {{ tm('labels.updatedAt') }}:
            {{ formatDate(prompt.updated_at) }}
          </div>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import { formatDate } from '@/utils/text';
import type { Prompt } from '@/stores/promptStore';

const props = defineProps<{
  modelValue: boolean;
  prompt: Prompt | null;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  edit: [];
}>();

const { tm } = useModuleI18n('features/prompt');
const { tm: sharedTm } = useModuleI18n('core.shared');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => void emit('update:modelValue', value),
});

const displayName = computed(() =>
  props.prompt?.prompt_id === 'default'
    ? sharedTm('promptSelector.defaultPrompt')
    : (props.prompt?.prompt_id ?? ''),
);
</script>

<style scoped>
.prompt-preview {
  display: flex;
  flex-direction: column;
  max-height: min(88dvh, 860px);
}

.prompt-preview__head {
  flex: 0 0 auto;
}

.prompt-preview__content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.prompt-preview__block {
  margin-bottom: 16px;
}

.prompt-preview__label {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
  margin: 0 0 8px;
}

.prompt-preview__code {
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
  max-height: 400px;
  overflow: auto;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.prompt-preview__dialog {
  margin-bottom: 8px;
}

.prompt-preview__dialog-text {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
  padding: 8px 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
