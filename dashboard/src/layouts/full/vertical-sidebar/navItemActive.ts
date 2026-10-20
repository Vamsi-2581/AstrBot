function normalizePath(path: string): string {
  return path.replace(/\/$/, '') || '/';
}

export function isNavItemActive(
  currentPath: string,
  matchedPaths: readonly string[],
  target: string,
): boolean {
  const targetPath = normalizePath(target);
  if (currentPath === targetPath) return true;

  return matchedPaths.some((matchedPath) => {
    const recordPath = normalizePath(matchedPath);
    if (recordPath === targetPath) return true;
    const staticPrefix = normalizePath(recordPath.split('/:')[0]);
    return staticPrefix !== '/' && staticPrefix === targetPath;
  });
}
