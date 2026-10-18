import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import PromptForm from '@/components/shared/PromptForm.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

const testState = vi.hoisted(() => ({
  mcpListMock: vi.fn(),
  promptCreateMock: vi.fn(),
  promptDeleteMock: vi.fn(),
  promptListMock: vi.fn(),
  promptUpdateMock: vi.fn(),
  skillListMock: vi.fn(),
  toolListMock: vi.fn(),
  askForConfirmationMock: vi.fn(),
}));

vi.mock('@/api/v1', () => ({
  mcpApi: {
    list: testState.mcpListMock,
  },
  promptApi: {
    create: testState.promptCreateMock,
    delete: testState.promptDeleteMock,
    list: testState.promptListMock,
    update: testState.promptUpdateMock,
  },
  skillApi: {
    list: testState.skillListMock,
  },
  toolApi: {
    list: testState.toolListMock,
  },
}));

vi.mock('@/utils/confirmDialog', () => ({
  askForConfirmation: testState.askForConfirmationMock,
  useConfirmDialog: () => undefined,
}));

describe('PromptForm', () => {
  beforeEach(() => {
    testState.mcpListMock.mockResolvedValue({
      data: {
        status: 'ok',
        data: [
          { name: 'server-a', tools: ['tool.alpha', 'tool.beta'] },
          { name: 'server-empty', tools: [] },
        ],
      },
    });
    testState.toolListMock.mockResolvedValue({
      data: {
        status: 'ok',
        data: [
          {
            name: 'tool.alpha',
            description: 'Alpha tool',
            mcp_server_name: 'server-a',
          },
          {
            name: 'tool.beta',
            description: 'Beta tool',
            mcp_server_name: 'server-a',
          },
        ],
      },
    });
    testState.skillListMock.mockResolvedValue({
      data: {
        status: 'ok',
        data: {
          skills: [
            {
              name: 'skill.one',
              description: 'First skill',
              active: true,
            },
          ],
        },
      },
    });
    testState.promptListMock.mockResolvedValue({
      data: {
        status: 'ok',
        data: [],
      },
    });
    testState.promptCreateMock.mockResolvedValue({
      data: {
        status: 'ok',
        message: 'Saved',
      },
    });
    testState.promptUpdateMock.mockResolvedValue({
      data: {
        status: 'ok',
        message: 'Updated',
      },
    });
    testState.promptDeleteMock.mockResolvedValue({
      data: {
        status: 'ok',
        message: 'Deleted',
      },
    });
    testState.askForConfirmationMock.mockResolvedValue(true);
  });

  it('renders MCP quick select chips and applies server tools', async () => {
    const wrapper = mountWithVuetify(PromptForm, {
      props: {
        modelValue: false,
        editingPrompt: {
          prompt_id: 'helper',
          system_prompt: 'This is a sufficiently long system prompt.',
          custom_error_message: '',
          begin_dialogs: [],
          tools: [],
          skills: [],
          folder_id: null,
        },
      },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div class="v-dialog-stub"><slot /></div>',
          },
        },
      },
    });

    await wrapper.setProps({ modelValue: true });
    await flushPromises();

    expect(wrapper.text()).toContain('MCP Servers Quick Select');
    expect(wrapper.text()).toContain('server-a');
    expect(wrapper.text()).toContain(
      'This Prompt loads no plugin or MCP tools',
    );

    const serverChip = wrapper
      .findAll('.v-chip')
      .find((chip) => chip.text().includes('server-a'));

    expect(serverChip).toBeDefined();

    await serverChip!.trigger('click');
    await flushPromises();

    expect(wrapper.text()).not.toContain(
      'This Prompt loads no plugin or MCP tools',
    );
    expect(wrapper.text()).toContain('tool.alpha');
    expect(wrapper.text()).toContain('tool.beta');
  });

  it('keeps disabled plugin skills in an existing prompt without offering them again', async () => {
    testState.skillListMock.mockResolvedValue({
      data: {
        status: 'ok',
        data: {
          skills: [
            {
              name: 'disabled-plugin-skill',
              description: 'Installed by a disabled plugin',
              active: true,
              source_type: 'plugin',
              plugin_active: false,
            },
            {
              name: 'available-skill',
              description: 'Available local skill',
              active: true,
            },
          ],
        },
      },
    });
    const wrapper = mountWithVuetify(PromptForm, {
      props: {
        modelValue: false,
        editingPrompt: {
          prompt_id: 'helper',
          system_prompt: 'This is a sufficiently long system prompt.',
          custom_error_message: '',
          begin_dialogs: [],
          tools: [],
          skills: ['disabled-plugin-skill'],
          folder_id: null,
        },
      },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div class="v-dialog-stub"><slot /></div>',
          },
        },
      },
    });

    await wrapper.setProps({ modelValue: true });
    await flushPromises();

    expect(wrapper.text()).toContain('disabled-plugin-skill');
    expect(wrapper.text()).toContain('available-skill');
    expect(wrapper.find('.skills-selection').text()).not.toContain(
      'disabled-plugin-skill',
    );

    const saveButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Save');
    expect(saveButton).toBeDefined();
    await saveButton!.trigger('click');
    await flushPromises();

    expect(testState.promptUpdateMock).toHaveBeenCalledWith(
      'helper',
      expect.objectContaining({
        skills: ['disabled-plugin-skill'],
      }),
    );
  });

  it('keeps builtin tools out of the prompt allowlist and warns on empty selection', async () => {
    testState.toolListMock.mockResolvedValue({
      data: {
        status: 'ok',
        data: [
          {
            name: 'tool.alpha',
            description: 'Alpha tool',
            mcp_server_name: 'server-a',
          },
          {
            name: 'tool.beta',
            description: 'Beta tool',
            mcp_server_name: 'server-a',
          },
          {
            name: 'web_search',
            description: 'Search the web',
            origin: 'builtin',
            origin_name: 'AstrBot Core',
            readonly: true,
            builtin_config_statuses: [
              {
                conf_id: 'default',
                conf_name: 'default',
                enabled: true,
                matched_conditions: [],
                failed_conditions: [],
              },
            ],
          },
        ],
      },
    });
    const wrapper = mountWithVuetify(PromptForm, {
      props: {
        modelValue: false,
        editingPrompt: {
          prompt_id: 'helper',
          system_prompt: 'This is a sufficiently long system prompt.',
          custom_error_message: '',
          begin_dialogs: [],
          tools: [],
          skills: [],
          folder_id: null,
        },
      },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div class="v-dialog-stub"><slot /></div>',
          },
        },
      },
    });

    await wrapper.setProps({ modelValue: true });
    await flushPromises();

    expect(wrapper.text()).toContain('web_search');
    expect(wrapper.text()).toContain('Enabled');
    expect(wrapper.text()).toContain(
      'This Prompt loads no plugin or MCP tools',
    );

    const selectAllButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Select All Extension Tools');
    expect(selectAllButton).toBeDefined();
    await selectAllButton!.trigger('click');
    await flushPromises();

    expect(wrapper.text()).not.toContain(
      'This Prompt loads no plugin or MCP tools',
    );

    const saveButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Save');
    expect(saveButton).toBeDefined();
    await saveButton!.trigger('click');
    await flushPromises();

    expect(testState.promptUpdateMock).toHaveBeenLastCalledWith(
      'helper',
      expect.objectContaining({
        tools: ['tool.alpha', 'tool.beta'],
      }),
    );
  });

  it('defaults new prompts to all extension tools', async () => {
    const wrapper = mountWithVuetify(PromptForm, {
      props: {
        modelValue: false,
        editingPrompt: null,
      },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div class="v-dialog-stub"><slot /></div>',
          },
        },
      },
    });

    await wrapper.setProps({ modelValue: true });
    await flushPromises();

    await wrapper.find('input').setValue('new-helper');
    await wrapper.find('textarea').setValue(
      'This is a sufficiently long system prompt.',
    );
    await flushPromises();

    const saveButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Save');
    expect(saveButton).toBeDefined();
    await saveButton!.trigger('click');
    await flushPromises();

    expect(testState.promptCreateMock).toHaveBeenCalledWith(
      expect.objectContaining({
        tools: null,
        skills: null,
      }),
    );
  });

  it('does not offer deletion for the system default prompt', async () => {
    const wrapper = mountWithVuetify(PromptForm, {
      props: {
        modelValue: true,
        editingPrompt: {
          prompt_id: 'default',
          system_prompt: 'This is the editable system default prompt.',
          custom_error_message: '',
          begin_dialogs: [],
          tools: null,
          skills: null,
          folder_id: null,
        },
      },
      global: {
        stubs: {
          VDialog: {
            props: ['modelValue'],
            template: '<div class="v-dialog-stub"><slot /></div>',
          },
        },
      },
    });

    await flushPromises();

    expect(
      wrapper
        .findAll('button')
        .some((button) => button.text().trim() === 'Delete'),
    ).toBe(false);
  });
});
