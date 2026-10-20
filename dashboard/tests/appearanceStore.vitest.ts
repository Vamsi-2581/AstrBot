import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { flushPromises } from '@vue/test-utils';

import { useAppearanceStore } from '@/stores/appearance';

const api = vi.hoisted(() => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
  list: vi.fn(),
  upload: vi.fn(),
  delete: vi.fn(),
}));

const cache = vi.hoisted(() => ({
  deleteWallpaperCache: vi.fn(),
  pruneWallpaperCache: vi.fn(),
}));

vi.mock('@/api/v1', () => ({
  appearanceApi: api,
}));

vi.mock('@/utils/wallpaperCache', () => cache);

const defaultSettings = {
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
};

const wallpaper = {
  id: 'a'.repeat(32),
  content_type: 'image/png',
  width: 640,
  height: 360,
  orientation: 'landscape',
  original_name: 'wallpaper.png',
  created_at: '2026-01-01T00:00:00+00:00',
  size_bytes: 1024,
  animated: false,
  theme_primary: '#336699',
  theme_secondary: '#224466',
  image_url: `/api/v1/appearance/wallpapers/${'a'.repeat(32)}`,
  thumbnail_url: `/api/v1/appearance/wallpapers/${'a'.repeat(32)}/thumbnail`,
};

function ok<T>(data: T) {
  return { data: { status: 'ok', data } };
}

