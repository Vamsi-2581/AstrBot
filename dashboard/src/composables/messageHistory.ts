import type { BranchGroup, ChatRecord, ChatThread } from '@/domain/chat';

function numericRecordId(id: ChatRecord['id']): number | null {
  if (id === undefined || id === null || id === '') return null;
  const value = typeof id === 'number' ? id : Number(id);
  return Number.isFinite(value) ? value : null;
}

export function mergeHistoryRecords(
  existing: ChatRecord[],
  incoming: ChatRecord[],
): ChatRecord[] {
  const merged = [...existing];
  for (const record of incoming) {
    if (record.id !== undefined && record.id !== null) {
      const previous = merged.find(
        (item) => String(item.id) === String(record.id),
      );
      if (previous) {
        Object.assign(previous, record);
        continue;
      }
    }
    const incomingId = numericRecordId(record.id);
    if (incomingId === null) {
      merged.push(record);
      continue;
    }
    const insertAt = merged.findIndex((item) => {
      const otherId = numericRecordId(item.id);
      return otherId !== null && otherId > incomingId;
    });
    if (insertAt < 0) merged.push(record);
    else merged.splice(insertAt, 0, record);
  }
  return merged;
}

export function normalizeBranchGroup(value: unknown): BranchGroup | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const raw = value as Record<string, unknown>;
  const groupId = raw.group_id;
  const index = raw.index;
  const total = raw.total;
  if (
    typeof groupId !== 'string' ||
    typeof index !== 'number' ||
    typeof total !== 'number'
  ) {
    return undefined;
  }
  return {
    group_id: groupId,
    index,
    total,
    provider: typeof raw.provider === 'string' ? raw.provider : undefined,
    model: typeof raw.model === 'string' ? raw.model : undefined,
  };
}

export function attachThreads(records: ChatRecord[], threads: ChatThread[]) {
  const threadsByMessage = new Map<string, ChatThread[]>();
  for (const thread of threads) {
    const key = String(thread.parent_message_id);
    const list = threadsByMessage.get(key) || [];
    list.push(thread);
    threadsByMessage.set(key, list);
  }
  for (const record of records) {
    const key =
      record.id === undefined || record.id === null ? '' : String(record.id);
    record.threads = threadsByMessage.get(key) || [];
  }
}
