<template>
  <v-dialog
    v-model="visible"
    max-width="400"
    :aria-label="tm('quickEditName.title')"
  >
    <v-card>
      <v-card-title class="py-3 px-4">{{
        tm('quickEditName.title')
      }}</v-card-title>
      <v-card-text class="pa-4">
        <v-text-field
          v-model="nameValue"
          :label="tm('ruleEditor.serviceConfig.customName')"
          variant="outlined"
          hide-details
          clearable
          autofocus
          @keyup.enter="emit('save')"
        />
      </v-card-text>
      <v-card-actions class="px-4 pb-4">
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="visible = false">{{
          tm('buttons.cancel')
        }}</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :loading="saving"
          @click="emit('save')"
        >
          {{ tm('buttons.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';

const props = defineProps<{
  modelValue: boolean;
  value: string;
  saving: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'update:value': [value: string];
  save: [];
}>();

const { tm } = useModuleI18n('features/session-management');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => {
    emit('update:modelValue', value);
  },
});

const nameValue = computed({
  get: () => props.value,
  set: (value: string) => {
    emit('update:value', value);
  },
});
</script>
