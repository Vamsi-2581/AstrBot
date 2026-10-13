import type { Ref } from 'vue';
import type {
  BranchGroup,
  ChatContent,
  ChatRecord,
  MessagePart,
  StreamPayload,
} from '@/domain/chat';

export type TransportMode = 'sse' | 'websocket';

export interface ActiveChatRun {
  run_id: string;
  session_id: string;
  llm_checkpoint_id?: string | null;
  status?: string;
  revision?: number;
  content?: ChatContent;
}

export interface ActiveConnection {
  sessionId: string;
  messageId: string;
  runId?: string;
  transport: TransportMode;
  abort?: AbortController;
  ws?: WebSocket;
  botRecord?: ChatRecord;
  userRecord?: ChatRecord;
  completed?: boolean;
  errorShown?: boolean;
  botVisible?: boolean;
  deferredBeforeBot?: ChatRecord;
  followUpCaptured?: boolean;
  followUpTargetRunId?: string;
}

export interface SendMessageStreamOptions {
  sessionId: string;
  messageId: string;
  parts: MessagePart[];
  transport: TransportMode;
  enableStreaming?: boolean;
  enableReasoning?: boolean;
  selectedProvider?: string;
  selectedModel?: string;
  userRecord?: ChatRecord;
  botRecord: ChatRecord;
  skipUserHistory?: boolean;
  llmCheckpointId?: string | null;
  branch?: BranchGroup;
}

export interface ContinueEditedMessageOptions {
  sessionId: string;
  sourceRecord: ChatRecord;
  enableStreaming?: boolean;
  enableReasoning?: boolean;
  selectedProvider?: string;
  selectedModel?: string;
}

export interface CreateLocalExchangeOptions {
  sessionId: string;
  messageId: string;
  parts: MessagePart[];
}

export interface UseMessagesOptions {
  currentSessionId: Ref<string>;
  webchatStepUpTokens?: Ref<Record<string, string> | null>;
  onSessionsChanged?: () => Promise<void> | void;
  onStreamUpdate?: (sessionId: string) => void;
  onMcpInputRequest?: (
    payload: StreamPayload,
    respond: (response: Record<string, unknown>) => void,
  ) => void;
}

export interface HistoryPaginationState {
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
  loading: boolean;
  error?: string;
}
