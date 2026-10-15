export interface VersionSupportResult {
  checked: boolean;
  supported: boolean;
  message: string;
}

export const normalizeAstrBotVersionSpec = (value: unknown): string =>
  String(value || '').trim();

export function normalizeVersionParts(value: unknown): number[] {
  const version = String(value || '')
    .trim()
    .replace(/^v/i, '')
    .split(/[+-]/)[0];
  const parts = version.split('.').map((part) => {
    const match = /^\d+/.exec(part);
    return match ? Number.parseInt(match[0], 10) : 0;
  });
  return parts.length ? parts : [0];
}

export function compareVersions(left: unknown, right: unknown): number {
  const leftParts = normalizeVersionParts(left);
  const rightParts = normalizeVersionParts(right);
  const length = Math.max(leftParts.length, rightParts.length, 3);
  for (let i = 0; i < length; i += 1) {
    const leftPart = leftParts[i] || 0;
    const rightPart = rightParts[i] || 0;
    if (leftPart > rightPart) return 1;
    if (leftPart < rightPart) return -1;
  }
  return 0;
}

export function getSupportedReleaseUpperBound(version: unknown): string {
  const parts = normalizeVersionParts(version);
  if (parts.length <= 2) {
    return `${(parts[0] || 0) + 1}.0`;
  }
  return `${parts[0] || 0}.${(parts[1] || 0) + 1}.0`;
}

export function checkVersionConstraint(
  currentVersion: string,
  constraint: string,
): boolean | null {
  const match = /^(<=|>=|==|!=|~=|<|>|=)\s*(\S.*)$/.exec(constraint);
  if (!match) return null;

  const [, operator, targetVersion] = match;
  const normalizedTarget = targetVersion.trim();
  if (!normalizedTarget) return null;
  if (!/^v?\d+/.test(normalizedTarget)) return null;

  if (operator === '~=') {
    return (
      compareVersions(currentVersion, normalizedTarget) >= 0 &&
      compareVersions(
        currentVersion,
        getSupportedReleaseUpperBound(normalizedTarget),
      ) < 0
    );
  }

  const comparison = compareVersions(currentVersion, normalizedTarget);
  if (operator === '>' || operator === '>=') {
    return operator === '>' ? comparison > 0 : comparison >= 0;
  }
  if (operator === '<' || operator === '<=') {
    return operator === '<' ? comparison < 0 : comparison <= 0;
  }
  if (operator === '!=') return comparison !== 0;
  return comparison === 0;
}

export function checkAstrBotVersionSupport(
  versionSpec: unknown,
  currentVersion: string,
): VersionSupportResult {
  const normalizedSpec = normalizeAstrBotVersionSpec(versionSpec);
  if (!normalizedSpec) {
    return { checked: false, supported: true, message: '' };
  }
  if (!currentVersion) {
    return { checked: false, supported: true, message: '' };
  }

  const constraints = normalizedSpec
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  if (!constraints.length) {
    return { checked: false, supported: true, message: '' };
  }

  for (const constraint of constraints) {
    const supported = checkVersionConstraint(currentVersion, constraint);
    if (supported === null) {
      return {
        checked: true,
        supported: false,
        message:
          'Invalid astrbot_version. Use a PEP 440 range, e.g. >=4.16,<5.',
      };
    }
    if (!supported) {
      return {
        checked: true,
        supported: false,
        message: `AstrBot ${currentVersion} does not satisfy plugin astrbot_version: ${normalizedSpec}`,
      };
    }
  }

  return { checked: true, supported: true, message: '' };
}
