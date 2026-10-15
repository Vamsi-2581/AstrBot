<template>
  <v-dialog
    :model-value="modelValue"
    max-width="520"
    :aria-label="title"
    @update:model-value="emit('update:modelValue', $event)"
    @click:outside="emit('cancel')"
  >
    <v-card>
      <v-card-title class="text-h3 pa-4 pb-0 pl-6 d-flex align-center">
        {{ title }}
        <v-spacer></v-spacer>
        <v-btn
          icon
          variant="text"
          size="small"
          :aria-label="
            tm('system_group.system.dashboard.totp.configSaveCancel')
          "
          @click="emit('cancel')"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text class="pa-4">
        <slot />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['update:modelValue', 'cancel']);
const { tm } = useModuleI18n('features/config-metadata');
</script>

<style scoped>
:deep(.totp-dialog-subtitle) {
  font-size: 0.9rem;
  color: rgba(var(--v-theme-on-surface), 0.68);
}

:deep(.totp-code-input) {
  max-width: 240px;
  margin: 0 auto;
}
</style>
