<template>
  <v-dialog
    v-model="visible"
    max-width="400"
    :aria-label="tm('deleteConfirm.title')"
  >
    <v-card class="app-dialog">
      <v-card-title class="text-h6">{{
        tm('deleteConfirm.title')
      }}</v-card-title>
      <v-card-text>
        {{
          target && isSenderRule(target)
            ? tm('deleteConfirm.senderMessage')
            : tm('deleteConfirm.message')
        }}
        <br /><br />
        <code>{{
          target && isSenderRule(target) ? target.sender_id : target?.umo
        }}</code>
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="visible = false">{{
          tm('buttons.cancel')
        }}</v-btn>
        <v-btn
          color="error"
          variant="tonal"
          :loading="deleting"
          @click="emit('confirm')"
          >{{ tm('buttons.delete') }}</v-btn
        >
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import { isSenderRule } from './sessionRuleNormalizers';
import type { SessionRuleItem } from './sessionRuleHelpers';

const props = defineProps<{
  modelValue: boolean;
  target: SessionRuleItem | null;
  deleting: boolean;
}>();

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

<style scoped>
code {
  background-color: rgb(var(--v-theme-surface-variant));
  padding: 2px var(--astrbot-space-2);
  border-radius: 4px;
  font-size: 12px;
}
</style>
