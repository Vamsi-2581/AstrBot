import { computed, ref } from 'vue';
import { configProfileApi, type OpenConfig } from '@/api/v1';
import {
  runConfigMutationWithStepUp,
  stepUpHeaders,
  type RequestDashboardStepUp,
} from '@/utils/stepUp';

interface ConfigSaveMessages {
  success: string;
  error: string;
  twoFactorRejected: string;
}

interface UseConfigProfileSaveOptions {
  tm: (key: string, params?: Record<string, string | number>) => string;
  requestStepUp: RequestDashboardStepUp;
  getConfigData: () => OpenConfig;
  getCurrentScope: () => string;
  messages: ConfigSaveMessages;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function useConfigProfileSave(options: UseConfigProfileSaveOptions) {
  const loaded = ref(false);
  const loadFailed = ref(false);
  const savedSnapshot = ref('');
  const saving = ref(false);
  const twoFactorOpen = ref(false);
  const twoFactorError = ref('');
  const snackbar = ref(false);
  const snackMessage = ref('');
  const snackColor = ref<'success' | 'error'>('success');

  function showSnack(message: string, color: 'success' | 'error') {
    snackMessage.value = message;
    snackColor.value = color;
    snackbar.value = true;
  }

  function snapshot(value: OpenConfig) {
    return JSON.stringify(value ?? {});
  }

  function markLoaded() {
    loadFailed.value = false;
    savedSnapshot.value = snapshot(options.getConfigData());
    loaded.value = true;
  }

  function markLoadFailed() {
    loaded.value = false;
    loadFailed.value = true;
  }

  const hasUnsavedChanges = computed(
    () =>
      loaded.value && snapshot(options.getConfigData()) !== savedSnapshot.value,
  );

  async function saveProfile(
    target: string,
    twoFactorCode = '',
  ): Promise<boolean> {
    if (saving.value) return false;
    saving.value = true;
    const submittedSnapshot = snapshot(options.getConfigData());
    const submittedConfig = JSON.parse(submittedSnapshot) as OpenConfig;
    const headers: Record<string, string> = {};
    if (twoFactorCode) headers['X-2FA-Code'] = twoFactorCode;

    try {
      const response = await runConfigMutationWithStepUp(
        (stepUp) => {
          if (stepUp) Object.assign(headers, stepUpHeaders(stepUp));
          const requestConfig = {
            headers,
            validateStatus: (status: number) =>
              (status >= 200 && status < 300) || status === 401,
          };
          return configProfileApi.update(
            target,
            submittedConfig,
            requestConfig,
          );
        },
        target,
        options.requestStepUp,
      );
      if (!response) return false;

      const payload = asRecord(response.data?.data);
      if (response.status === 401 && payload?.totp_required === true) {
        twoFactorError.value = twoFactorCode
          ? options.tm(options.messages.twoFactorRejected)
          : '';
        twoFactorOpen.value = true;
        return false;
      }

      if (response.data?.status === 'ok') {
        twoFactorOpen.value = false;
        twoFactorError.value = '';
        // Only adopt the submitted snapshot while the page still edits that
        // profile: the operator may have discarded the edit and switched away
        // mid-save, and the loaded profile's snapshot must not be overwritten.
        if (target === options.getCurrentScope()) {
          savedSnapshot.value = submittedSnapshot;
        }
        showSnack(
          response.data?.message || options.tm(options.messages.success),
          'success',
        );
        return true;
      }
      showSnack(
        response.data?.message || options.tm(options.messages.error),
        'error',
      );
      return false;
    } catch {
      showSnack(options.tm(options.messages.error), 'error');
      return false;
    } finally {
      saving.value = false;
    }
  }

  function confirmTwoFactor(code: string) {
    twoFactorError.value = '';
    void saveProfile(options.getCurrentScope(), code);
  }

  return {
    loaded,
    loadFailed,
    savedSnapshot,
    saving,
    twoFactorOpen,
    twoFactorError,
    snackbar,
    snackMessage,
    snackColor,
    showSnack,
    snapshot,
    markLoaded,
    markLoadFailed,
    hasUnsavedChanges,
    saveProfile,
    confirmTwoFactor,
  };
}
