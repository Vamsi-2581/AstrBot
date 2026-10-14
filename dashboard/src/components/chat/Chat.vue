<template>
  <div
    v-if="props.active"
    class="chat-ui"
    :class="{ 'is-dark': isDark, 'sidebar-collapsed': isSidebarCollapsed }"
  >
    <ChatSidebar
      v-model:collapsed="sidebarCollapsed"
      v-model:transport-mode="transportMode"
      :is-sidebar-collapsed="isSidebarCollapsed"
      :projects="projects"
      :selected-project-id="selectedProjectId"
      :sessions="sidebarSessions"
      :curr-session-id="currSessionId"
      :is-provider-workspace="isProviderWorkspace"
      :loading-sessions="loadingSessions"
      :sessions-pagination="sessionsPagination"
      :is-dark="isDark"
      :is-touch-device="isTouchDevice"
      :language-options="languageOptions"
      :current-language="currentLanguage"
      :locale="locale"
      :is-session-running="isSessionRunning"
      @select-session="selectSession"
      @new-chat="startNewChat"
      @open-provider-workspace="openProviderWorkspace"
      @share-session="openShareDialog"
      @edit-session-title="editSidebarSessionTitle"
      @delete-session="deleteSidebarSession"
      @create-project="openCreateProjectDialog"
      @edit-project="openEditProjectDialog"
      @delete-project="handleDeleteProject"
      @select-project="selectProject"
      @switch-language="switchLanguage"
      @toggle-theme="toggleTheme"
      @load-sessions="handleLoadSessions"
      @search-sessions="handleSessionSearch"
    />

    <main
      class="chat-main"
      :class="{
        'empty-chat':
          !isProviderWorkspace &&
          !selectedProject &&
          !loadingMessages &&
          !activeMessages.length,
      }"
      v-on="dragEvents"
    >
      <transition name="drop-fade">
        <div
          v-if="isDragging && !isProviderWorkspace"
          class="chat-drop-overlay"
        >
          <div class="chat-drop-overlay-content">
            <v-icon size="48" color="primary">mdi-cloud-upload</v-icon>
            <span class="chat-drop-text">{{ tm('input.dropToUpload') }}</span>
          </div>
        </div>
      </transition>
      <section v-if="isProviderWorkspace" class="provider-workspace-shell">
        <ProviderChatCompletionPanel
          class="provider-workspace-page"
          :show-border="false"
        />
      </section>

      <ProjectView
        v-else-if="selectedProject"
        :project="selectedProject"
        :sessions="projectSessions"
        @select-session="selectProjectSession"
        @edit-session-title="editProjectSessionTitle"
        @delete-session="deleteProjectSession"
      >
        <ChatComposer
          ref="inputRef"
          project
          :chat-input-props="chatInputProps"
          :chat-input-listeners="chatInputListeners"
          :placeholder="tm('input.projectPlaceholder')"
        />
      </ProjectView>

      <template v-else>
        <section
          ref="messagesContainer"
          class="messages-panel"
          @scroll="handleMessagesScroll"
        >
          <v-progress-linear
            v-if="activeSessionPagination?.loading"
            class="history-loading"
            color="primary"
            height="2"
            indeterminate
            :aria-label="tm('history.loading')"
          />
          <div v-if="loadingMessages" class="center-state">
            <v-progress-circular indeterminate size="32" width="3" />
          </div>

          <div
            v-else-if="!activeMessages.length && activeSessionPagination?.error"
            class="welcome-state"
          >
            <ChatLoadError
              :message="tm('history.loadFailed')"
              :loading="loadingMessages"
              @retry="retryCurrentSessionLoad"
            />
          </div>

          <div v-else-if="sessionProject" class="session-project-breadcrumb">
            <span>{{ sessionProject.title }}</span>
            <v-icon size="16">mdi-chevron-right</v-icon>
            <span>{{ currentSessionTitle }}</span>
          </div>

          <div v-else-if="!activeMessages.length" class="welcome-state">
            <div class="welcome-title">{{ tm('welcome.title') }}</div>
          </div>

          <div
            v-if="!loadingMessages && activeMessages.length"
            class="messages-list-shell"
          >
            <ChatLoadError
              v-if="activeSessionPagination?.error"
              class="history-load-error"
              :message="tm('history.loadEarlierFailed')"
              :loading="activeSessionPagination.loading"
              @retry="retryCurrentSessionLoad"
            />
            <ChatMessageList
              v-model:edit-draft="messageEditDraft"
              :messages="activeMessages"
              :branch-labels="branchLabels"
              :is-dark="isDark"
              :is-streaming="
                Boolean(currSessionId && isSessionRunning(currSessionId))
              "
              :enable-edit="
                !Boolean(currSessionId && isSessionRunning(currSessionId))
              "
              enable-regenerate
              enable-thread-selection
              :is-touch-device="isTouchDevice"
              :sidebar-reasoning-message-id="
                reasoningPanelOpen
                  ? (activeReasoningTarget?.message.id ?? null)
                  : null
              "
              :sidebar-reasoning-block-index="
                reasoningPanelOpen
                  ? (activeReasoningTarget?.blockIndex ?? null)
                  : null
              "
              :manage-refs-sidebar="false"
              :editing-message-id="editingMessage?.id || null"
              :saving-edit="savingMessageEdit"
              @open-edit="openMessageEdit"
              @cancel-edit="cancelMessageEdit"
              @save-edit="saveMessageEdit"
              @regenerate="handleRegenerateMessage"
              @regenerate-with-model="handleRegenerateMessage"
              @select-bot-text="handleBotTextSelection"
              @open-thread="openThreadPanel"
              @open-reasoning="openReasoningPanel"
              @open-refs="openRefsSidebar"
              @select-branch="setBranchSelection"
            />
          </div>
        </section>

        <ChatComposer
          ref="inputRef"
          :chat-input-props="chatInputProps"
          :chat-input-listeners="chatInputListeners"
          :show-scroll-to-bottom="showScrollToBottom"
          @scroll-to-bottom="scrollToBottom"
        />
      </template>
    </main>

    <div
      v-if="threadSelection.visible"
      class="thread-selection-action"
      :style="{
        left: `${threadSelection.left}px`,
        top: `${threadSelection.top}px`,
      }"
    >
      <button
        class="thread-selection-button"
        type="button"
        @click="createThreadFromSelection"
      >
        {{ tm('thread.askInThread') }}
      </button>
    </div>

    <ProjectDialog
      v-model="projectDialogOpen"
      :project="editingProject"
      :saving="savingProject"
      @save="saveProject"
    />
    <SessionTitleDialog
      v-model="sessionTitleDialogOpen"
      v-model:title="sessionTitleDraft"
      :saving="savingSessionTitle"
      @save="saveSessionTitleDialog"
    />
    <ThreadPanel
      v-model="threadPanelOpen"
      :thread="activeThread"
      :is-dark="isDark"
      :is-touch-device="isTouchDevice"
      :deleting="deletingThread"
      :web-chat-step-up-tokens="webChatStepUpTokens"
      :get-provider-selection="getSelectedProviderSelection"
      @delete="deleteThread"
      @consume-step-up="webChatStepUpTokens = null"
    />
    <ReasoningSidebar
      v-model="reasoningPanelOpen"
      :parts="activeReasoningParts"
      :is-dark="isDark"
    />
    <RefsSidebar v-model="refsSidebarOpen" :refs="selectedRefs" />
    <DashboardStepUpDialog
      :model-value="stepUpDialogOpen"
      :loading="stepUpLoading"
      :error-message="stepUpError"
      @update:model-value="(value) => !value && cancelWebChatTools()"
      @confirm="submitStepUp"
      @cancel="cancelWebChatTools"
    />
    <ShareSessionDialog
      v-model="shareDialogOpen"
      :session-id="shareSessionId"
    />
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  provide,
  reactive,
  ref,
  watch,
} from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDisplay } from 'vuetify';
import { isAxiosError } from 'axios';
import { chatApi, providerApi } from '@/api/v1';
import ProjectDialog, {
  type ProjectFormData,
} from '@/components/chat/ProjectDialog.vue';
import type { Project } from '@/components/chat/ProjectList.vue';
import ProjectView from '@/components/chat/ProjectView.vue';
import ChatSidebar from '@/components/chat/ChatSidebar.vue';
import ChatComposer from '@/components/chat/ChatComposer.vue';
import SessionTitleDialog from '@/components/chat/SessionTitleDialog.vue';
import {
  formatUsagePercent,
  readStoredValue,
  readTokenCount,
  writeStoredValue,
} from '@/components/chat/chatHelpers';
import DashboardStepUpDialog from '@/components/shared/DashboardStepUpDialog.vue';
import ChatMessageList from '@/components/chat/ChatMessageList.vue';
import ChatLoadError from '@/components/chat/ChatLoadError.vue';
import ShareSessionDialog from '@/components/chat/ShareSessionDialog.vue';
import type { RegenerateModelSelection } from '@/components/chat/RegenerateMenu.vue';
import ReasoningSidebar from '@/components/chat/ReasoningSidebar.vue';
import ThreadPanel from '@/components/chat/ThreadPanel.vue';
import RefsSidebar from '@/components/chat/message_list_comps/RefsSidebar.vue';
import { useSessions, type Session } from '@/composables/useSessions';
import type { MultiModelSelection } from '@/components/chat/MultiModelMenu.vue';
import {
  messageBlocks as buildMessageBlocks,
  useMessages,
  type TransportMode,
} from '@/composables/useMessages';
import type { ChatRecord, ChatThread, MessagePart } from '@/domain/chat';
import { useMediaHandling } from '@/composables/useMediaHandling';
import { useRecording } from '@/composables/useRecording';
import { useProjects } from '@/composables/useProjects';
import { useDragUpload } from '@/composables/useDragUpload';
import { useProviderModelSelection } from '@/composables/useProviderModelSelection';
import { useCustomizerStore } from '@/stores/customizer';
import ProviderChatCompletionPanel from '@/components/provider/ProviderChatCompletionPanel.vue';
import { useLanguageSwitcher, useModuleI18n } from '@/i18n/composables';
import { askForConfirmation, useConfirmDialog } from '@/utils/confirmDialog';
import {
  contextLimit,
  formatTokenCount,
  type ProviderModelMetadata,
  type ProviderMetadataSource,
} from '@/utils/providerMetadata';
import { useToast } from '@/utils/toast';
import { truncate } from '@/utils/text';
import { readChatDraft, writeChatDraft } from '@/utils/chatDraftStorage';
import { useDashboardStepUp } from '@/composables/useDashboardStepUp';

