<template>
  <v-dialog
    v-model="visible"
    max-width="800"
    scrollable
    :aria-label="mode === 'create' ? tm('groups.create') : tm('groups.edit')"
    @after-enter="emit('load-available')"
  >
    <v-card class="app-dialog session-group-dialog__card">
      <v-card-title class="py-3 px-4">
        {{ mode === 'create' ? tm('groups.create') : tm('groups.edit') }}
      </v-card-title>
      <v-card-text class="session-group-dialog__content">
        <v-text-field
          v-model="name"
          :label="tm('groups.name')"
          variant="outlined"
          hide-details
          class="mb-4"
        ></v-text-field>
        <v-row density="comfortable">
          <!-- 左侧：可选会话 -->
          <v-col cols="5">
            <div class="text-subtitle-2 mb-2">
              {{
                tm('groups.availableSessions', {
                  count: unselectedUmos.length,
                })
              }}
            </div>
            <v-text-field
              v-model="memberSearch"
              :placeholder="tm('groups.searchPlaceholder')"
              variant="outlined"
              density="compact"
              hide-details
              class="mb-2"
              clearable
              prepend-inner-icon="mdi-magnify"
              :aria-label="tm('groups.searchPlaceholder')"
            ></v-text-field>
            <v-list density="compact" class="transfer-list">
              <v-list-item
                v-for="umo in filteredUnselectedUmos"
                :key="umo"
                class="transfer-item"
                @click="emit('add-umo', umo)"
              >
                <template #prepend>
                  <v-icon size="small" color="on-surface-variant"
                    >mdi-plus</v-icon
                  >
                </template>
                <v-list-item-title>
                  <UmoDisplay
                    v-bind="resolveUmoDisplayProps(umo, umoInfoMap)"
                    compact
                    :show-info="false"
                    :show-platform="false"
                  />
                </v-list-item-title>
                <template #append>
                  <v-chip
                    v-if="resolveUmoInfo(umo, umoInfoMap).platform"
                    size="x-small"
                    :color="
                      getPlatformColor(resolveUmoInfo(umo, umoInfoMap).platform)
                    "
                    class="umo-list-platform"
                  >
                    {{ resolveUmoInfo(umo, umoInfoMap).platform }}
                  </v-chip>
                </template>
              </v-list-item>
              <v-list-item
                v-if="filteredUnselectedUmos.length === 0 && !loadingUmos"
              >
                <v-list-item-title
                  class="text-caption text-medium-emphasis text-center"
                  >{{ tm('groups.noMatch') }}</v-list-item-title
                >
              </v-list-item>
              <v-list-item v-if="loadingUmos">
                <v-list-item-title class="text-center"
                  ><v-progress-circular
                    indeterminate
                    size="20"
                  ></v-progress-circular
                ></v-list-item-title>
              </v-list-item>
            </v-list>
          </v-col>
          <!-- 中间：操作按钮 -->
          <v-col
            cols="2"
            class="d-flex flex-column align-center justify-center"
          >
            <v-btn
              icon
              size="small"
              variant="tonal"
              color="primary"
              class="mb-2"
              :disabled="unselectedUmos.length === 0"
              :aria-label="tm('groups.addToGroup')"
              @click="emit('add-all')"
            >
              <v-icon>mdi-chevron-double-right</v-icon>
            </v-btn>
            <v-btn
              icon
              size="small"
              variant="tonal"
              color="error"
              :disabled="selectedUmos.length === 0"
              :aria-label="tm('buttons.clear')"
              @click="emit('remove-all')"
            >
              <v-icon>mdi-chevron-double-left</v-icon>
            </v-btn>
          </v-col>
          <!-- 右侧：已选会话 -->
          <v-col cols="5">
            <div class="text-subtitle-2 mb-2">
              {{
                tm('groups.selectedSessions', {
                  count: selectedUmos.length,
                })
              }}
            </div>
            <v-text-field
              v-model="selectedSearch"
              :placeholder="tm('groups.searchPlaceholder')"
              variant="outlined"
              density="compact"
              hide-details
              class="mb-2"
              clearable
              prepend-inner-icon="mdi-magnify"
              :aria-label="tm('groups.searchPlaceholder')"
            ></v-text-field>
            <v-list density="compact" class="transfer-list">
              <v-list-item
                v-for="umo in filteredSelectedUmos"
                :key="umo"
                class="transfer-item"
                @click="emit('remove-umo', umo)"
              >
                <template #prepend>
                  <v-icon size="small" color="error">mdi-minus</v-icon>
                </template>
                <v-list-item-title>
                  <UmoDisplay
                    v-bind="resolveUmoDisplayProps(umo, umoInfoMap)"
                    compact
                    :show-info="false"
                    :show-platform="false"
                  />
                </v-list-item-title>
                <template #append>
                  <v-chip
                    v-if="resolveUmoInfo(umo, umoInfoMap).platform"
                    size="x-small"
                    :color="
                      getPlatformColor(resolveUmoInfo(umo, umoInfoMap).platform)
                    "
                    class="umo-list-platform"
                  >
                    {{ resolveUmoInfo(umo, umoInfoMap).platform }}
                  </v-chip>
                </template>
              </v-list-item>
              <v-list-item v-if="selectedUmos.length === 0">
                <v-list-item-title
                  class="text-caption text-medium-emphasis text-center"
                  >{{ tm('groups.noMembers') }}</v-list-item-title
                >
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions class="px-4 pb-4 session-group-dialog__actions">
        <v-spacer></v-spacer>
        <v-btn variant="text" @click="visible = false">{{
          tm('buttons.cancel')
        }}</v-btn>
        <v-btn color="primary" variant="tonal" @click="emit('save')">{{
          tm('buttons.save')
        }}</v-btn>
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
  resolveUmoDisplayProps,
  resolveUmoInfo,
} from './sessionRuleNormalizers';
import type { GroupDialogMode, UmoDisplayInfo } from './sessionRuleHelpers';

