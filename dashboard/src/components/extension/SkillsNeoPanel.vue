<script setup lang="ts">
import { computed } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import {
  candidatePromoteLoadingKey,
  type NeoCandidate,
  type NeoRelease,
  type ReleaseStage,
} from './skillsHelpers';

const { tm } = useModuleI18n('features/extension');

const props = defineProps<{
  loading: boolean;
  candidates: NeoCandidate[];
  releases: NeoRelease[];
  skillKey: string;
  status: string;
  stage: string;
  promoteLoading: Record<string, boolean>;
}>();

const emit = defineEmits<{
  (e: 'update:skillKey', value: string): void;
  (e: 'update:status', value: string): void;
  (e: 'update:stage', value: string): void;
  (e: 'evaluate', candidate: NeoCandidate, passed: boolean): void;
  (e: 'promote', candidate: NeoCandidate, stage: ReleaseStage): void;
  (e: 'viewPayload', payloadRef?: string): void;
  (e: 'deleteCandidate', candidate: NeoCandidate): void;
  (e: 'lifecycle', release: NeoRelease): void;
  (e: 'syncRelease', release: NeoRelease): void;
  (e: 'deleteRelease', release: NeoRelease): void;
}>();

const candidateStatusItems = computed(() => [
  { title: tm('skills.neoAll'), value: '' },
  { title: 'draft', value: 'draft' },
  { title: 'evaluating', value: 'evaluating' },
  { title: 'promoted', value: 'promoted' },
  { title: 'promoted_canary', value: 'promoted_canary' },
  { title: 'promoted_stable', value: 'promoted_stable' },
  { title: 'rejected', value: 'rejected' },
  { title: 'rolled_back', value: 'rolled_back' },
]);

const releaseStageItems = computed(() => [
  { title: tm('skills.neoAll'), value: '' },
  { title: 'canary', value: 'canary' },
  { title: 'stable', value: 'stable' },
]);

const activeReleaseCount = computed(
  () => props.releases.filter((item) => item.is_active).length,
);

const candidateHeaders = computed(() => [
  { title: 'ID', key: 'id', width: '180px' },
  { title: 'skill_key', key: 'skill_key' },
  { title: 'status', key: 'status', width: '130px' },
  { title: 'score', key: 'latest_score', width: '90px' },
  {
    title: tm('skills.actions'),
    key: 'actions',
    sortable: false,
    width: '420px',
  },
]);

const releaseHeaders = computed(() => [
  { title: 'ID', key: 'id', width: '180px' },
  { title: 'skill_key', key: 'skill_key' },
  { title: 'stage', key: 'stage', width: '100px' },
  { title: 'version', key: 'version', width: '90px' },
  { title: 'active', key: 'is_active', width: '110px' },
  {
    title: tm('skills.actions'),
    key: 'actions',
    sortable: false,
    width: '220px',
  },
]);

function isCandidatePromoteLoading(candidateId: string, stage: ReleaseStage) {
  return Boolean(
    props.promoteLoading[candidatePromoteLoadingKey(candidateId, stage)],
  );
}

function isCandidatePromoting(candidateId: string) {
  return (
    isCandidatePromoteLoading(candidateId, 'canary') ||
    isCandidatePromoteLoading(candidateId, 'stable')
  );
}
</script>

