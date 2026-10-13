export const STATUS_WAITING = 'waiting' as const;
export const STATUS_UPLOADING = 'uploading' as const;
export const STATUS_SUCCESS = 'success' as const;
export const STATUS_ERROR = 'error' as const;
export const STATUS_SKIPPED = 'skipped' as const;

export type SkillMode = 'local' | 'neo';
export type UploadStatus =
  | typeof STATUS_WAITING
  | typeof STATUS_UPLOADING
  | typeof STATUS_SUCCESS
  | typeof STATUS_ERROR
  | typeof STATUS_SKIPPED;
export type SnackbarColor = 'success' | 'error' | 'warning';
export type ReleaseStage = 'canary' | 'stable';

export interface SandboxCacheState {
  ready: boolean;
  count: number;
  updated_at: string | null;
}

export interface UploadItem {
  id: string;
  file: File;
  name: string;
  size: number;
  status: UploadStatus;
  validationMessage: string;
  filenameKey: string;
}

export interface UploadResultEntry {
  filename?: string;
  name?: string;
  error?: string;
}

export interface NeoFilterState {
  skill_key: string;
  status: string;
  stage: string;
}

export interface NeoCandidate {
  id: string;
  skill_key?: string;
  status?: string;
  latest_score?: number | null;
  payload_ref?: string;
  [key: string]: unknown;
}

export interface NeoRelease {
  id: string;
  skill_key?: string;
  stage?: string;
  version?: string | number;
  is_active: boolean;
  active?: boolean;
  [key: string]: unknown;
}

export interface SkillEntry {
  type: string;
  path: string;
  name: string;
  editable: boolean;
  [key: string]: unknown;
}

export interface PayloadDialogState {
  show: boolean;
  content: string;
}

export interface EditorDialogState {
  show: boolean;
  skillName: string;
  currentDir: string;
  entries: SkillEntry[];
  filePath: string;
  content: string;
  fileEditable: boolean;
  fileDirty: boolean;
  loadingFiles: boolean;
  loadingFile: boolean;
  saving: boolean;
  error: string;
}

export function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

export function getString(value: unknown) {
  return typeof value === 'string' ? value : '';
}

export function getBoolean(value: unknown, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

export function getNumber(value: unknown, fallback = 0) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function normalizeSkillEntry(value: unknown): SkillEntry | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const path = getString(record.path).trim();
  const name = getString(record.name).trim();
  const type = getString(record.type).trim();
  if (!path || !name || !type) {
    return null;
  }

  return {
    ...record,
    path,
    name,
    type,
    editable: record.editable !== false,
  };
}

export function normalizeNeoCandidate(value: unknown): NeoCandidate | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const id = getString(record.id).trim();
  if (!id) {
    return null;
  }

  const latestScore =
    typeof record.latest_score === 'number' &&
    Number.isFinite(record.latest_score)
      ? record.latest_score
      : null;

  return {
    ...record,
    id,
    skill_key: getString(record.skill_key) || undefined,
    status: getString(record.status) || undefined,
    latest_score: latestScore,
    payload_ref: getString(record.payload_ref) || undefined,
  };
}

export function normalizeNeoRelease(value: unknown): NeoRelease | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }

  const id = getString(record.id).trim();
  if (!id) {
    return null;
  }

  return {
    ...record,
    id,
    skill_key: getString(record.skill_key) || undefined,
    stage: getString(record.stage) || undefined,
    version:
      typeof record.version === 'string' || typeof record.version === 'number'
        ? record.version
        : undefined,
    active: typeof record.active === 'boolean' ? record.active : undefined,
    is_active: getBoolean(record.is_active, getBoolean(record.active)),
  };
}

export function normalizeNeoItemsPayload(payload: unknown) {
  if (Array.isArray(payload)) {
    return payload;
  }
  const record = asRecord(payload);
  if (!record || !Array.isArray(record.items)) {
    return [];
  }
  return record.items;
}

export function normalizeUploadName(name: string) {
  return String(name).trim().toLowerCase();
}

export function formatFileSize(size: number) {
  if (!Number.isFinite(size) || size <= 0) return '0 B';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function statusChipClass(status: UploadStatus) {
  return `skills-status-chip skills-status-chip--${status}`;
}

export function candidatePromoteLoadingKey(
  candidateId: string,
  stage: ReleaseStage,
) {
  return `${candidateId}:${stage}`;
}
