import type {
  ChatRecord,
  HistoryRecord,
  MessagePart,
  StreamPayload,
} from '@/domain/chat';
import { messageContent } from './messageContent';
import {
  appendCompletePlainSuffix,
  appendPlain,
  appendReasoningPart,
  finishToolCall,
  isRecord,
  markMessageStarted,
  parseJsonSafe,
  payloadText,
  upsertToolCall,
} from './messageRecordMutations';
import type { ActiveConnection } from './messagesTypes';

interface StreamPayloadDeps {
  activeConnections: Record<string, ActiveConnection>;
  getRecords: (sessionId: string) => ChatRecord[];
  resolvePartMedia: (part: MessagePart) => Promise<void>;
  resolveRecordMedia: (records: ChatRecord[]) => Promise<void>;
  normalizeHistoryRecord: (record: HistoryRecord) => ChatRecord;
  clearWebChatStepUpTokens: () => void;
}

const MEDIA_STREAM_TYPES = new Set(['image', 'record', 'file', 'video']);

export function createStreamPayloadHandlers(deps: StreamPayloadDeps) {
  function resolveInsertionAnchor(
    connection: ActiveConnection,
    records: ChatRecord[],
  ) {
    let insertionAnchor = connection.deferredBeforeBot;
    if (!insertionAnchor) return insertionAnchor;
    for (const candidate of Object.values(deps.activeConnections)) {
      if (candidate.messageId === connection.messageId) break;
      if (
        candidate.sessionId === connection.sessionId &&
        candidate.deferredBeforeBot === connection.deferredBeforeBot &&
        candidate.botVisible &&
        candidate.botRecord &&
        records.includes(candidate.botRecord)
      ) {
        insertionAnchor = candidate.botRecord;
      }
    }
    return insertionAnchor;
  }

  function ensureBotRecordVisible(connection: ActiveConnection) {
    const { botRecord, userRecord } = connection;
    if (!botRecord) return;
    const records = deps.getRecords(connection.sessionId);
    if (records.includes(botRecord)) {
      connection.botVisible = true;
      return;
    }
    if (!userRecord) return;

    const userIndex = records.indexOf(userRecord);
    const insertionAnchor = resolveInsertionAnchor(connection, records);
    const anchorIndex = insertionAnchor ? records.indexOf(insertionAnchor) : -1;
    if (anchorIndex >= 0) {
      records.splice(anchorIndex + 1, 0, botRecord);
    } else if (userIndex >= 0) {
      records.splice(userIndex + 1, 0, botRecord);
    } else {
      records.push(botRecord);
    }
    connection.botVisible = true;
  }

  function applyFollowUpCaptured(connection: ActiveConnection, data: unknown) {
    const followUpData = isRecord(data) ? data : {};
    connection.followUpCaptured = true;
    connection.followUpTargetRunId = String(followUpData.target_run_id || '');
    const target = Object.values(deps.activeConnections).find(
      (candidate) =>
        candidate.runId === connection.followUpTargetRunId &&
        candidate.botRecord,
    );
    const records = deps.getRecords(connection.sessionId);
    if (!target?.botRecord || !connection.userRecord) return;
    const userIndex = records.indexOf(connection.userRecord);
    const targetIndex = records.indexOf(target.botRecord);
    if (targetIndex >= 0) {
      if (userIndex > targetIndex) {
        records.splice(userIndex, 1);
        const updatedTargetIndex = records.indexOf(target.botRecord);
        records.splice(updatedTargetIndex, 0, connection.userRecord);
      } else if (userIndex < 0) {
        records.splice(targetIndex, 0, connection.userRecord);
      }
      connection.deferredBeforeBot = target.botRecord;
    } else if (userIndex < 0) {
      records.push(connection.userRecord);
    }
  }

  function applyRunStarted(connection: ActiveConnection, data: unknown) {
    deps.clearWebChatStepUpTokens();
    const runData = isRecord(data) ? data : {};
    connection.runId = String(runData.run_id || connection.messageId);
    ensureBotRecordVisible(connection);
  }

  function applyRunSnapshot(botRecord: ChatRecord, data: unknown) {
    const snapshot = isRecord(data) ? data : {};
    const snapshotContent = isRecord(snapshot.content)
      ? snapshot.content
      : { type: 'bot', message: [] };
    const snapshotRecord = deps.normalizeHistoryRecord({
      id: `active-run-${String(snapshot.run_id || 'unknown')}`,
      content: {
        type:
          typeof snapshotContent.type === 'string'
            ? snapshotContent.type
            : 'bot',
        message: snapshotContent.message,
        reasoning:
          typeof snapshotContent.reasoning === 'string'
            ? snapshotContent.reasoning
            : undefined,
        agentStats: isRecord(snapshotContent.agentStats)
          ? snapshotContent.agentStats
          : null,
        agent_stats: isRecord(snapshotContent.agent_stats)
          ? snapshotContent.agent_stats
          : null,
        refs: isRecord(snapshotContent.refs) ? snapshotContent.refs : null,
      },
      llm_checkpoint_id:
        typeof snapshot.llm_checkpoint_id === 'string'
          ? snapshot.llm_checkpoint_id
          : null,
    });
    snapshotRecord.content.isLoading =
      snapshot.status === 'running' &&
      snapshotRecord.content.message.length === 0;
    botRecord.content = snapshotRecord.content;
    botRecord.llm_checkpoint_id = snapshotRecord.llm_checkpoint_id;
    void deps.resolveRecordMedia([botRecord]);
  }

  function applySavedRecordFields(
    record: ChatRecord,
    savedMessage: Record<string, unknown> | null,
  ) {
    if (
      typeof savedMessage?.id === 'string' ||
      typeof savedMessage?.id === 'number'
    ) {
      record.id = savedMessage.id;
    }
    if (typeof savedMessage?.created_at === 'string') {
      record.created_at = savedMessage.created_at;
    }
    record.llm_checkpoint_id =
      typeof savedMessage?.llm_checkpoint_id === 'string'
        ? savedMessage.llm_checkpoint_id
        : record.llm_checkpoint_id;
  }

  function applyUserMessageSaved(
    userRecord: ChatRecord | undefined,
    data: unknown,
  ) {
    if (!userRecord) return;
    applySavedRecordFields(userRecord, isRecord(data) ? data : null);
  }

  function applyMessageSaved(botRecord: ChatRecord, data: unknown) {
    const savedMessage = isRecord(data) ? data : null;
    markMessageStarted(botRecord);
    applySavedRecordFields(botRecord, savedMessage);
    if (isRecord(savedMessage?.refs)) {
      messageContent(botRecord).refs = savedMessage.refs;
    }
  }

  function applyPlainStreamPart(
    botRecord: ChatRecord,
    data: unknown,
    chainType: string | undefined,
    streaming: boolean | undefined,
  ) {
    markMessageStarted(botRecord);
    if (chainType === 'reasoning') {
      appendReasoningPart(botRecord, payloadText(data));
      return;
    }
    if (chainType === 'tool_call') {
      upsertToolCall(botRecord, parseJsonSafe(data));
      return;
    }
    if (chainType === 'tool_call_result') {
      finishToolCall(botRecord, parseJsonSafe(data));
      return;
    }
    appendPlain(botRecord, payloadText(data), streaming !== false);
  }

  function applyMediaStreamPart(
    botRecord: ChatRecord,
    msgType: string,
    data: unknown,
  ) {
    markMessageStarted(botRecord);
    const rawFilename = String(data)
      .replace('[IMAGE]', '')
      .replace('[RECORD]', '')
      .replace('[FILE]', '')
      .replace('[VIDEO]', '');
    const separatorIndex = rawFilename.indexOf('|');
    const storedFilename =
      separatorIndex >= 0 ? rawFilename.slice(0, separatorIndex) : rawFilename;
    const displayFilename =
      separatorIndex >= 0
        ? rawFilename.slice(separatorIndex + 1)
        : storedFilename;
    const filename = displayFilename || storedFilename;
    const mediaPart: MessagePart = { type: msgType, filename };
    if (storedFilename && storedFilename !== filename) {
      mediaPart.stored_filename = storedFilename;
    }
    if (msgType === 'file') {
      messageContent(botRecord).message.push(mediaPart);
      return;
    }
    void deps
      .resolvePartMedia(mediaPart)
      .then(() => {
        messageContent(botRecord).message.push(mediaPart);
      })
      .catch((error: unknown) => {
        console.error('Failed to resolve streamed media:', error);
      });
  }

  function applyContentStreamPart(
    botRecord: ChatRecord,
    msgType: string | undefined,
    chainType: string | undefined,
    data: unknown,
    streaming: boolean | undefined,
  ): boolean {
    if (msgType === 'agent_stats' || chainType === 'agent_stats') {
      markMessageStarted(botRecord);
      messageContent(botRecord).agentStats = isRecord(data) ? data : null;
      return true;
    }
    if (msgType === 'error') {
      markMessageStarted(botRecord);
      appendPlain(botRecord, `\n\n${String(data)}`);
      return true;
    }
    if (msgType === 'complete' || msgType === 'break') {
      markMessageStarted(botRecord);
      appendCompletePlainSuffix(
        botRecord,
        payloadText(data),
        msgType === 'complete',
      );
      return true;
    }
    if (msgType === 'end') {
      markMessageStarted(botRecord);
      return true;
    }
    if (msgType === 'plain') {
      applyPlainStreamPart(botRecord, data, chainType, streaming);
      return true;
    }
    if (msgType && MEDIA_STREAM_TYPES.has(msgType)) {
      applyMediaStreamPart(botRecord, msgType, data);
      return true;
    }
    return false;
  }

  function processStreamPayload(
    botRecord: ChatRecord,
    payload: StreamPayload,
    userRecord?: ChatRecord,
    connection?: ActiveConnection,
  ) {
    const normalized: StreamPayload =
      payload?.ct === 'chat'
        ? { ...payload, type: payload.type || payload.t }
        : payload;
    const msgType = normalized?.type || normalized?.t;
    const chainType = normalized?.chain_type;
    const data = normalized?.data ?? '';

    if (msgType === 'follow_up_captured') {
      if (connection) applyFollowUpCaptured(connection, data);
      return;
    }
    if (msgType === 'run_started') {
      if (connection) applyRunStarted(connection, data);
      return;
    }
    if (msgType === 'session_id' || msgType === 'session_bound') return;
    if (connection && msgType !== 'user_message_saved' && msgType !== 'end') {
      ensureBotRecordVisible(connection);
    }
    if (msgType === 'run_snapshot') {
      applyRunSnapshot(botRecord, data);
      return;
    }
    if (msgType === 'user_message_saved') {
      applyUserMessageSaved(userRecord, data);
      return;
    }
    if (msgType === 'message_saved') {
      applyMessageSaved(botRecord, data);
      return;
    }
    applyContentStreamPart(
      botRecord,
      msgType,
      chainType,
      data,
      normalized.streaming,
    );
  }

  return {
    processStreamPayload,
    ensureBotRecordVisible,
  };
}
