<template>
  <section class="stat-card t2i-runtime-card">
    <div class="card-head">
      <div>
        <div class="section-title">{{ t('t2i.title') }}</div>
        <div class="section-subtitle">{{ t('t2i.subtitle') }}</div>
      </div>
    </div>
    <div class="t2i-runtime-grid">
      <div
        v-for="metric in metrics"
        :key="metric.label"
        class="t2i-runtime-metric"
      >
        <span class="metric-label">{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <span class="card-note">{{ metric.note }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useModuleI18n } from '@/i18n/composables';

interface T2iMetric {
  label: string;
  value: string;
  note: string;
}

defineProps<{
  metrics: T2iMetric[];
}>();

const { tm: t } = useModuleI18n('features/stats');
</script>

<style scoped>
.stat-card {
  border: 1px solid var(--stats-border);
  border-radius: 16px;
  background: var(--stats-surface);
}

.stats-page.is-dark .stat-card {
  border-color: var(--stats-border-strong);
  background: var(--stats-surface);
}

.t2i-runtime-card {
  margin-bottom: 20px;
  padding: 20px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 18px;
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

.stats-page.is-dark .section-subtitle {
  color: var(--stats-muted);
}

.t2i-runtime-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.t2i-runtime-metric {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--stats-border);
  border-radius: 12px;
  background: var(--stats-soft);
}

.t2i-runtime-metric strong {
  overflow: hidden;
  color: var(--stats-text);
  font-size: 1.1rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-label {
  color: var(--stats-subtle);
  font-size: 12px;
}

.stats-page.is-dark .metric-label {
  color: var(--stats-muted);
}

.card-note {
  margin-top: 8px;
  color: var(--stats-subtle);
  font-size: 12px;
  line-height: 1.5;
}

.stats-page.is-dark .card-note {
  color: var(--stats-muted);
}

@media (max-width: 1400px) {
  .t2i-runtime-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .t2i-runtime-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .card-head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .t2i-runtime-grid {
    grid-template-columns: 1fr;
  }

  .t2i-runtime-card {
    padding: 18px;
    border-radius: 14px;
  }
}
</style>
