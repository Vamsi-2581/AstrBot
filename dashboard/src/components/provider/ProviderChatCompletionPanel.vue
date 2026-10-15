<template>
  <div class="provider-chat-panel">
    <div
      class="provider-workbench"
      :class="{ 'provider-workbench--borderless': !props.showBorder }"
    >
      <div class="provider-workbench__sidebar">
        <ProviderSourcesPanel
          :displayed-provider-sources="displayedProviderSources"
          :selected-provider-source="selectedProviderSource ?? undefined"
          :available-source-types="availableSourceTypes"
          :tm="tmForSources"
          :resolve-source-icon="resolveSourceIcon"
          :is-monochrome-source-icon="isMonochromeSourceIcon"
          :get-source-display-name="getSourceDisplayName"
          @add-provider-source="addProviderSource"
          @select-provider-source="selectProviderSource"
          @delete-provider-source="deleteProviderSource"
        />
      </div>

      <div class="provider-workbench__divider"></div>

      <div class="provider-workbench__main">
        <ProviderChatCompletionBody
          v-model:model-search="modelSearch"
          :selected-provider-source="selectedProviderSource"
          :title="
            selectedProviderSource
              ? getSourceDisplayName(selectedProviderSource)
              : ''
          "
          :subtitle="selectedProviderSource?.api_base || ''"
          :basic-source-config="basicSourceConfig"
          :advanced-source-config="advancedSourceConfig"
          :provider-source-schema="providerSourceSchema"
          :provider-source-field-links="providerSourceFieldLinks"
          :entries="filteredMergedModelEntries"
          :available-count="availableModels.length"
          :loading-models="loadingModels"
          :saving-source="savingSource"
          :is-source-modified="isSourceModified"
          :supports-image-input="supportsImageInput"
          :supports-audio-input="supportsAudioInput"
          :supports-tool-call="supportsToolCall"
          :supports-reasoning="supportsReasoning"
          :format-context-limit="formatContextLimit"
          :saving-providers="savingProviderToggles"
          :testing-providers="testingProviders"
          :tm="tm"
          @save="saveProviderSource"
          @fetch-models="fetchAvailableModels"
          @open-manual-model="openManualModelDialog"
          @open-provider-edit="openProviderEdit"
          @toggle-provider-enable="toggleProviderEnable"
          @test-provider="testProvider"
          @delete-provider="deleteProvider"
          @add-model-provider="openModelAddDialog"
        />
      </div>
    </div>

    <ProviderManualModelDialog
      v-model="showManualModelDialog"
      v-model:manual-model-id="manualModelId"
      :manual-provider-id="manualProviderId"
      :tm="tm"
      @confirm="confirmManualModel"
    />

    <ProviderEditDialog
      v-model="showProviderEditDialog"
      :provider-edit-data="providerEditData"
      :provider-model-config-schema="providerModelConfigSchema"
      :saving-providers="savingProviders"
      :title="providerEditDialogTitle"
      :tm="tm"
      @save="saveEditedProvider"
    />

    <DashboardStepUpDialog
      v-model="stepUpDialogOpen"
      :loading="stepUpLoading"
      :error-message="stepUpErrorMessage"
      @confirm="submitStepUp"
      @cancel="cancelStepUp"
    />

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      location="top"
    >
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import ProviderChatCompletionBody from '@/components/provider/ProviderChatCompletionBody.vue';
import ProviderEditDialog from '@/components/provider/ProviderEditDialog.vue';
import ProviderManualModelDialog from '@/components/provider/ProviderManualModelDialog.vue';
import ProviderSourcesPanel from '@/components/provider/ProviderSourcesPanel.vue';
import DashboardStepUpDialog from '@/components/shared/DashboardStepUpDialog.vue';
import { useDashboardStepUp } from '@/composables/useDashboardStepUp';
import { useManualModelDialog } from '@/composables/useManualModelDialog';
import { useProviderModelConfigDialog } from '@/composables/useProviderModelConfigDialog';
import { useProviderSources } from '@/composables/useProviderSources';

type ProviderModelConfigDialogOptions = Parameters<
  typeof useProviderModelConfigDialog
