<template>
  <div class="panel-grid">
    <section class="stat-card chart-card chart-card-wide">
      <div class="card-head">
        <div>
          <div class="section-title">{{ t('messageTrend.title') }}</div>
          <div class="section-subtitle">
            {{ t('messageTrend.subtitle', { range: rangeLabel }) }}
          </div>
        </div>
        <div class="card-head-actions">
          <div class="section-metric">
            <span class="metric-label">{{
              t('messageTrend.totalMessages')
            }}</span>
            <span class="metric-value">{{ formatNumber(messageCount) }}</span>
          </div>
        </div>
      </div>
      <VueApexCharts
        type="area"
        height="320"
        :options="messageChartOptions"
        :series="messageChartSeries"
      />
    </section>

    <section class="stat-card provider-list-card">
      <div class="card-head compact">
        <div>
          <div class="section-title">
            {{ t('platformRanking.title') }}
          </div>
          <div class="section-subtitle">
            {{ t('platformRanking.subtitle', { range: rangeLabel }) }}
          </div>
        </div>
      </div>
      <div v-if="platformRanking.length" class="provider-list">
        <div
          v-for="platform in platformRanking"
          :key="platform.name"
          class="provider-row"
        >
          <div class="provider-identity">
            <img
              v-if="platform.icon"
              :src="platform.icon"
              alt=""
              class="platform-icon"
            />
            <v-icon v-else size="18" aria-hidden="true"
              >mdi-message-outline</v-icon
            >
            <span class="provider-name">{{ platform.name }}</span>
          </div>
          <strong>{{ formatNumber(platform.count) }}</strong>
        </div>
      </div>
      <div v-else class="empty-state">{{ t('empty.platformStats') }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { ApexOptions } from 'apexcharts';
import VueApexCharts from 'vue3-apexcharts';
import { useI18n, useModuleI18n } from '@/i18n/composables';

interface ChartSeriesEntry {
  name: string;
  data: unknown[];
}

type ChartSeries = ChartSeriesEntry[];

interface PlatformRankingItem {
  name: string;
  count: number;
  timestamp: number;
  icon?: string;
}

defineProps<{
  messageChartOptions: ApexOptions;
  messageChartSeries: ChartSeries;
  messageCount: number;
  platformRanking: PlatformRankingItem[];
  rangeLabel: string;
}>();

const { locale } = useI18n();
const { tm: t } = useModuleI18n('features/stats');

function formatNumber(value: number): string {
  return new Intl.NumberFormat(locale.value).format(value);
}
</script>

<style lang="scss" scoped>
@use './panel-styles' as panel;

.panel-grid {
  display: grid;
  grid-template-columns: 1.6fr 0.9fr;
  gap: 20px;
  margin-bottom: 20px;
  align-items: stretch;
}

.panel-grid > * {
  min-width: 0;
  width: 100%;
}

@include panel.stat-card;

.chart-card,
.provider-list-card {
  padding: 22px;
}

@include panel.card-head;
@include panel.card-head-compact;

.card-head-actions {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}

@include panel.section-title;
@include panel.section-subtitle;

.section-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.metric-label {
  color: var(--stats-subtle);
  font-size: 12px;
}

.stats-page.is-dark .metric-label {
  color: var(--stats-muted);
}

.metric-value {
  font-size: 22px;
  font-weight: 650;
}

@include panel.provider-list;

.provider-identity {
  align-items: center;
  display: flex;
  gap: 9px;
  min-width: 0;
}

.platform-icon {
  flex: 0 0 auto;
  height: 20px;
  object-fit: contain;
  width: 20px;
}

.empty-state {
  color: var(--stats-muted);
  font-size: 14px;
}

.stats-page.is-dark .empty-state {
  color: var(--stats-muted);
}

@media (max-width: 1080px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .card-head,
  .card-head-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .chart-card,
  .provider-list-card {
    padding: 18px;
    border-radius: 14px;
  }
}
</style>
