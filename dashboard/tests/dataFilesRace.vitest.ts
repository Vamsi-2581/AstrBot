import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  tree: vi.fn(),
  content: vi.fn(),
  metadata: vi.fn(),
  save: vi.fn(),
  download: vi.fn(),
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
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
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

describe('DataFilesPage stale failures', () => {
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

  it('does not surface an older failure for the newly selected file', async () => {
    const first = deferred<unknown>();
    api.content.mockImplementation((path: string) =>
      path === 'a.txt'
        ? first.promise
        : Promise.resolve({
            data: {
              data: {
                content: 'second file',
                etag: 'etag-b',
                writable: true,
              },
            },
          }),
    );
    const wrapper = mountWithVuetify(DataFilesPage);
    await flushPromises();

    await wrapper.find('button[aria-label="a.txt"]').trigger('click');
    await flushPromises();
    await wrapper.find('button[aria-label="b.txt"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('.editor-value').text()).toBe('second file');

    first.reject(new Error('stale failure'));
    await flushPromises();

    expect(wrapper.find('.editor-value').text()).toBe('second file');
    expect(wrapper.find('.v-alert').exists()).toBe(false);
    wrapper.unmount();
  });
});

describe('DataFilesPage unmount races', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0);
      return 0;
    });
    api.tree.mockResolvedValue({
      data: {
        data: {
          entries: [
            {
              ...file('a.png'),
              category: 'image',
              language: null,
              downloadable: true,
              mime_type: 'image/png',
            },
          ],
        },
      },
    });
  });

  it('does not create a preview after the page unmounts', async () => {
    const pending = deferred<unknown>();
    api.download.mockReturnValue(pending.promise);
    const createObjectURL = vi.fn(() => 'blob:stale');
    const original = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    });
    try {
      const wrapper = mountWithVuetify(DataFilesPage);
      await flushPromises();

      await wrapper.find('button[aria-label="a.png"]').trigger('click');
      await flushPromises();
      wrapper.unmount();

      pending.resolve({ data: new Blob(['stale'], { type: 'image/png' }) });
      await flushPromises();

      expect(api.download).toHaveBeenCalled();
      expect(createObjectURL).not.toHaveBeenCalled();
    } finally {
      if (original) {
        Object.defineProperty(URL, 'createObjectURL', original);
      } else {
        Reflect.deleteProperty(URL, 'createObjectURL');
      }
    }
  });
});
