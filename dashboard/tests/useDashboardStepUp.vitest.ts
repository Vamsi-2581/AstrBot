import { flushPromises } from '@vue/test-utils';
import { defineComponent } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  stepUp: vi.fn(),
  webChatStepUp: vi.fn(),
}));

vi.mock('@/api/v1/authorization', () => ({
  STEP_UP_TTL_SECONDS: 300,
  authorizationApi: api,
}));

import { useDashboardStepUp } from '@/composables/useDashboardStepUp';
import { mountWithVuetify } from './utils/mountWithVuetify';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

const Host = defineComponent({
  setup() {
    return useDashboardStepUp();
  },
  template: '<div />',
});

describe('useDashboardStepUp request generations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('ignores a late response from a cancelled request', async () => {
    const first = deferred<unknown>();
    const second = deferred<unknown>();
    api.stepUp
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);
    const wrapper = mountWithVuetify(Host);
    const targetA = {
      action: 'provider.manage',
      resourceType: 'provider',
      resourceId: 'a',
    };
    const targetB = {
      action: 'provider.manage',
      resourceType: 'provider',
      resourceId: 'b',
    };

    const promiseA = wrapper.vm.requestStepUp(targetA);
    const submitA = wrapper.vm.submitStepUp({ password: 'secret' });
    await flushPromises();
    wrapper.vm.cancelStepUp();
    await expect(promiseA).resolves.toBeNull();

    const promiseB = wrapper.vm.requestStepUp(targetB);
    const submitB = wrapper.vm.submitStepUp({ password: 'secret' });
    await flushPromises();

    first.resolve({ data: { data: { token: 'token-a' } } });
    await submitA;
    await flushPromises();
    expect(wrapper.vm.target).toEqual(targetB);

    let resolvedB: string | null = null;
    void promiseB.then((token) => {
      resolvedB = token;
    });
    await flushPromises();
    expect(resolvedB).toBeNull();

    second.resolve({ data: { data: { token: 'token-b' } } });
    await submitB;
    await expect(promiseB).resolves.toBe('token-b');
    wrapper.unmount();
  });

  it('does not apply a previous WebChat session token to a new session', async () => {
    const first = deferred<unknown>();
    const second = deferred<unknown>();
    api.webChatStepUp
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);
    const wrapper = mountWithVuetify(Host);

    const promiseA = wrapper.vm.requestWebChatStepUp('session-a');
    const submitA = wrapper.vm.submitStepUp({ password: 'secret' });
    await flushPromises();
    wrapper.vm.cancelStepUp();
    await expect(promiseA).resolves.toBeNull();

    const promiseB = wrapper.vm.requestWebChatStepUp('session-b');
    const submitB = wrapper.vm.submitStepUp({ password: 'secret' });
    await flushPromises();

    first.resolve({ data: { data: { tokens: { 'webchat.tool_run': 'a' } } } });
    await submitA;
    await flushPromises();
    expect(wrapper.vm.webChatExpiresAt).toBeNull();
    expect(wrapper.vm.target?.resourceId).toBe('session-b');

    second.resolve({ data: { data: { tokens: { 'webchat.tool_run': 'b' } } } });
    await submitB;
    await expect(promiseB).resolves.toEqual({ 'webchat.tool_run': 'b' });
    wrapper.unmount();
  });
});
