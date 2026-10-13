<template>
  <v-navigation-drawer
    v-model="chatSidebarDrawer"
    class="chat-sidebar"
    :class="{ collapsed: isSidebarCollapsed }"
    :permanent="lgAndUp"
    :temporary="!lgAndUp"
    :rail="lgAndUp && collapsed"
    :width="280"
    :rail-width="68"
    location="left"
    floating
  >
    <div class="sidebar-top">
      <div v-if="lgAndUp" class="brand-row">
        <v-btn
          icon
          size="small"
          variant="text"
          class="sidebar-toggle"
          @click="emit('update:collapsed', !collapsed)"
        >
          <v-icon
            size="20"
            class="sidebar-action-icon"
            :class="{ 'chevron-collapsed': isSidebarCollapsed }"
          >
            mdi-chevron-left
          </v-icon>
        </v-btn>
      </div>

      <v-btn
        class="new-chat-btn sidebar-provider-btn"
        :class="{
          'icon-only': isSidebarCollapsed,
          'sidebar-workspace-btn--active': isProviderWorkspace,
        }"
        variant="text"
        :icon="isSidebarCollapsed"
        @click="emit('open-provider-workspace')"
      >
        <v-icon
          size="20"
          class="sidebar-action-icon"
          :class="{ 'mr-2': !isSidebarCollapsed }"
          >mdi-creation</v-icon
        >
        <span v-if="!isSidebarCollapsed">{{
          tm('actions.providerConfig')
        }}</span>
      </v-btn>

      <v-btn
        class="new-chat-btn"
        :class="{ 'icon-only': isSidebarCollapsed }"
        variant="text"
        :icon="isSidebarCollapsed"
        @click="emit('new-chat')"
      >
        <v-icon
          size="20"
          class="sidebar-action-icon"
          :class="{ 'mr-2': !isSidebarCollapsed }"
          >mdi-square-edit-outline</v-icon
        >
        <span v-if="!isSidebarCollapsed">{{ tm('actions.newChat') }}</span>
      </v-btn>

      <ProjectList
        v-if="!isSidebarCollapsed"
        :projects="projects"
        :selected-project-id="selectedProjectId"
        @create-project="emit('create-project')"
        @edit-project="emit('edit-project', $event)"
        @delete-project="emit('delete-project', $event)"
        @select-project="emit('select-project', $event)"
      />
    </div>

    <div v-if="!isSidebarCollapsed" class="session-search">
      <v-text-field
        :model-value="sessionSearchInput"
        density="compact"
        variant="solo-filled"
        flat
        hide-details
        clearable
        prepend-inner-icon="mdi-magnify"
        :placeholder="tm('conversation.searchPlaceholder')"
        :aria-label="tm('conversation.searchPlaceholder')"
        @update:model-value="onSessionSearchInput"
      />
    </div>

    <div
      v-if="!isSidebarCollapsed"
      ref="sidebarContent"
      class="session-list"
      @scroll.passive="loadMoreSessions"
    >
      <div
        v-for="session in sessions"
        :key="session.session_id"
        class="session-item"
        :class="{
          active: !isProviderWorkspace && currSessionId === session.session_id,
        }"
        role="button"
        tabindex="0"
        @click="emit('select-session', session.session_id)"
        @keydown.enter="emit('select-session', session.session_id)"
        @keydown.space.prevent="emit('select-session', session.session_id)"
      >
        <span v-if="!isSidebarCollapsed" class="session-title">{{
          sessionTitle(session)
        }}</span>
        <div class="session-actions" @click.stop>
          <v-btn
            icon="mdi-share-variant-outline"
            size="x-small"
            variant="text"
            class="session-action-btn"
            :title="tm('actions.share')"
            @click="emit('share-session', session)"
          />
          <v-btn
            icon="mdi-pencil-outline"
            size="x-small"
            variant="text"
            class="session-action-btn"
            :title="tm('conversation.editDisplayName')"
            @click="emit('edit-session-title', session)"
          />
          <v-btn
            icon="mdi-delete-outline"
            size="x-small"
            variant="text"
            class="session-action-btn"
            :title="tm('actions.deleteChat')"
            @click="emit('delete-session', session)"
          />
        </div>
        <v-progress-circular
          v-if="isSessionRunning(session.session_id)"
          class="session-progress"
          indeterminate
          size="16"
          width="2"
        />
      </div>

      <div
        v-if="!isSidebarCollapsed && !sessions.length && !loadingSessions"
        class="empty-sessions"
      >
        {{ tm('conversation.noHistory') }}
      </div>

      <v-progress-linear
        v-if="sessionsPagination.loading"
        color="primary"
        height="2"
        indeterminate
        :aria-label="tm('conversation.loading')"
      />
      <ChatLoadError
        v-if="sessionsPagination.error"
        :message="tm('conversation.loadFailed')"
        :loading="sessionsPagination.loading"
        @retry="emit('load-sessions', sessionsPagination.append)"
      />
    </div>

    <div class="sidebar-footer">
      <StyledMenu
        location="top start"
        offset="10"
        :close-on-content-click="false"
      >
        <template #activator="{ props: menuProps }">
          <v-btn
            v-bind="menuProps"
            class="settings-btn"
            :class="{ 'icon-only': isSidebarCollapsed }"
            variant="text"
            :icon="isSidebarCollapsed"
          >
            <v-icon
              size="20"
              class="sidebar-action-icon"
              :class="{ 'mr-2': !isSidebarCollapsed }"
              >mdi-cog-outline</v-icon
            >
            <span v-if="!isSidebarCollapsed">{{
              t('core.common.settings')
            }}</span>
          </v-btn>
        </template>

        <div class="settings-menu-content">
          <v-menu
            location="end"
            offset="8"
            :open-on-hover="!isTouchDevice"
            :open-on-click="isTouchDevice"
            :close-on-content-click="true"
          >
            <template #activator="{ props: transportMenuProps }">
              <v-list-item
                v-bind="transportMenuProps"
                class="styled-menu-item"
                rounded="md"
              >
                <template #prepend>
                  <v-icon size="18">mdi-connection</v-icon>
                </template>
                <v-list-item-title>{{
                  tm('transport.title')
                }}</v-list-item-title>
                <template #append>
                  <span class="settings-menu-value">{{
                    currentTransportLabel
                  }}</span>
                  <v-icon size="18">mdi-chevron-right</v-icon>
                </template>
              </v-list-item>
            </template>

            <v-card class="styled-menu-card" elevation="4" rounded="md">
              <v-list density="compact" class="styled-menu-list pa-1">
                <v-list-item
                  v-for="item in transportOptions"
                  :key="item.value"
                  class="styled-menu-item"
                  :class="{
                    'styled-menu-item-active': transportMode === item.value,
                  }"
                  rounded="md"
                  @click="emit('update:transport-mode', item.value)"
                >
                  <v-list-item-title>{{ tm(item.labelKey) }}</v-list-item-title>
                  <template #append>
                    <v-icon v-if="transportMode === item.value" size="18">
                      mdi-check
                    </v-icon>
                  </template>
                </v-list-item>
              </v-list>
            </v-card>
          </v-menu>

          <v-menu
            location="end"
            offset="8"
            :open-on-hover="!isTouchDevice"
            :open-on-click="isTouchDevice"
            :close-on-content-click="true"
          >
            <template #activator="{ props: languageMenuProps }">
              <v-list-item
                v-bind="languageMenuProps"
                class="styled-menu-item"
                rounded="md"
              >
                <template #prepend>
                  <v-icon size="18">mdi-translate</v-icon>
                </template>
                <v-list-item-title>{{
                  t('core.common.language')
                }}</v-list-item-title>
                <template #append>
                  <span class="settings-menu-value">{{
                    currentLanguage?.label || locale
                  }}</span>
                  <v-icon size="18">mdi-chevron-right</v-icon>
                </template>
              </v-list-item>
            </template>

            <v-card class="styled-menu-card" elevation="4" rounded="md">
              <v-list density="compact" class="styled-menu-list pa-1">
                <v-list-item
                  v-for="lang in languageOptions"
                  :key="lang.value"
                  class="styled-menu-item"
                  :class="{
                    'styled-menu-item-active': locale === lang.value,
                  }"
                  rounded="md"
                  @click="emit('switch-language', lang.value as Locale)"
                >
                  <template #prepend>
                    <span class="language-flag">{{ lang.flag }}</span>
                  </template>
                  <v-list-item-title>{{ lang.label }}</v-list-item-title>
                  <template #append>
                    <v-icon v-if="locale === lang.value" size="18">
                      mdi-check
                    </v-icon>
                  </template>
                </v-list-item>
              </v-list>
            </v-card>
          </v-menu>

          <v-list-item
            class="styled-menu-item"
            rounded="md"
            @click="emit('toggle-theme')"
          >
            <template #prepend>
              <v-icon size="18">{{
                isDark ? 'mdi-white-balance-sunny' : 'mdi-weather-night'
              }}</v-icon>
            </template>
            <v-list-item-title>{{
              isDark ? tm('modes.lightMode') : tm('modes.darkMode')
            }}</v-list-item-title>
          </v-list-item>
        </div>
      </StyledMenu>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useDisplay } from 'vuetify';
