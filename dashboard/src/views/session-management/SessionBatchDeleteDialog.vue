<template>
  <v-dialog
    v-model="visible"
    max-width="500"
    :aria-label="tm('batchDeleteConfirm.title')"
  >
    <v-card>
      <v-card-title class="text-h6">{{
        tm('batchDeleteConfirm.title')
      }}</v-card-title>
      <v-card-text>
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
