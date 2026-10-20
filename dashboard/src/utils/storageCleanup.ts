export type CleanupTarget = 'logs' | 'cache' | 'traces' | 'all';

export function cleanupConfirmationKey(target: CleanupTarget): string {
  return target === 'traces' || target === 'all'
    ? 'system.cleanup.confirmWithTraces'
    : 'system.cleanup.confirm';
}
