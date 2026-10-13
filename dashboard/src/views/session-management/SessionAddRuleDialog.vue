<template>
  <v-dialog v-model="visible" max-width="600" :aria-label="tm('addRule.title')">
    <v-card class="app-dialog">
      <v-card-title class="d-flex align-center py-3 px-4">
        <span>{{ tm('addRule.title') }}</span>
        <v-spacer></v-spacer>
        <v-btn
          icon
          variant="text"
          :aria-label="tm('buttons.cancel')"
          @click="visible = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-4">
        <v-alert type="info" variant="tonal" class="mb-4">
          {{
            isSenderTarget
              ? tm('addRule.senderDescription')
              : tm('addRule.description')
          }}
        </v-alert>

        <v-text-field
          v-if="isSenderTarget"
          v-model="selectedNewSenderId"
          :label="tm('addRule.senderId')"
          :hint="tm('addRule.senderIdHint')"
          :error-messages="
            senderIdInvalid ? tm('addRule.senderIdError') : undefined
          "
          persistent-hint
          variant="outlined"
        />
        <v-autocomplete
          v-else
          v-model="selectedNewUmo"
          :items="availableUmos"
          :loading="loadingUmos"
          :label="tm('addRule.selectUmo')"
          variant="outlined"
          clearable
          :no-data-text="tm('addRule.noUmos')"
        >
          <template #item="{ props: listItemProps, item }">
            <v-list-item v-bind="listItemProps">
              <template #title>
                <UmoDisplay
                  v-bind="resolveUmoDisplayProps(item, umoInfoMap)"
                  compact
                  :show-info="false"
                  :show-platform="false"
                />
              </template>
              <template #append>
                <v-chip
                  v-if="resolveUmoInfo(item, umoInfoMap).platform"
                  size="x-small"
                  :color="
                    getPlatformColor(resolveUmoInfo(item, umoInfoMap).platform)
                  "
                  class="umo-list-platform"
                >
                  {{ resolveUmoInfo(item, umoInfoMap).platform }}
                </v-chip>
              </template>
            </v-list-item>
          </template>
          <template #selection="{ item }">
            <v-chip
              v-if="item && getUmoSelectionText(item, umoInfoMap)"
              size="small"
              variant="tonal"
              color="primary"
              class="umo-selection-chip"
            >
              {{ getUmoSelectionText(item, umoInfoMap) }}
            </v-chip>
          </template>
        </v-autocomplete>
      </v-card-text>

      <v-card-actions class="px-4 pb-4">
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="visible = false">{{
          tm('buttons.cancel')
        }}</v-btn>
        <v-btn
          color="primary"
          variant="tonal"
          :disabled="!canCreateNewRule"
          @click="emit('create')"
        >
          {{ tm('buttons.next') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import UmoDisplay from '@/components/shared/UmoDisplay.vue';
import { useModuleI18n } from '@/i18n/composables';
import { getPlatformColor } from '@/utils/platformUtils';
import {
  getUmoSelectionText,
  isSenderSubjectId,
  resolveUmoDisplayProps,
  resolveUmoInfo,
} from './sessionRuleNormalizers';
import type { UmoDisplayInfo } from './sessionRuleHelpers';

const props = defineProps<{
  modelValue: boolean;
  isSenderTarget: boolean;
  selectedNewUmo: string | null;
  selectedNewSenderId: string;
  availableUmos: string[];
  loadingUmos: boolean;
  umoInfoMap: Record<string, UmoDisplayInfo>;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'update:selectedNewUmo': [value: string | null];
  'update:selectedNewSenderId': [value: string];
  create: [];
}>();

const { tm } = useModuleI18n('features/session-management');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => {
    emit('update:modelValue', value);
  },
});

const selectedNewUmo = computed({
  get: () => props.selectedNewUmo,
  set: (value: string | null) => {
    emit('update:selectedNewUmo', value);
  },
});

const selectedNewSenderId = computed({
  get: () => props.selectedNewSenderId,
  set: (value: string) => {
    emit('update:selectedNewSenderId', value);
  },
});

const canCreateNewRule = computed(() =>
  props.isSenderTarget
    ? isSenderSubjectId(props.selectedNewSenderId)
    : Boolean(props.selectedNewUmo),
);

const senderIdInvalid = computed(() => {
  const value = props.selectedNewSenderId.trim();
  return props.isSenderTarget && value.length > 0 && !isSenderSubjectId(value);
});
</script>

<style scoped>
.umo-list-platform {
  max-width: 92px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.umo-selection-chip {
  max-width: 100%;
}
</style>
