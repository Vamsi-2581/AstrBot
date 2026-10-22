<template>
  <v-dialog v-model="isOpen" max-width="480" persistent :aria-label="title">
    <v-card>
      <v-card-title
        class="dialog-title d-flex align-center justify-space-between"
      >
        <span>{{ title }}</span>
        <v-btn
          icon="mdi-close"
          variant="text"
          :aria-label="t('core.common.close')"
          @click="handleClose"
        ></v-btn>
      </v-card-title>
      <v-card-text>
        <div class="message-text">{{ message }}</div>
        <div class="action-hints">
          <span class="hint-item">{{ confirmHint }}</span>
          <span class="hint-item">{{ cancelHint }}</span>
          <span class="hint-item">{{ closeHint }}</span>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="handleCancel">{{
          t('core.common.dialog.cancelButton')
        }}</v-btn>
        <v-btn color="error" class="confirm-button" @click="handleConfirm">{{
          t('core.common.dialog.confirmButton')
        }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from '@/i18n/composables';

const { t } = useI18n();

interface UnsavedChangesDialogOptions {
  title?: string;
  message?: string;
  confirmHint?: string;
  cancelHint?: string;
  closeHint?: string;
}

type UnsavedChangesDialogResult = boolean | 'close';

const isOpen = ref(false);
const title = ref('');
const message = ref('');
const confirmHint = ref('');
const cancelHint = ref('');
const closeHint = ref('');
let resolvePromise: ((value: UnsavedChangesDialogResult) => void) | null = null;

const settle = (result: UnsavedChangesDialogResult) => {
  const resolve = resolvePromise;
  resolvePromise = null;
  isOpen.value = false;
  resolve?.(result);
};

const open = (
  options: UnsavedChangesDialogOptions,
): Promise<UnsavedChangesDialogResult> => {
  settle('close');
  title.value = options.title || t('core.common.dialog.confirmTitle');
  message.value = options.message || t('core.common.dialog.confirmMessage');
  confirmHint.value = options.confirmHint || '';
  cancelHint.value = options.cancelHint || '';
  closeHint.value = options.closeHint || '';
  isOpen.value = true;

  return new Promise<UnsavedChangesDialogResult>((resolve) => {
    resolvePromise = resolve;
  });
};

const handleConfirm = () => {
  settle(true);
};

const handleCancel = () => {
  settle(false);
};

const handleClose = () => {
  settle('close');
};

defineExpose({ open });
</script>

<style scoped>
.message-text {
  margin-bottom: 8px;
  line-height: 1.5;
  font-size: 16px;
  font-weight: 600;
}

.action-hints {
  display: flex;
  gap: 15px;
}

.hint-item {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 12px;
  opacity: 0.7;
}

.dialog-title {
  font-size: 20px;
  font-weight: 500;
}

.confirm-button {
  color: rgb(239, 68, 68);
}
</style>
