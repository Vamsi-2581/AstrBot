import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  deleteWallpaperCache,
  pruneWallpaperCache,
  readWallpaperCache,
  writeWallpaperCache,
} from '@/utils/wallpaperCache';

const cacheStore = new Map<string, Response>();

const cacheMock = {
  match: vi.fn(async (key: string) => cacheStore.get(key)),
  put: vi.fn(async (key: string, response: Response) => {
    cacheStore.set(key, response);
  }),
  delete: vi.fn(async (key: string | Request) =>
    cacheStore.delete(
      typeof key === 'string' ? key : new URL(key.url).pathname,
    ),
  ),
  keys: vi.fn(async () =>
    Array.from(cacheStore.keys()).map(
      (key) => new Request(`https://dashboard.test${key}`),
    ),
  ),
};

const openMock = vi.fn(async () => cacheMock);

beforeEach(() => {
  cacheStore.clear();
  vi.clearAllMocks();
  Object.defineProperty(globalThis, 'caches', {
    configurable: true,
    value: { open: openMock },
  });
});

describe('wallpaper cache', () => {
  it('stores and reads full-size and still variants separately', async () => {
    const full = new Response('full');
    const still = new Response('still');

    await writeWallpaperCache('a'.repeat(32), full);
    await writeWallpaperCache('a'.repeat(32), still, 'still');

    expect(await (await readWallpaperCache('a'.repeat(32)))?.text()).toBe(
      'full',
    );
    expect(
      await (await readWallpaperCache('a'.repeat(32), 'still'))?.text(),
    ).toBe('still');
  });

  it('removes both variants when a wallpaper is deleted', async () => {
    await writeWallpaperCache('a'.repeat(32), new Response('full'));
    await writeWallpaperCache('a'.repeat(32), new Response('still'), 'still');

    await deleteWallpaperCache('a'.repeat(32));

    expect(cacheStore.size).toBe(0);
  });

  it('prunes entries for wallpapers that no longer exist', async () => {
    await writeWallpaperCache('a'.repeat(32), new Response('a'));
    await writeWallpaperCache('b'.repeat(32), new Response('b'));
    await writeWallpaperCache('b'.repeat(32), new Response('still'), 'still');

    await pruneWallpaperCache(['a'.repeat(32)]);

    expect(cacheStore.size).toBe(1);
    expect(
      await (await readWallpaperCache('b'.repeat(32)))?.text(),
    ).toBeUndefined();
  });

  it('falls back when the cache API is unavailable', async () => {
    Object.defineProperty(globalThis, 'caches', {
      configurable: true,
      value: undefined,
    });

    expect(await readWallpaperCache('a'.repeat(32))).toBeNull();
    await expect(
      writeWallpaperCache('a'.repeat(32), new Response('x')),
    ).resolves.toBeUndefined();
  });
});
