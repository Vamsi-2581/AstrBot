<template>
  <v-dialog
    v-model="visible"
    max-width="550"
    scrollable
    :aria-label="tm('ruleEditor.title')"
  >
    <v-card v-if="selectedUmo" class="d-flex flex-column" height="600">
      <v-card-title class="py-3 px-6 d-flex align-center border-b">
        <span>{{ tm('ruleEditor.title') }}</span>
        <v-chip
          size="x-small"
          class="ml-2 font-weight-regular"
          variant="outlined"
        >
          {{
            isSenderRule(selectedUmo) ? selectedUmo.sender_id : selectedUmo.umo
          }}
        </v-chip>
        <v-spacer></v-spacer>
        <v-btn
          icon="mdi-close"
          variant="text"
          :aria-label="tm('buttons.close')"
          @click="emit('close')"
        ></v-btn>
      </v-card-title>

      <v-card-text class="pa-0 overflow-y-auto">
        <div class="px-6 py-4">
          <!-- Service Config Section -->
          <div class="d-flex align-center mb-4">
            <h3 class="font-weight-bold mb-0">
              {{ tm('ruleEditor.serviceConfig.title') }}
            </h3>
          </div>

          <v-row v-if="isSenderRule(selectedUmo)" density="comfortable">
            <v-col cols="12">
              <v-checkbox
                v-model="senderOverlay.blocked"
                :label="tm('ruleEditor.serviceConfig.blocked')"
                color="error"
                hide-details
                class="mb-2"
              />
            </v-col>
            <v-col cols="12">
              <v-select
                v-model="senderLlmMode"
                :items="senderLlmModeOptions"
                item-title="label"
                item-value="value"
                :label="tm('ruleEditor.serviceConfig.llmMode')"
                variant="outlined"
                hide-details
              />
            </v-col>
          </v-row>
          <v-row v-else density="comfortable">
            <v-col cols="12">
              <v-checkbox
                v-model="serviceConfig.session_enabled"
                :label="tm('ruleEditor.serviceConfig.sessionEnabled')"
                color="success"
                hide-details
                class="mb-2"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-checkbox
                v-model="serviceConfig.llm_enabled"
                :label="tm('ruleEditor.serviceConfig.llmEnabled')"
                color="primary"
                hide-details
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-checkbox
                v-model="serviceConfig.tts_enabled"
                :label="tm('ruleEditor.serviceConfig.ttsEnabled')"
                color="secondary"
                hide-details
              />
            </v-col>
            <v-col cols="12">
              <v-checkbox
                v-model="serviceConfig.session_blocked"
                :label="tm('ruleEditor.serviceConfig.sessionBlocked')"
                color="error"
                hide-details
              />
            </v-col>
            <v-col cols="12" class="mt-2">
              <v-text-field
                v-model="serviceConfig.custom_name"
                :label="tm('ruleEditor.serviceConfig.customName')"
                variant="outlined"
                hide-details
                clearable
              />
            </v-col>
          </v-row>

          <div class="d-flex justify-end mt-4">
            <v-btn
              color="primary"
              variant="tonal"
              size="small"
              :loading="saving"
              prepend-icon="mdi-content-save"
              @click="emit('save-service-config')"
            >
              {{ tm('buttons.save') }}
            </v-btn>
          </div>

          <template v-if="!isSenderRule(selectedUmo)">
            <!-- Provider Config Section -->
            <div class="d-flex align-center mb-4 mt-4">
              <h3 class="font-weight-bold mb-0">
                {{ tm('ruleEditor.providerConfig.title') }}
              </h3>
            </div>

            <v-row density="comfortable">
              <v-col cols="12">
                <v-select
                  v-model="providerConfig.chat_completion"
                  :items="chatProviderOptions"
                  item-title="label"
                  item-value="value"
                  :label="tm('ruleEditor.providerConfig.chatProvider')"
                  variant="outlined"
                  hide-details
                  class="mb-2"
                />
              </v-col>
              <v-col cols="12">
                <v-select
                  v-model="providerConfig.speech_to_text"
                  :items="sttProviderOptions"
                  item-title="label"
                  item-value="value"
                  :label="tm('ruleEditor.providerConfig.sttProvider')"
                  variant="outlined"
                  hide-details
                  :disabled="!hasSttProviders"
                  class="mb-2"
                />
              </v-col>
              <v-col cols="12">
                <v-select
                  v-model="providerConfig.text_to_speech"
                  :items="ttsProviderOptions"
                  item-title="label"
                  item-value="value"
                  :label="tm('ruleEditor.providerConfig.ttsProvider')"
                  variant="outlined"
                  hide-details
                  :disabled="!hasTtsProviders"
                />
              </v-col>
            </v-row>

            <div class="d-flex justify-end mt-4">
              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                :loading="saving"
                prepend-icon="mdi-content-save"
                @click="emit('save-provider-config')"
              >
                {{ tm('buttons.save') }}
              </v-btn>
            </div>

            <!-- Prompt Config Section -->
            <div class="d-flex align-center mb-4 mt-4">
              <h3 class="font-weight-bold mb-0">
                {{ tm('ruleEditor.promptConfig.title') }}
              </h3>
            </div>

            <v-row density="comfortable">
              <v-col cols="12">
                <v-select
                  v-model="serviceConfig.prompt_id"
                  :items="promptOptions"
                  item-title="label"
                  item-value="value"
                  :label="tm('ruleEditor.promptConfig.selectPrompt')"
                  variant="outlined"
                  hide-details
                  clearable
                />
              </v-col>
              <v-col cols="12">
                <v-alert
                  type="info"
                  variant="tonal"
                  class="mt-2"
                  icon="mdi-information-outline"
                >
                  {{ tm('ruleEditor.promptConfig.hint') }}
                </v-alert>
              </v-col>
            </v-row>

            <div class="d-flex justify-end mt-4">
              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                :loading="saving"
                prepend-icon="mdi-content-save"
                @click="emit('save-service-config')"
              >
                {{ tm('buttons.save') }}
              </v-btn>
            </div>

            <!-- Plugin Config Section -->
            <div class="d-flex align-center mb-4 mt-4">
              <h3 class="font-weight-bold mb-0">
                {{ tm('ruleEditor.pluginConfig.title') }}
              </h3>
            </div>

            <v-row density="comfortable">
              <v-col cols="12">
                <v-select
                  v-model="pluginConfig.disabled_plugins"
                  :items="pluginOptions"
                  item-title="label"
                  item-value="value"
                  :label="tm('ruleEditor.pluginConfig.disabledPlugins')"
                  variant="outlined"
                  hide-details
                  multiple
                  chips
                  closable-chips
                  clearable
                />
              </v-col>
              <v-col cols="12">
                <v-alert
                  type="info"
                  variant="tonal"
                  class="mt-2"
                  icon="mdi-information-outline"
                >
                  {{ tm('ruleEditor.pluginConfig.hint') }}
                </v-alert>
              </v-col>
            </v-row>

            <div class="d-flex justify-end mt-4">
              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                :loading="saving"
                prepend-icon="mdi-content-save"
                @click="emit('save-plugin-config')"
              >
                {{ tm('buttons.save') }}
              </v-btn>
            </div>

            <!-- KB Config Section -->
            <div class="d-flex align-center mb-4 mt-4">
              <h3 class="font-weight-bold mb-0">
                {{ tm('ruleEditor.kbConfig.title') }}
              </h3>
            </div>

            <v-row density="comfortable">
              <v-col cols="12">
                <v-select
                  v-model="kbConfig.kb_ids"
                  :items="kbOptions"
                  item-title="label"
                  item-value="value"
                  :disabled="!hasKbs"
                  :label="tm('ruleEditor.kbConfig.selectKbs')"
                  variant="outlined"
                  hide-details
                  multiple
                  chips
                  closable-chips
                  clearable
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="kbConfig.top_k"
                  :label="tm('ruleEditor.kbConfig.topK')"
                  variant="outlined"
                  hide-details
                  type="number"
                  min="1"
                  max="20"
                  class="mt-3"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-checkbox
                  v-model="kbConfig.enable_rerank"
                  :label="tm('ruleEditor.kbConfig.enableRerank')"
                  color="primary"
                  hide-details
                  class="mt-3"
                />
              </v-col>
            </v-row>

            <div class="d-flex justify-end mt-4">
              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                :loading="saving"
                prepend-icon="mdi-content-save"
                @click="emit('save-kb-config')"
              >
                {{ tm('buttons.save') }}
              </v-btn>
            </div>
          </template>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import { isSenderRule } from './sessionRuleNormalizers';
