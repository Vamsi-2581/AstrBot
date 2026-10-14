<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import type { SkillMode } from '../skillsHelpers';

const props = defineProps<{
  neoEnabled: boolean;
  mode: SkillMode;
  runtime: string;
  sandboxReady: boolean;
  neoUnavailableMessage: string;
}>();

const emit = defineEmits<{
  (e: 'update:mode', value: SkillMode): void;
}>();

const { tm } = useModuleI18n('features/extension');

const modeModel = computed<SkillMode>({
  get: () => props.mode,
  set: (value) => {
    emit('update:mode', value);
  },
});
</script>

<template>
  <v-row
    v-if="neoEnabled"
    class="d-flex justify-end align-center px-4 py-3 pb-4"
  >
    <v-btn-toggle v-model="modeModel" mandatory divided density="comfortable">
      <v-btn value="local">{{ tm('skills.modeLocal') }}</v-btn>
      <v-btn value="neo">{{ tm('skills.modeNeo') }}</v-btn>
    </v-btn-toggle>
  </v-row>

  <div v-if="mode === 'local'" class="px-2 pb-2 d-flex flex-column ga-2">
    <v-alert
      v-if="runtime === 'sandbox' && !sandboxReady"
      type="info"
      variant="tonal"
      density="comfortable"
      border="start"
    >
      {{ tm('skills.sandboxDiscoveryPending') }}
    </v-alert>
  </div>

  <div v-if="mode === 'neo' && !neoEnabled" class="px-3 pb-3">
    <v-alert
      type="warning"
      variant="tonal"
      density="comfortable"
      border="start"
    >
      {{ neoUnavailableMessage }}
    </v-alert>
  </div>
</template>