import StyledMenu from '@/components/shared/StyledMenu.vue';
import ProjectList, { type Project } from '@/components/chat/ProjectList.vue';
import ChatLoadError from '@/components/chat/ChatLoadError.vue';
import { useCustomizerStore } from '@/stores/customizer';
import { useI18n, useModuleI18n } from '@/i18n/composables';
import type { Locale } from '@/i18n/types';
import type { Session } from '@/composables/useSessions';
import type { TransportMode } from '@/composables/useMessages';

interface LanguageOption {
  value: string;
  label: string;
  flag: string;
}

interface SidebarPagination {
  loading: boolean;
  error: boolean;
  append: boolean;
  hasMore: boolean;
}

interface Props {
  collapsed: boolean;
  isSidebarCollapsed: boolean;
  projects: Project[];
  selectedProjectId: string | null;
  sessions: Session[];
  currSessionId: string;
  isProviderWorkspace: boolean;
  loadingSessions: boolean;
  sessionsPagination: SidebarPagination;
  transportMode: TransportMode;
  isDark: boolean;
  isTouchDevice: boolean;
  languageOptions: LanguageOption[];
  currentLanguage?: LanguageOption;
  locale: Locale;
  isSessionRunning: (sessionId: string) => boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'select-session': [sessionId: string];
  'new-chat': [];
  'open-provider-workspace': [];
  'share-session': [session: Session];
  'edit-session-title': [session: Session];
  'delete-session': [session: Session];
  'create-project': [];
  'edit-project': [project: Project];
  'delete-project': [projectId: string];
  'select-project': [projectId: string];
  'update:transport-mode': [mode: TransportMode];
  'switch-language': [locale: Locale];
  'toggle-theme': [];
  'update:collapsed': [collapsed: boolean];
  'load-sessions': [append: boolean];
  'search-sessions': [value: string];
}>();

