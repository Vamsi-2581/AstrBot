<template>
  <div class="platform-dialog__step">
    <div>
      <v-icon icon="mdi-numeric-1-circle" class="mr-3"></v-icon>
    </div>
    <div class="platform-dialog__step-content">
      <h3>
        {{ tm('createDialog.step1Title') }}
      </h3>
      <small class="text-medium-emphasis">{{
        tm('createDialog.step1Hint')
      }}</small>
      <div>
        <div v-if="!updatingMode">
          <v-select
            :model-value="selectedPlatformType"
            :items="Object.keys(platformTemplates)"
            item-title="name"
            item-value="name"
            :label="tm('createDialog.platformTypeLabel')"
            variant="outlined"
            rounded="md"
            density="comfortable"
            hide-details
            class="mt-6 platform-type-field"
            @update:model-value="emit('update:selected-platform-type', $event)"
          >
            <template #item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps">
                <template #prepend>
                  <img
                    :src="getPlatformTemplateIcon(item)"
                    class="platform-template-icon"
                    alt=""
                  />
                </template>
                <v-tooltip
                  v-if="
                    [
                      'qq_official',
                      'qq_official_webhook',
                      'aiocqhttp',
                      'weixin_oc',
                    ].includes(platformTemplates[item]?.type ?? '')
                  "
                  activator="parent"
                  :text="
                    tm(
                      `createDialog.platformTooltips.${platformTemplates[item]?.type ?? ''}`,
                    )
                  "
                  location="end"
                  max-width="360"
                  open-delay="50"
                />
              </v-list-item>
            </template>
          </v-select>
          <div v-if="selectedPlatformConfig" class="mt-3">
            <div v-if="isLarkPlatform">
              <div class="creation-mode-title mt-4 mb-1">
                {{ tm('registrationAction.mode.title') }}
              </div>
              <v-radio-group
                :model-value="larkCreationMode"
                class="creation-mode-group"
                :aria-label="tm('registrationAction.mode.title')"
                hide-details
                @update:model-value="setLarkCreationMode"
              >
                <v-radio
                  value="scan"
                  :label="tm('registrationAction.mode.scan')"
                ></v-radio>
                <v-radio
                  value="manual"
                  :label="tm('registrationAction.mode.larkManual')"
                ></v-radio>
              </v-radio-group>

              <div
                v-if="larkCreationMode === 'scan'"
                class="registration-inline mt-3"
              >
                <v-text-field
                  :model-value="selectedPlatformConfig.id || ''"
                  :label="tm('registrationAction.platformIdLabel')"
                  :error="Boolean(scanPlatformIdError)"
                  :error-messages="scanPlatformIdError"
                  variant="outlined"
                  density="compact"
                  hide-details="auto"
                  class="registration-platform-id-field"
                  @update:model-value="emit('update:scan-platform-id', $event)"
                />
                <PlatformRegistrationAction
                  :platform-config="selectedPlatformConfig"
                  :active="larkCreationMode === 'scan'"
                  @created="emit('platform-registration-created', $event)"
                  @success="
                    emit('show-toast', {
                      message: $event,
                      type: 'success',
                    })
                  "
                  @error="
                    emit('show-toast', {
                      message: $event,
                      type: 'error',
                    })
                  "
                />
              </div>

              <div v-else-if="larkCreationMode === 'manual'" class="mt-2">
                <div class="platform-action-row">
                  <v-btn
                    color="info"
                    variant="tonal"
                    class="mt-2"
                    @click="openTutorial"
                  >
                    <v-icon start>mdi-help-circle-outline</v-icon>
                    {{ tm('dialog.viewTutorial') }}
                  </v-btn>
                </div>
                <AstrBotConfig
                  :iterable="selectedPlatformConfig"
                  :metadata="platformMetadata"
                  metadata-key="platform"
                />
              </div>
            </div>

            <div v-else-if="isDingtalkPlatform">
              <div class="creation-mode-title mt-4 mb-1">
                {{ tm('registrationAction.mode.title') }}
              </div>
              <v-radio-group
                :model-value="dingtalkCreationMode"
                class="creation-mode-group"
                :aria-label="tm('registrationAction.mode.title')"
                hide-details
                @update:model-value="setDingtalkCreationMode"
              >
                <v-radio
                  value="scan"
                  :label="tm('registrationAction.mode.scan')"
                ></v-radio>
                <v-radio
                  value="manual"
                  :label="tm('registrationAction.mode.manual')"
                ></v-radio>
              </v-radio-group>

              <div
                v-if="dingtalkCreationMode === 'scan'"
                class="registration-inline mt-3"
              >
                <v-text-field
                  :model-value="selectedPlatformConfig.id || ''"
                  :label="tm('registrationAction.platformIdLabel')"
                  :error="Boolean(scanPlatformIdError)"
                  :error-messages="scanPlatformIdError"
                  variant="outlined"
                  density="compact"
                  hide-details="auto"
                  class="registration-platform-id-field"
                  @update:model-value="emit('update:scan-platform-id', $event)"
                />
                <PlatformRegistrationAction
                  :platform-config="selectedPlatformConfig"
                  :active="dingtalkCreationMode === 'scan'"
                  @created="emit('platform-registration-created', $event)"
                  @success="
                    emit('show-toast', {
                      message: $event,
                      type: 'success',
                    })
                  "
                  @error="
                    emit('show-toast', {
                      message: $event,
                      type: 'error',
                    })
                  "
                />
              </div>

              <div v-else-if="dingtalkCreationMode === 'manual'" class="mt-2">
                <div class="platform-action-row">
                  <v-btn
                    color="info"
                    variant="tonal"
                    class="mt-2"
                    @click="openTutorial"
                  >
                    <v-icon start>mdi-help-circle-outline</v-icon>
                    {{ tm('dialog.viewTutorial') }}
                  </v-btn>
                </div>
                <AstrBotConfig
                  :iterable="selectedPlatformConfig"
                  :metadata="platformMetadata"
                  metadata-key="platform"
                />
              </div>
            </div>

            <div v-else-if="isQqOfficialPlatform">
              <div class="creation-mode-title mt-4 mb-1">
                {{ tm('registrationAction.mode.title') }}
              </div>
              <v-radio-group
                :model-value="qqOfficialCreationMode"
                class="creation-mode-group"
                :aria-label="tm('registrationAction.mode.title')"
                hide-details
                @update:model-value="setQqOfficialCreationMode"
              >
                <v-radio
                  value="scan"
                  :label="tm('registrationAction.mode.scan')"
                ></v-radio>
                <v-radio
                  value="manual"
                  :label="tm('registrationAction.mode.manual')"
                ></v-radio>
              </v-radio-group>

              <div
                v-if="qqOfficialCreationMode === 'scan'"
                class="registration-inline mt-3"
              >
                <v-text-field
                  :model-value="selectedPlatformConfig.id || ''"
                  :label="tm('registrationAction.platformIdLabel')"
                  :error="Boolean(scanPlatformIdError)"
                  :error-messages="scanPlatformIdError"
                  variant="outlined"
                  density="compact"
                  hide-details="auto"
                  class="registration-platform-id-field"
                  @update:model-value="emit('update:scan-platform-id', $event)"
                />
                <PlatformRegistrationAction
                  :platform-config="selectedPlatformConfig"
                  :active="qqOfficialCreationMode === 'scan'"
                  @created="emit('platform-registration-created', $event)"
                  @success="
                    emit('show-toast', {
                      message: $event,
                      type: 'success',
                    })
                  "
                  @error="
                    emit('show-toast', {
                      message: $event,
                      type: 'error',
                    })
                  "
                />
              </div>

              <div v-else-if="qqOfficialCreationMode === 'manual'" class="mt-2">
                <div class="platform-action-row">
                  <v-btn
                    color="info"
                    variant="tonal"
                    class="mt-2"
                    @click="openTutorial"
                  >
                    <v-icon start>mdi-help-circle-outline</v-icon>
                    {{ tm('dialog.viewTutorial') }}
                  </v-btn>
                </div>
                <AstrBotConfig
                  :iterable="selectedPlatformConfig"
                  :metadata="platformMetadata"
                  metadata-key="platform"
                />
              </div>
            </div>

            <div
              v-else-if="isWeixinOcPlatform"
              class="registration-inline mt-4"
            >
              <v-text-field
                :model-value="selectedPlatformConfig.id || ''"
                :label="tm('registrationAction.platformIdLabel')"
                :error="Boolean(scanPlatformIdError)"
                :error-messages="scanPlatformIdError"
                variant="outlined"
                density="compact"
                hide-details="auto"
                class="registration-platform-id-field"
                @update:model-value="emit('update:scan-platform-id', $event)"
              />
              <PlatformRegistrationAction
                :platform-config="selectedPlatformConfig"
                :active="isWeixinOcPlatform"
                @created="emit('platform-registration-created', $event)"
                @success="
                  emit('show-toast', {
                    message: $event,
                    type: 'success',
                  })
                "
                @error="
                  emit('show-toast', {
                    message: $event,
                    type: 'error',
                  })
                "
              />
            </div>

            <div v-else class="mt-2">
              <div class="platform-action-row">
                <v-btn
                  color="info"
                  variant="tonal"
                  class="mt-2"
                  @click="openTutorial"
                >
                  <v-icon start>mdi-help-circle-outline</v-icon>
                  {{ tm('dialog.viewTutorial') }}
                </v-btn>
              </div>
              <AstrBotConfig
                :iterable="selectedPlatformConfig"
                :metadata="platformMetadata"
                metadata-key="platform"
              />
            </div>
          </div>
        </div>
        <div v-else>
          <v-text-field
            v-model="updatingPlatformConfig.type"
            :label="tm('createDialog.platformTypeLabel')"
            variant="outlined"
            rounded="md"
            density="comfortable"
            hide-details
            class="mt-6 platform-type-field"
            disabled
          ></v-text-field>
          <div class="mt-3">
            <div class="mt-2">
              <AstrBotConfig
                :iterable="updatingPlatformConfig"
                :metadata="platformMetadata"
                metadata-key="platform"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fileApi } from '@/api/v1';