<template>
  <div>
    <v-card class="mx-3 mb-4 pa-4 neo-filter-card" variant="outlined">
      <div
        class="d-flex flex-wrap justify-space-between align-center ga-2 mb-3"
      >
        <div>
          <div class="text-subtitle-1 font-weight-bold">Neo Skills</div>
          <div class="text-caption text-medium-emphasis">
            {{ tm('skills.neoFilterHint') }}
          </div>
        </div>
      </div>

      <v-row class="ga-md-0 ga-2">
        <v-col cols="12" md="4">
          <v-text-field
            :model-value="skillKey"
            :label="tm('skills.neoSkillKey')"
            prepend-inner-icon="mdi-key-outline"
            density="comfortable"
            hide-details
            variant="outlined"
            @update:model-value="emit('update:skillKey', $event)"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            :model-value="status"
            :label="tm('skills.neoStatus')"
            :items="candidateStatusItems"
            item-title="title"
            item-value="value"
            prepend-inner-icon="mdi-progress-check"
            density="comfortable"
            hide-details
            variant="outlined"
            @update:model-value="emit('update:status', $event)"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-select
            :model-value="stage"
            :label="tm('skills.neoStage')"
            :items="releaseStageItems"
            item-title="title"
            item-value="value"
            prepend-inner-icon="mdi-layers-outline"
            density="comfortable"
            hide-details
            variant="outlined"
            @update:model-value="emit('update:stage', $event)"
          />
        </v-col>
      </v-row>
    </v-card>

    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
    ></v-progress-linear>

    <div class="mx-3 mb-3 d-flex flex-wrap ga-2">
      <v-chip size="small" color="primary" variant="tonal"
        >Candidates: {{ candidates.length }}</v-chip
      >
      <v-chip size="small" color="secondary" variant="tonal"
        >Releases: {{ releases.length }}</v-chip
      >
      <v-chip size="small" color="success" variant="tonal"
        >Active: {{ activeReleaseCount }}</v-chip
      >
    </div>

    <v-card class="mx-3 mb-4 neo-table-card" variant="outlined">
      <v-card-title class="text-subtitle-1 font-weight-bold">{{
        tm('skills.neoCandidates')
      }}</v-card-title>
      <v-data-table
        :headers="candidateHeaders"
        :items="candidates"
        density="compact"
        :items-per-page="10"
        class="neo-data-table"
      >
        <template #item.latest_score="{ item }">
          {{ item.latest_score ?? '-' }}
        </template>
        <template #item.actions="{ item }">
          <div class="d-flex ga-1 flex-wrap">
            <v-btn
              size="x-small"
              color="success"
              variant="tonal"
              @click="emit('evaluate', item, true)"
            >
              {{ tm('skills.neoPass') }}
            </v-btn>
            <v-btn
              size="x-small"
              color="warning"
              variant="tonal"
              @click="emit('evaluate', item, false)"
            >
              {{ tm('skills.neoReject') }}
            </v-btn>
            <v-btn
              size="x-small"
              color="primary"
              variant="tonal"
              :loading="isCandidatePromoteLoading(item.id, 'canary')"
              :disabled="isCandidatePromoting(item.id)"
              @click="emit('promote', item, 'canary')"
            >
              Canary
            </v-btn>
            <v-btn
              size="x-small"
              color="primary"
              variant="tonal"
              :loading="isCandidatePromoteLoading(item.id, 'stable')"
              :disabled="isCandidatePromoting(item.id)"
              @click="emit('promote', item, 'stable')"
            >
              Stable
            </v-btn>
            <v-btn
              size="x-small"
              variant="tonal"
              :disabled="!item.payload_ref"
              @click="emit('viewPayload', item.payload_ref)"
            >
              Payload
            </v-btn>
            <v-btn
              size="x-small"
              color="error"
              variant="tonal"
              @click="emit('deleteCandidate', item)"
            >
              {{ tm('skills.neoDelete') }}
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <v-card class="mx-3 mb-4 neo-table-card" variant="outlined">
      <v-card-title class="text-subtitle-1 font-weight-bold">{{
        tm('skills.neoReleases')
      }}</v-card-title>
      <v-data-table
        :headers="releaseHeaders"
        :items="releases"
        density="compact"
        :items-per-page="10"
        class="neo-data-table"
      >
        <template #item.is_active="{ item }">
          <v-chip
            size="small"
            :color="item.is_active ? 'success' : 'default'"
            variant="tonal"
          >
            {{ item.is_active ? 'active' : 'inactive' }}
          </v-chip>
        </template>
        <template #item.actions="{ item }">
          <div class="d-flex ga-1 flex-wrap">
            <v-btn
              size="x-small"
              color="warning"
              variant="tonal"
              @click="emit('lifecycle', item)"
            >
              {{
                item.is_active
                  ? tm('skills.neoDeactivate')
                  : tm('skills.neoRollback')
              }}
            </v-btn>
            <v-btn
              size="x-small"
              color="primary"
              variant="tonal"
              @click="emit('syncRelease', item)"
            >
              {{ tm('skills.neoSync') }}
            </v-btn>
            <v-btn
              size="x-small"
              color="error"
              variant="tonal"
              @click="emit('deleteRelease', item)"
            >
              {{ tm('skills.neoDelete') }}
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<style scoped>
.neo-filter-card {
  border-radius: 14px;
  border-color: rgba(var(--v-theme-primary), 0.25);
  background: linear-gradient(
    180deg,
    rgba(var(--v-theme-primary), 0.03),
    rgba(var(--v-theme-surface), 1)
  );
}

.neo-table-card {
  border-radius: 14px;
}

.neo-data-table :deep(.v-data-table-header__content) {
  font-weight: 700;
}

.neo-data-table :deep(tbody tr:hover) {
  background: rgba(var(--v-theme-primary), 0.04);
}
</style>
