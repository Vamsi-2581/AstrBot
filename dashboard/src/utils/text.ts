/**
 * Truncate a string to `max` characters, appending an ellipsis when it is
 * longer. Falsy input yields an empty string.
 */
export function truncate(
  value: string | null | undefined,
  max: number,
): string {
  if (!value) {
    return '';
  }
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

/** Format an ISO date string for display, returning '' for empty input. */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  return new Date(value).toLocaleString();
}

/** Remove every trailing slash from a path or URL. */
export function stripTrailingSlashes(value: string): string {
  let end = value.length;
  while (end > 0 && value[end - 1] === '/') {
    end -= 1;
  }
  return value.slice(0, end);
}
