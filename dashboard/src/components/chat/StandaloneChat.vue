<template>
  <div class="standalone-chat" v-on="dragEvents">
    <transition name="drop-fade">
      <div v-if="isDragging" class="chat-drop-overlay">
        <div class="chat-drop-overlay-content">
          <v-icon size="48" color="primary">mdi-cloud-upload</v-icon>
          <span class="chat-drop-text">{{ tm('input.dropToUpload') }}</span>
        </div>
      </div>
    </transition>
    <section ref="messagesContainer" class="standalone-messages">
      <div v-if="initializing" class="standalone-state">
        <v-progress-circular indeterminate size="28" width="3" />
      </div>

      <div v-else-if="!activeMessages.length" class="standalone-state">
        <div class="welcome-title">{{ tm('welcome.title') }}</div>
      </div>

      <ChatMessageList
        v-else
        :messages="activeMessages"
        :is-dark="isDark"
        :is-streaming="
          Boolean(currSessionId && isSessionRunning(currSessionId))
        "
      />
    </section>

    <section class="standalone-composer">
      <ChatInput
        ref="inputRef"
        v-model:prompt="draft"
        :staged-images-url="stagedImagesUrl"
        :staged-audio-url="stagedAudioUrl"
        :staged-files="stagedNonImageFiles"
        :failed-uploads="failedUploadViews"
        :active-uploads="activeUploadViews"
        :disabled="sending || initializing"
        :enable-streaming="enableStreaming"
        :enable-reasoning="enableReasoning"
        :is-recording="false"
        :is-running="Boolean(currSessionId && isSessionRunning(currSessionId))"
        :session-id="currSessionId || null"
        :current-session="currentSession"
        :config-id="configId || 'default'"
        :web-chat-tools-enabled="webChatToolsEnabled"
        send-shortcut="enter"
        @send="sendCurrentMessage"
        @stop="stopCurrentSession"
        @toggle-streaming="enableStreaming = !enableStreaming"
        @toggle-reasoning="enableReasoning = !enableReasoning"
        @remove-image="removeImage"
        @remove-audio="removeAudio"
        @remove-file="removeFile"
        @retry-failed-upload="retryFailedUpload"
        @discard-failed-upload="discardFailedUpload"
        @cancel-active-upload="cancelActiveUpload"
        @paste-image="handlePaste"
        @file-select="handleFilesSelected"
        @config-changed="handleChatConfigChange"
        @toggle-web-chat-tools="toggleWebChatTools"
      />
    </section>

    <DashboardStepUpDialog
      :model-value="stepUpDialogOpen"
      :loading="stepUpLoading"
      :error-message="stepUpError"
      @update:model-value="(value) => !value && cancelWebChatTools()"
      @confirm="submitStepUp"
      @cancel="cancelWebChatTools"
    />
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';
import { chatApi, configRouteApi } from '@/api/v1';
import ChatInput from '@/components/chat/ChatInput.vue';
import ChatMessageList from '@/components/chat/ChatMessageList.vue';
import DashboardStepUpDialog from '@/components/shared/DashboardStepUpDialog.vue';
import { useDragUpload } from '@/composables/useDragUpload';
import { useMediaHandling } from '@/composables/useMediaHandling';
import { useMessages, type TransportMode } from '@/composables/useMessages';
import type { MessagePart } from '@/domain/chat';
import type { Session } from '@/composables/useSessions';
import { useModuleI18n } from '@/i18n/composables';
import { useCustomizerStore } from '@/stores/customizer';
import { buildWebchatUmoDetails } from '@/utils/chatConfigBinding';
import { useDashboardStepUp } from '@/composables/useDashboardStepUp';

const props = withDefaults(defineProps<{ configId?: string | null }>(), {
  configId: 'default',
});

const { tm } = useModuleI18n('features/chat');
const customizer = useCustomizerStore();
const currSessionId = ref('');
const currentSession = ref<Session | null>(null);
const draft = ref('');
const initializing = ref(false);
const enableStreaming = ref(true);
const enableReasoning = ref(true);
const shouldStickToBottom = ref(true);
const messagesContainer = ref<HTMLElement | null>(null);
const inputRef = ref<InstanceType<typeof ChatInput> | null>(null);
const webChatStepUpTokens = ref<Record<string, string> | null>(null);
const webChatToolsEnabled = computed(() => webChatStepUpTokens.value !== null);

const isDark = computed(() => customizer.uiTheme === 'AstrBotDark');

const {
  stagedFiles,
  stagedImagesUrl,
  stagedAudioUrl,
  stagedNonImageFiles,
  processAndUploadImage,
  processAndUploadFile,
  handlePaste,
  removeImage,
  removeAudio,
  removeFile,
  failedUploadViews,
  activeUploadViews,
  retryFailedUpload,
  discardFailedUpload,
  cancelActiveUpload,
  clearStaged,
  cleanupMediaCache,
} = useMediaHandling();

const { isDragging, dragEvents } = useDragUpload((files) => {
  void handleFilesSelected(files);
});

const {
  sending,
  activeMessages,
  isSessionRunning,
  createLocalExchange,
  sendMessageStream,
  stopSession,
} = useMessages({
  currentSessionId: currSessionId,
  webchatStepUpTokens: webChatStepUpTokens,
  onStreamUpdate: () => {
    if (shouldStickToBottom.value) {
      scrollToBottom();
    }
  },
});

const {
  dialogOpen: stepUpDialogOpen,
  loading: stepUpLoading,
  errorMessage: stepUpError,
  webChatExpiresAt: webChatStepUpExpiresAt,
  requestWebChatStepUp,
  submitStepUp,
  cancelStepUp,
} = useDashboardStepUp();

