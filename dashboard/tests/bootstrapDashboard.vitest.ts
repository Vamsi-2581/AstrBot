import { describe, expect, it, vi } from 'vitest';
import { bootstrapDashboard } from '@/bootstrapDashboard';

function fakeApp() {
  const app = {
    use: vi.fn(() => app),
    mount: vi.fn(),
  };
  return app;
}

function dependencies() {
  const app = fakeApp();
  return {
    app,
    deps: {
      setupI18n: vi.fn().mockResolvedValue(undefined),
      createApp: vi.fn(() => app),
      createPinia: vi.fn(() => ({}) as never),
      router: { isReady: vi.fn().mockResolvedValue(undefined) },
      vuetify: {},
      confirmPlugin: {},
      setupThemeSync: vi.fn(),
    },
  };
}

describe('bootstrapDashboard', () => {
  it('mounts once when i18n initialization fails', async () => {
    const { app, deps } = dependencies();
    deps.setupI18n.mockRejectedValue(new Error('i18n failed'));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});

    await bootstrapDashboard(deps);

    expect(deps.createApp).toHaveBeenCalledTimes(1);
    expect(app.mount).toHaveBeenCalledTimes(1);
    expect(deps.setupThemeSync).toHaveBeenCalledTimes(1);
  });

  it('does not create a second app when mounting fails', async () => {
    const { app, deps } = dependencies();
    deps.router.isReady.mockRejectedValue(new Error('route failed'));

    await expect(bootstrapDashboard(deps)).rejects.toThrow('route failed');

    expect(deps.createApp).toHaveBeenCalledTimes(1);
    expect(app.mount).not.toHaveBeenCalled();
  });
});
