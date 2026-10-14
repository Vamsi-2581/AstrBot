<template>
  <div class="stats-page" :class="{ 'is-dark': isDark }">
    <v-container fluid class="stats-shell pa-4 pa-md-6">
      <v-alert v-if="errorMessage" type="error" variant="tonal" class="mb-4">
        {{ errorMessage }}
      </v-alert>

      <div v-if="loading && !baseStats" class="loading-wrap">
        <v-progress-circular indeterminate color="on-surface-variant" />
      </div>

      <template v-else>
        <StatsOverviewSection :cards="overviewCards" />

        <StatsT2iRuntimeCard :metrics="t2iRuntimeMetrics" />

        <div class="section-toolbar">
          <div>
            <div class="section-title">{{ t('messageOverview.title') }}</div>
            <div class="section-subtitle">
              {{ t('messageOverview.subtitle') }}
            </div>
          </div>
          <div class="range-switch">
            <button
              v-for="option in rangeOptions"
              :key="`toolbar-${option.value}`"
              type="button"
              class="range-chip"
              :class="{ active: selectedRange === option.value }"
              @click="selectedRange = option.value"
            >
              {{ t(option.labelKey) }}
            </button>
          </div>
        </div>

        <StatsTrendPanel
          :message-chart-options="messageChartOptions"
          :message-chart-series="messageChartSeries"
          :message-count="baseStats?.message_count ?? 0"
          :platform-ranking="platformRanking"
          :range-label="rangeLabel"
        />

        <div class="token-section-head">
          <div>
            <div class="section-title">{{ t('modelCalls.title') }}</div>
            <div class="section-subtitle">{{ t('modelCalls.subtitle') }}</div>
          </div>
        </div>

        <StatsModelCallsPanel
          :provider-chart-options="providerChartOptions"
          :provider-trend-series="providerTrendSeries"
          :range-total-tokens="providerStats?.range_total_tokens ?? 0"
          :range-total-calls="providerStats?.range_total_calls ?? 0"
          :avg-ttft-label="rangeAvgTtftLabel"
          :avg-duration-label="rangeAvgDurationLabel"
          :avg-tpm-label="rangeAvgTpmLabel"
          :success-rate-label="rangeSuccessRateLabel"
          :range-label="rangeLabel"
          :ranking="rangeProviderRanking"
        />

        <StatsSessionRankingPanel
          :ranking="rangeUmoRanking"
          :range-label="rangeLabel"
        />
      </template>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import type { ApexOptions } from 'apexcharts';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useTheme } from 'vuetify';
import { statsApi, type T2iRuntimeStatsData } from '@/api/v1';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import { getPlatformIcon } from '@/utils/platformUtils';
import StatsModelCallsPanel from './components/StatsModelCallsPanel.vue';
import StatsOverviewSection from './components/StatsOverviewSection.vue';
import StatsSessionRankingPanel from './components/StatsSessionRankingPanel.vue';
import StatsT2iRuntimeCard from './components/StatsT2iRuntimeCard.vue';
import StatsTrendPanel from './components/StatsTrendPanel.vue';

type TokenRange = 1 | 3 | 7;
type ChartSeries = Array<{
  name: string;
  data: unknown[];
}>;

interface RunningStats {
  hours: number;
  minutes: number;
  seconds: number;
}

interface BaseStatsResponse {
  message_count: number;
  platform_count: number;
  platform: Array<{
    name: string;
    count: number;
    timestamp: number;
  }>;
  message_time_series: Array<[number, number]>;
  memory: {
    process: number;
    system: number;
  };
  cpu_percent: number;
  running: RunningStats;
  thread_count: number;
  start_time: number;
}

interface ProviderTrendItem {
  name: string;
  data: Array<[number, number]>;
  total_tokens: number;
}

interface ProviderRankingItem {
  provider_id: string;
  tokens: number;
}

interface UmoRankingItem {
  umo: string;
  display_name?: string;
  platform_type?: string;
  tokens: number;
  icon?: string;
}

interface ProviderTokenStatsResponse {
  days: TokenRange;
  trend: {
    series: ProviderTrendItem[];
    total_series: Array<[number, number]>;
  };
  range_total_tokens: number;
  range_total_calls: number;
  range_avg_ttft_ms: number;
  range_avg_duration_ms: number;
  range_avg_tpm: number;
  range_success_rate: number;
  range_by_provider: ProviderRankingItem[];
  range_by_umo: UmoRankingItem[];
  today_total_tokens: number;
  today_total_calls: number;
  today_by_provider: ProviderRankingItem[];
}

