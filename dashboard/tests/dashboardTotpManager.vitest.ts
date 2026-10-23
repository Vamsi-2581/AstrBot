import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DashboardTotpManageDialog from '@/components/shared/DashboardTotpManageDialog.vue';
import DashboardTotpManager from '@/components/shared/DashboardTotpManager.vue';
import DashboardTotpRecoveryDialog from '@/components/shared/DashboardTotpRecoveryDialog.vue';
import { mountWithVuetify } from './utils/mountWithVuetify';

const recoverTotp = vi.fn();

vi.mock('@/api/v1', () => ({
  authApi: {
    recoverTotp: () => recoverTotp(),
  },
}));

describe('DashboardTotpManager recovery rotation', () => {
  beforeEach(() => {
    recoverTotp.mockReset();
  });

  it('shows a rotated recovery code even without a recovery hash', async () => {
    recoverTotp.mockResolvedValue({
      data: {
        status: 'ok',
        data: { recovery_code: 'NEW-RECOVERY-CODE' },
      },
    });
    const configRoot = {
      dashboard: {
        totp: {
          enable: true,
          secret: 'secret',
          recovery_code_hash: 'old-hash',
        },
      },
    };
    const wrapper = mountWithVuetify(DashboardTotpManager, {
      props: { modelValue: true, configRoot },
    });

    wrapper
      .findComponent(DashboardTotpManageDialog)
      .vm.$emit('rotate-recovery');
    await flushPromises();

    expect(
      wrapper.findComponent(DashboardTotpRecoveryDialog).props('recoveryCode'),
    ).toBe('NEW-RECOVERY-CODE');
    expect(configRoot.dashboard.totp.recovery_code_hash).toBe('old-hash');
  });

  it('updates the config hash when the server returns one', async () => {
    recoverTotp.mockResolvedValue({
      data: {
        status: 'ok',
        data: {
          recovery_code: 'NEW-RECOVERY-CODE',
          recovery_code_hash: 'new-hash',
        },
      },
    });
    const configRoot = {
      dashboard: {
        totp: {
          enable: true,
          secret: 'secret',
          recovery_code_hash: 'old-hash',
        },
      },
    };
    const wrapper = mountWithVuetify(DashboardTotpManager, {
      props: { modelValue: true, configRoot },
    });

    wrapper
      .findComponent(DashboardTotpManageDialog)
      .vm.$emit('rotate-recovery');
    await flushPromises();

    expect(
      wrapper.findComponent(DashboardTotpRecoveryDialog).props('recoveryCode'),
    ).toBe('NEW-RECOVERY-CODE');
    expect(configRoot.dashboard.totp.recovery_code_hash).toBe('new-hash');
  });
});