import AstrBotConfig from '@/components/shared/AstrBotConfig.vue';
import PlatformRegistrationAction from '@/components/platform/PlatformRegistrationAction.vue';
import { useModuleI18n } from '@/i18n/composables';
import {
  getPlatformIcon as getBasePlatformIcon,
  getTutorialLink,
} from '@/utils/platformUtils';
import {
  getString,
  type CreationMode,
  type PlatformConfigItem,
  type RecordValue,
  type RegistrationCreatedPayload,
  type ToastPayload,
} from './platformConfigHelpers';

defineOptions({
  name: 'PlatformCreationSection',
});

const props = defineProps<{
  updatingMode: boolean;
  platformTemplates: Record<string, PlatformConfigItem>;
  selectedPlatformType: string | null;
  selectedPlatformConfig: PlatformConfigItem | null;
  larkCreationMode: CreationMode;
  dingtalkCreationMode: CreationMode;
  qqOfficialCreationMode: CreationMode;
  isLarkPlatform: boolean;
  isDingtalkPlatform: boolean;
  isQqOfficialPlatform: boolean;
  isWeixinOcPlatform: boolean;
  scanPlatformIdError: string;
  updatingPlatformConfig: PlatformConfigItem;
  platformMetadata: RecordValue;
}>();

const emit = defineEmits<{
  'update:selected-platform-type': [value: string | null];
  'update:lark-creation-mode': [value: CreationMode];
  'update:dingtalk-creation-mode': [value: CreationMode];
  'update:qq-official-creation-mode': [value: CreationMode];
  'update:scan-platform-id': [value: string | null];
  'platform-registration-created': [data: RegistrationCreatedPayload];
  'show-toast': [payload: ToastPayload];
}>();