const { locale } = useI18n();
const { tm: t } = useModuleI18n('features/stats');
const theme = useTheme();
const loading = ref(true);
const errorMessage = ref('');
const baseStats = ref<BaseStatsResponse | null>(null);
const providerStats = ref<ProviderTokenStatsResponse | null>(null);
const t2iRuntimeStats = ref<T2iRuntimeStatsData | null>(null);
const selectedRange = ref<TokenRange>(1);
const isDark = computed(() => theme.global.current.value.dark);
const themePalette = computed(() => {
  const colors = theme.global.current.value.colors as Record<string, string>;
  return {
    primary: colors.primary,
    secondary: colors.secondary,
    info: colors.info,
    success: colors.success,
    warning: colors.warning,
    accent: colors.secondary,
    border: colors.outline ?? colors['outline-variant'] ?? colors.primary,
    mutedText:
      colors['on-surface-variant'] ?? colors['on-surface'] ?? colors.primary,
    lightPrimary:
      colors['surface-variant'] ?? colors.surface ?? colors.background,
    lightSecondary:
      colors['surface-variant'] ?? colors.surface ?? colors.background,
  };
});

let refreshTimer: number | null = null;
let isUnmounted = false;

function formatNumber(value: number): string {
  return new Intl.NumberFormat(locale.value).format(value);
}

function formatCompactNumber(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  return formatNumber(value);
}

function formatMemory(memoryMb: number): string {
  if (memoryMb >= 1024) {
    return `${(memoryMb / 1024).toFixed(1)} ${t('units.gb')}`;
  }
  return `${formatNumber(memoryMb)} ${t('units.mb')}`;
}

function formatBytes(value: number): string {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const exponent = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1,
  );
  const scaled = value / 1024 ** exponent;
  return `${scaled >= 10 || exponent === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[exponent]}`;
}

function formatDurationMs(value: number): string {
  if (!value || value <= 0) return '—';
  if (value < 1000) return `${Math.round(value)} ${t('units.ms')}`;
  return `${(value / 1000).toFixed(2)} ${t('units.secondsShort')}`;
}

function formatTpm(value: number): string {
  if (!value || value <= 0) return '—';
  return `${value.toFixed(0)} ${t('units.tpm')}`;
}

