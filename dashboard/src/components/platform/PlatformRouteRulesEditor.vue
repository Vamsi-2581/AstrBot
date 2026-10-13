<template>
  <div>
    <div class="mb-3 d-flex align-center justify-space-between">
      <div>
        <v-btn
          v-if="isEditingRoutes"
          color="primary"
          variant="tonal"
          size="small"
          @click="emit('add-route')"
        >
          <v-icon start>mdi-plus</v-icon>
          {{ tm('createDialog.addRouteRule') }}
        </v-btn>
      </div>
      <v-btn
        :color="isEditingRoutes ? 'on-surface-variant' : 'primary'"
        variant="tonal"
        size="small"
        @click="toggleEditMode"
      >
        <v-icon start>{{ isEditingRoutes ? 'mdi-eye' : 'mdi-pencil' }}</v-icon>
        {{
          isEditingRoutes
            ? tm('createDialog.viewMode')
            : tm('createDialog.editMode')
        }}
      </v-btn>
    </div>

    <v-data-table
      :headers="routeTableHeaders"
      :items="platformRoutes"
      item-value="umop"
      :no-data-text="tm('createDialog.noRouteRules')"
      hide-default-footer
      :items-per-page="-1"
      class="mt-2"
      variant="outlined"
    >
      <template #item.source="{ item }">
        <div class="route-source-cell">
          <div
            class="d-flex align-center route-source-input-row"
            :class="{
              'route-source-input-row--editing': isEditingRoutes,
            }"
          >
            <v-autocomplete
              v-if="
                isEditingRoutes &&
                updatingMode &&
                getRouteSourceMode(item) === 'known'
              "
              :model-value="item.sourceUmo"
              :items="knownRouteUmoItems"
              :loading="loadingKnownRouteUmos"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              :placeholder="tm('createDialog.routeSource.selectPlaceholder')"
              :aria-label="tm('createDialog.routeSource.selectPlaceholder')"
              :no-data-text="tm('createDialog.routeSource.noData')"
              class="route-source-autocomplete"
              @update:model-value="
                emit('apply-known-route-source', item, $event)
              "
              @focus="emit('load-known-route-umos')"
            >
              <template #item="{ props: sourceItemProps, item: sourceItem }">
                <v-list-item v-bind="sourceItemProps">
                  <template #title>
                    <UmoDisplay
                      v-bind="
                        getKnownRouteUmoDisplayProps(
                          sourceItem,
                          knownRouteUmoInfoMap,
                        )
                      "
                      compact
                      :show-info="false"
                    />
                  </template>
                </v-list-item>
              </template>
              <template #selection="{ item: sourceItem }">
                <v-chip
                  v-if="sourceItem && getKnownRouteUmoSelectionText(sourceItem)"
                  size="small"
                  variant="tonal"
                  color="primary"
                  class="umo-selection-chip"
                >
                  {{ getKnownRouteUmoSelectionText(sourceItem) }}
                </v-chip>
              </template>
            </v-autocomplete>
            <template v-else>
              <v-select
                v-if="isEditingRoutes"
                :model-value="item.messageType"
                :items="messageTypeOptions"
                item-title="label"
                item-value="value"
                :aria-label="tm('createDialog.messageTypeLabel')"
                variant="outlined"
                density="compact"
                hide-details
                class="route-message-type-field"
                @update:model-value="setRouteField(item, 'messageType', $event)"
              >
              </v-select>
              <small v-else>{{ getMessageTypeLabel(item.messageType) }}</small>
              <small class="mx-1">:</small>
              <v-text-field
                v-if="isEditingRoutes"
                :model-value="item.sessionId"
                variant="outlined"
                density="compact"
                hide-details
                :placeholder="tm('createDialog.sessionIdPlaceholder')"
                :aria-label="tm('createDialog.sessionIdPlaceholder')"
                @update:model-value="setRouteField(item, 'sessionId', $event)"
              >
              </v-text-field>
              <small v-else>{{
                item.sessionId === '*'
                  ? tm('createDialog.allSessions')
                  : item.sessionId
              }}</small>
            </template>
          </div>
          <button
            v-if="updatingMode && isEditingRoutes"
            class="route-source-mode-link"
            type="button"
            @click="emit('toggle-route-source-mode', item)"
          >
            {{ getRouteSourceModeLinkText(item) }}
          </button>
        </div>
      </template>

      <template #item.configId="{ item }">
        <div class="d-flex align-center">
          <v-select
            v-if="isEditingRoutes"
            :model-value="item.configId"
            :items="configInfoList"
            item-title="name"
            item-value="id"
            :aria-label="tm('createDialog.selectConfigLabel')"
            variant="outlined"
            density="compact"
            class="route-config-select"
            hide-details
            @update:model-value="setRouteField(item, 'configId', $event)"
          >
          </v-select>
          <div v-else>
            <small>{{ getConfigName(item.configId) }}</small>
          </div>
          <v-btn
            icon
            variant="text"
            density="compact"
            class="ml-2"
            :disabled="!item.configId"
            @click="emit('open-config-drawer', item.configId)"
          >
            <v-icon size="18">mdi-arrow-top-right-thick</v-icon>
          </v-btn>
        </div>
        <small
          v-if="configInfoList.findIndex((c) => c.id === item.configId) === -1"
          class="route-config-missing ml-2"
          >{{ tm('createDialog.configMissing') }}</small
        >
      </template>

      <template #item.actions="{ index }">
        <div v-if="isEditingRoutes" class="d-flex align-center">
          <v-btn
            icon
            size="x-small"
            variant="text"
            :disabled="index === 0"
            @click="emit('move-route-up', index)"
          >
            <v-icon>mdi-arrow-up</v-icon>
          </v-btn>
          <v-btn
            icon
            size="x-small"
            variant="text"
            :disabled="index === platformRoutes.length - 1"
            @click="emit('move-route-down', index)"
          >
            <v-icon>mdi-arrow-down</v-icon>
          </v-btn>
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="error"
            @click="emit('delete-route', index)"
          >
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </div>
        <span v-else class="text-medium-emphasis">-</span>
      </template>
    </v-data-table>
    <small class="ml-2 mt-2 d-block text-medium-emphasis">{{
      tm('createDialog.routeHint')
    }}</small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import UmoDisplay from '@/components/shared/UmoDisplay.vue';
