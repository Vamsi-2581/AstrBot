<template>
  <div class="overview-grid">
    <section
      v-for="card in cards"
      :key="card.label"
      class="stat-card overview-card"
    >
      <div class="card-icon">
        <v-icon size="18">{{ card.icon }}</v-icon>
      </div>
      <div class="card-label">{{ card.label }}</div>
      <div class="card-value">{{ card.value }}</div>
      <div class="card-note">{{ card.note }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
interface OverviewCard {
  label: string;
  value: string;
  note: string;
  icon: string;
}

defineProps<{
  cards: OverviewCard[];
}>();
</script>

<style lang="scss" scoped>
@use './panel-styles' as panel;

.overview-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

@include panel.stat-card;

.overview-card {
  padding: 20px 20px 18px;
}

.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: var(--stats-soft);
  color: rgb(var(--v-theme-primary));
}

.stats-page.is-dark .card-icon {
  background: var(--stats-soft-strong);
  color: rgb(var(--v-theme-primary));
}

@include panel.card-label;

.card-value {
  margin-top: 8px;
  font-size: clamp(24px, 2vw, 34px);
  line-height: 1.1;
  font-weight: 700;
  letter-spacing: -0.03em;
}

@include panel.card-note;

@media (max-width: 1400px) {
  .overview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
