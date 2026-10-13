<template>
  <v-dialog
    :model-value="modelValue"
    max-width="450"
    persistent
    :aria-label="tm('dialog.idConflict.title')"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card class="app-dialog">
      <v-card-title class="text-h6 bg-warning d-flex align-center">
        <v-icon start class="me-2">mdi-alert-circle-outline</v-icon>
        {{ tm('dialog.idConflict.title') }}
      </v-card-title>
      <v-card-text class="py-4 text-body-1 text-medium-emphasis">
        {{ tm('dialog.idConflict.message', { id: conflictId }) }}
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="emit('confirm')">{{
          tm('dialog.idConflict.confirm')
        }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

defineOptions({
  name: 'PlatformIdConflictDialog',
});

defineProps<{
  modelValue: boolean;
  conflictId: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  confirm: [];
}>();

const { tm } = useModuleI18n('features/platform');
</script>
