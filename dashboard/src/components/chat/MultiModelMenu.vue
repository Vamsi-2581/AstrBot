<template>
  <v-menu
    :close-on-content-click="false"
    location="bottom end"
    offset="8"
    @update:model-value="handleToggle"
  >
    <template #activator="{ props: menuProps }">
      <v-btn
        v-bind="menuProps"
        class="multi-model-btn"
        variant="text"
        size="small"
        prepend-icon="mdi-compare-horizontal"
      >
        {{ label }}
      </v-btn>
    </template>

    <v-card class="multi-model-card" elevation="4" rounded="md">
      <div class="multi-model-card__title">{{ tm('multiModel.title') }}</div>
      <div class="multi-model-card__hint">
        {{ tm('multiModel.hint', { count: maxModels }) }}
      </div>
      <v-progress-linear v-if="loading" indeterminate color="primary" />
      <v-list v-else density="compact" class="multi-model-list">
        <v-list-item
          v-for="provider in providers"
          :key="provider.id"
          :disabled="!isSelected(provider.id) && selected.length >= maxModels"
          @click="toggle(provider)"
        >
          <template #prepend>
            <v-checkbox-btn :model-value="isSelected(provider.id)" />
          </template>
          <v-list-item-title>{{ provider.id }}</v-list-item-title>
          <v-list-item-subtitle>{{ provider.model }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item v-if="!providers.length && !loading">
          <v-list-item-title>{{ tm('multiModel.empty') }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>
  </v-menu>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { providerApi } from '@/api/v1';
import { useModuleI18n } from '@/i18n/composables';

export interface MultiModelSelection {
  provider: string;
  model: string;
}

interface ProviderConfig {
  id: string;
  model?: string;
  enable?: boolean;
}

const props = defineProps<{
  modelValue: MultiModelSelection[];
  maxModels: number;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: MultiModelSelection[]];
}>();

const { tm } = useModuleI18n('features/chat');

const providers = ref<ProviderConfig[]>([]);
const loading = ref(false);
const loaded = ref(false);

const selected = computed(() => props.modelValue);
const label = computed(() =>
  selected.value.length
    ? tm('multiModel.selected', { count: selected.value.length })
    : tm('multiModel.button'),
);

function isSelected(providerId: string): boolean {
  return selected.value.some((item) => item.provider === providerId);
}

function toggle(provider: ProviderConfig) {
  const current = [...selected.value];
  const index = current.findIndex((item) => item.provider === provider.id);
  if (index >= 0) {
    current.splice(index, 1);
  } else {
    if (current.length >= props.maxModels) return;
    current.push({ provider: provider.id, model: provider.model || '' });
  }
  emit('update:modelValue', current);
}

async function loadProviders() {
  if (loading.value || loaded.value) return;
  loading.value = true;
  try {
    const response = await providerApi.listByProviderType('chat_completion');
    if (response.data.status === 'ok') {
      providers.value = (
        (response.data.data || []) as unknown as ProviderConfig[]
      ).filter((provider) => provider.enable !== false);
      loaded.value = true;
    }
  } catch (error) {
    console.error('Failed to load providers for multi-model chat:', error);
  } finally {
    loading.value = false;
  }
}

function handleToggle(isOpen: boolean) {
  if (isOpen) {
    void loadProviders();
  }
}
</script>

<style scoped>
.multi-model-card {
  min-width: 260px;
  max-width: min(340px, 86vw);
  padding: 8px 4px;
}

.multi-model-card__title {
  font-weight: 600;
  padding: 4px 12px;
}

.multi-model-card__hint {
  font-size: 12px;
  opacity: 0.7;
  padding: 0 12px 8px;
}

.multi-model-list {
  max-height: 320px;
  overflow-y: auto;
}
</style>
