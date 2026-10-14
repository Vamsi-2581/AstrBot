import type { UmoInfoData } from '@/api/v1';

export const FOLLOW_CONFIG_VALUE = '__astrbot_follow_config__';
export const FOLLOW_SESSION_VALUE = '__astrbot_follow_session__';

export type SnackbarColor = 'success' | 'error';
export type GroupDialogMode = 'create' | 'edit';
export type ProviderRuleType =
  'chat_completion' | 'speech_to_text' | 'text_to_speech';
export type ApiBatchScope = 'all' | 'group' | 'private' | 'custom_group';
export type RuleTargetType = 'session' | 'sender';

export type RuleKey =
  | 'session_service_config'
  | 'session_plugin_config'
  | 'kb_config'
  | `provider_perf_${ProviderRuleType}`;

export type BatchScope = 'selected' | ApiBatchScope | `custom_group:${string}`;

export interface ProviderOption {
  id: string;
  name: string;
  model?: string;
}

export interface PromptOption {
  name: string;
}

export interface PluginOption {
  name: string;
  display_name?: string;
}

export interface KnowledgeBaseOption {
  kb_id: string;
  kb_name: string;
  emoji?: string | null;
}

export interface SessionServiceConfig {
  session_enabled?: boolean;
  llm_enabled?: boolean;
  tts_enabled?: boolean;
  session_blocked?: boolean;
  blocked?: boolean;
  custom_name?: string;
  prompt_id?: string | null;
  [key: string]: unknown;
}

export interface SessionPluginConfig {
  enabled_plugins?: string[];
  disabled_plugins?: string[];
  [key: string]: unknown;
}

export interface SessionKbConfig {
  kb_ids?: string[];
  top_k?: number;
  enable_rerank?: boolean;
  [key: string]: unknown;
}

export interface SessionRuleSet {
  session_service_config?: SessionServiceConfig;
  session_plugin_config?: SessionPluginConfig;
  kb_config?: SessionKbConfig;
  provider_perf_chat_completion?: string;
  provider_perf_speech_to_text?: string;
  provider_perf_text_to_speech?: string;
  [key: string]: unknown;
}

export interface SessionRuleItem extends UmoInfoData {
  umo: string;
  sender_id?: string;
  target_type?: RuleTargetType;
  rules: SessionRuleSet;
}

export interface GroupItem {
  id: string;
  name: string;
  umos: string[];
  umo_count: number;
}

export interface GroupEditorState {
  id: string | null;
  name: string;
  umos: string[];
}

export interface SelectOption<T> {
  label: string;
  value: T;
  disabled?: boolean;
}

export interface TableOptionsLike {
  page?: number;
  itemsPerPage?: number;
}

export interface UmoDisplayInfo {
  umo: string;
  platform: string;
  message_type: string;
  session_id: string;
  auto_name: string;
  user_alias: string;
  display_name: string;
  rules?: SessionRuleSet;
}

export interface DebouncedCallback {
  (): void;
  cancel: () => void;
}

export interface SessionTableHeader {
  title: string;
  key: string;
  sortable: boolean;
  minWidth: string;
}

export interface SenderOverlayState {
  blocked: boolean;
  llm_enabled: boolean | null;
}
