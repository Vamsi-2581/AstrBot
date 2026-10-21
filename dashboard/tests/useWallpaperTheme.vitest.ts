import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { defineComponent, h, nextTick, ref } from 'vue';

import type { AppearanceWallpaper } from '@/api/v1';
import { useWallpaperTheme } from '@/composables/useWallpaperTheme';
import { themeNames } from '@/design/theme';
import vuetify from '@/plugins/vuetify';
import { mountWithVuetify } from './utils/mountWithVuetify';

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
  theme_primary: '#112233',
  theme_secondary: '#445566',
  image_url: `/api/v1/appearance/wallpapers/${'a'.repeat(32)}`,
  thumbnail_url: `/api/v1/appearance/wallpapers/${'a'.repeat(32)}/thumbnail`,
} satisfies AppearanceWallpaper;

const themes = vuetify.theme.themes.value;
const themeSnapshots = Object.fromEntries(
  Object.values(themeNames).map((name) => [name, { ...themes[name].colors }]),
);

function themeColors(name: (typeof themeNames)[keyof typeof themeNames]) {
  return {
    primary: themes[name].colors.primary,
    secondary: themes[name].colors.secondary,
  };
}

function mountHost() {
  const selected = ref<AppearanceWallpaper | null>(null);
  const enabled = ref(false);
  const Host = defineComponent({
    setup() {
      useWallpaperTheme(selected, enabled);
      return () => h('div');
    },
  });
  const wrapper = mountWithVuetify(Host);
  return { wrapper, selected, enabled };
}

beforeEach(() => {
  localStorage.clear();
  for (const name of Object.values(themeNames)) {
    Object.assign(themes[name].colors, themeSnapshots[name]);
  }
});

afterEach(() => {
  for (const name of Object.values(themeNames)) {
    Object.assign(themes[name].colors, themeSnapshots[name]);
  }
  localStorage.clear();
});

describe('useWallpaperTheme', () => {
  it('leaves theme colors untouched while auto theming is disabled', () => {
    const before = themeColors(themeNames.dark);
    const { wrapper } = mountHost();

    expect(themeColors(themeNames.dark)).toEqual(before);
    wrapper.unmount();
  });

  it('applies wallpaper colors and restores the user colors afterwards', async () => {
    localStorage.setItem('themePrimary', '#abcdef');
    localStorage.setItem('themeSecondary', '#fedcba');

    const { wrapper, selected, enabled } = mountHost();
    selected.value = wallpaper;
    enabled.value = true;
    await nextTick();

    for (const name of Object.values(themeNames)) {
      expect(themeColors(name)).toEqual({
        primary: wallpaper.theme_primary,
        secondary: wallpaper.theme_secondary,
      });
    }
    expect(localStorage.getItem('themePrimary')).toBe('#abcdef');
    expect(localStorage.getItem('themeSecondary')).toBe('#fedcba');

    enabled.value = false;
    await nextTick();

    for (const name of Object.values(themeNames)) {
      expect(themeColors(name)).toEqual({
        primary: '#abcdef',
        secondary: '#fedcba',
      });
    }
    wrapper.unmount();
  });

  it('restores the original colors when the user had no custom theme', async () => {
    const { wrapper, selected, enabled } = mountHost();
    selected.value = wallpaper;
    enabled.value = true;
    await nextTick();

    expect(themeColors(themeNames.light).primary).toBe(wallpaper.theme_primary);

    enabled.value = false;
    await nextTick();

    for (const name of Object.values(themeNames)) {
      expect(themeColors(name)).toEqual({
        primary: themeSnapshots[name].primary,
        secondary: themeSnapshots[name].secondary,
      });
    }
    wrapper.unmount();
  });
});
