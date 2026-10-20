import { watch, type Ref } from 'vue';
import { useTheme } from 'vuetify';

import type { AppearanceWallpaper } from '@/api/v1';
import { applyUserThemeColors, defaultThemeColors } from '@/design/theme';

const PREVIOUS_KEY = 'astrbot:appearance:theme-previous:v1';

type ThemePair = {
  primary: string;
  secondary: string;
};

function readPrevious(): ThemePair | null {
  try {
    const raw = localStorage.getItem(PREVIOUS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ThemePair>;
    if (
      typeof parsed.primary !== 'string' ||
      typeof parsed.secondary !== 'string'
    ) {
      return null;
    }
    return { primary: parsed.primary, secondary: parsed.secondary };
  } catch {
    return null;
  }
}

function writePrevious(value: ThemePair): void {
  try {
    localStorage.setItem(PREVIOUS_KEY, JSON.stringify(value));
  } catch {
    // Theme restoration remains best-effort when storage is unavailable.
  }
}

function currentThemePair(): ThemePair {
  try {
    return {
      primary:
        localStorage.getItem('themePrimary') || defaultThemeColors.primary,
      secondary:
        localStorage.getItem('themeSecondary') || defaultThemeColors.secondary,
    };
  } catch {
    return { ...defaultThemeColors };
  }
}

export function useWallpaperTheme(
  wallpaper: Ref<AppearanceWallpaper | null>,
  enabled: Ref<boolean>,
): void {
  const theme = useTheme();
  let previous = readPrevious();

  function apply(wallpaperValue: AppearanceWallpaper): void {
    if (!previous) {
      previous = currentThemePair();
      writePrevious(previous);
    }
    try {
      localStorage.setItem('themePrimary', wallpaperValue.theme_primary);
      localStorage.setItem('themeSecondary', wallpaperValue.theme_secondary);
    } catch {
      // Applying the Vuetify theme still works when storage is unavailable.
    }
    applyUserThemeColors(
      theme.themes.value,
      wallpaperValue.theme_primary,
      wallpaperValue.theme_secondary,
    );
  }

  function restore(): void {
    const pair = previous ?? currentThemePair();
    try {
      localStorage.setItem('themePrimary', pair.primary);
      localStorage.setItem('themeSecondary', pair.secondary);
    } catch {
      // Storage restoration is best-effort.
    }
    applyUserThemeColors(theme.themes.value, pair.primary, pair.secondary);
    previous = null;
    try {
      localStorage.removeItem(PREVIOUS_KEY);
    } catch {
      // Storage cleanup is best-effort.
    }
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
}
