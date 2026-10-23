import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('useProviderModelSelection', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetModules();
  });

  it('ignores a stored model without a stored provider', async () => {
    localStorage.setItem('selectedProviderModel', 'orphan-model');
    const { useProviderModelSelection } = await import(
      '@/composables/useProviderModelSelection'
    );
    const { selectedProviderId, selectedModelName } =
      useProviderModelSelection();
    expect(selectedProviderId.value).toBe('');
    expect(selectedModelName.value).toBe('');
  });

  it('clears the model and both keys when the provider is cleared', async () => {
    const { useProviderModelSelection } = await import(
      '@/composables/useProviderModelSelection'
    );
    const { selectedProviderId, selectedModelName, setSelection } =
      useProviderModelSelection();
    setSelection('provider-1', 'model-1');
    expect(localStorage.getItem('selectedProvider')).toBe('provider-1');
    expect(localStorage.getItem('selectedProviderModel')).toBe('model-1');

    setSelection('', 'stale-model');
    expect(selectedProviderId.value).toBe('');
    expect(selectedModelName.value).toBe('');
    expect(localStorage.getItem('selectedProvider')).toBeNull();
    expect(localStorage.getItem('selectedProviderModel')).toBeNull();
  });

  it('survives storage access failures', async () => {
    const setItem = vi
      .spyOn(Storage.prototype, 'setItem')
      .mockImplementation(() => {
        throw new Error('blocked');
      });
    const { useProviderModelSelection } = await import(
      '@/composables/useProviderModelSelection'
    );
    const { selectedProviderId, selectedModelName, setSelection } =
      useProviderModelSelection();
    expect(() => setSelection('provider-1', 'model-1')).not.toThrow();
    expect(selectedProviderId.value).toBe('provider-1');
    expect(selectedModelName.value).toBe('model-1');
    setItem.mockRestore();
  });
});
