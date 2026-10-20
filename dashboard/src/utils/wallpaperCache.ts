const CACHE_NAME = 'astrbot-wallpapers-v1';
const CACHE_PREFIX = '/api/v1/appearance/wallpapers/';

function cacheKey(wallpaperId: string, variant: string): string {
  const suffix = variant ? `:${variant}` : '';
  return `${CACHE_PREFIX}${encodeURIComponent(wallpaperId)}${suffix}`;
}

async function openCache(): Promise<Cache | null> {
  if (typeof caches === 'undefined') return null;
  try {
    return await caches.open(CACHE_NAME);
  } catch {
    return null;
  }
}

export async function readWallpaperCache(
  wallpaperId: string,
  variant = '',
): Promise<Blob | null> {
  const cache = await openCache();
  if (!cache) return null;
  try {
    const response = await cache.match(cacheKey(wallpaperId, variant));
    return response ? await response.blob() : null;
  } catch {
    return null;
  }
}

export async function writeWallpaperCache(
  wallpaperId: string,
  response: Response,
  variant = '',
): Promise<void> {
  if (!response.ok) return;
  const cache = await openCache();
  if (!cache) return;
  try {
    await cache.put(cacheKey(wallpaperId, variant), response.clone());
  } catch {
    // Cache is best-effort. Playback still works from the in-memory blob.
  }
}

export async function deleteWallpaperCache(wallpaperId: string): Promise<void> {
  const cache = await openCache();
  if (!cache) return;
  try {
    await Promise.all([
      cache.delete(cacheKey(wallpaperId, '')),
      cache.delete(cacheKey(wallpaperId, 'still')),
    ]);
  } catch {
    // A missing cache entry must not block wallpaper deletion.
  }
}

export async function pruneWallpaperCache(
  wallpaperIds: Iterable<string>,
): Promise<void> {
  const cache = await openCache();
  if (!cache) return;
  const valid = new Set(wallpaperIds);
  try {
    const requests = await cache.keys();
    await Promise.all(
      requests.map(async (request) => {
        const pathname = new URL(request.url).pathname;
        const match =
          /\/appearance\/wallpapers\/([0-9a-f]{32})(?::(?:still))?$/.exec(
            pathname,
          );
        if (match && !valid.has(match[1])) await cache.delete(request);
      }),
    );
  } catch {
    // Cache maintenance must not block loading the wallpaper library.
  }
}
