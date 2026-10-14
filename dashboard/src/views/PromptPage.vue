<template>
  <div class="prompt-page">
    <v-container fluid class="pa-0 prompt-shell">
      <header class="page-header prompt-header">
        <div class="prompt-header__main">
          <h1 class="page-header__title">
            {{ t('core.navigation.prompt') }}
            <ConfigDocsLink docs="use/prompt.html" />
          </h1>
          <p class="prompt-header__subtitle">{{ tm('page.description') }}</p>
        </div>
      </header>

      <PromptManager />
    </v-container>
  </div>
</template>

<script setup lang="ts">
import ConfigDocsLink from '@/components/shared/ConfigDocsLink.vue';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import { PromptManager } from '@/views/prompt';

const { t } = useI18n();
const { tm } = useModuleI18n('features/prompt');
</script>

<style scoped>
.prompt-page {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  width: 100%;
}

.prompt-shell {
  display: flex;
  flex: 1;
  flex-direction: column;
  margin: 0 auto;
  max-width: 1440px;
  min-height: 0;
  width: 100%;
}

.prompt-header {
  flex: 0 0 auto;
}

.prompt-header__main {
  min-width: 0;
}

.prompt-header__subtitle {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.875rem;
  line-height: 1.6;
  margin: 4px 0 0;
}
</style>
