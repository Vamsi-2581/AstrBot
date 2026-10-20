import { defineStore } from 'pinia';

import {
  appearanceApi,
  type AppearanceOrientation,
  type AppearanceSettings,
  type AppearanceWallpaper,
} from '@/api/v1';
import {
  deleteWallpaperCache,
  pruneWallpaperCache,
} from '@/utils/wallpaperCache';

const LEGACY_STORAGE_KEY = 'astrbot:appearance:v1';
const CHANNEL_NAME = 'astrbot:appearance:v1';
const SAVE_DELAY_MS = 350;
const MAX_UPLOAD_BYTES = 32 * 1024 * 1024;

const defaultSettings = (): AppearanceSettings => ({
  enabled: false,
  landscape_wallpaper_id: '',
  portrait_wallpaper_id: '',
  fit: 'cover',
  position: 'center center',
  blur: 0,
  brightness: 1,
  dim: 0.5,
  surface_opacity: 0.35,
  surface_blur: 14,
  saturation: 1,
  grayscale: 0,
  random_on_load: false,
  rotation_enabled: false,
  rotation_interval_minutes: 30,
  auto_theme: false,
  text_enhancement: 'soft_shadow',
  text_enhancement_strength: 1,
  mobile_sidebar_blur: 18,
});

let saveTimer: ReturnType<typeof setTimeout> | null = null;
let saveInFlight: Promise<void> | null = null;
let uploadController: AbortController | null = null;
let channel: BroadcastChannel | null = null;
let applyingRemote = false;
let settingsRevision = 0;

function clamp(
  value: unknown,
  minimum: number,
  maximum: number,
  fallback: number,
) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(Math.max(parsed, minimum), maximum);
}

function normalizeSettings(value?: Partial<AppearanceSettings> | null) {
  const defaults = defaultSettings();
  const saved = value ?? {};
  return {
    enabled: saved.enabled === true,
    landscape_wallpaper_id:
      typeof saved.landscape_wallpaper_id === 'string'
        ? saved.landscape_wallpaper_id
        : '',
    portrait_wallpaper_id:
      typeof saved.portrait_wallpaper_id === 'string'
        ? saved.portrait_wallpaper_id
        : '',
    fit: saved.fit === 'contain' ? 'contain' : 'cover',
    position: isPosition(saved.position) ? saved.position : defaults.position,
    blur: Math.round(clamp(saved.blur, 0, 40, defaults.blur)),
    brightness: clamp(saved.brightness, 0.5, 1.5, defaults.brightness),
    dim: clamp(saved.dim, 0, 0.9, defaults.dim),
    surface_opacity: clamp(
      saved.surface_opacity,
      0,
      1,
      defaults.surface_opacity,
    ),
    surface_blur: Math.round(
      clamp(saved.surface_blur, 0, 40, defaults.surface_blur),
    ),
    saturation: clamp(saved.saturation, 0, 2, defaults.saturation),
    grayscale: clamp(saved.grayscale, 0, 1, defaults.grayscale),
    random_on_load: saved.random_on_load === true,
    rotation_enabled: saved.rotation_enabled === true,
    rotation_interval_minutes: Math.round(
      clamp(
        saved.rotation_interval_minutes,
        1,
        1440,
        defaults.rotation_interval_minutes,
      ),
    ),
    auto_theme: saved.auto_theme === true,
    text_enhancement: isTextEnhancement(saved.text_enhancement)
      ? saved.text_enhancement
      : defaults.text_enhancement,
    text_enhancement_strength: clamp(
      saved.text_enhancement_strength,
      0,
      2,
      defaults.text_enhancement_strength,
    ),
    mobile_sidebar_blur: Math.round(
      clamp(saved.mobile_sidebar_blur, 0, 40, defaults.mobile_sidebar_blur),
    ),
  } satisfies AppearanceSettings;
}

function isPosition(value: unknown): value is AppearanceSettings['position'] {
  return (
    value === 'center center' ||
    value === 'center top' ||
    value === 'center bottom' ||
    value === 'left center' ||
    value === 'right center'
  );
}

function isTextEnhancement(
  value: unknown,
): value is AppearanceSettings['text_enhancement'] {
  return value === 'off' || value === 'soft_shadow' || value === 'stroke';
}

