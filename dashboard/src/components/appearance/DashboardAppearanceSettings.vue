<script setup lang="ts">
import { computed, onMounted } from 'vue';

import AppearanceControls from '@/components/appearance/AppearanceControls.vue';
import WallpaperGallery from '@/components/appearance/WallpaperGallery.vue';
import { useModuleI18n } from '@/i18n/composables';
import { useAppearanceStore } from '@/stores/appearance';
import { useToastStore } from '@/stores/toast';

const appearance = useAppearanceStore();
const toast = useToastStore();
const { tm } = useModuleI18n('features/settings');

const previewWallpaper = computed(() => {
  const settings = appearance.settings;
  const selectedId =
    settings.landscape_wallpaper_id || settings.portrait_wallpaper_id;
  return appearance.wallpapers.find((wallpaper) => wallpaper.id === selectedId);
});

const previewImageStyle = computed(() => ({
  backgroundImage: previewWallpaper.value
    ? `url("${previewWallpaper.value.thumbnail_url}")`
    : 'none',
  backgroundPosition: appearance.settings.position,
  backgroundSize: appearance.settings.fit,
  filter: `brightness(${appearance.settings.brightness}) saturate(${appearance.settings.saturation}) grayscale(${appearance.settings.grayscale})`,
}));

const previewShadeStyle = computed(() => ({
  backgroundColor: `rgb(0 0 0 / ${appearance.settings.dim})`,
}));

const previewSurfaceStyle = computed(() => ({
  backgroundColor: `rgba(var(--v-theme-surface), ${appearance.settings.surface_opacity})`,
  backdropFilter:
    appearance.settings.surface_blur > 0
      ? `blur(${appearance.settings.surface_blur}px) saturate(1.08)`
      : 'none',
}));

async function resetAppearance(): Promise<void> {
  try {
    await appearance.reset();
    toast.add({
      message: tm('appearance.messages.resetSuccess'),
      color: 'success',
    });
  } catch {
    toast.add({
      message: appearance.error || tm('appearance.messages.loadFailed'),
      color: 'error',
    });
  }
}

onMounted(() => {
  void appearance.hydrate();
});
</script>

<template>
  <section class="appearance-settings">
    <div class="appearance-settings__heading">
      <div>
        <div class="appearance-settings__title">
          {{ tm('appearance.title') }}
        </div>
        <p class="appearance-settings__subtitle">
          {{ tm('appearance.subtitle') }}
        </p>
      </div>
      <v-btn size="small" variant="tonal" @click="resetAppearance">
        <v-icon start>mdi-restore</v-icon>
        {{ tm('appearance.reset') }}
      </v-btn>
    </div>

    <v-alert
      v-if="appearance.error"
      type="error"
      variant="tonal"
      density="compact"
      closable
      @click:close="appearance.clearError()"
    >
      {{ appearance.error }}
    </v-alert>

    <div
      class="appearance-preview"
      :class="{ 'appearance-preview--empty': !previewWallpaper }"
    >
      <div class="appearance-preview__image" :style="previewImageStyle" />
      <div class="appearance-preview__shade" :style="previewShadeStyle" />
      <div class="appearance-preview__surface" :style="previewSurfaceStyle">
        <span>{{ tm('appearance.preview') }}</span>
        <v-btn size="x-small" color="primary">
          {{ tm('appearance.sampleAction') }}
        </v-btn>
      </div>
    </div>
    <p class="appearance-settings__hint">
      {{ tm('appearance.previewHint') }}
    </p>

    <AppearanceControls />

    <WallpaperGallery orientation="landscape" />
    <WallpaperGallery orientation="portrait" />
  </section>
</template>

<style scoped>
.appearance-settings {
  display: grid;
  gap: 20px;
  margin-top: 20px;
}

.appearance-settings__heading {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.appearance-settings__title {
  color: rgb(var(--v-theme-on-surface));
  font-size: 15px;
  font-weight: 600;
}

.appearance-settings__subtitle,
.appearance-settings__hint {
  color: rgba(var(--v-theme-on-surface), 0.66);
  font-size: 13px;
  margin: 4px 0 0;
}

.appearance-settings__hint {
  margin-top: -8px;
}

.appearance-preview {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 12px;
  height: 144px;
  isolation: isolate;
  overflow: hidden;
  position: relative;
}

.appearance-preview--empty {
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.3),
    rgb(var(--v-theme-surface))
  );
}

.appearance-preview__image,
.appearance-preview__shade,
.appearance-preview__surface {
  inset: 0;
  position: absolute;
}

.appearance-preview__image {
  background-repeat: no-repeat;
  opacity: 0.9;
  transform: scale(1.04);
}

.appearance-preview__surface {
  align-items: center;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.1);
  color: rgb(var(--v-theme-on-surface));
  display: flex;
  justify-content: space-between;
  margin: 28px;
  padding: 16px;
}

@media (max-width: 600px) {
  .appearance-settings__heading {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
