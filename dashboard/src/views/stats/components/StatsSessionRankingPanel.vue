<template>
  <section class="stat-card provider-list-card">
    <div class="card-head compact">
      <div>
        <div class="section-title">
          {{ t('sessionRanking.title', { range: rangeLabel }) }}
        </div>
        <div class="section-subtitle">
          {{ t('sessionRanking.subtitle') }}
        </div>
      </div>
    </div>
    <div v-if="ranking.length" class="provider-list">
      <div v-for="item in ranking" :key="item.umo" class="provider-row">
        <div class="provider-identity provider-identity--umo">
          <img v-if="item.icon" :src="item.icon" alt="" class="platform-icon" />
          <v-icon v-else size="18" aria-hidden="true"
            >mdi-message-outline</v-icon
          >
          <v-tooltip
            v-if="item.display_name && item.display_name !== item.umo"
            location="top"
            max-width="520"
          >
            <template #activator="{ props }">
              <span v-bind="props" class="provider-name provider-name--alias">
                {{ item.display_name }}
              </span>
            </template>
            <span class="umo-tooltip">{{ item.umo }}</span>
          </v-tooltip>
          <span v-else class="provider-name">{{ item.umo }}</span>
          <v-tooltip location="top">
            <template #activator="{ props }">
              <button
                v-bind="props"
                type="button"
                class="umo-copy-button"
                :class="{
                  'umo-copy-button--copied': copiedUmo === item.umo,
                }"
                :aria-label="
                  copiedUmo === item.umo
                    ? globalT('core.common.copied')
                    : globalT('core.common.copy')
                "
                @click="copyUmo(item.umo)"
              >
                <v-icon v-if="copiedUmo === item.umo" size="15"
                  >mdi-check</v-icon
                >
                <v-icon v-else size="15">mdi-content-copy</v-icon>
              </button>
            </template>
            <span>
              {{
                failedCopyUmo === item.umo
                  ? globalT('core.common.copyFailed')
                  : copiedUmo === item.umo
                    ? globalT('core.common.copied')
                    : globalT('core.common.copy')
              }}
            </span>
          </v-tooltip>
          <v-tooltip location="top">
            <template #activator="{ props }">
              <RouterLink
                v-bind="props"
                class="umo-conversation-link"
                :to="{ name: 'Conversation', query: { umo: item.umo } }"
                :aria-label="t('sessionRanking.openConversation')"
              >
                <v-icon size="15" aria-hidden="true"
                  >mdi-message-text-outline</v-icon
                >
              </RouterLink>
            </template>
            <span>{{ t('sessionRanking.openConversation') }}</span>
          </v-tooltip>
        </div>
        <strong>{{ formatNumber(item.tokens) }}</strong>
      </div>
    </div>
    <div v-else class="empty-state">
      {{ t('empty.sessionCalls', { range: rangeLabel }) }}
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import { copyToClipboard } from '@/utils/clipboard';

interface UmoRankingItem {
  umo: string;
  display_name?: string;
  platform_type?: string;
  tokens: number;
  icon?: string;
}

defineProps<{
  ranking: UmoRankingItem[];
  rangeLabel: string;
}>();

const { locale, t: globalT } = useI18n();
const { tm: t } = useModuleI18n('features/stats');
const copiedUmo = ref('');
const failedCopyUmo = ref('');
let copyFeedbackTimer: number | null = null;

async function copyUmo(umo: string): Promise<void> {
  const copied = await copyToClipboard(umo);
  copiedUmo.value = copied ? umo : '';
  failedCopyUmo.value = copied ? '' : umo;
  if (copyFeedbackTimer !== null) {
    window.clearTimeout(copyFeedbackTimer);
  }
  copyFeedbackTimer = window.setTimeout(() => {
    copiedUmo.value = '';
    failedCopyUmo.value = '';
  }, 2000);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat(locale.value).format(value);
}

onBeforeUnmount(() => {
  if (copyFeedbackTimer !== null) {
    window.clearTimeout(copyFeedbackTimer);
  }
});
</script>

<style lang="scss" scoped>
@use './panel-styles' as panel;

@include panel.stat-card;

.provider-list-card {
  padding: 22px;
  width: 100%;
}

@include panel.card-head;
@include panel.card-head-compact;
@include panel.section-title;
@include panel.section-subtitle;

@include panel.provider-list;

.provider-identity {
  align-items: center;
  display: flex;
  gap: 9px;
  min-width: 0;
}

.provider-identity--umo {
  flex: 1 1 auto;
}

.platform-icon {
  flex: 0 0 auto;
  height: 20px;
  object-fit: contain;
  width: 20px;
}

.provider-name--alias {
  border-bottom: 1px dotted currentColor;
  cursor: help;
}

.umo-tooltip {
  overflow-wrap: anywhere;
}

.umo-copy-button,
.umo-conversation-link {
  align-items: center;
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: var(--stats-subtle);
  cursor: pointer;
  display: inline-flex;
  flex: 0 0 auto;
  height: 26px;
  justify-content: center;
  padding: 0;
  text-decoration: none;
  transition:
    background-color 0.18s ease,
    color 0.18s ease;
  width: 26px;
}

.umo-copy-button:hover,
.umo-conversation-link:hover {
  background: rgba(var(--v-theme-on-surface), 0.07);
  color: var(--stats-text);
}

.umo-copy-button--copied {
  color: rgb(var(--v-theme-success));
}

.empty-state {
  color: var(--stats-muted);
  font-size: 14px;
}

.stats-page.is-dark .empty-state {
  color: var(--stats-muted);
}

@media (max-width: 900px) {
  .card-head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .provider-list-card {
    padding: 18px;
    border-radius: 14px;
  }
}
</style>
