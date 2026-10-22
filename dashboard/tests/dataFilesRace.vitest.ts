import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  tree: vi.fn(),
  content: vi.fn(),
  metadata: vi.fn(),
  save: vi.fn(),
}));

vi.mock('@/api/v1', () => ({ dataFilesApi: api }));
vi.mock('@/components/shared/LazyMonacoEditor', () => ({
  LazyMonacoEditor: {
    props: ['value'],
    template: '<div class="editor-value">{{ value }}</div>',
  },
}));
vi.mock('vue-router', async () => {
  const actual =
    await vi.importActual<typeof import('vue-router')>('vue-router');
  return {
    ...actual,
    useRoute: () => ({ query: {} }),
    useRouter: () => ({ replace: vi.fn().mockResolvedValue(undefined) }),
    onBeforeRouteLeave: vi.fn(),
  };
});

import DataFilesPage from '@/views/DataFilesPage.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function file(name: string) {
  return {
    name,
    path: name,
    type: 'file',
    readable: true,
    writable: true,
    downloadable: false,
    deletable: true,
    category: 'text',
    language: 'text',
    size: 1,
  };
}

describe('DataFilesPage selection races', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0);
      return 0;
    });
    api.tree.mockResolvedValue({
      data: { data: { entries: [file('a.txt'), file('b.txt')] } },
    });
  });

  it('does not apply an older file response to the newly selected file', async () => {
    const first = deferred<unknown>();
    const second = deferred<unknown>();
    api.content.mockImplementation((path: string) =>
      path === 'a.txt' ? first.promise : second.promise,
    );
    const wrapper = mountWithVuetify(DataFilesPage);
    await flushPromises();

    await wrapper.find('button[aria-label="a.txt"]').trigger('click');
    await flushPromises();
    await wrapper.find('button[aria-label="b.txt"]').trigger('click');
    await flushPromises();

    second.resolve({
      data: {
        data: { content: 'second file', etag: 'etag-b', writable: true },
      },
    });
    await flushPromises();
    first.resolve({
      data: { data: { content: 'first file', etag: 'etag-a', writable: true } },
    });
    await flushPromises();

    expect(wrapper.find('.editor-value').text()).toBe('second file');
    expect(wrapper.text()).toContain('b.txt');
    wrapper.unmount();
  });
});