const props = defineProps<{
  modelValue: boolean;
  mode: GroupDialogMode;
  name: string;
  selectedUmos: string[];
  unselectedUmos: string[];
  loadingUmos: boolean;
  memberSearch: string;
  selectedSearch: string;
  umoInfoMap: Record<string, UmoDisplayInfo>;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'update:name': [value: string];
  'update:memberSearch': [value: string];
  'update:selectedSearch': [value: string];
  'add-umo': [umo: string];
  'remove-umo': [umo: string];
  'add-all': [];
  'remove-all': [];
  save: [];
  'load-available': [];
}>();

const { tm } = useModuleI18n('features/session-management');

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => {
    emit('update:modelValue', value);
  },
});

const name = computed({
  get: () => props.name,
  set: (value: string) => {
    emit('update:name', value);
  },
});

const memberSearch = computed({
  get: () => props.memberSearch,
  set: (value: string) => {
    emit('update:memberSearch', value);
  },
});

const selectedSearch = computed({
  get: () => props.selectedSearch,
  set: (value: string) => {
    emit('update:selectedSearch', value);
  },
});

const filteredUnselectedUmos = computed(() => {
  if (!memberSearch.value) {
    return props.unselectedUmos;
  }

  const search = memberSearch.value.toLowerCase();
  return props.unselectedUmos.filter((umo) =>
    umo.toLowerCase().includes(search),
  );
});

const filteredSelectedUmos = computed(() => {
  if (!selectedSearch.value) {
    return props.selectedUmos;
  }

  const search = selectedSearch.value.toLowerCase();
  return props.selectedUmos.filter((umo) => umo.toLowerCase().includes(search));
});
</script>

<style scoped>
.transfer-list {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 8px;
  overscroll-behavior: contain;
}

.session-group-dialog__card {
  display: flex;
  flex-direction: column;
  max-height: min(88dvh, 900px);
}

.session-group-dialog__content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.session-group-dialog__actions {
  flex-shrink: 0;
}

.transfer-item {
  cursor: pointer;
  min-height: 44px;
  padding-top: var(--astrbot-space-1);
  padding-bottom: var(--astrbot-space-1);
}

.transfer-item:hover {
  background-color: rgb(var(--v-theme-surface-variant));
}

.umo-list-platform {
  max-width: 92px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