const props = withDefaults(
  defineProps<{ chatboxMode?: boolean; active?: boolean }>(),
  {
    chatboxMode: false,
    active: true,
  },
);

const route = useRoute();
const router = useRouter();
const { lgAndUp } = useDisplay();
const customizer = useCustomizerStore();
const { tm } = useModuleI18n('features/chat');
const confirmDialog = useConfirmDialog();
const toast = useToast();
const webChatStepUpTokens = ref<Record<string, string> | null>(null);
const webChatToolsEnabled = computed(() => webChatStepUpTokens.value !== null);
const { languageOptions, currentLanguage, switchLanguage, locale } =
  useLanguageSwitcher();
const {
  sessions,
  sessionsPagination,
  currSessionId,
  getSessions,
  setSessionSearch,
  newSession,
  newChat,
  deleteSession,
  updateSessionTitle,
} = useSessions(props.chatboxMode);

function handleSessionSearch(value: string) {
  void setSessionSearch(value);
}

const {
  projects,
  selectedProjectId,
  getProjects,
  createProject,
  updateProject,
  deleteProject: deleteProjectById,
  addSessionToProject,
  getProjectSessions,
} = useProjects();

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

type WorkspaceView = 'chat' | 'providers';

const sidebarCollapsed = ref(false);
interface TokenProviderConfig extends ProviderMetadataSource {
  id: string;
  enable?: boolean;
}

