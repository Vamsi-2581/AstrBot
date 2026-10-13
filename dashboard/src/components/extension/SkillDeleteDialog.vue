<script setup lang="ts">
import { useI18n, useModuleI18n } from '@/i18n/composables';

const { t } = useI18n();
const { tm } = useModuleI18n('features/extension');

defineProps<{
  show: boolean;
  deleting: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void;
  (e: 'confirm'): void;
}>();
</script>

<template>
  <v-dialog
    :model-value="show"
    max-width="400px"
    :aria-label="tm('skills.deleteTitle')"
    @update:model-value="emit('update:show', $event)"
  >
    <v-card>
      <v-card-title>{{ tm('skills.deleteTitle') }}</v-card-title>
      <v-card-text>{{ tm('skills.deleteMessage') }}</v-card-text>
      <v-card-actions class="d-flex justify-end">
        <v-btn variant="text" @click="emit('update:show', false)">{{
          tm('skills.cancel')
        }}</v-btn>
        <v-btn color="error" :loading="deleting" @click="emit('confirm')">
          {{ t('core.common.itemCard.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
