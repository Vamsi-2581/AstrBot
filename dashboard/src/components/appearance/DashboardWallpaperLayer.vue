<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import {
  appearanceApi,
  type AppearanceOrientation,
  type AppearanceWallpaper,
} from '@/api/v1';
import { fetchWithAuth } from '@/api/http';
import { useWallpaperTheme } from '@/composables/useWallpaperTheme';
import { useModuleI18n } from '@/i18n/composables';
import { useAppearanceStore } from '@/stores/appearance';
import { useToastStore } from '@/stores/toast';
import {
  readWallpaperCache,
  writeWallpaperCache,
} from '@/utils/wallpaperCache';

const ROTATION_LOCK_NAME = 'astrbot-wallpaper-rotation';
const ROTATION_LEASE_KEY = 'astrbot:appearance:rotation-lease';
const ROTATION_LEASE_MS = 15_000;

const appearance = useAppearanceStore();
const toast = useToastStore();
const { tm } = useModuleI18n('features/settings');
const portrait = ref(false);
const reducedMotion = ref(false);
const activeLayer = ref(0);
const layers = ref(['', '']);

let mediaQuery: MediaQueryList | null = null;
let motionQuery: MediaQueryList | null = null;
let transitionTimer: number | null = null;
let rotationTimer: number | null = null;
let rotationBusy = false;
let requestVersion = 0;
let requestController: AbortController | null = null;
let randomApplied = false;

const orientation = computed<AppearanceOrientation>(() =>
  portrait.value ? 'portrait' : 'landscape',
);

const wallpaper = computed<AppearanceWallpaper | null>(() =>
  appearance.currentWallpaper(orientation.value),
);

const useStillImage = computed(
  () => reducedMotion.value && wallpaper.value?.animated === true,
);

const wallpaperUrl = computed(() => {
  if (!appearance.active || !wallpaper.value) return '';
  return useStillImage.value
    ? appearanceApi.thumbnailUrl(wallpaper.value.id)
    : appearanceApi.imageUrl(wallpaper.value.id);
});

const cacheVariant = computed(() => (useStillImage.value ? 'still' : ''));

useWallpaperTheme(
  wallpaper,
  computed(() => appearance.settings.auto_theme),
);

class WallpaperRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'WallpaperRequestError';
  }
}

function updateOrientation(event?: MediaQueryListEvent): void {
  portrait.value = event?.matches ?? mediaQuery?.matches ?? false;
}

function updateReducedMotion(event?: MediaQueryListEvent): void {
  reducedMotion.value = event?.matches ?? motionQuery?.matches ?? false;
}

async function decodeImage(url: string): Promise<void> {
  const image = new Image();
  image.decoding = 'async';
  image.src = url;
  await new Promise<void>((resolve, reject) => {
    image.onload = () => void resolve();
    image.onerror = () =>
      void reject(new Error('Wallpaper could not be decoded'));
  });
  await image.decode?.().catch(() => undefined);
}

function revokeLayer(index: number): void {
  const url = layers.value[index];
  if (url.startsWith('blob:')) URL.revokeObjectURL(url);
  layers.value[index] = '';
}

function layerStyle(url: string): Record<string, string> {
  return { backgroundImage: url ? `url(${url})` : 'none' };
}

function clearLayers(): void {
  if (transitionTimer !== null) {
    window.clearTimeout(transitionTimer);
    transitionTimer = null;
  }
  revokeLayer(0);
  revokeLayer(1);
  activeLayer.value = 0;
}

async function fetchWallpaper(
  wallpaperValue: AppearanceWallpaper,
  url: string,
  variant: string,
  signal: AbortSignal,
): Promise<Blob> {
  const cached = await readWallpaperCache(wallpaperValue.id, variant);
  if (cached) return cached;

  const response = await fetchWithAuth(url, { cache: 'no-store', signal });
  if (!response.ok) {
    throw new WallpaperRequestError(
      'Wallpaper request failed',
      response.status,
    );
  }
  await writeWallpaperCache(wallpaperValue.id, response.clone(), variant);
  return response.blob();
}

