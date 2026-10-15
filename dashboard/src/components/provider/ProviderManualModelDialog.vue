<template>
  <v-dialog
    :model-value="modelValue"
    max-width="400"
    :aria-label="tm('models.manualDialogTitle')"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card class="app-dialog" :title="tm('models.manualDialogTitle')">
      <v-card-text class="py-4">
        <v-text-field
          :model-value="manualModelId"
          :label="tm('models.manualDialogModelLabel')"
          flat
          variant="solo-filled"
          autofocus
          clearable
          @update:model-value="onModelIdInput"
        ></v-text-field>
        <v-text-field
          :model-value="manualProviderId"
          flat
          variant="solo-filled"
          :label="tm('models.manualDialogPreviewLabel')"
          persistent-hint
          :hint="tm('models.manualDialogPreviewHint')"
        ></v-text-field>
      </v-card-text>
      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="emit('update:modelValue', false)">
          {{ tm('models.manualDialogCancel') }}
        </v-btn>
        <v-btn color="primary" @click="emit('confirm')">
          {{ tm('models.manualDialogAdd') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';
import { normalizeTextInput } from '@/utils/inputValue';

defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  manualModelId: {
    type: String,
    default: '',
  },
  manualProviderId: {
    type: String,
    default: '',
  },
  tm: {
    type: Function as PropType<
      (key: string, params?: Record<string, string | number>) => string
    >,
    required: true,
  },
});

const emit = defineEmits([
  'update:modelValue',
  'update:manualModelId',
  'confirm',
]);

function onModelIdInput(value: unknown): void {
  emit('update:manualModelId', normalizeTextInput(value));
}
</script>
