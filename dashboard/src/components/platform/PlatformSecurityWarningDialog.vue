<template>
  <v-dialog
    :model-value="modelValue"
    max-width="600"
    persistent
    :aria-label="tm('dialog.securityWarning.title')"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card class="app-dialog">
      <v-card-title>
        {{ tm('dialog.securityWarning.title') }}
      </v-card-title>
      <v-card-text class="py-4">
        <p>{{ tm(messageKey) }}</p>
        <span
          ><a :href="tutorialLink" target="_blank">{{
            tm('dialog.securityWarning.learnMore')
          }}</a></span
        >
      </v-card-text>
      <v-card-actions class="px-4 pb-4">
        <v-spacer></v-spacer>
        <v-btn color="error" @click="emit('confirm')">
          {{ tm('createDialog.warningContinue') }}
        </v-btn>
        <v-btn color="primary" @click="emit('dismiss')">
          {{ tm('createDialog.warningEditAgain') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

defineOptions({
  name: 'PlatformSecurityWarningDialog',
});

defineProps<{
  modelValue: boolean;
  messageKey: string;
  tutorialLink: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  confirm: [];
  dismiss: [];
}>();

const { tm } = useModuleI18n('features/platform');
</script>
