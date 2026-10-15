import { computed, ref } from 'vue';
import { pluginApi } from '@/api/v1';
import type { ToastColor } from '@/stores/toast';
import type { PluginSourceItem } from '@/types/extensions';
import { resolveErrorMessage } from '@/utils/errorUtils';

const SELECTED_SOURCE_STORAGE_KEY = 'selectedPluginSource';

interface UsePluginSourcesOptions {
  tm: (key: string, params?: Record<string, string | number>) => string;
  toast: (message: unknown, color: ToastColor, duration?: number) => void;
  refreshPluginMarket: () => void | Promise<void>;
}

export function usePluginSources(options: UsePluginSourcesOptions) {
  const showSourceDialog = ref(false);
  const showSourceManagerDialog = ref(false);
  const sourceName = ref('');
  const sourceUrl = ref('');
  const customSources = ref<PluginSourceItem[]>([]);
  const selectedSource = ref<string | null>(null);
  const showRemoveSourceDialog = ref(false);
  const sourceToRemove = ref<PluginSourceItem | null>(null);
  const editingSource = ref(false);
  const originalSourceUrl = ref('');

  const loadCustomSources = async () => {
    try {
      const res = await pluginApi.sources();
      if (res.data.status === 'ok') {
        customSources.value = Array.isArray(res.data.data) ? res.data.data : [];
      } else {
        options.toast(res.data.message, 'error');
      }
    } catch (error) {
      console.warn('Failed to load custom sources:', error);
      customSources.value = [];
    }

    const currentSource = localStorage.getItem(SELECTED_SOURCE_STORAGE_KEY);
    if (currentSource) {
      selectedSource.value = currentSource;
    }
  };

  const saveCustomSources = async () => {
    try {
      const res = await pluginApi.replaceSources(customSources.value);
      if (res.data.status !== 'ok') {
        options.toast(res.data.message, 'error');
      }
    } catch (error) {
      options.toast(
        resolveErrorMessage(error, options.tm('messages.operationFailed')),
        'error',
      );
    }
  };

  const addCustomSource = () => {
    showSourceManagerDialog.value = false;
    editingSource.value = false;
    originalSourceUrl.value = '';
    sourceName.value = '';
    sourceUrl.value = '';
    showSourceDialog.value = true;
  };

  const openSourceManagerDialog = async () => {
    await loadCustomSources();
    showSourceManagerDialog.value = true;
  };

  const selectPluginSource = (sourceUrlValue: string | null) => {
    selectedSource.value = sourceUrlValue;
    if (sourceUrlValue) {
      localStorage.setItem(SELECTED_SOURCE_STORAGE_KEY, sourceUrlValue);
    } else {
      localStorage.removeItem(SELECTED_SOURCE_STORAGE_KEY);
    }
    void options.refreshPluginMarket();
  };

  const sourceSelectItems = computed(() => [
    { title: options.tm('market.defaultSource'), value: '__default__' },
    ...customSources.value.map((source) => ({
      title: source.name,
      value: source.url,
    })),
  ]);

  const editCustomSource = (source: PluginSourceItem | null) => {
    if (!source) return;
    showSourceManagerDialog.value = false;
    editingSource.value = true;
    originalSourceUrl.value = source.url;
    sourceName.value = source.name ?? '';
    sourceUrl.value = source.url;
    showSourceDialog.value = true;
  };

  const removeCustomSource = (source: PluginSourceItem | null) => {
    if (!source) return;
    showSourceManagerDialog.value = false;
    sourceToRemove.value = source;
    showRemoveSourceDialog.value = true;
  };

  const confirmRemoveSource = () => {
    const source = sourceToRemove.value;
    if (source) {
      customSources.value = customSources.value.filter(
        (s) => s.url !== source.url,
      );
      void saveCustomSources();

      if (selectedSource.value === source.url) {
        selectedSource.value = null;
        localStorage.removeItem(SELECTED_SOURCE_STORAGE_KEY);
        void options.refreshPluginMarket();
      }

      options.toast(options.tm('market.sourceRemoved'), 'success');
      showRemoveSourceDialog.value = false;
      sourceToRemove.value = null;
    }
  };

  const saveCustomSource = () => {
    const normalizedUrl = sourceUrl.value.trim();

    if (!sourceName.value.trim() || !normalizedUrl) {
      options.toast(options.tm('messages.fillSourceNameAndUrl'), 'error');
      return;
    }

    try {
      new URL(normalizedUrl);
    } catch (_error) {
      options.toast(options.tm('messages.invalidUrl'), 'error');
      return;
    }

    if (editingSource.value) {
      const index = customSources.value.findIndex(
        (s) => s.url === originalSourceUrl.value,
      );
      if (index !== -1) {
        customSources.value[index] = {
          name: sourceName.value.trim(),
          url: normalizedUrl,
        };

        if (selectedSource.value === originalSourceUrl.value) {
          selectedSource.value = normalizedUrl;
          localStorage.setItem(
            SELECTED_SOURCE_STORAGE_KEY,
            selectedSource.value,
          );
          void options.refreshPluginMarket();
        }
      }
    } else {
      if (customSources.value.some((source) => source.url === normalizedUrl)) {
        options.toast(options.tm('market.sourceExists'), 'error');
        return;
      }

      customSources.value.push({
        name: sourceName.value.trim(),
        url: normalizedUrl,
      });
    }

    void saveCustomSources();
    options.toast(
      editingSource.value
        ? options.tm('market.sourceUpdated')
        : options.tm('market.sourceAdded'),
      'success',
    );

    sourceName.value = '';
    sourceUrl.value = '';
    editingSource.value = false;
    originalSourceUrl.value = '';
    showSourceDialog.value = false;
  };

  return {
    showSourceDialog,
    showSourceManagerDialog,
    sourceName,
    sourceUrl,
    customSources,
    selectedSource,
    showRemoveSourceDialog,
    sourceToRemove,
    editingSource,
    originalSourceUrl,
    loadCustomSources,
    saveCustomSources,
    addCustomSource,
    openSourceManagerDialog,
    selectPluginSource,
    sourceSelectItems,
    editCustomSource,
    removeCustomSource,
    confirmRemoveSource,
    saveCustomSource,
  };
}
