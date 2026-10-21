import type { AxiosRequestConfig } from 'axios';

import { httpClient } from './shared';
import type { V1Response } from './shared';
import type {
  AppearanceOrientation,
  AppearanceSettings,
  AppearanceWallpaper,
  AppearanceWallpaperListData,
} from './types';

export const appearanceApi = {
  getSettings(): V1Response<AppearanceSettings> {
    return httpClient.get('/api/v1/appearance/settings');
  },
  updateSettings(settings: AppearanceSettings): V1Response<AppearanceSettings> {
    return httpClient.put('/api/v1/appearance/settings', settings);
  },
  list(
    orientation?: AppearanceOrientation,
  ): V1Response<AppearanceWallpaperListData> {
    return httpClient.get('/api/v1/appearance/wallpapers', {
      params: orientation ? { orientation } : undefined,
    });
  },
  upload(
    file: File,
    orientation: AppearanceOrientation,
    config?: AxiosRequestConfig,
  ): V1Response<AppearanceWallpaper> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('orientation', orientation);
    return httpClient.post('/api/v1/appearance/wallpapers', formData, config);
  },
  delete(wallpaperId: string): V1Response<{ id: string }> {
    return httpClient.delete(
      `/api/v1/appearance/wallpapers/${encodeURIComponent(wallpaperId)}`,
    );
  },
  imageUrl(wallpaperId: string): string {
    return `/api/v1/appearance/wallpapers/${encodeURIComponent(wallpaperId)}`;
  },
  thumbnailUrl(wallpaperId: string): string {
    return `/api/v1/appearance/wallpapers/${encodeURIComponent(wallpaperId)}/thumbnail`;
  },
};
