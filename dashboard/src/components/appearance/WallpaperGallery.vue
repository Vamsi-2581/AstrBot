<script setup lang="ts">
import { computed, ref } from 'vue';

import type { AppearanceOrientation, AppearanceWallpaper } from '@/api/v1';
import { useModuleI18n } from '@/i18n/composables';
import { useAppearanceStore } from '@/stores/appearance';
import { useToastStore } from '@/stores/toast';
import { askForConfirmation, useConfirmDialog } from '@/utils/confirmDialog';

const props = defineProps<{
  orientation: AppearanceOrientation;
}>();

const MAX_UPLOAD_BYTES = 32 * 1024 * 1024;
const ACCEPTED_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
]);

const appearance = useAppearanceStore();
const toast = useToastStore();
const confirmDialog = useConfirmDialog();
const { tm } = useModuleI18n('features/settings');
const uploadInput = ref<HTMLInputElement | null>(null);

const wallpapers = computed(() => appearance.wallpapersFor(props.orientation));
const selectedId = computed(() =>
  props.orientation === 'portrait'
    ? appearance.settings.portrait_wallpaper_id
    : appearance.settings.landscape_wallpaper_id,
);
const uploading = computed(
  () =>
    appearance.uploading && appearance.uploadOrientation === props.orientation,
);

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

function selectWallpaper(wallpaper: AppearanceWallpaper): void {
  appearance.selectWallpaper(props.orientation, wallpaper.id);
}

function openUpload(): void {
  uploadInput.value?.click();
}

async function uploadWallpaper(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const [file] = input.files || [];
  input.value = '';
  if (!file) return;
  if (file.type && !ACCEPTED_TYPES.has(file.type)) {
    toast.add({ message: tm('appearance.invalidType'), color: 'error' });
    return;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    toast.add({ message: tm('appearance.fileTooLarge'), color: 'error' });
    return;
  }
  try {
    await appearance.uploadWallpaper(file, props.orientation);
    toast.add({
      message: tm('appearance.messages.uploadSuccess'),
      color: 'success',
    });
  } catch (error) {
    if ((error as { code?: string }).code === 'ERR_CANCELED') return;
    toast.add({
      message: appearance.error || tm('appearance.messages.uploadFailed'),
      color: 'error',
    });
  }
}

async function removeWallpaper(wallpaper: AppearanceWallpaper): Promise<void> {
  const confirmed = await askForConfirmation(
    tm('appearance.confirmDelete'),
    confirmDialog,
  );
  if (!confirmed) return;
  try {
    await appearance.removeWallpaper(wallpaper.id);
    toast.add({
      message: tm('appearance.messages.deleteSuccess'),
      color: 'success',
    });
  } catch {
    toast.add({
      message: appearance.error || tm('appearance.messages.deleteFailed'),
      color: 'error',
    });
  }
}
</script>