function hexToRgba(color: string | undefined, alpha: number): string {
  if (!color) return `rgba(0, 0, 0, ${alpha})`;
  if (!color.startsWith('#')) return color;

  let hex = color.slice(1);
  if (hex.length === 3) {
    hex = hex
      .split('')
      .map((char) => char + char)
      .join('');
  }

  if (hex.length !== 6) return color;

  const red = Number.parseInt(hex.slice(0, 2), 16);
  const green = Number.parseInt(hex.slice(2, 4), 16);
  const blue = Number.parseInt(hex.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function formatDateTime(timestampSec: number): string {
  if (!timestampSec) return '—';
  return new Date(timestampSec * 1000).toLocaleString(locale.value, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatRunningTime(running?: RunningStats | null): string {
  if (!running) return '—';
  const parts = [
    running.hours > 0 ? `${running.hours}${t('units.hoursShort')}` : '',
    running.minutes > 0 || running.hours > 0
      ? `${running.minutes}${t('units.minutesShort')}`
      : '',
    `${running.seconds}${t('units.secondsShort')}`,
  ].filter(Boolean);
  return parts.join(' ');
}

function aggregateOverflowSeries(
  series: ProviderTrendItem[],
): ProviderTrendItem[] {
  if (series.length <= 5) return series;
  const leading = series.slice(0, 4);
  const overflow = series.slice(4);
  const mergedPoints = overflow[0].data.map(([timestamp], index) => {
    const total = overflow.reduce(
      (sum, item) => sum + (item.data[index]?.[1] ?? 0),
      0,
    );
    return [timestamp, total] as [number, number];
  });
  return [
    ...leading,
    {
      name: t('chart.others'),
      data: mergedPoints,
      total_tokens: overflow.reduce((sum, item) => sum + item.total_tokens, 0),
    },
  ];
}

async function fetchBaseStats(): Promise<void> {
  const response = await statsApi.get(selectedRange.value * 24 * 60 * 60);
  baseStats.value = response.data.data;
}

async function fetchProviderStats(): Promise<void> {
  const response = await statsApi.providerTokens(selectedRange.value);
  providerStats.value = response.data.data;
}

async function fetchT2iRuntimeStats(): Promise<void> {
  const response = await statsApi.t2iRuntime();
  t2iRuntimeStats.value = response.data.data;
}

async function refreshStats(): Promise<void> {
  try {
    errorMessage.value = '';
    await Promise.all([
      fetchBaseStats(),
      fetchProviderStats(),
      fetchT2iRuntimeStats(),
    ]);
  } catch {
    console.error('Failed to load stats page data');
    errorMessage.value = t('errors.loadFailed');
  } finally {
    loading.value = false;
  }
}

const rangeOptions: ReadonlyArray<{ labelKey: string; value: TokenRange }> = [
  { labelKey: 'ranges.oneDay', value: 1 },
  { labelKey: 'ranges.threeDays', value: 3 },
  { labelKey: 'ranges.oneWeek', value: 7 },
];

const rangeLabel = computed(() => {
  if (selectedRange.value === 3) return t('rangeLabels.threeDays');
  if (selectedRange.value === 7) return t('rangeLabels.oneWeek');
  return t('rangeLabels.oneDay');
});

const overviewCards = computed(() => [
  {
    label: t('overviewCards.platformCount.label'),
    value: formatNumber(baseStats.value?.platform_count ?? 0),
    note: t('overviewCards.platformCount.note'),
    icon: 'mdi-robot-outline',
  },
  {
    label: t('overviewCards.messageCount.label'),
    value: formatNumber(baseStats.value?.message_count ?? 0),
    note: t('overviewCards.messageCount.note'),
    icon: 'mdi-message-outline',
  },
  {
    label: t('overviewCards.todayModelCalls.label'),
    value: formatCompactNumber(providerStats.value?.today_total_tokens ?? 0),
    note: t('overviewCards.todayModelCalls.note'),
    icon: 'mdi-creation-outline',
  },
  {
    label: t('overviewCards.cpu.label'),
    value: `${baseStats.value?.cpu_percent ?? 0}%`,
    note: t('overviewCards.cpu.note'),
    icon: 'mdi-chip',
  },
  {
    label: t('overviewCards.memory.label'),
    value: formatMemory(baseStats.value?.memory?.process ?? 0),
    note: t('overviewCards.memory.note', {
      systemMemory: formatMemory(baseStats.value?.memory?.system ?? 0),
    }),
    icon: 'mdi-memory',
  },
  {
    label: t('overviewCards.uptime.label'),
    value: formatRunningTime(baseStats.value?.running),
    note: t('overviewCards.uptime.note', { startTime: startTimeLabel.value }),
    icon: 'mdi-timer-outline',
  },
]);

const t2iRuntimeMetrics = computed(() => {
  const stats = t2iRuntimeStats.value;
  return [
    {
      label: t('t2i.browser.label'),
      value: stats?.browser_connected
        ? t('t2i.browser.connected')
        : t('t2i.browser.disconnected'),
      note: t('t2i.browser.note', {
        starts: formatNumber(stats?.browser_starts ?? 0),
        restarts: formatNumber(stats?.browser_restarts ?? 0),
      }),
    },
    {
      label: t('t2i.renders.label'),
      value: formatNumber(stats?.successful_renders ?? 0),
      note: t('t2i.renders.note', {
        failed: formatNumber(stats?.failed_renders ?? 0),
        cancelled: formatNumber(stats?.cancelled_renders ?? 0),
      }),
    },
    {
      label: t('t2i.pages.label'),
      value: `${formatNumber(stats?.active_pages ?? 0)} / ${formatNumber(stats?.peak_active_pages ?? 0)}`,
      note: t('t2i.pages.note'),
    },
    {
      label: t('t2i.lastDuration.label'),
      value: formatDurationMs(stats?.last_render_duration_ms ?? 0),
      note: t('t2i.lastDuration.note', {
        average: formatDurationMs(stats?.average_render_duration_ms ?? 0),
      }),
    },
    {
      label: t('t2i.maxDuration.label'),
      value: formatDurationMs(stats?.max_render_duration_ms ?? 0),
      note: t('t2i.maxDuration.note'),
    },
    {
      label: t('t2i.contexts.label'),
      value: formatNumber(stats?.context_count ?? 0),
      note: t('t2i.contexts.note', {
        output: formatBytes(stats?.output_bytes ?? 0),
      }),
    },
  ];
});

const messageChartSeries = computed<ChartSeries>(() => [
  {
    name: t('chart.messages'),
    data: (baseStats.value?.message_time_series ?? []).map(
      ([timestamp, value]) => [timestamp * 1000, value],
    ),
  },
]);

const providerTrendSeries = computed<ChartSeries>(() =>
  aggregateOverflowSeries(providerStats.value?.trend.series ?? []).map(
    (item) => ({
      name: item.name,
      data: item.data,
    }),
  ),
);

const rangeProviderRanking = computed(
  () => providerStats.value?.range_by_provider ?? [],
);

const rangeUmoRanking = computed(() =>
  (providerStats.value?.range_by_umo ?? []).slice(0, 10).map((item) => ({
    ...item,
    icon: getPlatformIcon(item.platform_type || item.umo.split(':', 1)[0]),
  })),
);

const rangeAvgTtftLabel = computed(() =>
  formatDurationMs(providerStats.value?.range_avg_ttft_ms ?? 0),
);

const rangeAvgDurationLabel = computed(() =>
  formatDurationMs(providerStats.value?.range_avg_duration_ms ?? 0),
);

const rangeAvgTpmLabel = computed(() =>
  formatTpm(providerStats.value?.range_avg_tpm ?? 0),
);

const rangeSuccessRateLabel = computed(() => {
  if (!(providerStats.value?.range_total_calls ?? 0)) {
    return '—';
  }
  const rate = providerStats.value?.range_success_rate ?? 0;
  return `${(rate * 100).toFixed(1)}%`;
});

const platformRanking = computed(() =>
  [...(baseStats.value?.platform ?? [])]
    .sort((left, right) => right.count - left.count)
    .slice(0, 6)
    .map((platform) => ({
      ...platform,
      icon: getPlatformIcon(platform.name),
    })),
);

const startTimeLabel = computed(() =>
  formatDateTime(baseStats.value?.start_time ?? 0),
);

const providerChartColors = computed(() =>
  isDark.value
    ? [
        '#6F8FAF',
        '#7E9A73',
        '#A78468',
        '#8A78A8',
        '#6B9995',
        '#B07A87',
        '#8C8F62',
        '#7C8798',
      ]
    : [
        '#5F7E9B',
        '#708865',
        '#9A7557',
        '#786696',
        '#5D8985',
        '#9C6674',
        '#80844F',
        '#69788D',
      ],
);

const messageChartOptions = computed<ApexOptions>(() => ({
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    zoom: { enabled: false },
    fontFamily: 'AstrBot UI, AstrBot Noto Sans SC, system-ui, sans-serif',
  },
  theme: {
    mode: isDark.value ? 'dark' : 'light',
  },
  colors: [themePalette.value.primary],
  stroke: {
    curve: 'smooth',
    width: 2.4,
  },
  fill: {
    type: 'solid',
    opacity: 0.12,
  },
  grid: {
    borderColor: hexToRgba(
      themePalette.value.border,
      isDark.value ? 0.4 : 0.26,
    ),
    strokeDashArray: 0,
  },
  dataLabels: { enabled: false },
  xaxis: {
    type: 'datetime',
    labels: {
      datetimeUTC: false,
      style: { colors: themePalette.value.mutedText },
    },
    axisBorder: {
      color: hexToRgba(themePalette.value.border, isDark.value ? 0.4 : 0.26),
    },
    axisTicks: {
      color: hexToRgba(themePalette.value.border, isDark.value ? 0.4 : 0.26),
    },
  },
  yaxis: {
    labels: {
      formatter: (value) => formatCompactNumber(Number(value)),
      style: { colors: themePalette.value.mutedText },
    },
  },
  tooltip: {
    theme: isDark.value ? 'dark' : 'light',
    x: {
      format: 'MM/dd HH:mm',
    },
  },
  legend: { show: false },
}));

const providerChartOptions = computed<ApexOptions>(() => ({
  chart: {
    background: 'transparent',
    toolbar: { show: false },
    zoom: { enabled: false },
    stacked: true,
    fontFamily: 'AstrBot UI, AstrBot Noto Sans SC, system-ui, sans-serif',
  },
  theme: {
    mode: isDark.value ? 'dark' : 'light',
  },
  plotOptions: {
    bar: {
      horizontal: false,
      borderRadius: 4,
      columnWidth: '58%',
    },
  },
  colors: providerChartColors.value,
  dataLabels: { enabled: false },
  grid: {
    borderColor: hexToRgba(
      themePalette.value.border,
      isDark.value ? 0.4 : 0.26,
    ),
  },
  xaxis: {
    type: 'datetime',
    labels: {
      datetimeUTC: false,
      style: { colors: themePalette.value.mutedText },
    },
    axisBorder: {
      color: hexToRgba(themePalette.value.border, isDark.value ? 0.4 : 0.26),
    },
    axisTicks: {
      color: hexToRgba(themePalette.value.border, isDark.value ? 0.4 : 0.26),
    },
  },
  yaxis: {
    labels: {
      formatter: (value) => formatCompactNumber(Number(value)),
      style: { colors: themePalette.value.mutedText },
    },
  },
  tooltip: {
    theme: isDark.value ? 'dark' : 'light',
    x: {
      format: 'MM/dd HH:mm',
    },
  },
  legend: {
    position: 'top',
    horizontalAlign: 'left',
    labels: {
      colors: themePalette.value.mutedText,
    },
  },
}));

watch(selectedRange, async () => {
  try {
    await Promise.all([fetchBaseStats(), fetchProviderStats()]);
  } catch {
    console.error('Failed to refresh stats range');
    errorMessage.value = t('errors.rangeFailed');
  }
});

onMounted(async () => {
  await refreshStats();
  // The initial request may settle after this component has unmounted.
  if (isUnmounted) return;
  refreshTimer = window.setInterval(() => {
    void refreshStats();
  }, 60_000);
});

onBeforeUnmount(() => {
  isUnmounted = true;
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer);
  }
});
</script>

<style scoped>
.stats-page {
  --stats-bg: rgb(var(--v-theme-background));
  --stats-surface: rgb(var(--v-theme-surface));
  --stats-text: rgb(var(--v-theme-on-surface));
  --stats-muted: rgba(var(--v-theme-on-surface), 0.68);
  --stats-subtle: rgba(var(--v-theme-on-surface), 0.56);
  --stats-border: rgba(var(--v-theme-on-surface), 0.1);
  --stats-border-strong: rgba(var(--v-theme-on-surface), 0.14);
  --stats-soft: rgba(var(--v-theme-primary), 0.08);
  --stats-soft-strong: rgba(var(--v-theme-primary), 0.14);
  min-height: 100%;
  background: var(--stats-bg);
}

.stats-page.is-dark {
  --stats-border: rgba(var(--v-theme-on-surface), 0.14);
  --stats-border-strong: rgba(var(--v-theme-on-surface), 0.18);
  --stats-soft: rgba(var(--v-theme-primary), 0.12);
  --stats-soft-strong: rgba(var(--v-theme-primary), 0.2);
}

.stats-shell {
  max-width: 1560px;
  margin: 0 auto;
  color: var(--stats-text);
  font-family: var(--astrbot-font-ui);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 24px;
}

.stats-title {
  margin: 0;
  font-size: 1.5rem;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: 0;
}

.stats-subtitle {
  margin: 4px 0 0;
  color: var(--stats-muted);
  font-size: 0.875rem;
}

.stats-page.is-dark .stats-subtitle,
.stats-page.is-dark .section-subtitle {
  color: var(--stats-muted);
}

.header-meta {
  display: flex;
  gap: 12px;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid var(--stats-border);
  border-radius: 999px;
  background: var(--stats-surface);
  color: var(--stats-muted);
  font-size: 13px;
}

.stats-page.is-dark .meta-pill {
  border-color: var(--stats-border-strong);
  background: var(--stats-surface);
  color: var(--stats-muted);
}

.loading-wrap {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

.section-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.section-toolbar .section-subtitle {
  max-width: 680px;
}

.section-title {
  font-size: 19px;
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.section-subtitle {
  margin-top: 6px;
  color: var(--stats-muted);
  font-size: 13px;
}

.token-section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 16px;
}

.range-switch {
  display: inline-flex;
  gap: 8px;
  padding: 6px;
  border: 1px solid var(--stats-border);
  border-radius: 999px;
  background: var(--stats-surface);
}

.stats-page.is-dark .range-switch {
  border-color: var(--stats-border-strong);
  background: var(--stats-surface);
}

.range-chip {
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--stats-muted);
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease;
}

.range-chip.active {
  background: var(--stats-soft);
  color: rgb(var(--v-theme-primary));
}

.stats-page.is-dark .range-chip {
  color: var(--stats-muted);
}

.stats-page.is-dark .range-chip.active {
  background: var(--stats-soft-strong);
  color: rgb(var(--v-theme-primary));
}

@media (max-width: 900px) {
  .stats-header,
  .token-section-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .section-toolbar {
    justify-content: flex-start;
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .stats-shell {
    padding-left: 12px !important;
    padding-right: 12px !important;
  }
}
</style>