describe('appearance store', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.clearAllMocks();
    setActivePinia(createPinia());
    api.getSettings.mockResolvedValue(ok(defaultSettings));
    api.updateSettings.mockImplementation((settings) =>
      Promise.resolve(ok(settings)),
    );
    api.list.mockResolvedValue(ok({ items: [] }));
    cache.deleteWallpaperCache.mockResolvedValue(undefined);
    cache.pruneWallpaperCache.mockResolvedValue(undefined);
  });

  it('hydrates server settings and separated wallpaper libraries', async () => {
    const portrait = {
      ...wallpaper,
      id: 'b'.repeat(32),
      orientation: 'portrait',
    };
    api.list.mockResolvedValue(ok({ items: [wallpaper, portrait] }));

    const store = useAppearanceStore();
    await store.hydrate();

    expect(store.loaded).toBe(true);
    expect(store.wallpapers).toHaveLength(2);
    expect(store.wallpapersFor('landscape').map((item) => item.id)).toEqual([
      wallpaper.id,
    ]);
    expect(store.wallpapersFor('portrait').map((item) => item.id)).toEqual([
      portrait.id,
    ]);
  });

  it('selects a wallpaper and saves the selection after the debounce', async () => {
    const store = useAppearanceStore();
    store.wallpapers = [wallpaper];
    store.selectWallpaper('landscape', wallpaper.id);

    expect(store.settings.enabled).toBe(true);
    expect(store.settings.landscape_wallpaper_id).toBe(wallpaper.id);

    await vi.advanceTimersByTimeAsync(350);
    await flushPromises();

    expect(api.updateSettings).toHaveBeenCalledWith(
      expect.objectContaining({
        enabled: true,
        landscape_wallpaper_id: wallpaper.id,
      }),
    );
  });

  it('clears a selection that no longer exists on the server', async () => {
    const store = useAppearanceStore();
    store.settings = {
      ...defaultSettings,
      enabled: true,
      landscape_wallpaper_id: 'c'.repeat(32),
    };
    store.wallpapers = [wallpaper];

    expect(store.reconcileSelections()).toBe(true);
    expect(store.settings.landscape_wallpaper_id).toBe('');
  });

  it('removes a wallpaper, clears its selection, and drops its cache', async () => {
    api.delete.mockResolvedValue(ok({ id: wallpaper.id }));
    const store = useAppearanceStore();
    store.wallpapers = [wallpaper];
    store.settings = {
      ...defaultSettings,
      enabled: true,
      landscape_wallpaper_id: wallpaper.id,
    };

    await store.removeWallpaper(wallpaper.id);

    expect(api.delete).toHaveBeenCalledWith(wallpaper.id);
    expect(store.wallpapers).toEqual([]);
    expect(store.settings.landscape_wallpaper_id).toBe('');
    expect(cache.deleteWallpaperCache).toHaveBeenCalledWith(wallpaper.id);
  });

  it('rejects files above the upload limit before calling the API', async () => {
    const store = useAppearanceStore();
    const file = {
      size: 33 * 1024 * 1024,
      type: 'image/png',
    } as File;

    await expect(store.uploadWallpaper(file, 'landscape')).rejects.toThrow(
      '32 MiB',
    );
    expect(api.upload).not.toHaveBeenCalled();
  });

  it('picks a random wallpaper without repeating the current one', () => {
    const other = { ...wallpaper, id: 'd'.repeat(32) };
    const store = useAppearanceStore();
    store.wallpapers = [wallpaper, other];
    store.settings = {
      ...defaultSettings,
      landscape_wallpaper_id: wallpaper.id,
    };

    const selected = store.selectRandom('landscape');

    expect(selected?.id).toBe(other.id);
    expect(store.settings.landscape_wallpaper_id).toBe(other.id);
  });

  it('keeps newer local edits when an older save response arrives late', async () => {
    let resolveFirstSave: (value: unknown) => void = () => undefined;
    api.updateSettings
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirstSave = resolve;
          }),
      )
      .mockImplementation((settings) => Promise.resolve(ok(settings)));

    const store = useAppearanceStore();
    store.settings = { ...defaultSettings };
    store.update({ blur: 4 });
    const pendingSave = store.saveNow();
    store.update({ blur: 9 });

    resolveFirstSave(ok({ ...defaultSettings, blur: 4 }));
    await pendingSave;

    expect(store.settings.blur).toBe(9);
  });

  it('serializes saves so a delayed older request cannot replace a newer one', async () => {
    let resolveFirst: (value: unknown) => void = () => undefined;
    let resolveSecond: (value: unknown) => void = () => undefined;
    api.updateSettings
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          }),
      );

    const store = useAppearanceStore();
    store.settings = { ...defaultSettings };
    store.update({ blur: 4 });
    const first = store.saveNow();
    store.update({ enabled: true });
    const second = store.saveNow();

    await flushPromises();
    expect(api.updateSettings).toHaveBeenCalledTimes(1);

    resolveFirst(ok({ ...defaultSettings, blur: 4 }));
    await first;
    await flushPromises();
    expect(api.updateSettings).toHaveBeenCalledTimes(2);
    expect(api.updateSettings.mock.calls[1][0]).toMatchObject({
      enabled: true,
      blur: 4,
    });

    resolveSecond(ok({ ...defaultSettings, enabled: true, blur: 4 }));
    await second;
  });

  it('migrates legacy browser settings once and removes the key', async () => {
    localStorage.setItem(
      'astrbot:appearance:v1',
      JSON.stringify({ enabled: true, blur: 12, surfaceOpacity: 0.5 }),
    );

    const store = useAppearanceStore();
    await store.hydrate();

    expect(store.settings.enabled).toBe(true);
    expect(store.settings.blur).toBe(12);
    expect(store.settings.surface_opacity).toBe(0.5);
    expect(localStorage.getItem('astrbot:appearance:v1')).toBeNull();
    expect(api.updateSettings).toHaveBeenCalled();
  });

  it('does not reapply legacy settings over server settings', async () => {
    localStorage.setItem(
      'astrbot:appearance:v1',
      JSON.stringify({ enabled: true, blur: 12 }),
    );
    api.getSettings.mockResolvedValue(ok({ ...defaultSettings, blur: 20 }));

    const store = useAppearanceStore();
    await store.hydrate();

    expect(store.settings.blur).toBe(20);
    expect(localStorage.getItem('astrbot:appearance:v1')).toBeNull();
    expect(api.updateSettings).not.toHaveBeenCalled();
  });
});
