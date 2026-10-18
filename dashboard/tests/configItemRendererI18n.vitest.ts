import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initI18n } from '@/i18n/composables';
import ConfigItemRenderer from '@/components/shared/ConfigItemRenderer.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

vi.mock('@/utils/monacoLoader', () => ({}));

function mountCheckboxList(
  pluginI18n: Record<string, unknown>,
  options: string[],
) {
  return mountWithVuetify(ConfigItemRenderer, {
    props: {
      modelValue: [],
      itemMeta: {
        type: 'list',
        options,
        render_type: 'checkbox',
      },
      pluginName: 'demo',
      configKey: 'key',
      pluginI18n,
    },
  });
}

describe('ConfigItemRenderer plugin i18n labels', () => {
  beforeEach(async () => {
    await initI18n('zh-CN');
  });

  it('renders array labels from plugin i18n', () => {
    const wrapper = mountCheckboxList(
      { 'zh-CN': { config: { key: { labels: ['甲', '乙'] } } } },
      ['a', 'b'],
    );
    const text = wrapper.text();
    expect(text).toContain('甲');
    expect(text).toContain('乙');
    wrapper.unmount();
  });

  it('falls back to option values for missing array entries', () => {
    const wrapper = mountCheckboxList(
      { 'zh-CN': { config: { key: { labels: ['甲'] } } } },
      ['a', 'b'],
    );
    const text = wrapper.text();
    expect(text).toContain('甲');
    expect(text).toContain('b');
    wrapper.unmount();
  });

  it('ignores an empty plugin i18n label array', () => {
    const wrapper = mountCheckboxList(
      { 'zh-CN': { config: { key: { labels: [] } } } },
      ['a', 'b'],
    );
    const text = wrapper.text();
    expect(text).toContain('a');
    expect(text).toContain('b');
    wrapper.unmount();
  });
});
