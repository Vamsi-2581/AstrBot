import type {
  ChatContent,
  ChatRecord,
  ChatSessionProject,
  MessageDisplayBlock,
  MessagePart,
} from '@/domain/chat';

export function normalizeMessageParts(
  parts: unknown,
  fallbackReasoning = '',
): MessagePart[] {
  const normalizedParts = normalizePartsInternal(parts);
  if (
    fallbackReasoning &&
    !normalizedParts.some((part) => part.type === 'think')
  ) {
    normalizedParts.unshift({ type: 'think', think: fallbackReasoning });
  }
  return normalizedParts;
}

export function extractReasoningText(
  parts: MessagePart[] | unknown,
  fallbackReasoning = '',
) {
  const normalizedParts = Array.isArray(parts)
    ? parts
    : normalizeMessageParts(parts, fallbackReasoning);
  const text = normalizedParts
    .filter((part) => part.type === 'think')
    .map((part) => String(part.think || ''))
    .join('');
  return text || fallbackReasoning;
}

export function reasoningActivityCounts(
  parts: MessagePart[] | unknown,
  fallbackReasoning = '',
) {
  const normalizedParts = Array.isArray(parts)
    ? parts
    : normalizeMessageParts(parts, fallbackReasoning);
  let thinkCount = 0;
  let toolCount = 0;

  for (const part of normalizedParts) {
    if (part.type === 'think' && String(part.think || '').trim()) {
      thinkCount += 1;
    }
    if (part.type === 'tool_call' && Array.isArray(part.tool_calls)) {
      toolCount += part.tool_calls.length;
    }
  }

  return { thinkCount, toolCount };
}

export function reasoningActivityTitle(
  counts: ReturnType<typeof reasoningActivityCounts>,
  tm: (key: string, params?: Record<string, string | number>) => string,
) {
  return (
    [
      counts.thinkCount > 0
        ? tm('reasoning.thinkSummary', { count: counts.thinkCount })
        : '',
      counts.toolCount > 0
        ? tm('reasoning.toolSummary', { count: counts.toolCount })
        : '',
    ]
      .filter(Boolean)
      .join(tm('reasoning.summarySeparator')) || tm('reasoning.thinking')
  );
}

export function thinkingParts(content: ChatContent): MessagePart[] {
  const firstThinkingBlock = messageBlocks(content).find(
    (block) => block.kind === 'thinking',
  );
  if (firstThinkingBlock) return firstThinkingBlock.parts;

  const fallbackReasoning = String(content.reasoning || '');
  return fallbackReasoning ? [{ type: 'think', think: fallbackReasoning }] : [];
}

export function displayParts(content: ChatContent): MessagePart[] {
  return messageBlocks(content)
    .filter((block) => block.kind === 'content')
    .flatMap((block) => block.parts);
}

function pushBlock(
  blocks: MessageDisplayBlock[],
  kind: MessageDisplayBlock['kind'] | null,
  parts: MessagePart[],
) {
  if (kind && parts.length) {
    blocks.push({ kind, parts });
  }
}

export function messageBlocks(content: ChatContent): MessageDisplayBlock[] {
  const parts = Array.isArray(content.message)
    ? content.message
    : normalizeMessageParts(content.message, content.reasoning || '');

  const blocks: MessageDisplayBlock[] = [];
  let currentKind: MessageDisplayBlock['kind'] | null = null;
  let currentParts: MessagePart[] = [];

  for (const part of parts) {
    if (isEmptyPlainPart(part)) continue;

    const nextKind: MessageDisplayBlock['kind'] = isThinkingPart(part)
      ? 'thinking'
      : 'content';

    if (currentKind !== nextKind) {
      pushBlock(blocks, currentKind, currentParts);
      currentKind = nextKind;
      currentParts = [{ ...part }];
      continue;
    }

    currentParts.push({ ...part });
  }

  pushBlock(blocks, currentKind, currentParts);

  if (!blocks.length && content.reasoning) {
    return [
      {
        kind: 'thinking',
        parts: [{ type: 'think', think: String(content.reasoning) }],
      },
    ];
  }

  return blocks;
}

export function partToPayload(part: MessagePart) {
  if (part.type === 'plain') return { type: 'plain', text: part.text || '' };
  if (part.type === 'reply') {
    return {
      type: 'reply',
      message_id: part.message_id,
      selected_text: part.selected_text || '',
    };
  }
  return {
    type: part.type,
    attachment_id: part.attachment_id,
    filename: part.filename,
  };
}

function normalizePartsInternal(parts: unknown): MessagePart[] {
  if (typeof parts === 'string') {
    return parts ? [{ type: 'plain', text: parts }] : [];
  }
  if (!Array.isArray(parts)) return [];
  return parts.map((part): MessagePart => {
    if (!part || typeof part !== 'object') {
      return { type: 'plain', text: String(part ?? '') };
    }
    const record = part as Record<string, unknown>;
    if (record.type === 'reasoning') {
      return {
        ...record,
        type: 'think',
        think: String(record.think ?? record.text ?? ''),
      };
    }
    return {
      ...record,
      type: typeof record.type === 'string' ? record.type : 'plain',
    };
  });
}

function isEmptyPlainPart(part: MessagePart) {
  return part.type === 'plain' && !String(part.text || '');
}

function isThinkingPart(part: MessagePart) {
  return part.type === 'think' || part.type === 'tool_call';
}

export function normalizeSessionProject(
  value: unknown,
): ChatSessionProject | null {
  if (!value || typeof value !== 'object') return null;
  const project = value as Record<string, unknown>;
  if (
    typeof project.project_id !== 'string' ||
    typeof project.title !== 'string'
  ) {
    return null;
  }

  return {
    project_id: project.project_id,
    title: project.title,
    emoji: typeof project.emoji === 'string' ? project.emoji : undefined,
  };
}

export function stripUploadOnlyFields(part: MessagePart): MessagePart {
  const copied = { ...part };
  delete copied.path;
  return copied;
}

export function cloneContentWithEditedText(
  record: ChatRecord,
  editedText: string,
): ChatContent {
  const content = record.content || { type: 'bot', message: [] };
  const message = Array.isArray(content.message)
    ? content.message.map((part) => ({ ...part }))
    : [];
  let replaced = false;
  for (const part of message) {
    if (part.type === 'plain') {
      part.text = editedText;
      replaced = true;
      break;
    }
  }
  if (!replaced && editedText) {
    message.push({ type: 'plain', text: editedText });
  }
  return {
    ...content,
    message,
  };
}

export function messageContent(msg: ChatRecord): ChatContent {
  return msg.content || { type: 'bot', message: [] };
}

export function messageParts(msg: ChatRecord): MessagePart[] {
  const parts = messageContent(msg).message;
  if (Array.isArray(parts)) return parts;
  if (typeof parts === 'string') return [{ type: 'plain', text: parts }];
  return [];
}

export function isUserMessage(msg: ChatRecord) {
  return messageContent(msg).type === 'user';
}
