import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/v1', () => ({
  logApi: { liveUrl: () => '/api/v1/log/live' },
}));
vi.mock('@/api/http', () => ({
  fetchWithAuth: vi.fn(),
}));

import { fetchWithAuth } from '@/api/http';
import { useCommonStore } from '@/stores/common';

function sseResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk));
        }
        controller.close();
      },
    }),
    { status: 200 },
  );
}

describe('live log SSE parsing', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('token', 'token');
  });

  it('parses named events, multi-line data, and data without a space', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValue(
      sseResponse([
        'id: 1\ndata:{"uuid":"one","data":"first"}\n\n',
        'id: 2\ndata: {"uuid":"two",\ndata: "data":"second"}\n\n',
      ]),
    );
    const common = useCommonStore();

    await common.createEventSource();
    await vi.waitFor(() => expect(common.getLogCache()).toHaveLength(2));

    expect(common.getLogCache().map((entry) => entry.uuid)).toEqual([
      'one',
      'two',
    ]);
    expect(common.getLogCache()[1]?.data).toBe('second');
    common.closeEventSource();
  });
});
