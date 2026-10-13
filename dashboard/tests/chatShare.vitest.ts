import { beforeEach, describe, expect, it, vi } from 'vitest';

const generated = vi.hoisted(() => ({
  createChatShare: vi.fn(),
  listChatShares: vi.fn(),
  revokeChatShare: vi.fn(),
  getSharedConversation: vi.fn(),
}));

vi.mock('@/api/v1/shared', () => ({
  generatedQuery: (params: unknown) => params,
  typed: (response: unknown) => response,
  openApiV1: generated,
}));

import { chatApi } from '@/api/v1/chat';

describe('chat share api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a share with the selected expiry', async () => {
    generated.createChatShare.mockResolvedValue({
      data: { data: { share_id: 'share-1', token: 'token-1' } },
    });

    const response = await chatApi.createShare('sess-1', 30);

    expect(generated.createChatShare).toHaveBeenCalledWith({
      path: { session_id: 'sess-1' },
      body: { expires_in_days: 30 },
    });
    expect(response.data.data?.share_id).toBe('share-1');
  });

  it('lists shares for a session', async () => {
    generated.listChatShares.mockResolvedValue({
      data: { data: { shares: [] } },
    });

    const response = await chatApi.listShares('sess-1');

    expect(generated.listChatShares).toHaveBeenCalledWith({
      path: { session_id: 'sess-1' },
    });
    expect(response.data.data?.shares).toEqual([]);
  });

  it('revokes a share', async () => {
    generated.revokeChatShare.mockResolvedValue({ data: { data: {} } });

    await chatApi.revokeShare('share-1');

    expect(generated.revokeChatShare).toHaveBeenCalledWith({
      path: { share_id: 'share-1' },
    });
  });

  it('reads a shared transcript without auth state', async () => {
    generated.getSharedConversation.mockResolvedValue({
      data: { data: { title: 'Shared', messages: [] } },
    });

    const response = await chatApi.getSharedConversation('token-1');

    expect(generated.getSharedConversation).toHaveBeenCalledWith({
      path: { token: 'token-1' },
    });
    expect(response.data.data?.title).toBe('Shared');
  });
});