function readLegacySettings(): Partial<AppearanceSettings> | null {
  try {
    const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw) as Record<string, unknown>;
    return {
      enabled: saved.enabled === true,
      landscape_wallpaper_id:
        typeof saved.landscapeWallpaperId === 'string'
          ? saved.landscapeWallpaperId
          : '',
      portrait_wallpaper_id:
        typeof saved.portraitWallpaperId === 'string'
          ? saved.portraitWallpaperId
          : '',
      fit: saved.fit === 'contain' ? 'contain' : 'cover',
      position: isPosition(saved.position) ? saved.position : undefined,
      blur: typeof saved.blur === 'number' ? saved.blur : undefined,
      brightness:
        typeof saved.brightness === 'number' ? saved.brightness : undefined,
      dim: typeof saved.dim === 'number' ? saved.dim : undefined,
      surface_opacity:
        typeof saved.surfaceOpacity === 'number'
          ? saved.surfaceOpacity
          : undefined,
    };
  } catch {
    return null;
  }
}

function isDefaultSettings(settings: AppearanceSettings): boolean {
  const defaults = defaultSettings();
  return (Object.keys(defaults) as (keyof AppearanceSettings)[]).every(
    (key) => settings[key] === defaults[key],
  );
}

function clearLegacySettings(): void {
  try {
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch {
    // Legacy cleanup is best-effort; the settings were already read.
  }
}

function errorMessage(error: unknown): string {
  const typed = error as {
    response?: { data?: { detail?: string; message?: string } };
    message?: string;
  };
  return (
    typed.response?.data?.detail ||
    typed.response?.data?.message ||
    typed.message ||
    'Appearance request failed'
  );
}

export const useAppearanceStore = defineStore('appearance', {
  state: () => ({
    settings: defaultSettings(),
    wallpapers: [] as AppearanceWallpaper[],
    loaded: false,
    loading: false,
    saving: false,
    uploading: false,
    uploadProgress: 0,
    uploadOrientation: null as AppearanceOrientation | null,
    error: '',
  }),

  getters: {
    active(state): boolean {
      return Boolean(
        state.settings.enabled &&
        (state.settings.landscape_wallpaper_id ||
          state.settings.portrait_wallpaper_id),
      );
    },
    textEnhancementClass(state): string {
      if (
        !state.settings.enabled ||
        (!state.settings.landscape_wallpaper_id &&
          !state.settings.portrait_wallpaper_id) ||
        state.settings.text_enhancement === 'off'
      ) {
        return '';
      }
      return `dashboard-appearance-text-${state.settings.text_enhancement}`;
    },
    rootStyle(state): Record<string, string> {
      const settings = state.settings;
      const active = Boolean(
        settings.enabled &&
        (settings.landscape_wallpaper_id || settings.portrait_wallpaper_id),
      );
      const floatingOpacity = Math.max(0.78, settings.surface_opacity);
      return {
        '--dashboard-surface-opacity': String(
          active ? settings.surface_opacity : 1,
        ),
        '--dashboard-floating-opacity': String(floatingOpacity),
        '--dashboard-dialog-opacity': String(
          Math.max(0.92, settings.surface_opacity),
        ),
        '--dashboard-wallpaper-dim': String(settings.dim),
        '--dashboard-wallpaper-blur': `${settings.blur}px`,
        '--dashboard-wallpaper-brightness': String(settings.brightness),
        '--dashboard-wallpaper-fit': settings.fit,
        '--dashboard-wallpaper-position': settings.position,
        '--dashboard-wallpaper-saturation': String(settings.saturation),
        '--dashboard-wallpaper-grayscale': String(settings.grayscale),
        '--dashboard-surface-backdrop':
          settings.surface_blur > 0
            ? `blur(${settings.surface_blur}px) saturate(1.08)`
            : 'none',
        '--dashboard-text-shadow':
          settings.text_enhancement === 'soft_shadow'
            ? `0 1px ${Math.max(1, 2 * settings.text_enhancement_strength)}px rgb(0 0 0 / ${Math.min(0.55, 0.22 + 0.18 * settings.text_enhancement_strength)})`
            : 'none',
        '--dashboard-text-stroke':
          settings.text_enhancement === 'stroke'
            ? `${Math.max(0.1, 0.3 * settings.text_enhancement_strength)}px rgb(0 0 0 / 48%)`
            : '0',
        '--dashboard-mobile-sidebar-backdrop':
          settings.mobile_sidebar_blur > 0
            ? `blur(${settings.mobile_sidebar_blur}px) saturate(1.08)`
            : 'none',
      };
    },
  },

  actions: {
    wallpapersFor(orientation: AppearanceOrientation): AppearanceWallpaper[] {
      return this.wallpapers.filter(
        (wallpaper) =>
          wallpaper.orientation === orientation ||
          wallpaper.orientation === 'both',
      );
    },

    currentWallpaper(
      orientation: AppearanceOrientation,
    ): AppearanceWallpaper | null {
      const settings = this.settings;
      const primary =
        orientation === 'portrait'
          ? settings.portrait_wallpaper_id
          : settings.landscape_wallpaper_id;
      const fallback =
        orientation === 'portrait'
          ? settings.landscape_wallpaper_id
          : settings.portrait_wallpaper_id;
      return (
        this.wallpapers.find((wallpaper) => wallpaper.id === primary) ??
        this.wallpapers.find((wallpaper) => wallpaper.id === fallback) ??
        null
      );
    },

    async hydrate(): Promise<void> {
      if (this.loaded || this.loading) return;
      this.loading = true;
      this.error = '';
      try {
        const [settingsResponse, wallpapersResponse] = await Promise.all([
          appearanceApi.getSettings(),
          appearanceApi.list(),
        ]);
        this.settings = normalizeSettings(settingsResponse.data.data);
        this.wallpapers = wallpapersResponse.data.data.items;
        await pruneWallpaperCache(this.wallpapers.map((item) => item.id));
        const legacy = readLegacySettings();
        let migrated = false;
        if (legacy && isDefaultSettings(this.settings)) {
          this.settings = normalizeSettings({ ...this.settings, ...legacy });
          migrated = true;
        }
        settingsRevision += 1;
        const changed = this.reconcileSelections();
        this.loaded = true;
        this.setupChannel();
        if (changed || migrated) {
          await this.saveNow();
        }
        if (legacy) {
          clearLegacySettings();
        }
      } catch (error) {
        this.error = errorMessage(error);
      } finally {
        this.loading = false;
      }
    },

    async loadWallpapers(): Promise<void> {
      try {
        const response = await appearanceApi.list();
        this.wallpapers = response.data.data.items;
        await pruneWallpaperCache(this.wallpapers.map((item) => item.id));
        if (this.reconcileSelections()) {
          await this.saveNow();
        }
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    selectWallpaper(
      orientation: AppearanceOrientation,
      wallpaperId: string,
    ): void {
      this.update(
        orientation === 'portrait'
          ? { portrait_wallpaper_id: wallpaperId, enabled: true }
          : { landscape_wallpaper_id: wallpaperId, enabled: true },
      );
    },

    selectRandom(
      orientation: AppearanceOrientation,
    ): AppearanceWallpaper | null {
      const pool = this.wallpapersFor(orientation);
      if (!pool.length) return null;
      const current =
        orientation === 'portrait'
          ? this.settings.portrait_wallpaper_id
          : this.settings.landscape_wallpaper_id;
      const candidates = pool.filter((wallpaper) => wallpaper.id !== current);
      const selected =
        candidates[Math.floor(Math.random() * candidates.length)] ?? pool[0];
      this.selectWallpaper(orientation, selected.id);
      return selected;
    },

    update(patch: Partial<AppearanceSettings>): void {
      this.settings = normalizeSettings({ ...this.settings, ...patch });
      settingsRevision += 1;
      this.scheduleSave();
      this.broadcastSettings();
    },

    async saveNow(): Promise<void> {
      if (saveTimer !== null) {
        clearTimeout(saveTimer);
        saveTimer = null;
      }
      const previousSave = saveInFlight;
      const request = (async () => {
        // Serialize saves so an older, slower request cannot reach the server
        // after a newer one and replace it with stale settings.
        if (previousSave) {
          await previousSave.catch(() => undefined);
        }
        const revision = settingsRevision;
        this.saving = true;
        this.error = '';
        try {
          const response = await appearanceApi.updateSettings({
            ...this.settings,
          });
          if (revision === settingsRevision) {
            this.settings = normalizeSettings(response.data.data);
            this.broadcastSettings();
          }
        } catch (error) {
          this.error = errorMessage(error);
          throw error;
        } finally {
          this.saving = false;
        }
      })();
      saveInFlight = request;
      try {
        await request;
      } finally {
        if (saveInFlight === request) saveInFlight = null;
      }
    },

    scheduleSave(): void {
      if (saveTimer !== null) clearTimeout(saveTimer);
      saveTimer = setTimeout(() => {
        saveTimer = null;
        void this.saveNow().catch(() => undefined);
      }, SAVE_DELAY_MS);
    },

    async uploadWallpaper(
      file: File,
      orientation: AppearanceOrientation,
    ): Promise<AppearanceWallpaper> {
      if (file.size > MAX_UPLOAD_BYTES) {
        throw new Error('Wallpaper must not exceed 32 MiB');
      }
      if (file.type && !file.type.startsWith('image/')) {
        throw new Error('Wallpaper must be an image');
      }
      this.uploading = true;
      this.uploadProgress = 0;
      this.uploadOrientation = orientation;
      this.error = '';
      uploadController = new AbortController();
      try {
        const response = await appearanceApi.upload(file, orientation, {
          signal: uploadController.signal,
          onUploadProgress: (event) => {
            if (!event.total) return;
            this.uploadProgress = Math.min(
              100,
              Math.round((event.loaded / event.total) * 100),
            );
          },
        });
        const wallpaper = response.data.data;
        this.wallpapers = [wallpaper, ...this.wallpapers];
        this.settings = normalizeSettings({
          ...this.settings,
          enabled: true,
          ...(orientation === 'portrait'
            ? { portrait_wallpaper_id: wallpaper.id }
            : { landscape_wallpaper_id: wallpaper.id }),
        });
        settingsRevision += 1;
        await this.saveNow();
        this.broadcastWallpapers();
        return wallpaper;
      } catch (error) {
        if ((error as { code?: string }).code === 'ERR_CANCELED') {
          throw error;
        }
        this.error = errorMessage(error);
        throw error;
      } finally {
        uploadController = null;
        this.uploading = false;
        this.uploadProgress = 0;
        this.uploadOrientation = null;
      }
    },

    cancelUpload(): void {
      uploadController?.abort();
    },

    async removeWallpaper(wallpaperId: string): Promise<void> {
      this.error = '';
      try {
        await appearanceApi.delete(wallpaperId);
        this.wallpapers = this.wallpapers.filter(
          (wallpaper) => wallpaper.id !== wallpaperId,
        );
        this.settings = normalizeSettings({
          ...this.settings,
          landscape_wallpaper_id:
            this.settings.landscape_wallpaper_id === wallpaperId
              ? ''
              : this.settings.landscape_wallpaper_id,
          portrait_wallpaper_id:
            this.settings.portrait_wallpaper_id === wallpaperId
              ? ''
              : this.settings.portrait_wallpaper_id,
        });
        settingsRevision += 1;
        await deleteWallpaperCache(wallpaperId);
        await this.saveNow();
        this.broadcastWallpapers();
      } catch (error) {
        this.error = errorMessage(error);
        throw error;
      }
    },

    clearMissingWallpaper(wallpaperId: string): void {
      this.settings = normalizeSettings({
        ...this.settings,
        landscape_wallpaper_id:
          this.settings.landscape_wallpaper_id === wallpaperId
            ? ''
            : this.settings.landscape_wallpaper_id,
        portrait_wallpaper_id:
          this.settings.portrait_wallpaper_id === wallpaperId
            ? ''
            : this.settings.portrait_wallpaper_id,
      });
      settingsRevision += 1;
      this.scheduleSave();
    },

    async reset(): Promise<void> {
      this.settings = defaultSettings();
      settingsRevision += 1;
      await this.saveNow();
    },

    clearError(): void {
      this.error = '';
    },

    reconcileSelections(): boolean {
      let changed = false;
      for (const [key, orientation] of [
        ['landscape_wallpaper_id', 'landscape'],
        ['portrait_wallpaper_id', 'portrait'],
      ] as const) {
        const wallpaperId = this.settings[key];
        if (!wallpaperId) continue;
        const wallpaper = this.wallpapers.find(
          (candidate) => candidate.id === wallpaperId,
        );
        if (
          !wallpaper ||
          (wallpaper.orientation !== orientation &&
            wallpaper.orientation !== 'both')
        ) {
          this.settings = { ...this.settings, [key]: '' };
          changed = true;
        }
      }
      if (changed) settingsRevision += 1;
      return changed;
    },

    setupChannel(): void {
      if (channel || typeof BroadcastChannel === 'undefined') return;
      channel = new BroadcastChannel(CHANNEL_NAME);
      channel.onmessage = (event: MessageEvent) => {
        const message = event.data as {
          type?: string;
          settings?: AppearanceSettings;
        };
        if (message.type === 'settings' && message.settings) {
          applyingRemote = true;
          try {
            this.settings = normalizeSettings(message.settings);
            settingsRevision += 1;
          } finally {
            applyingRemote = false;
          }
        } else if (message.type === 'wallpapers') {
          void this.loadWallpapers();
        }
      };
    },

    broadcastSettings(): void {
      if (applyingRemote) return;
      channel?.postMessage({
        type: 'settings',
        settings: { ...this.settings },
      });
    },

    broadcastWallpapers(): void {
      channel?.postMessage({ type: 'wallpapers' });
    },
  },
});
