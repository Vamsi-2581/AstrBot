<template>
  <v-dialog
    v-model="visible"
    max-width="420"
    :aria-label="tm('conversation.editDisplayName')"
  >
    <v-card>
      <v-card-title class="text-title-small">
        {{ tm('conversation.editDisplayName') }}
      </v-card-title>
      <v-card-text>
        <v-text-field
          v-model="draft"
          :label="tm('conversation.displayName')"
          variant="outlined"
          density="comfortable"
          hide-details
          autofocus
          @keydown.enter="emit('save')"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="visible = false">
          {{ t('core.common.cancel') }}
        </v-btn>
        <v-btn color="primary" :loading="saving" @click="emit('save')">
          {{ t('core.common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n, useModuleI18n } from '@/i18n/composables';

interface Props {
  modelValue: boolean;
  title: string;
  saving: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'update:title': [value: string];
  save: [];
}>();

const { t } = useI18n();
const { tm } = useModuleI18n('features/chat');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => {
    emit('update:modelValue', value);
  },
});

const draft = computed({
  get: () => props.title,
  set: (value: string) => {
    emit('update:title', value);
  },
});
</script>
