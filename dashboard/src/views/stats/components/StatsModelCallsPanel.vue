<template>
  <div class="token-grid">
    <section class="stat-card chart-card chart-card-wide provider-trend-card">
      <div class="card-head">
        <div>
          <div class="section-title">{{ t('modelTrend.title') }}</div>
          <div class="section-subtitle">
            {{ t('modelTrend.subtitle') }}
          </div>
        </div>
      </div>
      <VueApexCharts
        type="bar"
        height="420"
        :options="providerChartOptions"
        :series="providerTrendSeries"
      />
    </section>

    <section class="token-side-column">
      <section class="stat-card token-total-card">
        <div class="card-label">
          {{ t('modelTotal.title', { range: rangeLabel }) }}
        </div>
        <div class="token-total-value">
          {{ formatNumber(rangeTotalTokens) }}
          <span class="token-total-unit">{{ t('units.tokens') }}</span>
        </div>
        <div class="card-note">
          {{
            t('modelTotal.callCount', {
              count: formatNumber(rangeTotalCalls),
            })
          }}
        </div>
        <div class="token-meta-list">
          <div class="token-meta-item">
            <span>{{ t('modelTotal.avgTtft') }}</span>
            <strong>{{ avgTtftLabel }}</strong>
          </div>
          <div class="token-meta-item">
            <span>{{ t('modelTotal.avgDuration') }}</span>
            <strong>{{ avgDurationLabel }}</strong>
          </div>
          <div class="token-meta-item">
            <span>{{ t('modelTotal.avgTpm') }}</span>
            <strong>{{ avgTpmLabel }}</strong>
          </div>
          <div class="token-meta-item">
            <span>{{ t('modelTotal.successRate') }}</span>
            <strong>{{ successRateLabel }}</strong>
          </div>
        </div>
      </section>

      <section class="stat-card provider-list-card">
        <div class="card-head compact">
          <div>
            <div class="section-title">
              {{ t('modelRanking.title', { range: rangeLabel }) }}
            </div>
            <div class="section-subtitle">
              {{ t('modelRanking.subtitle') }}
            </div>
          </div>
        </div>
        <div
          v-if="ranking.length"
          class="provider-list provider-list--scrollable"
        >
          <div
            v-for="provider in ranking"
            :key="provider.provider_id"
            class="provider-row"
          >
            <span class="provider-name">{{ provider.provider_id }}</span>
            <strong>{{ formatNumber(provider.tokens) }}</strong>
          </div>
        </div>
        <div v-else class="empty-state">
          {{ t('empty.modelCalls', { range: rangeLabel }) }}
        </div>
      </section>
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

interface ProviderRankingItem {
  provider_id: string;
  tokens: number;
}

defineProps<{
  providerChartOptions: ApexOptions;
  providerTrendSeries: ChartSeries;
  rangeTotalTokens: number;
  rangeTotalCalls: number;
  avgTtftLabel: string;
  avgDurationLabel: string;
  avgTpmLabel: string;
  successRateLabel: string;
  rangeLabel: string;
  ranking: ProviderRankingItem[];
}>();

const { locale } = useI18n();
const { tm: t } = useModuleI18n('features/stats');

function formatNumber(value: number): string {
  return new Intl.NumberFormat(locale.value).format(value);
}
</script>

<style lang="scss" scoped>
@use './panel-styles' as panel;

.token-grid {
  display: grid;
  grid-template-columns: 1.6fr 0.9fr;
  gap: 20px;
  margin-bottom: 20px;
  align-items: stretch;
}

.token-grid > * {
  min-width: 0;
  width: 100%;
}

.token-side-column {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 20px;
  min-width: 0;
  width: 100%;
}

.token-side-column > * {
  min-width: 0;
}

@include panel.stat-card;

.chart-card,
.provider-list-card,
.token-total-card {
  padding: 22px;
}

@include panel.card-head;
@include panel.card-head-compact;
@include panel.section-title;
@include panel.section-subtitle;
@include panel.card-label;
@include panel.card-note;

.token-total-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 170px;
  width: 100%;
}

.provider-trend-card {
  min-height: 520px;
}

.provider-list-card {
  width: 100%;
}

.token-total-value {
  margin-top: var(--astrbot-space-2);
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  font-size: 32px;
  line-height: 32px;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.token-total-unit {
  font-size: 18px;
  line-height: 24px;
}

.token-meta-list {
  margin-top: 18px;
  border-top: 1px solid var(--stats-border);
  padding-top: 14px;
  display: grid;
  gap: 10px;
}

.token-meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  color: var(--stats-muted);
  font-size: 14px;
}

@include panel.provider-list;

.provider-list--scrollable {
  max-height: 296px;
  overflow-y: auto;
  padding-right: 6px;
}

.empty-state {
  color: var(--stats-muted);
  font-size: 14px;
}

.stats-page.is-dark .empty-state {
  color: var(--stats-muted);
}

.token-total-card .card-label,
.token-total-card .card-note,
.token-side-column .section-subtitle {
  overflow-wrap: anywhere;
}

@media (max-width: 1080px) {
  .token-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .card-head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .chart-card,
  .provider-list-card,
  .token-total-card {
    padding: 18px;
    border-radius: 14px;
  }
}
</style>
