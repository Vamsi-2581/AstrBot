import { ref, type Ref } from 'vue';

interface ManualModelDialogOptions {
  selectedProviderSource: Ref<{ id?: string } | null>;
  manualModelId: Ref<string>;
  modelAlreadyConfigured: (modelId: string) => boolean;
  openModelAddDialog: (modelId: string) => void;
  tm: (key: string, params?: Record<string, string | number>) => string;
  showMessage: (message: string, color?: string) => void;
}

export function useManualModelDialog(options: ManualModelDialogOptions) {
  const showManualModelDialog = ref(false);

  function openManualModelDialog(): void {
    if (!options.selectedProviderSource.value) {
      options.showMessage(options.tm('providerSources.selectHint'), 'error');
      return;
    }
    options.manualModelId.value = '';
    showManualModelDialog.value = true;
  }

  function confirmManualModel(): void {
    const modelId = options.manualModelId.value.trim();
    if (!options.selectedProviderSource.value) {
      options.showMessage(options.tm('providerSources.selectHint'), 'error');
      return;
    }
    if (!modelId) {
      options.showMessage(options.tm('models.manualModelRequired'), 'error');
      return;
    }
    if (options.modelAlreadyConfigured(modelId)) {
      options.showMessage(options.tm('models.manualModelExists'), 'error');
      return;
    }
    showManualModelDialog.value = false;
    options.openModelAddDialog(modelId);
  }

  return {
    showManualModelDialog,
    openManualModelDialog,
    confirmManualModel,
  };
}
