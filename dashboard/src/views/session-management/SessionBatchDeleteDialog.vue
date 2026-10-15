<template>
  <SessionDeleteDialogShell
    v-model="visible"
    :title="tm('batchDeleteConfirm.title')"
    :max-width="500"
    :deleting="deleting"
    @confirm="emit('confirm')"
  >
    {{ tm('batchDeleteConfirm.message', { count: selectedItems.length }) }}
    <div class="session-selection-list mt-3">
      <v-chip
        v-for="item in selectedItems"
        :key="item.umo"
        size="small"
        class="ma-1"
        variant="outlined"
      >
        {{ getUmoDisplayText(item, umoInfoMap) }}
      </v-chip>
    </div>
  </SessionDeleteDialogShell>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import SessionDeleteDialogShell from './SessionDeleteDialogShell.vue';
import { getUmoDisplayText } from './sessionRuleNormalizers';
import type { SessionRuleItem, UmoDisplayInfo } from './sessionRuleHelpers';

const props = defineProps<{
  modelValue: boolean;
  selectedItems: SessionRuleItem[];
  deleting: boolean;
  umoInfoMap: Record<string, UmoDisplayInfo>;
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
.session-selection-list {
  max-height: 200px;
  overflow-y: auto;
}
</style>
