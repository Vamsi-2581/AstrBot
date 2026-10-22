/** Read browser state without letting restricted storage abort chat setup. */
export function readStoredValue(key: string): string {
  try {
    return localStorage.getItem(key) || '';
  } catch {
    return '';
  }
}

/** Persist browser state when storage is available. */
export function writeStoredValue(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Browser persistence must not block chat interactions.
  }
}

/** Remove browser state when storage is available. */
export function removeStoredValue(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Browser persistence must not block chat interactions.
  }
}

/** Normalize a raw token count into a finite non-negative number. */
export function readTokenCount(value: unknown): number {
  const count = Number(value || 0);
  return Number.isFinite(count) && count > 0 ? count : 0;
}

/** Render a usage percentage with progressive precision. */
export function formatUsagePercent(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '0';
  if (value >= 10) return String(Math.round(value));
  if (value >= 1) return String(Math.round(value * 10) / 10);
  return String(Math.round(value * 100) / 100);
}
