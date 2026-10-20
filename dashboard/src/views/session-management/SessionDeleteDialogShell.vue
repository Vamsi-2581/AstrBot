<template>
  <v-dialog v-model="visible" :max-width="maxWidth" :aria-label="title">
    <v-card :class="{ 'app-dialog': appDialog }">
      <v-card-title class="text-title-small">{{ title }}</v-card-title>
      <v-card-text>
        <slot />
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="visible = false">
          {{ tm('buttons.cancel') }}
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          :loading="deleting"
          @click="emit('confirm')"
        >
          {{ tm('buttons.delete') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    title: string;
    maxWidth?: number;
    appDialog?: boolean;
    deleting: boolean;
  }>(),
  {
    maxWidth: 400,
    appDialog: false,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  confirm: [];
}>();

const { tm } = useModuleI18n('features/session-management');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => {
    emit('update:modelValue', value);
  },
});
</script>