>[0];

const props = defineProps({
  showBorder: {
    type: Boolean,
    default: true,
  },
});

const { tm } = useModuleI18n('features/provider');
const tmForSources = (key: string, params?: Record<string, unknown>): string =>
  tm(key, params as Record<string, string | number> | undefined);
const {
  dialogOpen: stepUpDialogOpen,
  loading: stepUpLoading,
  errorMessage: stepUpErrorMessage,
  requestStepUp,
  submitStepUp,
  cancelStepUp,
} = useDashboardStepUp();

const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
});

function showMessage(message: string, color = 'success') {
  snackbar.value = { show: true, message, color };
}

const {
  selectedProviderSource,
  availableModels,
  loadingModels,
  savingSource,
  savingProviderToggles,
  testingProviders,
  isSourceModified,
  configSchema,
  providerSourceSchema,
  manualModelId,
  modelSearch,
  availableSourceTypes,
  displayedProviderSources,
  filteredMergedModelEntries,
  basicSourceConfig,
  advancedSourceConfig,
  manualProviderId,
  resolveSourceIcon,
  isMonochromeSourceIcon,
  getSourceDisplayName,
  supportsImageInput,
  supportsAudioInput,
  supportsToolCall,
  supportsReasoning,
  formatContextLimit,
  selectProviderSource,
  addProviderSource,
  deleteProviderSource,
  saveProviderSource,
  fetchAvailableModels,
  buildModelProviderConfig,
  deleteProvider,
  testProvider,
  toggleProviderEnable,
  loadConfig,
  modelAlreadyConfigured,
} = useProviderSources({
  defaultTab: 'chat_completion',
  tm: tmForSources,
  showMessage,
  requestStepUp,
});

const providerSourceFieldLinks = computed(() =>
  selectedProviderSource.value?.provider === 'ssycloud'
    ? {
        key: {
          label: tm('providerSources.getApiKey'),
          href: 'https://www.shengsuanyun.com/?from=CH_T70U2X9L',
        },
      }
    : {},
);

const {
  showProviderEditDialog,
  providerEditData,
  savingProviders,
  providerModelConfigSchema,
  providerEditDialogTitle,
  openProviderEdit,
  openModelAddDialog,
  saveEditedProvider,
} = useProviderModelConfigDialog({
  selectedProviderSource,
  configSchema:
    configSchema as unknown as ProviderModelConfigDialogOptions['configSchema'],
  buildModelProviderConfig,
  modelAlreadyConfigured,
  loadConfig,
  tm,
  showMessage,
  requestStepUp,
});

const { showManualModelDialog, openManualModelDialog, confirmManualModel } =
  useManualModelDialog({
    selectedProviderSource,
    manualModelId,
    modelAlreadyConfigured,
    openModelAddDialog,
    tm,
    showMessage,
  });
</script>

<style scoped>
.provider-chat-panel {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.provider-workbench {
  flex: 1;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 24px;
  background: rgb(var(--v-theme-surface));
  display: grid;
  grid-template-columns: minmax(280px, 320px) 1px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
}

.provider-workbench--borderless {
  border: 0;
  border-radius: 0;
  background: transparent;
}

.provider-workbench__sidebar,
.provider-workbench__main {
  min-width: 0;
  min-height: 0;
}

.provider-workbench__sidebar,
.provider-workbench__main,
.provider-workbench__divider {
  height: 100%;
}

.provider-workbench__divider {
  background: rgba(var(--v-theme-on-surface), 0.08);
}

.provider-workbench__main {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

@media (max-width: 960px) {
  .provider-workbench {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1px minmax(0, 1fr);
  }

  .provider-workbench__sidebar,
  .provider-workbench__main,
  .provider-workbench__divider {
    height: auto;
  }

  .provider-workbench__divider {
    min-height: 1px;
  }
}

@media (max-width: 600px) {
  .provider-chat-panel {
    overflow: auto;
  }

  .provider-workbench {
    border-radius: 16px;
    overflow: visible;
  }

  .provider-workbench--borderless {
    border-radius: 0;
  }

  .provider-workbench__main {
    overflow: visible;
  }
}
</style>