const activeWorkspace = ref<WorkspaceView>('chat');
const projectDialogOpen = ref(false);
const editingProject = ref<Project | null>(null);
const savingProject = ref(false);
const sessionTitleDialogOpen = ref(false);
const sessionTitleDraft = ref('');
const editingSessionTitleId = ref('');
const refreshProjectSessionsAfterTitleSave = ref(false);
const savingSessionTitle = ref(false);
const messageEditDraft = ref('');
const editingMessage = ref<ChatRecord | null>(null);
const savingMessageEdit = ref(false);
const projectSessions = ref<Session[]>([]);
const loadingSessions = ref(false);
const draftOwner = readStoredValue('user');
const draft = ref(readChatDraft(draftOwner, currSessionId.value));
const tokenProviderConfigs = ref<TokenProviderConfig[]>([]);
const tokenModelMetadata = ref<Record<string, ProviderModelMetadata>>({});
const selectedTokenProviderId = ref('');
const messagesContainer = ref<HTMLElement | null>(null);
const inputRef = ref<InstanceType<typeof ChatComposer> | null>(null);
const shouldStickToBottom = ref(true);
const suppressAutoScroll = ref(false);
let autoScrollFrame: number | null = null;
const LOAD_EARLIER_SCROLL_THRESHOLD = 120;
const replyTarget = ref<ChatRecord | null>(null);
const threadPanelOpen = ref(false);
const activeThread = ref<ChatThread | null>(null);
const reasoningPanelOpen = ref(false);
const activeReasoningTarget = ref<{
  message: ChatRecord;
  blockIndex: number;
} | null>(null);
const deletingThread = ref(false);
const refsSidebarOpen = ref(false);
const selectedRefs = ref<Record<string, unknown> | undefined>(undefined);
const threadSelection = reactive<{
  visible: boolean;
  left: number;
  top: number;
  message: ChatRecord | null;
  selectedText: string;
}>({
  visible: false,
  left: 0,
  top: 0,
  message: null,
  selectedText: '',
});
const enableStreaming = ref(true);
const enableReasoning = ref(true);
const sendShortcut = ref<'enter' | 'shift_enter'>('enter');
const DRAFT_SAVE_DELAY_MS = 300;
let activeDraftSessionId = currSessionId.value;
let draftSaveTimer: number | null = null;
const {
  isRecording,
  startRecording: startRecorder,
  stopRecording: stopRecorder,
} = useRecording();
const isSidebarCollapsed = computed(() =>
  lgAndUp.value ? sidebarCollapsed.value : !customizer.chatSidebarOpen,
);
const isProviderWorkspace = computed(
  () => activeWorkspace.value === 'providers',
);
const { isDragging, dragEvents } = useDragUpload((files) => {
  if (isProviderWorkspace.value) return;
  void handleFilesSelected(files);
});
const activeReasoningParts = computed<MessagePart[]>(() => {
  if (!activeReasoningTarget.value) return [];
  const blocks = buildMessageBlocks(
    activeReasoningTarget.value.message.content || { type: 'bot', message: [] },
  );
  const block = blocks[activeReasoningTarget.value.blockIndex];
  return block?.kind === 'thinking' ? block.parts : [];
});

watch(reasoningPanelOpen, (open) => {
  if (!open) {
    activeReasoningTarget.value = null;
  }
});

const {
  loadingMessages,
  sending,
  loadedSessions,
  paginationBySession,
  sessionProjects,
  sessionDetails,
  activeMessages,
  isSessionRunning,
  isUserMessage,
  messageParts,
  loadSessionMessages,
  loadEarlierMessages,
  createLocalExchange,
  createLocalBranchRecord,
  branchLabels,
  setBranchSelection,
  sendMessageStream,
  editMessage,
  continueEditedMessage,
  regenerateMessage,
  stopSession,
} = useMessages({
  currentSessionId: currSessionId,
  webchatStepUpTokens: webChatStepUpTokens,
  onSessionsChanged: getSessions,
  onStreamUpdate: (sessionId) => {
    if (sessionId === currSessionId.value && shouldStickToBottom.value) {
      scrollToBottom();
    }
  },
  onMcpInputRequest: (payload, respond) => {
    const server = String(payload.server_name || 'MCP server');
    const message = String(
      payload.message || 'This MCP server requests input.',
    );
    if (payload.mode === 'url') {
      const url = String(payload.url || '');
      if (
        window.confirm(
          tm('interaction.openUrl', {
            server,
            message,
            url: String(payload.url_display || url),
          }),
        )
      ) {
        window.open(url, '_blank', 'noopener,noreferrer');
        respond({ action: 'accept' });
      } else {
        respond({ action: 'cancel' });
      }
      return;
    }
    const schema = payload.schema as {
      properties?: Record<string, { type?: string; title?: string }>;
      required?: string[];
    };
    if (!schema?.properties) {
      respond({ action: 'cancel' });
      return;
    }
    if (!window.confirm(tm('interaction.formAccept', { server, message }))) {
      respond({ action: 'decline' });
      return;
    }
    const content: Record<string, unknown> = {};
    for (const [name, definition] of Object.entries(schema.properties)) {
      const value = window.prompt(
        tm('interaction.fieldPrompt', { field: definition.title || name }),
        '',
      );
      if (value === null) {
        respond({ action: 'cancel' });
        return;
      }
      if (definition.type === 'integer')
        content[name] = Number.parseInt(value, 10);
      else if (definition.type === 'number') content[name] = Number(value);
      else if (definition.type === 'boolean')
        content[name] = value.toLowerCase() === 'true';
      else content[name] = value;
    }
    if ((schema.required || []).some((name) => content[name] === '')) {
      window.alert(tm('interaction.invalidForm'));
      respond({ action: 'cancel' });
      return;
    }
    respond({ action: 'accept', content });
  },
});

const multiModelEnabled = ref(false);
const multiModelMax = ref(3);
const multiModelSelection = ref<MultiModelSelection[]>([]);

async function loadChatFeatures() {
  try {
    const response = await chatApi.getFeatures();
    const data = response.data.data;
    multiModelEnabled.value = Boolean(data?.multi_model?.enable);
    multiModelMax.value = data?.multi_model?.max_models || 3;
    if (!multiModelEnabled.value) {
      multiModelSelection.value = [];
    }
  } catch (error) {
    console.error('Failed to load chat features:', error);
  }
}

const activeSessionPagination = computed(() =>
  currSessionId.value
    ? paginationBySession.get(currSessionId.value)
    : undefined,
);

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

const shareDialogOpen = ref(false);
const shareSessionId = ref('');
function openShareDialog(session: Session) {
  shareSessionId.value = session.session_id;
  shareDialogOpen.value = true;
}

watch(currSessionId, (sessionId, previousSessionId) => {
  if (!previousSessionId || sessionId === previousSessionId) return;
  cancelStepUp();
  webChatStepUpTokens.value = null;
});

const activeConfigId = ref<string | null>(null);

const transportMode = ref<TransportMode>(
  (readStoredValue('chat.transportMode') as TransportMode) === 'websocket'
    ? 'websocket'
    : 'sse',
);

const pointerMediaQuery = window.matchMedia('(pointer: coarse)');
const isTouchDevice = ref<boolean>(pointerMediaQuery.matches);
const handlePointerChange = (event: MediaQueryListEvent) => {
  isTouchDevice.value = event.matches;
};
pointerMediaQuery.addEventListener('change', handlePointerChange);

watch(transportMode, (mode) => {
  writeStoredValue('chat.transportMode', mode);
});

watch(draft, (value) => {
  if (draftSaveTimer !== null) window.clearTimeout(draftSaveTimer);
  const sessionId = activeDraftSessionId;
  draftSaveTimer = window.setTimeout(() => {
    writeChatDraft(draftOwner, sessionId, value);
    draftSaveTimer = null;
  }, DRAFT_SAVE_DELAY_MS);
});

watch(currSessionId, (sessionId) => {
  flushDraft();
  activeDraftSessionId = sessionId;
  draft.value = readChatDraft(draftOwner, sessionId);
});

