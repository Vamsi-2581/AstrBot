<template>
  <DashboardTotpDialogShell
    :model-value="modelValue"
    :title="tm('system_group.system.dashboard.totp.configSaveTitle')"
    @update:model-value="onVisibilityChange"
    @cancel="onCancel"
  >
    <div class="totp-dialog-subtitle mb-3">
      {{ tm('system_group.system.dashboard.totp.configSaveSubtitle') }}
    </div>
    <div v-if="rotationHint" class="totp-dialog-rotation-hint mb-3">
      {{ rotationHint }}
    </div>
    <v-text-field
      v-model="code"
      :label="tm('system_group.system.dashboard.totp.configSaveCode')"
      variant="outlined"
      density="compact"
      class="totp-code-input"
      maxlength="6"
      :error-messages="errorMessage"
      :loading="saving"
      hide-details="auto"
      prepend-inner-icon="mdi-shield-key"
      @keyup.enter="confirm"
    ></v-text-field>
    <div class="d-flex justify-end ga-2 mt-4">
      <v-btn variant="text" :disabled="saving" @click="onCancel">
        {{ tm('system_group.system.dashboard.totp.configSaveCancel') }}
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        :loading="saving"
        :disabled="!code || code.length < 6"
        @click="confirm"
      >
        {{ tm('system_group.system.dashboard.totp.configSaveConfirm') }}
      </v-btn>
    </div>
  </DashboardTotpDialogShell>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import DashboardTotpDialogShell from './DashboardTotpDialogShell.vue';
import { useModuleI18n } from '@/i18n/composables';

defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: String,
    default: '',
  },
  saving: {
    type: Boolean,
    default: false,
  },
  rotationHint: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel']);
const { tm } = useModuleI18n('features/config-metadata');

const code = ref('');

function resetState() {
  code.value = '';
}

function onVisibilityChange(val: boolean) {
  if (!val) {
    resetState();
  }
  emit('update:modelValue', val);
}

function onCancel() {
  resetState();
  emit('cancel');
  emit('update:modelValue', false);
}

function confirm() {
  if (!code.value) return;
  emit('confirm', code.value);
}
</script>

<style scoped>
.totp-dialog-rotation-hint {
  font-size: 0.82rem;
  color: rgba(var(--v-theme-info, 33, 150, 243), 0.78);
  background: rgba(var(--v-theme-info, 33, 150, 243), 0.08);
  padding: 8px 12px;
  border-radius: 6px;
  line-height: 1.4;
}
</style>