import { useModuleI18n } from '@/i18n/composables';
import {
  getKnownRouteUmoDisplayProps,
  getKnownRouteUmoInfo,
  getRouteSourceMode,
  parseUmop,
  type ConfigInfo,
  type KnownRouteUmoInfo,
  type PlatformRoute,
} from './platformConfigHelpers';

defineOptions({
  name: 'PlatformRouteRulesEditor',
});

const props = defineProps<{
  platformRoutes: PlatformRoute[];
  isEditingRoutes: boolean;
  updatingMode: boolean;
  knownRouteUmoItems: string[];
  loadingKnownRouteUmos: boolean;
  knownRouteUmoInfoMap: Record<string, KnownRouteUmoInfo>;
  configInfoList: ConfigInfo[];
}>();

const emit = defineEmits<{
  'update:platform-routes': [value: PlatformRoute[]];
  'update:is-editing-routes': [value: boolean];
  'add-route': [];
  'move-route-up': [index: number];
  'move-route-down': [index: number];
  'delete-route': [index: number];
  'toggle-edit-mode': [];
  'toggle-route-source-mode': [route: PlatformRoute];
  'apply-known-route-source': [route: PlatformRoute, umo: string | null];
  'load-known-route-umos': [];
  'open-config-drawer': [configId: string | null | undefined];
}>();

const { tm } = useModuleI18n('features/platform');

const routeTableHeaders = computed(() => [
  {
    title: tm('createDialog.routeTableHeaders.source'),
    key: 'source',
    sortable: false,
    width: '60%',
  },
  {
    title: tm('createDialog.routeTableHeaders.config'),
    key: 'configId',
    sortable: false,
    width: '20%',
  },
  {
    title: tm('createDialog.routeTableHeaders.actions'),
    key: 'actions',
    sortable: false,
    align: 'center' as const,
    width: '20%',
  },
]);

const messageTypeOptions = computed(() => [
  { label: tm('createDialog.messageTypeOptions.all'), value: '*' },
  {
    label: tm('createDialog.messageTypeOptions.group'),
    value: 'GroupMessage',
  },
  {
    label: tm('createDialog.messageTypeOptions.friend'),
    value: 'FriendMessage',
  },
]);

function toggleEditMode() {
  emit('update:is-editing-routes', !props.isEditingRoutes);
  emit('toggle-edit-mode');
}

function setRouteField<K extends keyof PlatformRoute>(
  route: PlatformRoute,
  key: K,
  value: PlatformRoute[K],
) {
  route[key] = value;
  emit('update:platform-routes', [...props.platformRoutes]);
}

function getMessageTypeLabel(messageType: string): string {
  const typeMap: Record<string, string> = {
    '*': tm('createDialog.messageTypeLabels.all'),
    '': tm('createDialog.messageTypeLabels.all'),
    GroupMessage: tm('createDialog.messageTypeLabels.group'),
    FriendMessage: tm('createDialog.messageTypeLabels.friend'),
  };
  return typeMap[messageType] || messageType;
}

function getRouteSourceModeLinkText(route: PlatformRoute): string {
  return getRouteSourceMode(route) === 'known'
    ? tm('createDialog.routeSource.switchToManual')
    : tm('createDialog.routeSource.switchToKnown');
}

function getConfigName(configId: string): string {
  const config = props.configInfoList.find((item) => item.id === configId);
  return config ? config.name : configId;
}

function getKnownRouteUmoSelectionText(umo: string): string {
  if (!umo) {
    return '';
  }

  const info = getKnownRouteUmoInfo(umo, props.knownRouteUmoInfoMap);
  const parsed = parseUmop(umo);
  const aliasName = info.user_alias || '';
  const autoName = info.auto_name || '';
  if (aliasName && autoName && aliasName !== autoName) {
    return `${aliasName}（${autoName}）`;
  }
  return (
    aliasName ||
    autoName ||
    (parsed
      ? `${getMessageTypeLabel(parsed.messageType)}:${parsed.sessionId}`
      : umo)
  );
}
</script>

<style scoped>
.route-source-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--astrbot-space-1);
  min-width: 260px;
}

.route-source-input-row {
  min-width: 250px;
}

.route-source-input-row--editing {
  padding-top: var(--astrbot-space-4);
}

.route-source-mode-link {
  padding: 2px 0;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  text-decoration: underline;
}

.route-source-mode-link:hover {
  text-decoration: underline;
}

.umo-selection-chip {
  max-width: 100%;
}

.route-source-autocomplete {
  min-width: 260px;
}

.route-message-type-field {
  max-width: 140px;
}

.route-config-select {
  min-width: 200px;
}

.route-config-missing {
  color: rgb(var(--v-theme-error));
}
</style>