const { t } = useI18n();
const { tm } = useModuleI18n('features/chat');
const { lgAndUp } = useDisplay();
const customizer = useCustomizerStore();

const chatSidebarDrawer = computed({
  get: () => lgAndUp.value || customizer.chatSidebarOpen,
  set: (value: boolean) => {
    if (!lgAndUp.value) {
      customizer.SET_CHAT_SIDEBAR(value);
    }
  },
});

const transportOptions: Array<{ value: TransportMode; labelKey: string }> = [
  { value: 'sse', labelKey: 'transport.sse' },
  { value: 'websocket', labelKey: 'transport.websocket' },
];
const currentTransportLabel = computed(() =>
  tm(
    transportOptions.find((item) => item.value === props.transportMode)
      ?.labelKey || 'transport.sse',
  ),
);

const sessionSearchInput = ref('');
let sessionSearchTimer: ReturnType<typeof setTimeout> | null = null;
function onSessionSearchInput(value: string) {
  sessionSearchInput.value = value ?? '';
  if (sessionSearchTimer) {
    clearTimeout(sessionSearchTimer);
  }
  sessionSearchTimer = setTimeout(() => {
    emit('search-sessions', sessionSearchInput.value);
  }, 250);
}
onBeforeUnmount(() => {
  if (sessionSearchTimer) {
    clearTimeout(sessionSearchTimer);
  }
});

