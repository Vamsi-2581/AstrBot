import { describe, expect, it } from 'vitest';
import { cleanupConfirmationKey } from '@/utils/storageCleanup';

describe('storage cleanup confirmation', () => {
  it('warns before removing trace history', () => {
    expect(cleanupConfirmationKey('traces')).toBe(
      'system.cleanup.confirmWithTraces',
    );
    expect(cleanupConfirmationKey('all')).toBe(
      'system.cleanup.confirmWithTraces',
    );
  });

  it('uses the ordinary confirmation for logs and cache', () => {
    expect(cleanupConfirmationKey('logs')).toBe('system.cleanup.confirm');
    expect(cleanupConfirmationKey('cache')).toBe('system.cleanup.confirm');
  });
});