async function applyWallpaper(url: string): Promise<void> {
  const version = ++requestVersion;
  requestController?.abort();
  requestController = null;

  if (!url || !wallpaper.value) {
    clearLayers();
    return;
  }

  const currentWallpaper = wallpaper.value;
  const variant = cacheVariant.value;
  const controller = new AbortController();
  requestController = controller;
  try {
    const blob = await fetchWallpaper(
      currentWallpaper,
      url,
      variant,
      controller.signal,
    );
    if (version !== requestVersion || controller.signal.aborted) return;

    const objectUrl = URL.createObjectURL(blob);
    try {
      await decodeImage(objectUrl);
    } catch (error) {
      URL.revokeObjectURL(objectUrl);
      throw error;
    }
    if (version !== requestVersion || controller.signal.aborted) {
      URL.revokeObjectURL(objectUrl);
      return;
    }

    const nextLayer = activeLayer.value === 0 ? 1 : 0;
    revokeLayer(nextLayer);
    layers.value[nextLayer] = objectUrl;
    requestAnimationFrame(() => {
      if (version !== requestVersion) {
        if (layers.value[nextLayer] === objectUrl) revokeLayer(nextLayer);
        return;
      }
      const previousLayer = activeLayer.value;
      activeLayer.value = nextLayer;
      if (transitionTimer !== null) window.clearTimeout(transitionTimer);
      transitionTimer = window.setTimeout(
        () => void revokeLayer(previousLayer),
        reducedMotion.value ? 0 : 700,
      );
    });
  } catch (error) {
    if (controller.signal.aborted || version !== requestVersion) return;
    if (error instanceof WallpaperRequestError && error.status === 404) {
      appearance.clearMissingWallpaper(currentWallpaper.id);
      toast.add({
        message: tm('appearance.messages.missing'),
        color: 'warning',
      });
    }
    // Keep the previous layer for transient failures, including auth expiry.
  } finally {
    if (requestController === controller) requestController = null;
  }
}

function acquireRotationLease(): boolean {
  if (typeof localStorage === 'undefined') return true;
  const now = Date.now();
  const until = Number(localStorage.getItem(ROTATION_LEASE_KEY) || 0);
  if (Number.isFinite(until) && until > now) return false;
  try {
    localStorage.setItem(ROTATION_LEASE_KEY, String(now + ROTATION_LEASE_MS));
  } catch {
    return false;
  }
  return true;
}

async function runRotation(): Promise<void> {
  if (
    rotationBusy ||
    !appearance.loaded ||
    !appearance.settings.enabled ||
    !appearance.settings.rotation_enabled ||
    document.visibilityState !== 'visible'
  ) {
    return;
  }
  if (appearance.wallpapersFor(orientation.value).length < 2) return;
  const run = async () => {
    rotationBusy = true;
    try {
      const selected = appearance.selectRandom(orientation.value);
      if (selected) await appearance.saveNow();
    } catch {
      // Rotation is opportunistic; a failed save is retried on the next tick.
    } finally {
      rotationBusy = false;
    }
  };
  if (navigator.locks?.request) {
    await navigator.locks.request(
      ROTATION_LOCK_NAME,
      { ifAvailable: true },
      async (lock) => {
        if (lock) await run();
      },
    );
    return;
  }
  if (acquireRotationLease()) await run();
}

function clearRotation(): void {
  if (rotationTimer !== null) {
    window.clearInterval(rotationTimer);
    rotationTimer = null;
  }
}

function scheduleRotation(): void {
  clearRotation();
  if (
    !appearance.loaded ||
    !appearance.settings.enabled ||
    !appearance.settings.rotation_enabled ||
    document.visibilityState !== 'visible'
  ) {
    return;
  }
  const interval =
    Math.max(1, appearance.settings.rotation_interval_minutes) * 60_000;
  rotationTimer = window.setInterval(
    () => void runRotation().catch(() => undefined),
    interval,
  );
}

function onVisibilityChange(): void {
  if (document.visibilityState === 'visible') {
    scheduleRotation();
  } else {
    clearRotation();
  }
}

watch(
  [wallpaperUrl, useStillImage],
  ([url]) => {
    void applyWallpaper(url);
  },
  { immediate: true },
);

watch(
  () =>
    [
      appearance.loaded,
      appearance.settings.random_on_load,
      appearance.settings.enabled,
    ] as const,
  async ([loaded, randomOnLoad, enabled]) => {
    if (!loaded || !randomOnLoad || !enabled || randomApplied) return;
    if (!appearance.wallpapersFor(orientation.value).length) return;
    randomApplied = true;
    const selected = appearance.selectRandom(orientation.value);
    if (selected) await appearance.saveNow().catch(() => undefined);
  },
  { immediate: true },
);

watch(
  () =>
    [
      appearance.loaded,
      appearance.settings.enabled,
      appearance.settings.rotation_enabled,
      appearance.settings.rotation_interval_minutes,
    ] as const,
  scheduleRotation,
  { immediate: true },
);

onMounted(() => {
  void appearance.hydrate();
  mediaQuery = window.matchMedia('(orientation: portrait)');
  motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  updateOrientation();
  updateReducedMotion();
  mediaQuery.addEventListener('change', updateOrientation);
  motionQuery.addEventListener('change', updateReducedMotion);
  document.addEventListener('visibilitychange', onVisibilityChange);
  scheduleRotation();
});

onBeforeUnmount(() => {
  requestVersion += 1;
  requestController?.abort();
  requestController = null;
  clearRotation();
  if (transitionTimer !== null) window.clearTimeout(transitionTimer);
  if (mediaQuery) mediaQuery.removeEventListener('change', updateOrientation);
  if (motionQuery)
    motionQuery.removeEventListener('change', updateReducedMotion);
  document.removeEventListener('visibilitychange', onVisibilityChange);
  revokeLayer(0);
  revokeLayer(1);
});
</script>

