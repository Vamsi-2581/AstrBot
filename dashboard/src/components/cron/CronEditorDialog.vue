<template>
  <v-dialog v-model="modelValue" max-width="620" scrollable :aria-label="title">
    <v-card class="dashboard-dialog-card cron-dialog__card">
      <v-card-title class="text-headline-small pt-5 px-5">{{
        title
      }}</v-card-title>
      <v-card-text class="px-5 pb-2 cron-dialog__content">
        <div class="dashboard-form-grid dashboard-form-grid--single">
          <v-text-field
            v-model="job.name"
            :label="tm('form.name')"
            variant="outlined"
            density="comfortable"
          />
          <v-textarea
            v-model="job.note"
            :label="tm('form.note')"
            variant="outlined"
            density="comfortable"
            rows="5"
          />

          <div class="schedule-field">
            <v-select
              v-model="job.schedule_mode"
              class="schedule-mode-select"
              :items="scheduleModeOptions"
              item-title="label"
              item-value="value"
              :label="tm('form.scheduleMode')"
              variant="outlined"
              density="comfortable"
              hide-details
            />

            <v-text-field
              v-if="job.schedule_mode === 'once'"
              v-model="job.run_at"
              :label="tm('form.runAt')"
              type="datetime-local"
              variant="outlined"
              density="comfortable"
              hide-details
            />

            <div
              v-else-if="job.schedule_mode === 'interval'"
              class="schedule-inline-fields"
            >
              <v-text-field
                v-model.number="job.interval_value"
                :label="tm('form.intervalEvery')"
                type="number"
                min="1"
                variant="outlined"
                density="comfortable"
                hide-details
              />
              <v-select
                v-model="job.interval_unit"
                :items="intervalUnitOptions"
                item-title="label"
                item-value="value"
                :label="tm('form.intervalUnit')"
                variant="outlined"
                density="comfortable"
                hide-details
              />
            </div>

            <v-text-field
              v-else-if="job.schedule_mode === 'daily'"
              v-model="job.daily_time"
              :label="tm('form.dailyTime')"
              type="time"
              variant="outlined"
              density="comfortable"
              hide-details
            />

            <div
              v-else-if="job.schedule_mode === 'weekly'"
              class="schedule-inline-fields"
            >
              <v-select
                v-model="job.weekly_day"
                :items="weekdayOptions"
                item-title="label"
                item-value="value"
                :label="tm('form.weeklyDay')"
                variant="outlined"
                density="comfortable"
                hide-details
              />
              <v-text-field
                v-model="job.weekly_time"
                :label="tm('form.weeklyTime')"
                type="time"
                variant="outlined"
                density="comfortable"
                hide-details
              />
            </div>

            <div
              v-else-if="job.schedule_mode === 'monthly'"
              class="schedule-inline-fields"
            >
              <v-text-field
                v-model.number="job.monthly_day"
                :label="tm('form.monthlyDay')"
                type="number"
                min="1"
                max="31"
                variant="outlined"
                density="comfortable"
                hide-details
              />
              <v-text-field
                v-model="job.monthly_time"
                :label="tm('form.monthlyTime')"
                type="time"
                variant="outlined"
                density="comfortable"
                hide-details
              />
            </div>

            <v-text-field
              v-else
              v-model="job.cron_expression"
              :label="tm('form.cron')"
              :placeholder="tm('form.cronPlaceholder')"
              variant="outlined"
              density="comfortable"
              hide-details
            />
          </div>

          <v-autocomplete
            v-model="job.session"
            :items="availableUmos"
            :loading="loadingUmos"
            :label="tm('form.session')"
            variant="outlined"
            density="comfortable"
            clearable
            hide-details
            :no-data-text="tm('form.noUmos')"
            @focus="emit('load-umos')"
          >
            <template #item="{ props, item }">
              <v-list-item v-bind="props">
                <template #title>
                  <UmoDisplay
                    v-bind="getUmoDisplayProps(resolveUmoSlotValue(item))"
                    compact
                    :show-info="false"
                    :show-platform="false"
                  />
                </template>
                <template #append>
                  <v-chip
                    v-if="getUmoInfo(resolveUmoSlotValue(item)).platform"
                    size="x-small"
                    :color="
                      getPlatformColor(
                        getUmoInfo(resolveUmoSlotValue(item)).platform,
                      )
                    "
                    class="cron-umo-platform"
                  >
                    {{ getUmoInfo(resolveUmoSlotValue(item)).platform }}
                  </v-chip>
                </template>
              </v-list-item>
            </template>
            <template #selection="{ item }">
              <v-chip
                v-if="item && getUmoSelectionText(resolveUmoSlotValue(item))"
                size="small"
                variant="tonal"
                color="primary"
                class="umo-selection-chip"
              >
                {{ getUmoSelectionText(resolveUmoSlotValue(item)) }}
              </v-chip>
            </template>
          </v-autocomplete>
        </div>
      </v-card-text>
      <v-card-actions class="justify-end px-5 pb-5 cron-dialog__actions">
        <v-btn variant="text" @click="modelValue = false">{{
          tm('actions.cancel')
        }}</v-btn>
        <v-btn
          variant="tonal"
          color="primary"
          :loading="creating"
          @click="emit('save')"
        >
          {{ submitText }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';
import { getPlatformColor as resolvePlatformColor } from '@/utils/platformUtils';
import UmoDisplay from '@/components/shared/UmoDisplay.vue';

type ScheduleMode =
  'once' | 'interval' | 'daily' | 'weekly' | 'monthly' | 'cron';
type IntervalUnit = 'minutes' | 'hours' | 'days';
type UmoInfo = {
  umo: string;
  platform?: string;
  message_type?: string;
  session_id?: string;
  auto_name?: string;
  user_alias?: string;
  display_name?: string;
};
type CronJobFormState = {
  schedule_mode: ScheduleMode;
  name: string;
  note: string;
  cron_expression: string;
  run_at: string;
  interval_value: number;
  interval_unit: IntervalUnit;
  daily_time: string;
  weekly_day: number;
  weekly_time: string;
  monthly_day: number;
  monthly_time: string;
  session: string;
  timezone: string;
  enabled: boolean;
};

const modelValue = defineModel<boolean>({ required: true });

const dialogProps = withDefaults(
  defineProps<{
    job: CronJobFormState;
    title: string;
    submitText: string;
    scheduleModeOptions?: { label: string; value: string }[];
    intervalUnitOptions?: { label: string; value: string }[];
    weekdayOptions?: { label: string; value: number }[];
    availableUmos?: string[];
    loadingUmos?: boolean;
    creating?: boolean;
    umoInfoMap?: Record<string, UmoInfo>;
  }>(),
  {
    scheduleModeOptions: () => [],
    intervalUnitOptions: () => [],
    weekdayOptions: () => [],
    availableUmos: () => [],
    loadingUmos: false,
    creating: false,
    umoInfoMap: () => ({}),
  },
);

const emit = defineEmits<{
  save: [];
  'load-umos': [];
}>();

const { tm } = useModuleI18n('features/cron');

function parseUmoInfo(umo: string): UmoInfo {
  const parts = umo.split(':');
  return {
    umo,
    platform: parts[0] || '',
    message_type: parts[1] || '',
    session_id: parts.slice(2).join(':') || umo,
    auto_name: '',
    user_alias: '',
    display_name: umo,
  };
}

function getUmoInfo(umo: string): UmoInfo {
  return dialogProps.umoInfoMap[umo] || parseUmoInfo(umo);
}

function getUmoDisplayProps(umo: string) {
  const info = getUmoInfo(umo);
  return {
    umo,
    platform: info.platform || '',
    messageType: info.message_type || '',
    sessionId: info.session_id || '',
    autoName: info.auto_name || '',
    userAlias: info.user_alias || '',
  };
}

function getPlatformColor(platform = '') {
  return resolvePlatformColor(platform);
}

function getUmoSelectionText(value?: string | null): string {
  if (!value) return '';
  const info = getUmoInfo(value);
  const aliasName = info.user_alias || '';
  const autoName = info.auto_name || '';
  if (aliasName && autoName && aliasName !== autoName) {
    return `${aliasName}（${autoName}）`;
  }
  return aliasName || autoName || value || info.display_name || '';
}

function resolveUmoSlotValue(item: unknown): string {
  return typeof item === 'string' ? item : '';
}
</script>

<style scoped>
.cron-umo-platform {
  margin-inline-start: 12px;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.umo-selection-chip {
  max-width: 100%;
}

.cron-dialog__card {
  display: flex;
  flex-direction: column;
  max-height: min(88dvh, 960px);
}

.cron-dialog__content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.cron-dialog__actions {
  flex-shrink: 0;
}

.schedule-field {
  display: grid;
  grid-template-columns: minmax(150px, 180px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  margin-bottom: 16px;
}

.schedule-mode-select {
  min-width: 0;
}

.schedule-inline-fields {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

@media (max-width: 900px) {
  .schedule-field,
  .schedule-inline-fields {
    grid-template-columns: 1fr;
  }
}
</style>