const isDark = computed(() => customizer.uiTheme === 'AstrBotDark');
const canSend = computed(
  () =>
    Boolean(draft.value.trim() || stagedFiles.value.length) && !sending.value,
);
const currentSession = computed(
  () =>
    sessions.value.find(
      (session) => session.session_id === currSessionId.value,
    ) ||
    projectSessions.value.find(
      (session) => session.session_id === currSessionId.value,
    ) ||
    sessionDetails.get(currSessionId.value) ||
    null,
);
const sessionProject = computed(() =>
  currSessionId.value
    ? (sessionProjects.get(currSessionId.value) ?? null)
    : null,
);
const sidebarSessions = computed<Session[]>(() => {
  const current = currentSession.value;
  if (
    current &&
    !sessionProject.value &&
    !sessions.value.some((session) => session.session_id === current.session_id)
  ) {
    return [current, ...sessions.value];
  }
  return sessions.value;
});
const currentSessionTitle = computed(() =>
  currentSession.value ? sessionTitle(currentSession.value) : '',
);
const selectedProject = computed(
  () =>
    projects.value.find(
      (project) => project.project_id === selectedProjectId.value,
    ) || null,
);
const chatInputReplyTarget = computed(() =>
  replyTarget.value?.id === null || replyTarget.value?.id === undefined
    ? null
    : {
        messageId: replyTarget.value.id,
        selectedText: replyPreview(replyTarget.value.id, ''),
      },
);
const currentTokenProvider = computed(() => {
  const selectedProvider = tokenProviderConfigs.value.find(
    (provider) => provider.id === selectedTokenProviderId.value,
  );
  return selectedProvider || tokenProviderConfigs.value[0] || null;
});
const currentTokenMetadata = computed(() => {
  const model = currentTokenProvider.value?.model;
  return model ? tokenModelMetadata.value[model] || null : null;
});
const latestContextTokens = computed(() => {
  for (let index = activeMessages.value.length - 1; index >= 0; index -= 1) {
    const message = activeMessages.value[index];
    if (isUserMessage(message)) continue;
    const stats = message.content?.agentStats;
    if (!stats) continue;
    if (
      stats.current_context_tokens !== undefined &&
      stats.current_context_tokens !== null
    ) {
      return readTokenCount(stats.current_context_tokens);
    }
    const usage = stats.token_usage;
    if (!usage) continue;
    return (
      readTokenCount(usage.input_other) +
      readTokenCount(usage.input_cached) +
      readTokenCount(usage.output)
    );
  }
  return 0;
});
const tokenUsageIndicator = computed(() => {
  const used = latestContextTokens.value;
  const limit = contextLimit(
    currentTokenProvider.value,
    currentTokenMetadata.value,
  );
  if (used <= 0 || limit <= 0) return null;

  const percent = (used / limit) * 100;
  return {
    used,
    limit,
    percent: Math.min(100, Math.max(0, percent)),
    tooltip: tm('tokenUsage.tooltip', {
      used: formatTokenCount(used),
      limit: formatTokenCount(limit),
      percent: formatUsagePercent(percent),
    }),
  };
});

const chatInputProps = computed(() => ({
  prompt: draft.value,
  stagedImagesUrl: stagedImagesUrl.value,
  stagedAudioUrl: stagedAudioUrl.value,
  stagedFiles: stagedNonImageFiles.value,
  failedUploads: failedUploadViews.value,
  activeUploads: activeUploadViews.value,
  disabled: sending.value,
  enableStreaming: enableStreaming.value,
  enableReasoning: enableReasoning.value,
  isRecording: isRecording.value,
  isRunning: Boolean(
    currSessionId.value && isSessionRunning(currSessionId.value),
  ),
  tokenUsage: tokenUsageIndicator.value,
  webChatToolsEnabled: webChatToolsEnabled.value,
  sessionId: currSessionId.value || null,
  currentSession: currentSession.value,
  replyTo: chatInputReplyTarget.value,
  sendShortcut: sendShortcut.value,
  multiModelEnabled: multiModelEnabled.value,
  multiModelMax: multiModelMax.value,
  multiModelSelection: multiModelSelection.value,
}));

const chatInputListeners = {
  send: sendCurrentMessage,
  stop: stopCurrentSession,
  toggleStreaming,
  toggleReasoning: () => {
    enableReasoning.value = !enableReasoning.value;
  },
  removeImage,
  removeAudio,
  removeFile,
  retryFailedUpload,
  discardFailedUpload,
  cancelActiveUpload,
  startRecording,
  stopRecording,
  pasteImage: handlePaste,
  fileSelect: handleFilesSelected,
  clearReply: () => {
    replyTarget.value = null;
  },
  configChanged: handleChatConfigChange,
  toggleWebChatTools,
  'update:prompt': (value: string) => {
    draft.value = value;
  },
  'update:multiModelSelection': (value: MultiModelSelection[]) => {
    multiModelSelection.value = value;
  },
};

function getSelectedProviderSelection() {
  const inputSelection = inputRef.value?.getCurrentSelection();
  if (inputSelection?.providerId) {
    selectedTokenProviderId.value = inputSelection.providerId;
    return inputSelection;
  }
  if (typeof window === 'undefined') {
    return { providerId: '', modelName: '' };
  }
  syncSelectedTokenProvider();
  return {
    providerId: readStoredValue('selectedProvider'),
    modelName: readStoredValue('selectedProviderModel'),
  };
}

const {
  selectedProviderId: currentProviderId,
  selectedModelName: currentModelName,
  setSelection: setProviderSelection,
} = useProviderModelSelection();

const SESSION_PROVIDER_STORAGE_PREFIX = 'chat.sessionProvider.';

/** Read a validated provider/model choice for one chat session. */
function readSessionProviderSelection(sessionId: string) {
  try {
    const raw = readStoredValue(SESSION_PROVIDER_STORAGE_PREFIX + sessionId);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.providerId === 'string' && parsed.providerId) {
      return {
        providerId: parsed.providerId,
        modelName: typeof parsed.modelName === 'string' ? parsed.modelName : '',
      };
    }
  } catch {
    // Ignore corrupted entries.
  }
  return null;
}

/** Persist a provider/model choice without blocking chat interactions. */
function writeSessionProviderSelection(
  sessionId: string,
  selection: { providerId?: string; modelName?: string } | null,
) {
  if (!sessionId || !selection?.providerId) return;
  try {
    writeStoredValue(
      SESSION_PROVIDER_STORAGE_PREFIX + sessionId,
      JSON.stringify({
        providerId: selection.providerId,
        modelName: selection.modelName || '',
      }),
    );
  } catch {
    // Session model persistence must not block chat flows.
  }
}

// Remember the model picked by the user for the active session.
watch([currentProviderId, currentModelName], ([providerId, modelName]) => {
  if (!currSessionId.value || !providerId) return;
  writeSessionProviderSelection(currSessionId.value, {
    providerId,
    modelName,
  });
});

provide('isDark', isDark);

