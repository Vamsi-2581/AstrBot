<template>
  <v-dialog v-model="isOpen" max-width="400" :aria-label="title">
    <v-card>
      <v-card-title class="text-headline-small pl-6 pt-4">{{
        title
      }}</v-card-title>
      <v-card-text>{{ message }}</v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="handleCancel">{{
          t('core.common.dialog.cancelButton')
        }}</v-btn>
        <v-btn color="error" @click="handleConfirm">{{
          t('core.common.dialog.confirmButton')
        }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from '@/i18n/composables';
import type { ConfirmDialogOptions } from '@/utils/confirmDialog';

const { t } = useI18n();

const isOpen = ref(false);
const title = ref('');
const message = ref('');
let resolvePromise: ((value: boolean) => void) | null = null;

const open = (options: ConfirmDialogOptions): Promise<boolean> => {
  title.value = options.title || t('core.common.dialog.confirmTitle');
  message.value = options.message || t('core.common.dialog.confirmMessage');
  isOpen.value = true;

  return new Promise<boolean>((resolve) => {
    resolvePromise = resolve; // ✅ 赋值 Promise 解析方法
  });
};

const handleConfirm = () => {
  isOpen.value = false;
  if (resolvePromise) resolvePromise(true); // ✅ 解析 Promise
};

const handleCancel = () => {
  isOpen.value = false;
  if (resolvePromise) resolvePromise(false); // ✅ 解析 Promise
};

defineExpose({ open }); // ✅ 确保 `confirmPlugin.ts` 可以访问 `open`
</script>
