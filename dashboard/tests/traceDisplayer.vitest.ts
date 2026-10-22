import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TraceDisplayer from '@/components/shared/TraceDisplayer.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

const state = vi.hoisted(() => ({
  history: vi.fn(),
  plugins: vi.fn(),
  sessions: vi.fn(),
  sources: [] as Array<{
    close: ReturnType<typeof vi.fn>;
    onerror: (() => void) | null;
  }>,
}));

vi.mock('@/api/v1', () => ({
  logApi: {
    liveUrl: () => '/api/v1/logs/live',
  },
  traceApi: {
    history: state.history,
    detail: vi.fn(),
  },
  pluginApi: {
    getAll: state.plugins,
  },
  sessionApi: {
    activeUmos: state.sessions,
  },
}));

vi.mock('event-source-polyfill', () => ({
  EventSourcePolyfill: class {
    close = vi.fn();
    onerror: (() => void) | null = null;

    constructor() {
      state.sources.push(this);
    }
  },
}));

describe('TraceDisplayer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    state.sources.splice(0);
    state.history.mockResolvedValue({
      data: {
        status: 'ok',
        data: { traces: [], total: 0, page: 1, storage: {} },
      },
    });
    state.plugins.mockResolvedValue({ data: { data: [] } });
    state.sessions.mockResolvedValue({ data: { data: { umo_infos: [] } } });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('cancels a scheduled SSE reconnect when the displayer is unmounted', async () => {
    vi.useFakeTimers();
    const wrapper = mountWithVuetify(TraceDisplayer);
    await flushPromises();

    expect(state.history).toHaveBeenCalled();
    expect(state.sources).toHaveLength(1);

    state.sources[0]!.onerror?.();
    expect(state.sources[0]!.close).toHaveBeenCalledOnce();

    wrapper.unmount();
    await vi.runAllTimersAsync();

    expect(state.sources).toHaveLength(1);
  });

  it('renders table chrome from the trace catalog', async () => {
    const wrapper = mountWithVuetify(TraceDisplayer);
    await flushPromises();

    expect(wrapper.text()).toContain('Status');
    expect(wrapper.text()).toContain('Platform');
    expect(wrapper.text()).toContain('Timestamp');
    expect(wrapper.text()).toContain('Message');
    expect(wrapper.text()).toContain('UMO');
    expect(wrapper.text()).toContain('Sender');
    expect(wrapper.text()).toContain('Spans');
    expect(wrapper.text()).toContain('No trace data yet');
  });
});
