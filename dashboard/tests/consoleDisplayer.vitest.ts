import { readFile } from 'node:fs/promises';
import { describe, expect, it } from 'vitest';

describe('ConsoleDisplayer log rendering', () => {
  it('batches DOM insertion and keeps log content text-only', async () => {
    const source = await readFile(
      'src/components/shared/ConsoleDisplayer.vue',
      'utf8',
    );

    expect(source).toContain('document.createDocumentFragment()');
    expect(source).toContain('target.appendChild(fragment)');
    expect(source).toContain('element.textContent = cleanText');
    expect(source).toContain('highlight.textContent = cleanText.slice');
    expect(source).not.toContain('innerHTML = log');
  });

  it('filters logs with a debounced, localized search field', async () => {
    const source = await readFile(
      'src/components/shared/ConsoleDisplayer.vue',
      'utf8',
    );

    expect(source).toContain("useModuleI18n('features/logs')");
    expect(source).toContain('matchesKeyword(log)');
    expect(source).toContain('searchTimer.value = window.setTimeout');
    expect(source).toContain("tm('search.placeholder')");
  });

  it('intersects level, source, plugin, and platform filters', async () => {
    const source = await readFile(
      'src/components/shared/ConsoleDisplayer.vue',
      'utf8',
    );

    expect(source).toContain('matchesSource(log)');
    expect(source).toContain('matchesPlugin(log)');
    expect(source).toContain('matchesPlatform(log)');
    expect(source).toContain("selectedPlatform.value === '__unscoped__'");
    expect(source).toContain("tm('filters.button')");
    expect(source).toContain("tm('filters.unscopedPlatform')");
  });

  it('prefers plugin display names while keeping ids as values', async () => {
    const source = await readFile(
      'src/components/shared/ConsoleDisplayer.vue',
      'utf8',
    );

    expect(source).toContain('pluginDisplayNames.value[value] || value');
    expect(source).toContain('subtitle: value');
    expect(source).toContain('pluginApi.list()');
  });

  it('applies the configurable log font size', async () => {
    const source = await readFile(
      'src/components/shared/ConsoleDisplayer.vue',
      'utf8',
    );

    expect(source).toContain('--console-log-font-size');
  });
});
