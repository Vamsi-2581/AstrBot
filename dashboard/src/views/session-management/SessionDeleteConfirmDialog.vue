<template>
  <SessionDeleteDialogShell
    v-model="visible"
    :title="tm('deleteConfirm.title')"
    app-dialog
    :deleting="deleting"
    @confirm="emit('confirm')"
  >
    {{
      target && isSenderRule(target)
        ? tm('deleteConfirm.senderMessage')
        : tm('deleteConfirm.message')
    }}
    <br /><br />
    <code>{{
      target && isSenderRule(target) ? target.sender_id : target?.umo
    }}</code>
  </SessionDeleteDialogShell>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import SessionDeleteDialogShell from './SessionDeleteDialogShell.vue';
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
