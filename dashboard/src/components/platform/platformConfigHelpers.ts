export type RecordValue = Record<string, unknown>;
export type CreationMode = '' | 'scan' | 'manual';
export type ConfigMode = '0' | '1';
export type RouteSourceMode = 'manual' | 'known';

export interface PlatformConfigItem extends RecordValue {
  id?: string;
  type?: string;
  app_id?: string;
  app_secret?: string;
  client_id?: string;
  client_secret?: string;
  appid?: string;
  secret?: string;
  weixin_oc_token?: string;
  ws_reverse_token?: string;
  logo_token?: string;
}

export interface ConfigInfo extends RecordValue {
  id: string;
  name: string;
}

export interface PlatformRoute {
  umop: string | null;
  originalUmop: string | null;
  sourceMode: RouteSourceMode;
  sourceUmo: string;
  messageType: string;
  sessionId: string;
  configId: string;
}

export interface ParsedUmop {
  platform: string;
  messageType: string;
  sessionId: string;
}

export interface KnownRouteUmoInfo extends RecordValue {
  umo: string;
  platform?: string;
  message_type?: string;
  session_id?: string;
  auto_name?: string;
  user_alias?: string;
  display_name?: string;
}

export interface RegistrationCreatedPayload extends RecordValue {
  platform_id_suffix?: string;
  bot_name?: string;
}

export interface ToastPayload {
  message: string;
  type: 'success' | 'error';
}

export function asRecord(value: unknown): RecordValue | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as RecordValue;
}

export function getString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

export function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function normalizePlatformConfig(value: unknown): PlatformConfigItem {
  const record = asRecord(value);
  return record ? { ...record } : {};
}

export function normalizePlatformTemplates(
  value: unknown,
): Record<string, PlatformConfigItem> {
  const record = asRecord(value);
  if (!record) {
    return {};
  }

  const templates: Record<string, PlatformConfigItem> = {};
  for (const [key, templateValue] of Object.entries(record)) {
    templates[key] = normalizePlatformConfig(templateValue);
  }
  return templates;
}

export function normalizePlatformConfigList(
  value: unknown,
): PlatformConfigItem[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => normalizePlatformConfig(item));
}

export function normalizeConfigInfoList(value: unknown): ConfigInfo[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const infoList: ConfigInfo[] = [];
  for (const item of value) {
    const record = asRecord(item);
    const id = getString(record?.id);
    const name = getString(record?.name);
    if (record && id && name) {
      infoList.push({ ...record, id, name });
    }
  }
  return infoList;
}

export function normalizeRoutingTable(value: unknown): Record<string, string> {
  const record = asRecord(value);
  if (!record) {
    return {};
  }

  const routing: Record<string, string> = {};
  for (const [umop, configId] of Object.entries(record)) {
    const normalizedConfigId = getString(configId);
    if (normalizedConfigId) {
      routing[umop] = normalizedConfigId;
    }
  }
  return routing;
}

export function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === 'string');
}

export function normalizeKnownRouteUmoInfos(
  value: unknown,
): KnownRouteUmoInfo[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const infos: KnownRouteUmoInfo[] = [];
  for (const item of value) {
    const record = asRecord(item);
    const umo = getString(record?.umo);
    if (!record || !umo) {
      continue;
    }
    infos.push({
      ...record,
      umo,
      platform: getString(record.platform) ?? undefined,
      message_type: getString(record.message_type) ?? undefined,
      session_id: getString(record.session_id) ?? undefined,
      auto_name: getString(record.auto_name) ?? undefined,
      user_alias: getString(record.user_alias) ?? undefined,
      display_name: getString(record.display_name) ?? undefined,
    });
  }
  return infos;
}

export function sanitizePlatformIdPart(value: unknown): string {
  return String(value ?? '')
    .trim()
    .replace(/\s+/g, '')
    .replace(/[!:]/g, '_');
}

export function buildRandomPlatformIdSuffix(): string {
  const letters = 'abcdefghijklmnopqrstuvwxyz';
  let suffix = '_';
  for (let i = 0; i < 4; i += 1) {
    suffix += letters[Math.floor(Math.random() * letters.length)];
  }
  return suffix;
}

export function parseUmop(umop: string | null | undefined): ParsedUmop | null {
  if (!umop) {
    return null;
  }

  const firstSeparatorIndex = umop.indexOf(':');
  if (firstSeparatorIndex === -1) {
    return null;
  }
  const secondSeparatorIndex = umop.indexOf(':', firstSeparatorIndex + 1);
  if (secondSeparatorIndex === -1) {
    return null;
  }

  return {
    platform: umop.slice(0, firstSeparatorIndex),
    messageType: umop.slice(firstSeparatorIndex + 1, secondSeparatorIndex),
    sessionId: umop.slice(secondSeparatorIndex + 1),
  };
}

export function isParsedUmopMatchPlatform(
  parsedUmop: ParsedUmop | null,
  platformId: string,
): boolean {
  if (!parsedUmop) {
    return false;
  }
  return (
    parsedUmop.platform === platformId ||
    parsedUmop.platform === '' ||
    parsedUmop.platform === '*'
  );
}

export function isUmopMatchPlatform(umop: string, platformId: string): boolean {
  return isParsedUmopMatchPlatform(parseUmop(umop), platformId);
}

export function isPlatformIdValid(id: unknown): boolean {
  const normalized = getString(id);
  if (!normalized) {
    return false;
  }
  return !/[!:\s]/.test(normalized);
}

export function getOneBotSecurityToken(
  platformConfig: Record<string, unknown> | undefined,
): string | undefined {
  if (!platformConfig) {
    return undefined;
  }
  const platformType = getString(platformConfig.type);
  if (platformType === 'napcat') {
    return getString(platformConfig.token) ?? undefined;
  }
  return getString(platformConfig.ws_reverse_token) ?? undefined;
}

export function getKnownRouteUmoInfo(
  umo: string,
  infoMap: Record<string, KnownRouteUmoInfo>,
): KnownRouteUmoInfo {
  const parsed = parseUmop(umo);
  return (
    infoMap[umo] || {
      umo,
      platform: parsed?.platform || '',
      message_type: parsed?.messageType || '',
      session_id: parsed?.sessionId || umo,
      auto_name: '',
      user_alias: '',
      display_name: umo,
    }
  );
}

export function getKnownRouteUmoDisplayProps(
  umo: string,
  infoMap: Record<string, KnownRouteUmoInfo>,
) {
  const info = getKnownRouteUmoInfo(umo, infoMap);
  const parsed = parseUmop(umo);
  return {
    umo,
    platform: info.platform || parsed?.platform || '',
    messageType: info.message_type || parsed?.messageType || '',
    sessionId: info.session_id || parsed?.sessionId || '',
    autoName: info.auto_name || '',
    userAlias: info.user_alias || '',
  };
}

export function getRouteSourceMode(route: PlatformRoute): RouteSourceMode {
  return route.sourceMode || 'manual';
}