<template>
  <section class="wallpaper-gallery">
    <div class="wallpaper-gallery__heading">
      <div>
        <div class="wallpaper-gallery__title">
          {{ tm(`appearance.gallery.${orientation}.title`) }}
        </div>
        <p>{{ tm(`appearance.gallery.${orientation}.subtitle`) }}</p>
      </div>
      <div class="wallpaper-gallery__actions">
        <v-btn
          v-if="uploading"
          size="small"
          variant="text"
          color="error"
          @click="appearance.cancelUpload()"
        >
          {{ tm('appearance.cancel') }}
        </v-btn>
        <v-btn
          size="small"
          color="primary"
          variant="tonal"
          :loading="uploading"
          :disabled="appearance.uploading"
          @click="openUpload"
        >
          <v-icon start>mdi-upload</v-icon>
          {{ tm('appearance.upload') }}
        </v-btn>
      </div>
    </div>

    <v-progress-linear
      v-if="uploading"
      :model-value="appearance.uploadProgress"
      color="primary"
      height="4"
      rounded
      class="wallpaper-gallery__progress"
    />

    <div v-if="!wallpapers.length" class="wallpaper-gallery__empty">
      {{ tm('appearance.gallery.empty') }}
    </div>
    <div v-else class="wallpaper-gallery__grid">
      <article
        v-for="wallpaper in wallpapers"
        :key="wallpaper.id"
        class="wallpaper-card"
        :class="{ 'wallpaper-card--selected': selectedId === wallpaper.id }"
      >
        <button
          type="button"
          class="wallpaper-card__select"
          :aria-label="tm('appearance.select')"
          @click="selectWallpaper(wallpaper)"
        >
          <img
            :src="wallpaper.thumbnail_url"
            :alt="tm('appearance.wallpaperAlt')"
            loading="lazy"
          />
          <span
            v-if="wallpaper.orientation === 'both'"
            class="wallpaper-card__badge"
          >
            {{ tm('appearance.bothBadge') }}
          </span>
        </button>
        <div class="wallpaper-card__body">
          <div class="wallpaper-card__meta">
            <span :title="wallpaper.original_name">
              {{ wallpaper.original_name || tm('appearance.untitled') }}
            </span>
            <span>
              {{ wallpaper.width }} × {{ wallpaper.height }} ·
              {{ formatBytes(wallpaper.size_bytes) }}
            </span>
          </div>
          <div class="wallpaper-card__theme" aria-hidden="true">
            <span
              class="wallpaper-card__swatch"
              :style="{ backgroundColor: wallpaper.theme_primary }"
            />
            <span
              class="wallpaper-card__swatch"
              :style="{ backgroundColor: wallpaper.theme_secondary }"
            />
          </div>
          <v-btn
            size="x-small"
            icon="mdi-delete-outline"
            variant="text"
            color="error"
            :aria-label="tm('appearance.delete')"
            @click="removeWallpaper(wallpaper)"
          />
        </div>
      </article>
    </div>

    <input
      ref="uploadInput"
      class="wallpaper-gallery__file-input"
      type="file"
      accept="image/jpeg,image/png,image/webp,image/gif"
      @change="uploadWallpaper"
    />
  </section>
</template>

<style scoped>
.wallpaper-gallery {
  border-top: 1px solid rgb(var(--v-theme-on-surface) / 10%);
  padding-top: 20px;
}

.wallpaper-gallery__heading,
.wallpaper-gallery__actions,
.wallpaper-card__body,
.wallpaper-card__meta {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.wallpaper-gallery__title {
  color: rgb(var(--v-theme-on-surface));
  font-size: 15px;
  font-weight: 600;
}

.wallpaper-gallery__heading p {
  color: rgb(var(--v-theme-on-surface) / 66%);
  font-size: 13px;
  margin: 4px 0 0;
}

.wallpaper-gallery__progress {
  margin-top: 12px;
}

.wallpaper-gallery__empty {
  color: rgb(var(--v-theme-on-surface) / 64%);
  padding: 16px 0 0;
}

.wallpaper-gallery__grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  margin-top: 16px;
}

.wallpaper-card {
  border: 1px solid rgb(var(--v-theme-on-surface) / 12%);
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.wallpaper-card--selected {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
}

.wallpaper-card__select {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  padding: 0;
  border: 0;
  background: rgb(var(--v-theme-surface-variant));
  cursor: pointer;
}

.wallpaper-card__select img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.wallpaper-card__badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(0 0 0 / 55%);
  color: white;
  font-size: 11px;
}

.wallpaper-card__body {
  padding: 10px 12px;
}

.wallpaper-card__meta {
  align-items: flex-start;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  font-size: 12px;
  color: rgb(var(--v-theme-on-surface) / 66%);
}

.wallpaper-card__meta span:first-child {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(var(--v-theme-on-surface));
}

.wallpaper-card__theme {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.wallpaper-card__swatch {
  width: 14px;
  height: 14px;
  border: 1px solid rgb(var(--v-theme-on-surface) / 20%);
  border-radius: 50%;
}

.wallpaper-gallery__file-input {
  display: none;
}

@media (max-width: 600px) {
  .wallpaper-gallery__grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }
}
</style>
