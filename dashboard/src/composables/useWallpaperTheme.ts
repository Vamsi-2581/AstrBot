import { onScopeDispose, watch, type Ref } from 'vue';
import { useTheme } from 'vuetify';

import type { AppearanceWallpaper } from '@/api/v1';
import { applyUserThemeColors, defaultThemeColors } from '@/design/theme';

const PREVIOUS_KEY = 'astrbot:appearance:theme-previous:v1';

type ThemePair = {
  primary: string;
  secondary: string;
};

type ThemeSnapshot = Record<string, ThemePair>;

function readStoredTheme(): ThemePair | null {
  try {
    const primary = localStorage.getItem('themePrimary');
    const secondary = localStorage.getItem('themeSecondary');
    if (!primary && !secondary) return null;
    return {
      primary: primary || defaultThemeColors.primary,
      secondary: secondary || defaultThemeColors.secondary,
    };
  } catch {
    return null;
  }
}

function isThemePair(value: unknown): value is ThemePair {
  if (typeof value !== 'object' || value === null) return false;
  const pair = value as Partial<ThemePair>;
  return typeof pair.primary === 'string' && typeof pair.secondary === 'string';
}

function readPrevious(): ThemeSnapshot | null {
  try {
    const raw = localStorage.getItem(PREVIOUS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (typeof parsed !== 'object' || parsed === null) return null;
    const snapshot: ThemeSnapshot = {};
    for (const [name, pair] of Object.entries(parsed)) {
      if (isThemePair(pair)) snapshot[name] = pair;
    }
    return Object.keys(snapshot).length > 0 ? snapshot : null;
  } catch {
    return null;
  }
}

function writePrevious(value: ThemeSnapshot): void {
  try {
    localStorage.setItem(PREVIOUS_KEY, JSON.stringify(value));
  } catch {
    // Theme restoration remains best-effort when storage is unavailable.
  }
}

function removePrevious(): void {
  try {
    localStorage.removeItem(PREVIOUS_KEY);
  } catch {
    // Theme restoration remains best-effort when storage is unavailable.
  }
}

export function useWallpaperTheme(
  wallpaper: Ref<AppearanceWallpaper | null>,
  enabled: Ref<boolean>,
): void {
  const theme = useTheme();
  let previous = readPrevious();

  function captureTheme(): ThemeSnapshot {
    const snapshot: ThemeSnapshot = {};
    for (const [name, definition] of Object.entries(theme.themes.value)) {
      const colors = definition.colors;
      snapshot[name] = {
        primary:
          typeof colors?.primary === 'string'
            ? colors.primary
            : defaultThemeColors.primary,
        secondary:
          typeof colors?.secondary === 'string'
            ? colors.secondary
            : defaultThemeColors.secondary,
      };
    }
    return snapshot;
  }

  function apply(wallpaperValue: AppearanceWallpaper): void {
    if (!previous) {
      // Capture the user's theme per variant before the wallpaper colours
      // replace it. The custom theme keys stay untouched so Settings keeps
      // showing the user's own selection while auto theming is active.
      previous = captureTheme();
      writePrevious(previous);
    }
    applyUserThemeColors(
      theme.themes.value,
      wallpaperValue.theme_primary,
      wallpaperValue.theme_secondary,
    );
  }

  function restore(): void {
    if (!previous) return;
    const stored = readStoredTheme();
    if (stored) {
      applyUserThemeColors(
        theme.themes.value,
        stored.primary,
        stored.secondary,
      );
    } else {
      for (const [name, pair] of Object.entries(previous)) {
        const definition = theme.themes.value[name];
        if (!definition?.colors) continue;
        definition.colors.primary = pair.primary;
        definition.colors.secondary = pair.secondary;
      }
    }
    previous = null;
    removePrevious();
  }

  watch(
    [wallpaper, enabled],
    ([wallpaperValue, isEnabled]) => {
      if (isEnabled && wallpaperValue) {
        apply(wallpaperValue);
        return;
      }
      restore();
    },
    { immediate: true },
  );

  onScopeDispose(restore);
}