<template>
  <div
    v-if="appearance.active && wallpaper"
    class="dashboard-wallpaper"
    :class="{ 'dashboard-wallpaper--reduced': reducedMotion }"
    aria-hidden="true"
  >
    <div
      v-for="(url, index) in layers"
      :key="index"
      class="dashboard-wallpaper__layer"
      :class="{ 'dashboard-wallpaper__layer--active': activeLayer === index }"
      :style="layerStyle(url)"
    />
  </div>
</template>

<style>
.dashboard-wallpaper {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.dashboard-wallpaper::after {
  position: absolute;
  inset: 0;
  background: rgb(0 0 0 / var(--dashboard-wallpaper-dim, 0.5));
  content: '';
}

.dashboard-wallpaper__layer {
  position: absolute;
  inset: calc(-1 * var(--dashboard-wallpaper-blur, 0px));
  background-position: var(--dashboard-wallpaper-position, center center);
  background-repeat: no-repeat;
  background-size: var(--dashboard-wallpaper-fit, cover);
  filter: blur(var(--dashboard-wallpaper-blur, 0px))
    brightness(var(--dashboard-wallpaper-brightness, 1))
    saturate(var(--dashboard-wallpaper-saturation, 1))
    grayscale(var(--dashboard-wallpaper-grayscale, 0));
  opacity: 0;
  transition: opacity 650ms ease;
}

.dashboard-wallpaper__layer--active {
  opacity: 1;
}

.dashboard-wallpaper--reduced .dashboard-wallpaper__layer {
  transition: none;
}

.dashboard-appearance-active {
  --dashboard-wallpaper-surface: rgba(
    var(--v-theme-surface),
    var(--dashboard-surface-opacity, 1)
  );
  background: transparent;
  isolation: isolate;
}

.dashboard-appearance-active .v-application__wrap {
  position: relative;
  z-index: 1;
  background: transparent;
}

.dashboard-appearance-active .v-main {
  background-color: transparent;
}

.dashboard-appearance-active .page-wrapper {
  background-color: var(--dashboard-wallpaper-surface);
}

.dashboard-appearance-active
  .v-card:where(
    :not(.bg-primary):not(.bg-secondary):not(.bg-success):not(.bg-warning):not(
        .bg-error
      ):not(.bg-info)
  ) {
  background-color: var(--dashboard-wallpaper-surface);
  backdrop-filter: var(--dashboard-surface-backdrop, none);
  -webkit-backdrop-filter: var(--dashboard-surface-backdrop, none);
}

.dashboard-appearance-active .v-table,
.dashboard-appearance-active .v-data-table {
  background-color: transparent !important;
}

.dashboard-appearance-active .v-app-bar.top-header,
.dashboard-appearance-active .v-navigation-drawer.leftSidebar {
  background-color: var(--dashboard-wallpaper-surface) !important;
}

.dashboard-appearance-active .sidebar-footer {
  background-color: var(--dashboard-wallpaper-surface) !important;
}

.dashboard-appearance-active .v-overlay__content > .v-card,
.dashboard-appearance-active .v-dialog .v-card,
.dashboard-appearance-active .v-overlay__content > .v-list {
  background-color: rgba(
    var(--v-theme-surface),
    var(--dashboard-dialog-opacity, 0.92)
  );
}

.dashboard-appearance-active .v-menu .v-overlay__content,
.dashboard-appearance-active .v-menu .v-list,
.dashboard-appearance-active .v-overlay__content > .v-list {
  background-color: rgba(
    var(--v-theme-surface),
    var(--dashboard-floating-opacity, 0.78)
  );
  backdrop-filter: var(--dashboard-surface-backdrop, none);
  -webkit-backdrop-filter: var(--dashboard-surface-backdrop, none);
}

.dashboard-appearance-text-soft_shadow .page-wrapper,
.dashboard-appearance-text-soft_shadow .v-navigation-drawer,
.dashboard-appearance-text-soft_shadow .v-app-bar {
  text-shadow: var(--dashboard-text-shadow, none);
}

.dashboard-appearance-text-stroke .page-wrapper,
.dashboard-appearance-text-stroke .v-navigation-drawer,
.dashboard-appearance-text-stroke .v-app-bar {
  -webkit-text-stroke: var(--dashboard-text-stroke, 0);
}

@media (max-width: 960px) {
  .dashboard-appearance-active .v-navigation-drawer.leftSidebar {
    backdrop-filter: var(--dashboard-mobile-sidebar-backdrop, none);
    -webkit-backdrop-filter: var(--dashboard-mobile-sidebar-backdrop, none);
  }
}

@media (prefers-reduced-motion: reduce) {
  .dashboard-wallpaper__layer {
    transition: none;
  }
}
</style>
