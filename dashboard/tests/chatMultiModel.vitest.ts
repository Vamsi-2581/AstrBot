import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';

const generated = vi.hoisted(() => ({ getChatFeatures: vi.fn() }));

vi.mock('@/api/v1', () => ({
  chatApi: {},
  fileApi: {},
}));
vi.mock('@/api/v1/shared', () => ({
  generatedQuery: (params: unknown) => params,
  typed: (response: unknown) => response,
  openApiV1: generated,
}));
vi.mock('@/api/http', () => ({ fetchWithAuth: vi.fn() }));

import { chatApi } from '@/api/v1/chat';
import { useMessages } from '@/composables/useMessages';
import type { ChatRecord } from '@/domain/chat';

describe('multi-model chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('reads chat feature flags', async () => {
    generated.getChatFeatures.mockResolvedValue({
      data: { data: { multi_model: { enable: true, max_models: 4 } } },
    });

    const response = await chatApi.getFeatures();

    expect(generated.getChatFeatures).toHaveBeenCalled();
    expect(response.data.data?.multi_model).toEqual({
      enable: true,
      max_models: 4,
    });
  });

  it('shows only the selected branch record', () => {
    const currentSessionId = ref('s1');
    const messages = useMessages({ currentSessionId });
    const records: ChatRecord[] = [
      { id: 1, content: { type: 'user', message: [] } },
      {
        id: 2,
        content: { type: 'bot', message: [] },
        branchGroup: { group_id: 'g', index: 0, total: 2 },
      },
      {
        id: 3,
        content: { type: 'bot', message: [] },
        branchGroup: { group_id: 'g', index: 1, total: 2 },
      },
    ];
    messages.messagesBySession.set('s1', records);

    expect(messages.activeMessages.value.map((record) => record.id)).toEqual([
      1, 2,
    ]);

    messages.setBranchSelection('g', 1);
    expect(messages.activeMessages.value.map((record) => record.id)).toEqual([
      1, 3,
    ]);
  });

  it('creates branch records and registers labels', () => {
    const currentSessionId = ref('s1');
    const messages = useMessages({ currentSessionId });
    messages.messagesBySession.set('s1', []);

    const record = messages.createLocalBranchRecord('s1', 'm1', {
      group_id: 'g',
      index: 1,
      total: 2,
      provider: 'openai',
      model: 'gpt-4o',
    });

    expect(record.branchGroup?.index).toBe(1);
    expect(messages.branchLabels.get('g')?.[1]).toBe('gpt-4o');
  });
});
