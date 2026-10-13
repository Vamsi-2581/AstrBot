import type { DynamicConfig, UmoListRequest } from '@/api/generated/openapi-v1';
import type {
  BatchScope,
  GroupItem,
  KnowledgeBaseOption,
  PluginOption,
  PromptOption,
  ProviderOption,
  ProviderRuleType,
  SessionKbConfig,
  SessionPluginConfig,
  SessionRuleItem,
  SessionRuleSet,
  SessionServiceConfig,
  UmoDisplayInfo,
} from './sessionRuleHelpers';

export function normalizeString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

export function normalizeStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

export function normalizeBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

export function isWebchatScope(scopeId: string): boolean {
  const entry = scopeId.trim();
  if (!entry) {
    return false;
  }
  if (entry.startsWith('session:')) {
    return entry.split(':')[1] === 'webchat';
  }
  const separator = entry.indexOf(':');
  return separator > 0 && entry.slice(0, separator) === 'webchat';
}

export function unwrittenServiceEnabled(scopeId: string): boolean {
  return Boolean(scopeId) && isWebchatScope(scopeId);
}

export function normalizeNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function normalizeProviderOption(raw: unknown): ProviderOption | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  const id = normalizeString(source.id);
  const name = normalizeString(source.name);
  if (!id || !name) {
    return null;
  }

  return {
    id,
    name,
    model: normalizeString(source.model) || undefined,
  };
}

export function normalizePromptOption(raw: unknown): PromptOption | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  const name = normalizeString(source.name);
  return name ? { name } : null;
}

export function normalizePluginOption(raw: unknown): PluginOption | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  const name = normalizeString(source.name);
  if (!name) {
    return null;
  }

  return {
    name,
    display_name: normalizeString(source.display_name) || undefined,
  };
}

export function normalizeKnowledgeBaseOption(
  raw: unknown,
): KnowledgeBaseOption | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  const kbId = normalizeString(source.kb_id);
  const kbName = normalizeString(source.kb_name);
  if (!kbId || !kbName) {
    return null;
  }

  return {
    kb_id: kbId,
    kb_name: kbName,
    emoji: normalizeString(source.emoji) || null,
  };
}

export function normalizeSessionServiceConfig(
  raw: unknown,
  umo = '',
): SessionServiceConfig {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  const source = raw as Record<string, unknown>;
  const fallback = unwrittenServiceEnabled(umo);
  return {
    ...source,
    session_enabled: normalizeBoolean(source.session_enabled, fallback),
    llm_enabled: normalizeBoolean(source.llm_enabled, fallback),
    tts_enabled: normalizeBoolean(source.tts_enabled, fallback),
    session_blocked: normalizeBoolean(source.session_blocked, false),
    custom_name: normalizeString(source.custom_name) || undefined,
    prompt_id: normalizeString(source.prompt_id) || null,
  };
}

export function normalizeSenderServiceConfig(
  raw: unknown,
): SessionServiceConfig {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  const source = raw as Record<string, unknown>;
  const config: SessionServiceConfig = {};
  if (typeof source.blocked === 'boolean') {
    config.blocked = source.blocked;
  }
  if (typeof source.llm_enabled === 'boolean') {
    config.llm_enabled = source.llm_enabled;
  }
  return config;
}

export function normalizeSessionPluginConfig(
  raw: unknown,
): SessionPluginConfig {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  const source = raw as Record<string, unknown>;
  return {
    ...source,
    enabled_plugins: normalizeStringArray(source.enabled_plugins),
    disabled_plugins: normalizeStringArray(source.disabled_plugins),
  };
}

export function normalizeSessionKbConfig(raw: unknown): SessionKbConfig {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  const source = raw as Record<string, unknown>;
  return {
    ...source,
    kb_ids: normalizeStringArray(source.kb_ids),
    top_k: normalizeNumber(source.top_k, 5),
    enable_rerank: normalizeBoolean(source.enable_rerank, true),
  };
}

export function toRuleValue(
  value: string | SessionServiceConfig | SessionPluginConfig | SessionKbConfig,
): DynamicConfig {
  return value as unknown as DynamicConfig;
}

