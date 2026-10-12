<template>
  <div class="shared-page">
    <div class="shared-page__card">
      <header class="shared-page__header">
        <h1 class="shared-page__title">
          {{ transcript?.title || tm('share.untitled') }}
        </h1>
        <p class="shared-page__meta">
          {{ tm('share.readOnlyNotice') }}
        </p>
        <p v-if="transcript?.truncated" class="shared-page__meta">
          {{ tm('share.truncated') }}
        </p>
      </header>

      <v-progress-linear v-if="loading" indeterminate color="primary" />

      <div v-else-if="error" class="shared-page__error">
        <v-icon size="32" color="error">mdi-link-off</v-icon>
        <p>{{ tm('share.unavailable') }}</p>
      </div>

      <div v-else class="shared-page__messages">
        <div
          v-for="(message, index) in transcript?.messages || []"
          :key="index"
          class="shared-message"
          :class="`shared-message--${message.role}`"
        >
          <div class="shared-message__role">
            {{
              message.role === 'assistant' ? tm('share.bot') : tm('share.user')
            }}
          </div>
          <div class="shared-message__text">{{ message.text }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { chatApi } from '@/api/v1';
import { useModuleI18n } from '@/i18n/composables';
import type { SharedConversationData } from '@/api/v1/types';

const route = useRoute();
const { tm } = useModuleI18n('features/chat');

const transcript = ref<SharedConversationData | null>(null);
const loading = ref(true);
const error = ref(false);

onMounted(async () => {
  const token = String(route.params.token || '');
  try {
    const response = await chatApi.getSharedConversation(token);
    transcript.value = response.data.data ?? null;
  } catch (err) {
    console.error(err);
    error.value = true;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.shared-page {
  min-height: 100vh;
  background: rgb(var(--v-theme-background));
  padding: 32px 16px;
}

.shared-page__card {
  max-width: 820px;
  margin: 0 auto;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
}

.shared-page__title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.shared-page__meta {
  font-size: 12px;
  opacity: 0.7;
  margin: 0;
}

.shared-page__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 0;
  opacity: 0.8;
}

.shared-page__messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 20px;
}

.shared-message {
  border-radius: 10px;
  padding: 12px 14px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.shared-message--assistant {
  background: rgba(var(--v-theme-primary), 0.08);
}

.shared-message__role {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  opacity: 0.6;
  margin-bottom: 4px;
}

.shared-message__text {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