const sidebarContent = ref<HTMLElement | null>(null);

/** Request the next sidebar page when the scroll container nears its end. */
function loadMoreSessions() {
  const container = sidebarContent.value;
  if (
    !container ||
    container.clientHeight === 0 ||
    props.isSidebarCollapsed ||
    !props.sessionsPagination.hasMore ||
    props.sessionsPagination.loading ||
    props.sessionsPagination.error
  ) {
    return;
  }
  if (
    container.scrollHeight - container.scrollTop - container.clientHeight >
    120
  ) {
    return;
  }
  emit('load-sessions', true);
}

watch(
  [
    () => props.sessionsPagination.loading,
    () => props.sessions.length,
    () => props.isSidebarCollapsed,
  ],
  () => {
    void nextTick(loadMoreSessions);
  },
  { flush: 'post' },
);

function sessionTitle(session: Session) {
  return session.display_name?.trim() || tm('conversation.newConversation');
}
</script>

<style scoped>
.chat-sidebar {
  height: 100%;
  background: var(--chat-sidebar-bg);
}

.chat-sidebar.collapsed {
  background: transparent;
}

.chat-sidebar :deep(.v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-top {
  padding: 12px;
}

.brand-row {
  display: flex;
  align-items: center;
}

.brand-row {
  justify-content: flex-start;
  min-height: 36px;
  margin-bottom: 8px;
}

.sidebar-toggle,
.new-chat-btn,
.settings-btn {
  color: var(--chat-muted);
  border-radius: 8px;
}

.sidebar-action-icon {
  color: currentcolor;
}

.sidebar-toggle {
  width: 40px;
  height: 40px;
  min-width: 40px;
}

.new-chat-btn,
.settings-btn {
  width: 100%;
  justify-content: flex-start;
  border-radius: 8px;
  text-transform: none;
  font-weight: 500;
}

.sidebar-provider-btn {
  margin-bottom: 8px;
}

.new-chat-btn:not(.icon-only),
.settings-btn:not(.icon-only) {
  padding-inline: 12px;
}

.new-chat-btn.icon-only,
.settings-btn.icon-only {
  width: 40px;
  height: 40px;
  min-width: 40px;
  justify-content: center;
}

.chat-sidebar.collapsed .brand-row,
.chat-sidebar.collapsed .sidebar-footer {
  display: flex;
  justify-content: center;
}

.sidebar-toggle:hover,
.new-chat-btn:hover,
.settings-btn:hover {
  background: var(--chat-session-active-bg);
}

.sidebar-workspace-btn--active {
  background: var(--chat-session-active-bg);
  color: rgb(var(--v-theme-on-surface));
}

.chevron-collapsed {
  transform: rotate(180deg);
}

.session-search {
  padding: 4px 12px 0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  width: 100%;
  min-height: 38px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  padding-right: 68px;
  position: relative;
  box-sizing: border-box;
  cursor: pointer;
  text-align: left;
}

.session-item:hover,
.session-item.active {
  background: var(--chat-session-active-bg);
}

.session-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
}

.session-progress {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  flex-shrink: 0;
  transition: right 0.16s ease;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0;
  pointer-events: none;
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  visibility: hidden;
}

.session-item:hover .session-actions,
.session-item:focus-within .session-actions {
  opacity: 1;
  pointer-events: auto;
  visibility: visible;
}

.session-item:hover .session-progress,
.session-item:focus-within .session-progress {
  right: 62px;
}

.session-action-btn {
  color: var(--chat-muted);
}

.session-action-btn:hover {
  color: rgb(var(--v-theme-on-surface));
}

.empty-sessions {
  padding: 12px;
  color: var(--chat-muted);
  font-size: 13px;
}

.sidebar-footer {
  margin-top: auto;
  padding: 10px 12px 14px;
}

.settings-menu-content {
  min-width: 230px;
  padding: 6px;
}

.settings-menu-value {
  color: var(--chat-muted);
  font-size: 12px;
  margin-right: 4px;
  max-width: 92px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.language-flag {
  display: inline-block;
  width: 20px;
  margin-right: 8px;
}
</style>
