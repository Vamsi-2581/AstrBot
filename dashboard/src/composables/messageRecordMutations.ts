import type { ChatRecord, ToolCall } from '@/domain/chat';
import { extractReasoningText } from './messageContent';

export function appendPlain(record: ChatRecord, text: string, append = true) {
  markMessageStarted(record);
  const content = record.content;
  let last = content.message[content.message.length - 1];
  if (last?.type !== 'plain') {
    last = { type: 'plain', text: '' };
    content.message.push(last);
  }
  last.text = append ? `${last.text || ''}${text}` : text;
}

export function appendReasoningPart(record: ChatRecord, text: string) {
  markMessageStarted(record);
  if (!text) return;
  const content = record.content;
  const last = content.message[content.message.length - 1];
  if (last?.type === 'think') {
    last.think = `${String(last.think || '')}${text}`;
  } else {
    content.message.push({ type: 'think', think: text });
  }
  content.reasoning = extractReasoningText(content.message);
}

export function upsertToolCall(record: ChatRecord, value: unknown) {
  markMessageStarted(record);
  if (!isRecord(value)) return;
  const toolCall: ToolCall = { ...value };
  const targetId = toolCall.id;
  if (targetId !== undefined && targetId !== null) {
    for (const part of record.content.message) {
      if (part.type !== 'tool_call' || !Array.isArray(part.tool_calls))
        continue;
      const matched = part.tool_calls.find((item) => item.id === targetId);
      if (matched) {
        Object.assign(matched, toolCall);
        return;
      }
    }
  }
  record.content.message.push({
    type: 'tool_call',
    tool_calls: [{ ...toolCall }],
  });
}

export function finishToolCall(record: ChatRecord, value: unknown) {
  markMessageStarted(record);
  if (!isRecord(value)) return;
  const result: ToolCall = { ...value };
  const targetId = result.id;
  for (const part of record.content.message) {
    if (part.type !== 'tool_call' || !Array.isArray(part.tool_calls)) continue;
    const tool = part.tool_calls.find((item) => item.id === targetId);
    if (tool) {
      tool.result = result.result;
      tool.finished_ts = result.ts ?? Date.now() / 1000;
      return;
    }
  }
  record.content.message.push({
    type: 'tool_call',
    tool_calls: [
      {
        id: targetId,
        result: result.result,
        finished_ts: result.ts ?? Date.now() / 1000,
      },
    ],
  });
}

export function markMessageStarted(record: ChatRecord) {
  record.content.isLoading = false;
}

export function hasPlainText(record: ChatRecord) {
  return record.content.message.some(
    (part) =>
      part.type === 'plain' && typeof part.text === 'string' && part.text,
  );
}

/**
 * Restores a suffix omitted from streamed plain-text chunks when completion
 * carries the cumulative response text.
 */
export function appendCompletePlainSuffix(
  record: ChatRecord,
  finalText: string,
  appendSuffix = true,
) {
  if (!finalText) return;
  if (!hasPlainText(record)) {
    appendPlain(record, finalText, false);
    return;
  }
  if (!appendSuffix) return;

  const streamedText = record.content.message
    .filter((part) => part.type === 'plain')
    .map((part) => (typeof part.text === 'string' ? part.text : ''))
    .join('');
  if (!finalText.startsWith(streamedText)) return;

  const suffix = finalText.slice(streamedText.length);
  if (suffix) appendPlain(record, suffix);
}

export function payloadText(value: unknown) {
  if (typeof value === 'string') return value;
  if (value === undefined || value === null) return '';
  if (typeof value === 'object') {
    const payload = value as Record<string, unknown>;
    if (typeof payload.text === 'string') return payload.text;
    if (typeof payload.content === 'string') return payload.content;
    if (typeof payload.message === 'string') return payload.message;
  }
  return String(value);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function parseJsonSafe(value: unknown) {
  if (typeof value !== 'string') return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}