const { tm } = useModuleI18n('features/platform');

function getPlatformIcon(platformType: string | undefined): string | undefined {
  const normalizedType = getString(platformType);
  if (!normalizedType) {
    return undefined;
  }

  const template = props.platformTemplates[normalizedType];
  const logoToken = getString(template?.logo_token);
  if (logoToken) {
    return fileApi.tokenUrl(logoToken);
  }
  return getBasePlatformIcon(normalizedType);
}

function getPlatformTemplateIcon(templateKey: string): string | undefined {
  const template = props.platformTemplates[templateKey];
  return getPlatformIcon(getString(template?.type) ?? templateKey);
}

function openTutorial() {
  const platformType = getString(props.selectedPlatformConfig?.type);
  if (!platformType) {
    return;
  }
  window.open(getTutorialLink(platformType), '_blank');
}

function setLarkCreationMode(value: unknown) {
  emit('update:lark-creation-mode', value as CreationMode);
}

function setDingtalkCreationMode(value: unknown) {
  emit('update:dingtalk-creation-mode', value as CreationMode);
}

function setQqOfficialCreationMode(value: unknown) {
  emit('update:qq-official-creation-mode', value as CreationMode);
}
</script>

<style scoped>
.platform-dialog__step {
  display: flex;
  align-items: flex-start;
  width: 100%;
}

.platform-dialog__step-content {
  flex: 1;
}

.platform-type-field {
  min-width: 300px;
  max-width: 30%;
}

.platform-template-icon {
  width: 32px;
  height: 32px;
  margin-right: var(--astrbot-space-4);
  object-fit: contain;
}

.platform-action-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.creation-mode-title {
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}

.registration-inline {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  width: 320px;
  gap: 8px;
}

.registration-platform-id-field {
  width: 300px;
}
</style>
