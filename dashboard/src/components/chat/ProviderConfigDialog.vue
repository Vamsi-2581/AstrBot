<template>
  <v-dialog
    v-model="dialog"
    max-width="1600"
    scrollable
    :aria-label="tm('actions.providerConfig')"
  >
    <v-card class="provider-config-dialog">
      <div class="provider-config-dialog__body">
        <ProviderChatCompletionPanel
          class="provider-config-dialog__page"
          :show-border="false"
        />
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import ProviderChatCompletionPanel from '@/components/provider/ProviderChatCompletionPanel.vue';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:modelValue']);
const { tm } = useModuleI18n('features/chat');
const dialog = computed({
  get: () => props.modelValue,
  set: (val) => {
    emit('update:modelValue', val);
  },
});
</script>

<style scoped>
.provider-config-dialog {
  width: 100%;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 28px;
}

.provider-config-dialog__body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.provider-config-dialog__page {
  flex: 1;
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
}

:deep(.v-overlay__content) {
  width: min(1600px, 70vw);
  height: min(920px, 70dvh);
  max-width: 70vw;
  max-height: 70dvh;
  margin: 0;
}

@media (max-width: 960px) {
  .provider-config-dialog {
    border-radius: 20px;
  }

  :deep(.v-overlay__content) {
    width: calc(100dvw - 24px);
    height: calc(100dvh - 24px);
    max-width: calc(100dvw - 24px);
    max-height: calc(100dvh - 24px);
  }
}

@media (max-width: 600px) {
  .provider-config-dialog {
    border-radius: 0;
  }

  .provider-config-dialog__body {
    overflow: auto;
  }

  :deep(.v-overlay__content) {
    width: 100dvw;
    height: 100dvh;
    max-width: 100dvw;
    max-height: 100dvh;
  }
}
</style>