import {
  FOLLOW_SESSION_VALUE,
  type ProviderRuleType,
  type SelectOption,
  type SenderOverlayState,
  type SessionRuleItem,
} from './sessionRuleHelpers';

interface ServiceConfigForm {
  session_enabled: boolean;
  llm_enabled: boolean;
  tts_enabled: boolean;
  session_blocked: boolean;
  custom_name: string;
  prompt_id: string | null;
}

interface PluginConfigForm {
  enabled_plugins: string[];
  disabled_plugins: string[];
}

interface KbConfigForm {
  kb_ids: string[];
  top_k: number;
  enable_rerank: boolean;
}

const props = defineProps<{
  modelValue: boolean;
  selectedUmo: SessionRuleItem | null;
  saving: boolean;
  senderOverlay: SenderOverlayState;
  serviceConfig: ServiceConfigForm;
  providerConfig: Record<ProviderRuleType, string>;
  pluginConfig: PluginConfigForm;
  kbConfig: KbConfigForm;
  chatProviderOptions: SelectOption<string>[];
  sttProviderOptions: SelectOption<string>[];
  ttsProviderOptions: SelectOption<string>[];
  promptOptions: SelectOption<string | null>[];
  pluginOptions: SelectOption<string>[];
  kbOptions: SelectOption<string>[];
  hasSttProviders: boolean;
  hasTtsProviders: boolean;
  hasKbs: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'save-service-config': [];
  'save-provider-config': [];
  'save-plugin-config': [];
  'save-kb-config': [];
  close: [];
}>();

const { tm } = useModuleI18n('features/session-management');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => {
    emit('update:modelValue', value);
  },
});

const senderLlmMode = computed({
  get: () => {
    if (props.senderOverlay.llm_enabled === null) {
      return FOLLOW_SESSION_VALUE;
    }
    return props.senderOverlay.llm_enabled ? 'true' : 'false';
  },
  set: (value: string) => {
    props.senderOverlay.llm_enabled =
      value === FOLLOW_SESSION_VALUE ? null : value === 'true';
  },
});

const senderLlmModeOptions = computed<SelectOption<string>[]>(() => [
  {
    label: tm('ruleEditor.serviceConfig.llmFollowSession'),
    value: FOLLOW_SESSION_VALUE,
  },
  { label: tm('status.enabled'), value: 'true' },
  { label: tm('status.disabled'), value: 'false' },
]);
</script>
