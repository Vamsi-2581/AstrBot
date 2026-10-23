import { flushPromises } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UnsavedChangesConfirmDialog from '@/components/config/UnsavedChangesConfirmDialog.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

describe('UnsavedChangesConfirmDialog', () => {
  it('settles a previous open before replacing it with a new request', async () => {
    const wrapper = mountWithVuetify(UnsavedChangesConfirmDialog);

    const first = wrapper.vm.open({ message: 'first' });
    const second = wrapper.vm.open({ message: 'second' });

    await expect(first).resolves.toBe('close');

    let secondResolved = false;
    void second.then(() => {
      secondResolved = true;
    });
    await flushPromises();
    expect(secondResolved).toBe(false);

    const confirm = document.body.querySelector('.confirm-button');
    (confirm as HTMLElement).click();
    await flushPromises();
    await expect(second).resolves.toBe(true);
    wrapper.unmount();
  });
});
