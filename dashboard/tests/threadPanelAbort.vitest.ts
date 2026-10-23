import { flushPromises } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  getThread: vi.fn(),
  sendThreadMessageUrl: vi.fn(() => '/threads/thread-1/messages'),
}));
const http = vi.hoisted(() => ({ fetchWithAuth: vi.fn() }));

vi.mock('@/api/v1', () => ({ chatApi: api }));
vi.mock('@/api/http', () => ({
  fetchWithAuth: http.fetchWithAuth,
}));
vi.mock('@/components/chat/ChatMessageList.vue', () => ({
  default: {
    props: ['messages'],
    template:
      '<div class="chat-message-list-stub">{{ JSON.stringify(messages) }}</div>',
  },
}));

import ThreadPanel from '@/components/chat/ThreadPanel.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

function thread(threadId: string) {
  return { thread_id: threadId, selected_text: 'Selected' };
}

function abortableResponse() {
  return new Promise((_resolve, reject) => {
    http.fetchWithAuth.mock.calls
      .at(-1)?.[1]
      ?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError')),
      );
  });
}

describe('ThreadPanel abort handling', () => {
  it('aborts an active stream when the panel closes', async () => {
    api.getThread.mockResolvedValue({ data: { data: { history: [] } } });
    http.fetchWithAuth.mockImplementation(() => abortableResponse());
    const wrapper = mountWithVuetify(ThreadPanel, {
      props: { modelValue: true, thread: thread('thread-1'), isDark: false },
    });
    await flushPromises();

    await wrapper.find('.thread-input').setValue('Question');
    await wrapper.find('.thread-composer').trigger('submit');
    await flushPromises();
    const signal = http.fetchWithAuth.mock.calls[0]?.[1]?.signal as AbortSignal;
    expect(signal.aborted).toBe(false);

    await wrapper
      .find('.thread-panel-actions button:last-of-type')
      .trigger('click');
    await flushPromises();

    expect(signal.aborted).toBe(true);
    expect(wrapper.text()).not.toContain('Aborted');
    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
    wrapper.unmount();
  });

  it('aborts when the selected thread changes', async () => {
    api.getThread.mockResolvedValue({ data: { data: { history: [] } } });
    http.fetchWithAuth.mockImplementation(() => abortableResponse());
    const wrapper = mountWithVuetify(ThreadPanel, {
      props: { modelValue: true, thread: thread('thread-1'), isDark: false },
    });
    await flushPromises();
    await wrapper.find('.thread-input').setValue('Question');
    await wrapper.find('.thread-composer').trigger('submit');
    await flushPromises();
    const signal = http.fetchWithAuth.mock.calls[0]?.[1]?.signal as AbortSignal;

    await wrapper.setProps({ thread: thread('thread-2') });
    await flushPromises();

    expect(signal.aborted).toBe(true);
    wrapper.unmount();
  });
});

describe('ThreadPanel reopen handling', () => {
  it('reloads the thread when the panel is reopened', async () => {
    api.getThread.mockClear();
    api.getThread.mockResolvedValue({ data: { data: { history: [] } } });
    const wrapper = mountWithVuetify(ThreadPanel, {
      props: { modelValue: true, thread: thread('thread-1'), isDark: false },
    });
    await flushPromises();
    expect(api.getThread).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ modelValue: false });
    await wrapper.setProps({ modelValue: true });
    await flushPromises();

    expect(api.getThread).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });
});