onMounted(async () => {
  window.addEventListener('beforeunload', flushDraft);
  loadingSessions.value = true;
  try {
    await Promise.all([
      getSessions(),
      getProjects(),
      loadTokenProviders(),
      loadChatFeatures(),
    ]);
    const routeSessionId = getRouteSessionId();
    if (routeSessionId === 'models') {
      activeWorkspace.value = 'providers';
    } else if (routeSessionId) {
      await selectSession(routeSessionId, false);
    }
  } finally {
    loadingSessions.value = false;
  }
});

onBeforeUnmount(() => {
  flushDraft();
  window.removeEventListener('beforeunload', flushDraft);
  if (autoScrollFrame !== null) {
    window.cancelAnimationFrame(autoScrollFrame);
    autoScrollFrame = null;
  }
  pointerMediaQuery.removeEventListener('change', handlePointerChange);
  cleanupMediaCache();
});

watch(
  () => route.params.conversationId,
  async () => {
    const routeSessionId = getRouteSessionId();
    if (routeSessionId === 'models') {
      activeWorkspace.value = 'providers';
      return;
    }
    if (routeSessionId && routeSessionId !== currSessionId.value) {
      showChatWorkspace();
      selectedProjectId.value = null;
      await selectSession(routeSessionId, false);
    } else if (!routeSessionId && currSessionId.value) {
      showChatWorkspace();
      currSessionId.value = '';
    }
  },
);

watch(activeMessages, () => {
  if (!suppressAutoScroll.value && shouldStickToBottom.value) {
    scrollToBottom();
  }
});

function getRouteSessionId() {
  const raw = route.params.conversationId;
  return Array.isArray(raw) ? raw[0] : raw || '';
}

function basePath() {
  return props.chatboxMode ? '/chatbox' : '/chat';
}

function closeMobileSidebar() {
  if (!lgAndUp.value) {
    customizer.SET_CHAT_SIDEBAR(false);
  }
}

function closeSecondaryPanels() {
  threadSelection.visible = false;
  threadPanelOpen.value = false;
  activeThread.value = null;
  reasoningPanelOpen.value = false;
  activeReasoningTarget.value = null;
  refsSidebarOpen.value = false;
  selectedRefs.value = undefined;
}

function showChatWorkspace() {
  activeWorkspace.value = 'chat';
}

async function openProviderWorkspace() {
  closeSecondaryPanels();
  activeWorkspace.value = 'providers';
  const targetPath = `${basePath()}/models`;
  if (route.path !== targetPath) {
    await router.push(targetPath);
  }
  closeMobileSidebar();
}

function sessionTitle(session: Session) {
  return session.display_name?.trim() || tm('conversation.newConversation');
}

function syncSelectedTokenProvider() {
  if (typeof window === 'undefined') return;
  selectedTokenProviderId.value = readStoredValue('selectedProvider');
}

async function loadTokenProviders() {
  syncSelectedTokenProvider();
  try {
    const response = await providerApi.listByProviderType('chat_completion');
    if (response.data.status === 'ok') {
      tokenModelMetadata.value = (response.data.model_metadata || {}) as Record<
        string,
        ProviderModelMetadata
      >;
      tokenProviderConfigs.value = (
        (response.data.data || []) as unknown as TokenProviderConfig[]
      ).filter((provider) => provider.enable !== false);
    }
  } catch (error) {
    console.error('Failed to load provider context metadata:', error);
  }
}

async function startNewChat() {
  showChatWorkspace();
  selectedProjectId.value = null;
  replyTarget.value = null;
  newChat();
  closeMobileSidebar();
  await focusChatInput();
}

function openCreateProjectDialog() {
  editingProject.value = null;
  projectDialogOpen.value = true;
}

function openEditProjectDialog(project: Project) {
  editingProject.value = project;
  projectDialogOpen.value = true;
}

/** Open a project and return keyboard focus to the composer. */
async function selectProject(projectId: string) {
  showChatWorkspace();
  selectedProjectId.value = projectId;
  currSessionId.value = '';
  replyTarget.value = null;
  await router.push(basePath());
  await loadProjectSessions(projectId);
  closeMobileSidebar();
  await focusChatInput();
}

async function loadProjectSessions(projectId = selectedProjectId.value) {
  if (!projectId) {
    projectSessions.value = [];
    return;
  }
  projectSessions.value = await getProjectSessions(projectId);
}

async function handleDeleteProject(projectId: string) {
  const ok = await deleteProjectById(projectId);
  if (!ok) return;
  if (selectedProjectId.value === projectId) {
    selectedProjectId.value = null;
    projectSessions.value = [];
  }
}

function openSessionTitleDialog(
  sessionId: string,
  title: string,
  refreshProjectSessions = false,
) {
  editingSessionTitleId.value = sessionId;
  sessionTitleDraft.value = title;
  refreshProjectSessionsAfterTitleSave.value = refreshProjectSessions;
  sessionTitleDialogOpen.value = true;
}

/** Save a session title and refresh the list that currently owns it. */
async function saveSessionTitleDialog() {
  if (!editingSessionTitleId.value) return;

  savingSessionTitle.value = true;
  try {
    const sessionId = editingSessionTitleId.value;
    const displayName = sessionTitleDraft.value.trim();
    await chatApi.updateSession(sessionId, {
      display_name: displayName,
    });
    updateSessionTitle(sessionId, displayName);
    const sessionDetail = sessionDetails.get(sessionId);
    if (sessionDetail) {
      sessionDetail.display_name = displayName;
    }
    const projectSession = projectSessions.value.find(
      (session) => session.session_id === sessionId,
    );
    if (projectSession) {
      projectSession.display_name = displayName;
    }
    if (refreshProjectSessionsAfterTitleSave.value) {
      await loadProjectSessions();
    } else {
      await getSessions();
    }
    sessionTitleDialogOpen.value = false;
  } finally {
    savingSessionTitle.value = false;
  }
}

function editSidebarSessionTitle(session: Session) {
  openSessionTitleDialog(session.session_id, session.display_name || '');
}

async function deleteSidebarSession(session: Session) {
  const title = sessionTitle(session);
  const message = tm('conversation.confirmDelete', { name: title });
  if (!(await askForConfirmation(message, confirmDialog))) return;

  const wasCurrent = currSessionId.value === session.session_id;
  if (!(await deleteSession(session.session_id))) return;
  writeChatDraft(draftOwner, session.session_id, '');
  if (wasCurrent && !currSessionId.value) {
    selectedProjectId.value = null;
    await router.push(basePath());
  }
}

async function selectProjectSession(sessionId: string) {
  selectedProjectId.value = null;
  await selectSession(sessionId);
}

async function editProjectSessionTitle(sessionId: string, title: string) {
  openSessionTitleDialog(sessionId, title, true);
}