watch(webChatStepUpExpiresAt, (expiresAt) => {
  if (expiresAt === null) webChatStepUpTokens.value = null;
});

watch(currSessionId, (sessionId, previousSessionId) => {
  if (!previousSessionId || sessionId === previousSessionId) return;
  cancelStepUp();
  webChatStepUpTokens.value = null;
});

const activeConfigId = ref<string | null>(null);

watch(
  () => props.configId,
  (configId, previousConfigId) => {
    const nextConfigId = configId || 'default';
    if (nextConfigId === (previousConfigId || 'default')) return;
    activeConfigId.value = nextConfigId;
    cancelStepUp();
    webChatStepUpTokens.value = null;
  },
);

const transportMode = computed<TransportMode>(() =>
  (localStorage.getItem('chat.transportMode') as TransportMode) === 'websocket'
    ? 'websocket'
    : 'sse',
);

onMounted(async () => {
  await ensureSession();
  inputRef.value?.focusInput();
});

onBeforeUnmount(() => {
  cleanupMediaCache();
});

async function ensureSession() {
  if (currSessionId.value) return currSessionId.value;
  initializing.value = true;
  try {
    const response = await chatApi.createSession();
    const session = response.data?.data as Session;
    currSessionId.value = session.session_id;
    currentSession.value = session;
    await bindConfigToSession(session.session_id);
    return session.session_id;
  } finally {
    initializing.value = false;
  }
}

async function bindConfigToSession(sessionId: string) {
  const confId = props.configId || 'default';
  const umo = buildWebchatUmoDetails(sessionId).umo;
  await configRouteApi.upsert(umo, { config_id: confId });
}

async function sendCurrentMessage() {
  if (!draft.value.trim() && !stagedFiles.value.length) return;
  const sessionId = await ensureSession();
  const text = draft.value.trim();
  const parts = buildOutgoingParts(text);
  const messageId = crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  const selection = inputRef.value?.getCurrentSelection();
  const { userRecord, botRecord } = createLocalExchange({
    sessionId,
    messageId,
    parts,
  });

  draft.value = '';
  clearStaged({ revokeUrls: false });
  scrollToBottom();
  await focusChatInput();

  sendMessageStream({
    sessionId,
    messageId,
    parts,
    transport: transportMode.value,
    enableStreaming: enableStreaming.value,
    enableReasoning: enableReasoning.value,
    selectedProvider: selection?.providerId || '',
    selectedModel: selection?.modelName || '',
    userRecord,
    botRecord,
  });
}

async function toggleWebChatTools() {
  if (webChatToolsEnabled.value) {
    cancelWebChatTools();
    return;
  }
  const sessionId = await ensureSession();
  const tokens = await requestWebChatStepUp(sessionId);
  if (tokens) webChatStepUpTokens.value = tokens;
}

function cancelWebChatTools() {
  cancelStepUp();
  webChatStepUpTokens.value = null;
}

function handleChatConfigChange(payload: {
  configId: string;
  agentRunnerType: string;
}) {
  const configId = payload.configId || 'default';
  const previousConfigId = activeConfigId.value;
  activeConfigId.value = configId;
  if (!previousConfigId || configId === previousConfigId) return;
  cancelWebChatTools();
}

function buildOutgoingParts(text: string): MessagePart[] {
  const parts: MessagePart[] = [];
  if (text) {
    parts.push({ type: 'plain', text });
  }
  stagedFiles.value.forEach((file) => {
    parts.push({
      type: file.type,
      attachment_id: file.attachment_id,
      filename: file.filename,
      embedded_url: file.url,
    });
  });
  return parts;
}

async function stopCurrentSession() {
  if (!currSessionId.value) return;
  await stopSession(currSessionId.value);
}

async function handleFilesSelected(files: FileList) {
  const selectedFiles = Array.from(files || []);
  for (const file of selectedFiles) {
    if (file.type.startsWith('image/')) {
      await processAndUploadImage(file);
    } else {
      await processAndUploadFile(file);
    }
  }
}

function scrollToBottom() {
  void nextTick(() => {
    const container = messagesContainer.value;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
    shouldStickToBottom.value = true;
  });
}

async function focusChatInput() {
  await nextTick();
  window.requestAnimationFrame(() => {
    inputRef.value?.focusInput();
  });
}
</script>

<style scoped>
.standalone-chat {
  --standalone-muted: rgba(var(--v-theme-on-surface), 0.62);
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  background: rgb(var(--v-theme-background));
}

.chat-drop-overlay {
  position: absolute;
  z-index: 100;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  border: 2px dashed rgba(var(--v-theme-primary), 0.45);
  border-radius: 16px;
  background-color: rgba(var(--v-theme-primary), 0.12);
}

.chat-drop-overlay-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.chat-drop-text {
  color: rgb(var(--v-theme-primary));
  font-size: 16px;
  font-weight: 500;
}

.drop-fade-enter-active,
.drop-fade-leave-active {
  transition: opacity 0.2s ease;
}

.drop-fade-enter-from,
.drop-fade-leave-to {
  opacity: 0;
}

.standalone-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 22px 14px;
}

.standalone-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.welcome-title {
  font-family: var(--astrbot-font-ui);
  font-size: 24px;
  font-weight: 700;
}

.standalone-composer {
  position: relative;
  z-index: 1;
  padding-bottom: 10px;
  background: rgb(var(--v-theme-background));
}

.standalone-composer::before {
  content: '';
  position: absolute;
  z-index: -1;
  left: 0;
  right: 0;
  top: -32px;
  height: 32px;
  pointer-events: none;
  background: linear-gradient(
    to bottom,
    rgba(var(--v-theme-background), 0),
    rgb(var(--v-theme-background))
  );
}

.standalone-composer :deep(.input-area) {
  border-top: 0;
}
</style>