export function normalizeRuleSet(
  raw: unknown,
  umo = '',
  sender = false,
): SessionRuleSet {
  if (!raw || typeof raw !== 'object') {
    return {};
  }

  const source = raw as Record<string, unknown>;
  return {
    ...source,
    session_service_config: sender
      ? normalizeSenderServiceConfig(source.session_service_config)
      : normalizeSessionServiceConfig(source.session_service_config, umo),
    session_plugin_config: normalizeSessionPluginConfig(
      source.session_plugin_config,
    ),
    kb_config: normalizeSessionKbConfig(source.kb_config),
    provider_perf_chat_completion:
      normalizeString(source.provider_perf_chat_completion) || undefined,
    provider_perf_speech_to_text:
      normalizeString(source.provider_perf_speech_to_text) || undefined,
    provider_perf_text_to_speech:
      normalizeString(source.provider_perf_text_to_speech) || undefined,
  };
}

export function parseUmoInfo(umo: string): UmoDisplayInfo {
  const parts = umo.split(':');
  return {
    umo,
    platform: parts[0] || '',
    message_type: parts[1] || '',
    session_id: parts.slice(2).join(':') || umo,
    auto_name: '',
    user_alias: '',
    display_name: umo,
  };
}

export function normalizeUmoInfo(
  raw: unknown,
  fallbackUmo = '',
): UmoDisplayInfo | null {
  if (!raw || typeof raw !== 'object') {
    return fallbackUmo ? parseUmoInfo(fallbackUmo) : null;
  }

  const source = raw as Record<string, unknown>;
  const umo = normalizeString(source.umo) || fallbackUmo;
  if (!umo) {
    return null;
  }

  return {
    umo,
    platform: normalizeString(source.platform),
    message_type: normalizeString(source.message_type),
    session_id:
      normalizeString(source.session_id) || parseUmoInfo(umo).session_id,
    auto_name: normalizeString(source.auto_name),
    user_alias: normalizeString(source.user_alias),
    display_name: normalizeString(source.display_name) || umo,
    rules:
      source.rules && typeof source.rules === 'object'
        ? normalizeRuleSet(source.rules, umo)
        : undefined,
  };
}

export function normalizeRuleItem(raw: unknown): SessionRuleItem | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  if (source.target_type === 'sender') {
    const senderId = normalizeString(source.sender_id);
    if (!senderId) {
      return null;
    }
    return {
      umo: '',
      sender_id: senderId,
      target_type: 'sender',
      platform: '',
      message_type: '',
      session_id: '',
      auto_name: '',
      user_alias: '',
      display_name: senderId,
      rules: normalizeRuleSet(source.rules, '', true),
    };
  }

  const info = normalizeUmoInfo(raw);
  if (!info) {
    return null;
  }

  return {
    ...info,
    target_type: 'session',
    rules: normalizeRuleSet(source.rules, info.umo),
  };
}

export function normalizeGroup(raw: unknown): GroupItem | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const source = raw as Record<string, unknown>;
  const id = normalizeString(source.id);
  const name = normalizeString(source.name);
  if (!id || !name) {
    return null;
  }

  return {
    id,
    name,
    umos: normalizeStringArray(source.umos),
    umo_count: normalizeNumber(source.umo_count, 0),
  };
}

export function normalizeUmoValue(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }
  if (value && typeof value === 'object') {
    return normalizeString((value as Record<string, unknown>).umo);
  }
  return '';
}

export function resolveUmoInfo(
  value: unknown,
  infoMap: Record<string, UmoDisplayInfo>,
): UmoDisplayInfo {
  const umo = normalizeUmoValue(value);
  if (!umo) {
    return parseUmoInfo('');
  }

  return infoMap[umo] || parseUmoInfo(umo);
}

export function resolveUmoDisplayProps(
  value: unknown,
  infoMap: Record<string, UmoDisplayInfo>,
): {
  umo: string;
  platform: string;
  messageType: string;
  sessionId: string;
  autoName: string;
  userAlias: string;
} {
  const info = resolveUmoInfo(value, infoMap);
  return {
    umo: info.umo,
    platform: info.platform,
    messageType: info.message_type,
    sessionId: info.session_id,
    autoName: info.auto_name,
    userAlias: info.user_alias,
  };
}