async function deleteProjectSession(sessionId: string) {
  if (!(await deleteSession(sessionId))) return;
  writeChatDraft(draftOwner, sessionId, '');
  await loadProjectSessions();
}

async function saveProject(formData: ProjectFormData, projectId?: string) {
  savingProject.value = true;
  try {
    const ok = projectId
      ? await updateProject(
          projectId,
          formData.title,
          formData.emoji,
          formData.description,
        )
      : await createProject(
          formData.title,
          formData.emoji,
          formData.description,
        );
    if (ok) {
      projectDialogOpen.value = false;
      editingProject.value = null;
    }
  } finally {
    savingProject.value = false;
  }
}

/** Select a session and restore its provider before any asynchronous loading. */
async function selectSession(sessionId: string, pushRoute = true) {
  showChatWorkspace();
  selectedProjectId.value = null;
  currSessionId.value = sessionId;
  replyTarget.value = null;
  const storedSelection = readSessionProviderSelection(sessionId);
  if (storedSelection) {
    setProviderSelection(storedSelection.providerId, storedSelection.modelName);
  } else {
    writeSessionProviderSelection(sessionId, getSelectedProviderSelection());
  }
  if (pushRoute && route.path !== `${basePath()}/${sessionId}`) {
    await router.push(`${basePath()}/${sessionId}`);
    if (currSessionId.value !== sessionId) return;
  }
  if (!loadedSessions.get(sessionId)) {
    await loadSessionMessages(sessionId);
    if (currSessionId.value !== sessionId) return;
  }
  scrollToBottom();
  closeMobileSidebar();
  await focusChatInput();
}

