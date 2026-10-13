<template>
  <v-dialog
    :model-value="modelValue"
    max-width="520"
    :aria-label="tm('share.title')"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card class="share-dialog">
      <v-card-title class="share-dialog__title">
        {{ tm('share.title') }}
      </v-card-title>
      <v-card-subtitle class="share-dialog__subtitle">
        {{ tm('share.subtitle') }}
      </v-card-subtitle>
      <v-card-text>
        <div class="share-dialog__create">
          <v-select
            v-model="expiresInDays"
            :items="expiryOptions"
            item-title="label"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            :label="tm('share.expiryLabel')"
          />
          <v-btn
            color="primary"
            :loading="creating"
            :disabled="creating"
            @click="createShare"
          >
            {{ tm('share.create') }}
          </v-btn>
        </div>

        <v-alert
          v-if="createdLink"
          type="success"
          variant="tonal"
          density="compact"
          class="mt-4"
        >
          <div class="share-dialog__link">
            <code class="share-dialog__link-text">{{ createdLink }}</code>
            <v-btn
              size="small"
              variant="text"
              :title="tm('share.copy')"
              @click="copyLink"
            >
              {{ tm('share.copy') }}
            </v-btn>
          </div>
          <div class="share-dialog__hint">{{ tm('share.onceHint') }}</div>
        </v-alert>

        <v-divider class="my-4" />

        <div class="share-dialog__list-title">{{ tm('share.existing') }}</div>
        <v-progress-linear v-if="loading" indeterminate color="primary" />
        <div v-else-if="!shares.length" class="share-dialog__empty">
          {{ tm('share.none') }}
        </div>
        <v-list v-else density="compact" class="share-dialog__list">
          <v-list-item v-for="share in shares" :key="share.share_id">
            <v-list-item-title class="share-dialog__item-title">
              {{ share.share_id.slice(0, 8) }}
              <v-chip
                size="x-small"
                :color="share.active ? 'success' : 'default'"
                class="ml-2"
              >
                {{ share.active ? tm('share.active') : tm('share.inactive') }}
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ expiryLabel(share.expires_at) }}
            </v-list-item-subtitle>
            <template #append>
              <v-btn
                v-if="share.active"
                size="small"
                variant="text"
                color="error"
                @click="revokeShare(share.share_id)"
              >
                {{ tm('share.revoke') }}
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">
          {{ tm('share.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { chatApi } from '@/api/v1';
import { useModuleI18n } from '@/i18n/composables';
import { copyToClipboard } from '@/utils/clipboard';
import { useToast } from '@/utils/toast';

const props = defineProps<{
  modelValue: boolean;
  sessionId: string;
}>();

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();

const { tm } = useModuleI18n('features/chat');
const toast = useToast();

type ShareExpiry = 0 | 1 | 7 | 30 | 90;
const expiresInDays = ref<ShareExpiry>(7);
const creating = ref(false);
const loading = ref(false);
const shares = ref<
  Array<{
    share_id: string;
    expires_at: string | null;
    active: boolean;
  }>
>([]);
const createdLink = ref('');

const expiryOptions = computed<Array<{ value: ShareExpiry; label: string }>>(
  () => [
    { value: 1, label: tm('share.expiry1') },
    { value: 7, label: tm('share.expiry7') },
    { value: 30, label: tm('share.expiry30') },
    { value: 90, label: tm('share.expiry90') },
    { value: 0, label: tm('share.expiryNever') },
  ],
);

function buildLink(token: string): string {
  const base = import.meta.env.BASE_URL || '/';
  const origin = window.location.origin;
  return `${origin}${base}#/share/${token}`;
}

function expiryLabel(expiresAt: string | null): string {
  if (!expiresAt) {
    return tm('share.expiryNever');
  }
  return `${tm('share.expiresAt')}: ${new Date(expiresAt).toLocaleString()}`;
}

async function loadShares() {
  if (!props.sessionId) {
    return;
  }
  loading.value = true;
  try {
    const response = await chatApi.listShares(props.sessionId);
    shares.value = response.data.data?.shares ?? [];
  } catch (error) {
    console.error(error);
    shares.value = [];
  } finally {
    loading.value = false;
  }
}

async function createShare() {
  creating.value = true;
  try {
    const response = await chatApi.createShare(
      props.sessionId,
      expiresInDays.value,
    );
    const token = response.data.data?.token;
    createdLink.value = token ? buildLink(token) : '';
    await loadShares();
  } catch (error) {
    console.error(error);
    toast.error(tm('share.createFailed'));
  } finally {
    creating.value = false;
  }
}

async function revokeShare(shareId: string) {
  try {
    await chatApi.revokeShare(shareId);
    await loadShares();
  } catch (error) {
    console.error(error);
    toast.error(tm('share.revokeFailed'));
  }
}

async function copyLink() {
  if (await copyToClipboard(createdLink.value)) {
    toast.success(tm('share.copied'));
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      createdLink.value = '';
      void loadShares();
    }
  },
);
</script>

<style scoped>
.share-dialog__create {
  display: flex;
  gap: 12px;
  align-items: center;
}

.share-dialog__link {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.share-dialog__link-text {
  word-break: break-all;
  font-size: 12px;
}

.share-dialog__hint {
  margin-top: 6px;
  font-size: 12px;
  opacity: 0.8;
}

.share-dialog__list-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.share-dialog__empty {
  opacity: 0.7;
  font-size: 13px;
}

.share-dialog__item-title {
  display: flex;
  align-items: center;
}
</style>