export function isSenderSubjectId(value: string): boolean {
  const parts = value.trim().split(':');
  return (
    parts.length >= 4 &&
    parts[0].toLowerCase() === 'im' &&
    parts[1].trim().length > 0 &&
    parts[2].trim().length > 0 &&
    parts.slice(3).join(':').trim().length > 0
  );
}

export function isSenderRule(
  item: SessionRuleItem | null | undefined,
): item is SessionRuleItem & { sender_id: string; target_type: 'sender' } {
  return item?.target_type === 'sender' && Boolean(item.sender_id);
}

export function hasProviderConfig(
  rules: SessionRuleSet | null | undefined,
): boolean {
  return Boolean(
    rules?.provider_perf_chat_completion ||
    rules?.provider_perf_speech_to_text ||
    rules?.provider_perf_text_to_speech,
  );
}

export function getProviderRule(
  rules: SessionRuleSet,
  type: ProviderRuleType,
): string | undefined {
  switch (type) {
    case 'chat_completion':
      return rules.provider_perf_chat_completion;
    case 'speech_to_text':
      return rules.provider_perf_speech_to_text;
    case 'text_to_speech':
      return rules.provider_perf_text_to_speech;
  }
}

export function setProviderRule(
  rules: SessionRuleSet,
  type: ProviderRuleType,
  value: string,
): void {
  switch (type) {
    case 'chat_completion':
      rules.provider_perf_chat_completion = value;
      return;
    case 'speech_to_text':
      rules.provider_perf_speech_to_text = value;
      return;
    case 'text_to_speech':
      rules.provider_perf_text_to_speech = value;
  }
}

export function clearProviderRule(
  rules: SessionRuleSet,
  type: ProviderRuleType,
): void {
  switch (type) {
    case 'chat_completion':
      delete rules.provider_perf_chat_completion;
      return;
    case 'speech_to_text':
      delete rules.provider_perf_speech_to_text;
      return;
    case 'text_to_speech':
      delete rules.provider_perf_text_to_speech;
  }
}

export function buildBatchTargetPayload(
  scope: BatchScope,
  groupId: string | null,
  umos: string[],
): Partial<Pick<UmoListRequest, 'scope' | 'group_id' | 'umos'>> {
  const payload: Partial<Pick<UmoListRequest, 'scope' | 'group_id' | 'umos'>> =
    {};

  if (
    scope === 'all' ||
    scope === 'group' ||
    scope === 'private' ||
    scope === 'custom_group'
  ) {
    payload.scope = scope;
  }
  if (groupId) {
    payload.group_id = groupId;
  }
  if (umos.length > 0) {
    payload.umos = umos;
  }

  return payload;
}

export function sessionAliasName(
  item: UmoDisplayInfo | SessionRuleItem | null | undefined,
): string {
  if (!item) {
    return '';
  }
  return (
    item.user_alias || item.rules?.session_service_config?.custom_name || ''
  );
}

export function getUmoDisplayText(
  value: unknown,
  infoMap: Record<string, UmoDisplayInfo>,
): string {
  const item =
    typeof value === 'string'
      ? resolveUmoInfo(value, infoMap)
      : (value as UmoDisplayInfo | SessionRuleItem | null);
  if (!item) {
    return '';
  }

  const umo = item.umo || normalizeUmoValue(value);
  const aliasName = sessionAliasName(item);
  const autoName = item.auto_name || '';

  let displayName = '';
  if (aliasName && autoName && aliasName !== autoName) {
    displayName = `${aliasName}（${autoName}）`;
  } else {
    displayName = aliasName || autoName;
  }

  if (displayName && umo) {
    return `${displayName} (UMO: ${umo})`;
  }

  return displayName || (umo ? `UMO: ${umo}` : item.display_name || '');
}

export function getUmoSelectionText(
  value: unknown,
  infoMap: Record<string, UmoDisplayInfo>,
): string {
  const item =
    typeof value === 'string'
      ? resolveUmoInfo(value, infoMap)
      : (value as UmoDisplayInfo | SessionRuleItem | null);
  if (!item) {
    return '';
  }

  const umo = item.umo || normalizeUmoValue(value);
  const aliasName = sessionAliasName(item);
  const autoName = item.auto_name || '';

  if (aliasName && autoName && aliasName !== autoName) {
    return `${aliasName}（${autoName}）`;
  }

  return aliasName || autoName || umo || item.display_name || '';
}
