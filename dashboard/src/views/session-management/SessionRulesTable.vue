<template>
  <v-data-table-server
    v-model:items-per-page="tableItemsPerPage"
    v-model:page="tablePage"
    v-model="tableSelectedItems"
    :headers="headers"
    :items="items"
    :loading="loading"
    :items-length="itemsLength"
    class="elevation-0 session-rules-table"
    show-select
    :item-value="itemValue"
    return-object
    @update:options="emit('update:options', $event)"
  >
    <!-- UMO 信息 -->
    <template #item.umo_info="{ item }">
      <code v-if="isSenderRule(item)" class="text-body-2">{{
        item.sender_id
      }}</code>
      <UmoDisplay
        v-else
        :umo="item.umo"
        :platform="item.platform"
        :message-type="item.message_type"
        :session-id="item.session_id"
        :auto-name="item.auto_name"
        :user-alias="item.user_alias"
        :custom-name="item.rules?.session_service_config?.custom_name"
        editable
        :edit-tooltip="tm('buttons.editCustomName')"
        @edit="emit('edit-custom-name', item)"
      />
    </template>

    <!-- 规则概览 -->
    <template #item.rules_overview="{ item }">
      <div v-if="isSenderRule(item)" class="d-flex flex-wrap ga-1">
        <v-chip
          v-if="item.rules.session_service_config?.blocked === true"
          size="x-small"
          color="error"
          variant="outlined"
        >
          {{ tm('customRules.blocked') }}
        </v-chip>
        <v-chip
          v-if="
            typeof item.rules.session_service_config?.llm_enabled === 'boolean'
          "
          size="x-small"
          color="primary"
          variant="outlined"
        >
          {{ tm('customRules.llmEnabled') }}
        </v-chip>
      </div>
      <div v-else class="d-flex flex-wrap ga-1">
        <v-chip
          v-if="item.rules.session_service_config"
          size="x-small"
          color="primary"
          variant="outlined"
        >
          {{ tm('customRules.serviceConfig') }}
        </v-chip>
        <v-chip
          v-if="item.rules.session_plugin_config"
          size="x-small"
          color="secondary"
          variant="outlined"
        >
          {{ tm('customRules.pluginConfig') }}
        </v-chip>
        <v-chip
          v-if="item.rules.kb_config"
          size="x-small"
          color="info"
          variant="outlined"
        >
          {{ tm('customRules.kbConfig') }}
        </v-chip>
        <v-chip
          v-if="hasProviderConfig(item.rules)"
          size="x-small"
          color="warning"
          variant="outlined"
        >
          {{ tm('customRules.providerConfig') }}
        </v-chip>
      </div>
    </template>

    <!-- 操作按钮 -->
    <template #item.actions="{ item }">
      <v-btn
        size="small"
        variant="tonal"
        color="primary"
        class="mr-1"
        :aria-label="tm('buttons.editRule')"
        @click="emit('edit-rule', item)"
      >
        <v-icon>mdi-pencil</v-icon>
        <v-tooltip activator="parent" location="top">{{
          tm('buttons.editRule')
        }}</v-tooltip>
      </v-btn>
      <v-btn
        size="small"
        variant="tonal"
        color="error"
        :aria-label="tm('buttons.deleteAllRules')"
        @click="emit('delete-rules', item)"
      >
        <v-icon>mdi-delete</v-icon>
        <v-tooltip activator="parent" location="top">{{
          tm('buttons.deleteAllRules')
        }}</v-tooltip>
      </v-btn>
    </template>

    <!-- 空状态 -->
    <template #no-data>
      <div class="text-center py-8">
        <v-icon size="64" color="on-surface-variant"
          >mdi-file-document-edit-outline</v-icon
        >
        <div class="text-h6 mt-4">
          {{ tm('customRules.noRules') }}
        </div>
        <div class="text-body-2 text-medium-emphasis">
          {{
            isSenderTarget
              ? tm('customRules.noSenderRulesDesc')
              : tm('customRules.noRulesDesc')
          }}
        </div>
        <v-btn
          color="primary"
          variant="tonal"
          class="mt-4"
          @click="emit('add-rule')"
        >
          <v-icon start>mdi-plus</v-icon>
          {{ tm('buttons.addRule') }}
        </v-btn>
      </div>
    </template>
  </v-data-table-server>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import UmoDisplay from '@/components/shared/UmoDisplay.vue';
import { useModuleI18n } from '@/i18n/composables';
import { hasProviderConfig, isSenderRule } from './sessionRuleNormalizers';
import type {
  SessionRuleItem,
  SessionTableHeader,
  TableOptionsLike,
} from './sessionRuleHelpers';

const props = defineProps<{
  headers: SessionTableHeader[];
  items: SessionRuleItem[];
  loading: boolean;
  itemsLength: number;
  itemsPerPage: number;
  page: number;
  selectedItems: SessionRuleItem[];
  itemValue: string;
  isSenderTarget: boolean;
}>();

const emit = defineEmits<{
  'update:itemsPerPage': [value: number];
  'update:page': [value: number];
  'update:selectedItems': [value: SessionRuleItem[]];
  'update:options': [options: TableOptionsLike];
  'edit-rule': [item: SessionRuleItem];
  'delete-rules': [item: SessionRuleItem];
  'edit-custom-name': [item: SessionRuleItem];
  'add-rule': [];
}>();

const { tm } = useModuleI18n('features/session-management');

const tableItemsPerPage = computed({
  get: () => props.itemsPerPage,
  set: (value: number) => {
    emit('update:itemsPerPage', value);
  },
});

const tablePage = computed({
  get: () => props.page,
  set: (value: number) => {
    emit('update:page', value);
  },
});

const tableSelectedItems = computed({
  get: () => props.selectedItems,
  set: (value: SessionRuleItem[]) => {
    emit('update:selectedItems', value);
  },
});
</script>

<style scoped>
.session-rules-table {
  font-size: 12px;
}

code {
  background-color: rgb(var(--v-theme-surface-variant));
  padding: 2px var(--astrbot-space-2);
  border-radius: 4px;
  font-size: 12px;
}
</style>
