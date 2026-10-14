<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

const modelValue = defineModel<boolean>({ required: true });
const title = defineModel<string>('title', { required: true });

withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  save: [];
}>();

const { tm } = useModuleI18n('features/conversation');
</script>

<template>
  <v-dialog
    v-model="modelValue"
    max-width="500"
    :aria-label="tm('dialogs.edit.title')"
  >
    <v-card>
      <v-card-title class="text-h3 pa-4 pb-0 pl-6">
        {{ tm('dialogs.edit.title') }}
      </v-card-title>
      <v-card-text class="pa-6 pb-2">
        <v-text-field
          v-model="title"
          :label="tm('dialogs.edit.titleLabel')"
          :placeholder="tm('dialogs.edit.titlePlaceholder')"
          variant="solo-filled"
          flat
          autofocus
          @keyup.enter="emit('save')"
        />
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" :disabled="loading" @click="modelValue = false">
          {{ tm('dialogs.edit.cancel') }}
        </v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :loading="loading"
          @click="emit('save')"
        >
          {{ tm('dialogs.edit.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