/** Create the target session if needed, then start one chat request. */
async function sendCurrentMessage() {
  if (!canSend.value) return;

  const draftSessionId = activeDraftSessionId;
  const draftText = draft.value;
  const text = draftText.trim();
  const outgoingParts = buildOutgoingParts(text);
  sending.value = true;
  try {
    let sessionId = currSessionId.value;
    const targetProjectId = selectedProjectId.value;
    const targetProject = selectedProject.value;
    if (!sessionId) {
      sessionId = await newSession();
      await nextTick();
      draft.value = draftText;
      if (targetProjectId) {
        await addSessionToProject(sessionId, targetProjectId);
        sessionProjects.set(
          sessionId,
          targetProject
            ? {
                project_id: targetProject.project_id,
                title: targetProject.title,
                emoji: targetProject.emoji,
              }
            : null,
        );
        await loadProjectSessions(targetProjectId);
        selectedProjectId.value = null;
      }
      // Refresh only after the project association completes. Otherwise the
      // newly created project session briefly appears in the ordinary list.
      await getSessions();
    }

    const messageId = crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`;
    const selection = getSelectedProviderSelection();
    const branchModels =
      multiModelEnabled.value && multiModelSelection.value.length > 1
        ? multiModelSelection.value
        : [];
    const primaryModel = branchModels[0];
    if (primaryModel) {
      writeSessionProviderSelection(sessionId, {
        providerId: primaryModel.provider,
        modelName: primaryModel.model,
      });
    } else {
      writeSessionProviderSelection(sessionId, selection);
    }
    const { userRecord, botRecord } = createLocalExchange({
      sessionId,
      messageId,
      parts: outgoingParts,
    });
    updateTitleFromText(sessionId, text);

    if (draftSaveTimer !== null) {
      window.clearTimeout(draftSaveTimer);
      draftSaveTimer = null;
    }
    writeChatDraft(draftOwner, draftSessionId, '');
    writeChatDraft(draftOwner, activeDraftSessionId, '');
    draft.value = '';
    replyTarget.value = null;
    clearStaged({ revokeUrls: false });
    scrollToBottom();

    if (branchModels.length > 1) {
      const groupId = messageId;
      const total = branchModels.length;
      const primaryBranch = {
        group_id: groupId,
        index: 0,
        total,
        provider: primaryModel.provider,
        model: primaryModel.model,
      };
      botRecord.branchGroup = primaryBranch;
      const labels = branchLabels.get(groupId) || [];
      labels[0] = primaryModel.model || primaryModel.provider;
      branchLabels.set(groupId, labels);

      sendMessageStream({
        sessionId,
        messageId,
        parts: outgoingParts,
        transport: 'sse',
        enableStreaming: enableStreaming.value,
        enableReasoning: enableReasoning.value,
        selectedProvider: primaryModel.provider,
        selectedModel: primaryModel.model,
        userRecord,
        botRecord,
        branch: primaryBranch,
      });

      branchModels.slice(1).forEach((model, offset) => {
        const index = offset + 1;
        const branchId = `${messageId}-branch-${index}`;
        const branch = {
          group_id: groupId,
          index,
          total,
          provider: model.provider,
          model: model.model,
        };
        const branchRecord = createLocalBranchRecord(
          sessionId,
          branchId,
          branch,
        );
        sendMessageStream({
          sessionId,
          messageId: branchId,
          parts: outgoingParts,
          transport: 'sse',
          enableStreaming: enableStreaming.value,
          enableReasoning: enableReasoning.value,
          selectedProvider: model.provider,
          selectedModel: model.model,
          botRecord: branchRecord,
          skipUserHistory: true,
          branch,
        });
      });
    } else {
      sendMessageStream({
        sessionId,
        messageId,
        parts: outgoingParts,
        transport: transportMode.value,
        enableStreaming: enableStreaming.value,
        enableReasoning: enableReasoning.value,
        selectedProvider: selection?.providerId || '',
        selectedModel: selection?.modelName || '',
        userRecord,
        botRecord,
      });
    }
  } catch (error) {
    console.error('Failed to send message:', error);
  } finally {
    sending.value = false;
    await focusChatInput();
  }
}

function flushDraft() {
  if (draftSaveTimer !== null) {
    window.clearTimeout(draftSaveTimer);
    draftSaveTimer = null;
  }
  writeChatDraft(draftOwner, activeDraftSessionId, draft.value);
}

async function toggleWebChatTools() {
  if (webChatToolsEnabled.value) {
    cancelWebChatTools();
    return;
  }
  const sessionId = currSessionId.value || (await newSession());
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
  if (!previousConfigId || previousConfigId === configId) return;
  // A proof is bound to the config route as well as the WebChat session.
  // Clear it immediately when the user changes the selected profile instead
  // of relying on a later authorization failure.
  cancelWebChatTools();
}

function buildOutgoingParts(text: string): MessagePart[] {
  const parts: MessagePart[] = [];
  if (replyTarget.value?.id !== null && replyTarget.value?.id !== undefined) {
    parts.push({
      type: 'reply',
      message_id: replyTarget.value.id,
      selected_text: '',
    });
  }
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

function updateTitleFromText(sessionId: string, text: string) {
  const session = sessions.value.find((item) => item.session_id === sessionId);
  if (!session || session.display_name || !text) return;
  updateSessionTitle(sessionId, text.slice(0, 40));
}

function replyPreview(messageId?: string | number, fallback?: string) {
  if (fallback) return truncate(fallback, 80);
  const found = activeMessages.value.find(
    (message) => String(message.id) === String(messageId),
  );
  const text = found ? plainTextFromMessage(found) : '';
  return text ? truncate(text, 80) : tm('reply.replyTo');
}

function plainTextFromMessage(message: ChatRecord) {
  return messageParts(message)
    .filter((part) => part.type === 'plain' && part.text)
    .map((part) => part.text)
    .join('\n');
}

function scrollToMessage(messageId?: string | number) {
  if (!messageId) return;
  const index = activeMessages.value.findIndex(
    (message) => String(message.id) === String(messageId),
  );
  if (index < 0) return;
  const rows = messagesContainer.value?.querySelectorAll('.message-row');
  rows?.[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function openMessageEdit(message: ChatRecord) {
  messageEditDraft.value = plainTextFromMessage(message);
  editingMessage.value = message;
  void nextTick(() => {
    scrollToMessage(message.id);
  });
}

function cancelMessageEdit() {
  editingMessage.value = null;
  messageEditDraft.value = '';
}

async function saveMessageEdit() {
  if (!currSessionId.value || !editingMessage.value) return;
  const sessionId = currSessionId.value;
  const target = editingMessage.value;
  savingMessageEdit.value = true;
  try {
    const result = await editMessage(sessionId, target, messageEditDraft.value);
    if (
      currSessionId.value !== sessionId ||
      !activeMessages.value.includes(target)
    ) {
      cancelMessageEdit();
      return;
    }
    cancelMessageEdit();

    if (result.needsRegenerate && result.truncatedAfterMessage) {
      const selection = getSelectedProviderSelection();
      continueEditedMessage({
        sessionId,
        sourceRecord: target,
        enableStreaming: enableStreaming.value,
        enableReasoning: enableReasoning.value,
        selectedProvider: selection?.providerId || '',
        selectedModel: selection?.modelName || '',
      });
      scrollToBottom();
    } else if (result.needsRegenerate) {
      const index = activeMessages.value.findIndex(
        (message) => String(message.id) === String(target.id),
      );
      const nextBot = activeMessages.value
        .slice(index + 1)
        .find((message) => !isUserMessage(message));
      if (nextBot) {
        await handleRegenerateMessage(nextBot);
      }
    }
  } catch (error) {
    console.error('Failed to edit message:', error);
  } finally {
    savingMessageEdit.value = false;
  }
}

/** Regenerate a bot message with the selected or restored provider. */
async function handleRegenerateMessage(
  message: ChatRecord,
  selection?: RegenerateModelSelection,
) {
  if (!currSessionId.value || isUserMessage(message)) return;
  const resolvedSelection = selection ?? getSelectedProviderSelection();
  writeSessionProviderSelection(currSessionId.value, resolvedSelection);
  message.threads = [];
  await regenerateMessage(
    currSessionId.value,
    message,
    resolvedSelection?.providerId || '',
    resolvedSelection?.modelName || '',
    enableStreaming.value,
    enableReasoning.value,
  );
}

function handleBotTextSelection(event: MouseEvent, message: ChatRecord) {
  if (
    message.id === null ||
    message.id === undefined ||
    String(message.id).startsWith('local-')
  )
    return;
  const container = event.currentTarget as HTMLElement | null;
  window.setTimeout(() => {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim() || '';
    if (!selection || !selectedText) {
      threadSelection.visible = false;
      return;
    }
    if (
      !container ||
      !container.contains(selection.anchorNode) ||
      !container.contains(selection.focusNode)
    ) {
      threadSelection.visible = false;
      return;
    }
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    threadSelection.message = message;
    threadSelection.selectedText = selectedText;
    threadSelection.left = Math.min(
      window.innerWidth - 180,
      Math.max(12, rect.left + rect.width / 2 - 70),
    );
    threadSelection.top = Math.max(12, rect.top - 42);
    threadSelection.visible = true;
  }, 0);
}

async function createThreadFromSelection() {
  const message = threadSelection.message;
  if (!currSessionId.value || !message?.id || !threadSelection.selectedText)
    return;
  try {
    const response = await chatApi.createThread({
      session_id: currSessionId.value,
      parent_message_id: message.id,
      selected_text: threadSelection.selectedText,
    });
    if (response.data?.status !== 'ok') {
      toast.error(response.data?.message || tm('thread.createFailed'));
      return;
    }
    const thread = response.data?.data as ChatThread | undefined;
    if (!thread) {
      toast.error(tm('thread.createFailed'));
      return;
    }
    message.threads = message.threads || [];
    if (!message.threads.some((item) => item.thread_id === thread.thread_id)) {
      message.threads.push(thread);
    }
    openThreadPanel(thread);
    window.getSelection()?.removeAllRanges();
  } catch (error) {
    toast.error(
      isAxiosError(error)
        ? error.response?.data?.message || error.message
        : tm('thread.createFailed'),
    );
    console.error('Failed to create thread:', error);
  } finally {
    threadSelection.visible = false;
  }
}

function openThreadPanel(thread: ChatThread) {
  reasoningPanelOpen.value = false;
  activeReasoningTarget.value = null;
  refsSidebarOpen.value = false;
  activeThread.value = thread;
  threadPanelOpen.value = true;
}

function openRefsSidebar(refs: unknown) {
  threadPanelOpen.value = false;
  activeThread.value = null;
  reasoningPanelOpen.value = false;
  activeReasoningTarget.value = null;
  selectedRefs.value =
    refs && typeof refs === 'object'
      ? (refs as Record<string, unknown>)
      : undefined;
  refsSidebarOpen.value = true;
}

function openReasoningPanel(payload: {
  message: ChatRecord;
  blockIndex: number;
}) {
  threadPanelOpen.value = false;
  activeThread.value = null;
  refsSidebarOpen.value = false;
  selectedRefs.value = undefined;
  activeReasoningTarget.value = payload;
  reasoningPanelOpen.value = true;
}

async function deleteThread(thread: ChatThread) {
  if (deletingThread.value) return;
  if (!(await askForConfirmation(tm('thread.confirmDelete'), confirmDialog)))
    return;
  deletingThread.value = true;
  try {
    await chatApi.deleteThread(thread.thread_id);
    removeThreadFromMessages(thread.thread_id);
    if (activeThread.value?.thread_id === thread.thread_id) {
      threadPanelOpen.value = false;
      activeThread.value = null;
    }
  } catch (error) {
    console.error('Failed to delete thread:', error);
  } finally {
    deletingThread.value = false;
  }
}

function removeThreadFromMessages(threadId: string) {
  for (const message of activeMessages.value) {
    if (!message.threads?.length) continue;
    message.threads = message.threads.filter(
      (thread) => thread.thread_id !== threadId,
    );
  }
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

function toggleStreaming() {
  enableStreaming.value = !enableStreaming.value;
}

async function startRecording() {
  try {
    await startRecorder();
  } catch (error) {
    console.error('Failed to start recording:', error);
    toast.error(tm('voice.error'));
  }
}

async function stopRecording() {
  try {
    const audioFile = await stopRecorder();
    const uploaded = await processAndUploadFile(audioFile);
    if (!uploaded) {
      toast.error(tm('voice.error'));
    }
  } catch (error) {
    console.error('Failed to stop recording:', error);
    toast.error(tm('voice.error'));
  }
}

const showScrollToBottom = computed(
  () =>
    !shouldStickToBottom.value &&
    activeMessages.value.length > 0 &&
    !loadingMessages.value,
);

function handleMessagesScroll() {
  threadSelection.visible = false;
  const container = messagesContainer.value;
  if (!container) return;
  const distance =
    container.scrollHeight - container.scrollTop - container.clientHeight;
  shouldStickToBottom.value = distance < 80;
  maybeLoadEarlierOnScroll(container);
}

async function loadEarlierWithAnchor() {
  const sessionId = currSessionId.value;
  if (!sessionId || activeSessionPagination.value?.loading) return;
  const container = messagesContainer.value;
  const firstMessage = activeMessages.value[0];
  const firstId =
    firstMessage?.id === undefined || firstMessage?.id === null
      ? ''
      : String(firstMessage.id);
  const beforeScrollTop = Math.max(0, container?.scrollTop || 0);
  const beforeTop = firstId
    ? container
        ?.querySelector<HTMLElement>(
          `[data-message-id="${CSS.escape(firstId)}"]`,
        )
        ?.getBoundingClientRect().top
    : undefined;
  suppressAutoScroll.value = true;
  try {
    await loadEarlierMessages(sessionId);
    if (currSessionId.value !== sessionId) return;
    await nextTick();
    if (beforeTop === undefined || !container || !firstId) return;
    const row = container.querySelector<HTMLElement>(
      `[data-message-id="${CSS.escape(firstId)}"]`,
    );
    if (row) {
      const currentScrollTop = Math.max(0, container.scrollTop);
      const userScrollDelta = currentScrollTop - beforeScrollTop;
      container.scrollTop +=
        row.getBoundingClientRect().top - beforeTop + userScrollDelta;
    }
  } finally {
    suppressAutoScroll.value = false;
  }
}

async function retryCurrentSessionLoad() {
  const sessionId = currSessionId.value;
  if (!sessionId || activeSessionPagination.value?.loading) return;
  if (activeMessages.value.length && activeSessionPagination.value?.has_more) {
    await loadEarlierWithAnchor();
    return;
  }
  await loadSessionMessages(sessionId, true, true);
}

/** Load the next sidebar page when the sidebar requests more sessions. */
function handleLoadSessions(append: boolean) {
  void getSessions(append);
}

function maybeLoadEarlierOnScroll(container: HTMLElement) {
  const sessionId = currSessionId.value;
  const pagination = activeSessionPagination.value;
  if (!sessionId || !pagination) return;
  if (!pagination.has_more || pagination.loading || pagination.error) return;
  if (container.scrollHeight <= container.clientHeight) return;
  if (container.scrollTop > LOAD_EARLIER_SCROLL_THRESHOLD) return;
  void loadEarlierWithAnchor();
}

function scrollToBottom() {
  // Coalesce stream, mutation, and resize notifications into one scroll per frame.
  if (autoScrollFrame !== null) return;
  autoScrollFrame = window.requestAnimationFrame(() => {
    autoScrollFrame = null;
    const container = messagesContainer.value;
    if (!container || suppressAutoScroll.value) return;
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

async function stopCurrentSession() {
  if (!currSessionId.value) return;
  try {
    await stopSession(currSessionId.value);
  } catch (error) {
    console.error('Failed to stop session:', error);
  }
}

function toggleTheme() {
  customizer.SET_THEME_MODE(isDark.value ? 'light' : 'dark');
}
</script>

<style scoped>
.chat-ui {
  --chat-sidebar-bg: rgb(var(--v-theme-surface));
  --chat-session-active-bg: rgb(var(--v-theme-surface-variant));
  --chat-page-bg: rgb(var(--v-theme-background));
  --chat-border: rgb(var(--v-theme-outline-variant));
  --chat-muted: rgb(var(--v-theme-on-surface-variant));
  display: flex;
  flex: 1 1 0%;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--chat-page-bg);
  color: rgb(var(--v-theme-on-surface));
  font-family: var(--astrbot-font-ui);
}

:global(.dashboard-appearance-active .chat-ui) {
  --chat-page-bg: transparent;
  --chat-sidebar-bg: var(--dashboard-wallpaper-surface);
}

.chat-main {
  flex: 1 1 0%;
  min-width: 0;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  align-self: stretch;
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

.chat-main.empty-chat {
  justify-content: center;
}

.provider-workspace-shell {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.provider-workspace-page {
  height: 100%;
  min-height: 0;
}

.messages-panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-anchor: none;
  padding: 24px max(24px, calc((100% - 980px) / 2)) 18px;
}

.history-loading {
  position: sticky;
  top: 0;
  z-index: 2;
  pointer-events: none;
}

.history-load-error {
  margin: 0 auto 12px;
}

.empty-chat .messages-panel {
  flex: 0 0 auto;
  min-height: auto;
  overflow: visible;
  padding: 0 max(24px, calc((100% - 980px) / 2)) 20px;
}

.center-state,
.welcome-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-chat .welcome-state {
  height: auto;
}

.welcome-title {
  font-size: 28px;
  font-weight: 800;
}

.welcome-subtitle {
  margin-top: 8px;
  color: var(--chat-muted);
  font-size: 16px;
}

.session-project-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: min(760px, 82%);
  margin-bottom: 18px;
  color: var(--chat-muted);
  font-size: 13px;
  font-weight: 500;
}

.session-project-breadcrumb span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thread-selection-action {
  position: fixed;
  z-index: 1200;
  pointer-events: auto;
}

.thread-selection-button {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.14);
  border-radius: 999px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

kbd {
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  font: inherit;
}

:deep(.hr-node) {
  margin-top: 1.25rem;
  margin-bottom: 1.25rem;
  opacity: 0.5;
  border-top-width: 0.3px;
}

:deep(.paragraph-node) {
  margin: 0.5rem 0;
  line-height: 1.7;
}

:deep(.list-node) {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

@media (max-width: 760px) {
  .messages-panel {
    padding: 18px 14px;
  }
}
</style>
