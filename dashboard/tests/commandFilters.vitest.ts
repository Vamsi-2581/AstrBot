import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useCommandFilters } from '@/components/extension/componentPanel/composables/useCommandFilters';
import type { CommandItem } from '@/domain/commands';

function command(overrides: Partial<CommandItem>): CommandItem {
  return {
    command_id: 'plugin:cmd',
    handler_full_name: 'handler',
    handler_name: 'handler',
    plugin: 'plugin',
    plugin_display_name: null,
    module_path: 'module',
    description: '',
    type: 'command',
    parent_signature: '',
    parent_group_handler: '',
    original_command: 'cmd',
    current_fragment: 'cmd',
    effective_command: 'cmd',
    signature: 'cmd',
    display_signature: 'cmd',
    aliases: [],
    action: null,
    enabled: true,
    plugin_activated: true,
    is_group: false,
    has_conflict: false,
    reserved: false,
    sub_commands: [],
    ...overrides,
  };
}

describe('useCommandFilters ordering', () => {
  it('orders the filter dropdowns by UTF-16 code units, not locale collation', () => {
    const commands = ref([
      command({ plugin: 'zebra', action: 'zeta' }),
      command({ plugin: 'Apple', action: 'Beta' }),
      command({ plugin: 'apple', action: 'beta' }),
      command({ plugin: 'banana', action: 'alpha' }),
    ]);
    const filters = useCommandFilters(commands);

    expect(filters.availablePlugins.value).toEqual([
      'Apple',
      'apple',
      'banana',
      'zebra',
    ]);
    expect(filters.availableActions.value).toEqual([
      'Beta',
      'alpha',
      'beta',
      'zeta',
    ]);
  });
});
