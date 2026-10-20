import { describe, expect, it } from 'vitest';

import { isNavItemActive } from '@/layouts/full/vertical-sidebar/navItemActive';

describe('isNavItemActive', () => {
  it('matches an exact route', () => {
    expect(
      isNavItemActive('/btw/runs', ['/main', '/btw/runs'], '/btw/runs'),
    ).toBe(true);
  });

  it('keeps a parent item active for its child routes', () => {
    expect(
      isNavItemActive(
        '/dashboard/statistics',
        ['/main', '/dashboard', '/dashboard/statistics'],
        '/dashboard',
      ),
    ).toBe(true);
  });

  it('does not activate a prefix sibling item', () => {
    expect(isNavItemActive('/btw/runs', ['/main', '/btw/runs'], '/btw')).toBe(
      false,
    );
  });

  it('keeps an item active for parametric child routes', () => {
    expect(
      isNavItemActive(
        '/extension/example',
        ['/main', '/extension/:pluginId+'],
        '/extension',
      ),
    ).toBe(true);
    expect(
      isNavItemActive(
        '/extension/example/pages/settings',
        ['/main', '/extension/:extensionId/pages/:pageId'],
        '/extension',
      ),
    ).toBe(true);
  });

  it('ignores unrelated suffixes', () => {
    expect(
      isNavItemActive(
        '/extension-marketplace',
        ['/main', '/extension-marketplace'],
        '/extension',
      ),
    ).toBe(false);
  });
});
