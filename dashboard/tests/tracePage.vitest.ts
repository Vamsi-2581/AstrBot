import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TracePage from '@/views/TracePage.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

const api = vi.hoisted(() => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
}));

vi.mock('@/api/v1', () => ({
  traceApi: api,
}));

vi.mock('@/components/shared/TraceDisplayer.vue', () => ({
  default: {
    props: ['recordingEnabled', 'recordingBusy'],
    emits: ['toggle-recording'],
    template:
      '<button data-testid="trace-displayer" :data-recording="String(recordingEnabled)" @click="$emit(\'toggle-recording\')">toggle</button>',
  },
}));

describe('TracePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSettings.mockResolvedValue({
      data: { status: 'ok', data: { enabled: true } },
    });
  });

  it('reflects the setting supplied during initialization', async () => {
    const wrapper = mountWithVuetify(TracePage);
    await flushPromises();

    expect(api.getSettings).toHaveBeenCalledOnce();
    expect(
      wrapper
        .find('[data-testid="trace-displayer"]')
        .attributes('data-recording'),
    ).toBe('true');
  });

  it('submits the next recording state and keeps the previous value on failure', async () => {
    api.updateSettings.mockResolvedValue({
      data: { status: 'error', message: 'rejected' },
    });
    const wrapper = mountWithVuetify(TracePage);
    await flushPromises();

    await wrapper.get('[data-testid="trace-displayer"]').trigger('click');
    await flushPromises();

    expect(api.updateSettings).toHaveBeenCalledWith({ enabled: false });
    expect(
      wrapper
        .find('[data-testid="trace-displayer"]')
        .attributes('data-recording'),
    ).toBe('true');
  });
});
