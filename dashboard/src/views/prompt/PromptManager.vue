<template>
  <div class="prompt-manager">
    <div class="prompt-workbench">
      <!-- 文件夹侧栏 - 仅桌面端显示 -->
      <aside class="prompt-workbench__sidebar">
        <div class="prompt-panel__head">
          <h2 class="prompt-panel__title">{{ tm('folder.sidebarTitle') }}</h2>
          <v-btn
            icon="mdi-folder-plus"
            variant="text"
            size="small"
            :title="tm('folder.createButton')"
            :aria-label="tm('folder.createButton')"
            @click="showCreateFolderDialog = true"
          />
        </div>
        <FolderTree
          class="prompt-panel__tree"
          @move-folder="openMoveFolderDialog"
          @success="showSuccess"
          @error="showError"
          @prompt-dropped="handlePromptDropped"
        />
      </aside>

      <div class="prompt-workbench__divider" aria-hidden="true"></div>

      <!-- 主内容区 -->
      <main class="prompt-workbench__main">
        <div class="prompt-main__head">
          <FolderBreadcrumb class="prompt-main__breadcrumb" />
          <div class="prompt-main__actions">
            <v-btn
              variant="outlined"
              prepend-icon="mdi-upload"
              rounded="md"
              @click="triggerImport"
            >
              {{ tm('buttons.import') }}
            </v-btn>
            <v-btn
              color="primary"
              variant="tonal"
              prepend-icon="mdi-plus"
              rounded="md"
              @click="openCreatePromptDialog"
            >
              {{ tm('buttons.create') }}
            </v-btn>
            <input
              ref="importFileInput"
              type="file"
              accept="application/json,.json"
              hidden
              @change="handleImportFile"
            />
          </div>
        </div>

        <div class="prompt-main__body">
          <!-- 加载状态 - 只有加载超过阈值才显示骨架屏 -->
          <v-fade-transition>
            <div v-if="showSkeleton" class="prompt-skeleton">
              <v-skeleton-loader
                v-for="n in 6"
                :key="n"
                type="card"
                rounded="md"
              />
            </div>
          </v-fade-transition>

          <template v-if="!loading">
            <!-- 子文件夹区域 -->
            <section v-if="currentFolders.length > 0" class="prompt-section">
              <h3 class="prompt-section__title">
                <v-icon size="small">mdi-folder</v-icon>
                {{ tm('folder.foldersTitle') }} ({{ currentFolders.length }})
              </h3>
              <div class="prompt-grid">
                <FolderCard
                  v-for="folder in currentFolders"
                  :key="folder.folder_id"
                  :folder="folder"
                  @click="promptStore.navigateToFolder(folder.folder_id)"
                  @open="promptStore.navigateToFolder(folder.folder_id)"
                  @rename="openRenameFolderDialog(folder)"
                  @move="openMoveFolderDialog(folder)"
                  @delete="confirmDeleteFolder(folder)"
                  @prompt-dropped="handlePromptDropped"
                />
              </div>
            </section>

            <!-- Prompt 区域 -->
            <section v-if="currentPrompts.length > 0" class="prompt-section">
              <h3 class="prompt-section__title">
                <v-icon size="small">mdi-text-box-outline</v-icon>
                {{ tm('prompt.promptsTitle') }} ({{ currentPrompts.length }})
              </h3>
              <div class="prompt-grid">
                <PromptCard
                  v-for="prompt in currentPrompts"
                  :key="prompt.prompt_id"
                  :prompt="prompt"
                  @view="viewPrompt(prompt)"
                  @edit="editPrompt(prompt)"
                  @move="openMovePromptDialog(prompt)"
                  @delete="confirmDeletePrompt(prompt)"
                  @export="handlePromptExport"
                />
              </div>
            </section>

            <!-- 空状态 -->
            <div
              v-if="currentFolders.length === 0 && currentPrompts.length === 0"
              class="prompt-empty"
            >
              <v-icon size="56" color="on-surface-variant"
                >mdi-folder-open-outline</v-icon
              >
              <h3 class="prompt-empty__title">{{ tm('empty.folderEmpty') }}</h3>
              <p class="prompt-empty__text">
                {{ tm('empty.folderEmptyDescription') }}
              </p>
              <div class="prompt-empty__actions">
                <v-btn
                  color="primary"
                  variant="tonal"
                  prepend-icon="mdi-plus"
                  @click="openCreatePromptDialog"
                >
                  {{ tm('buttons.create') }}
                </v-btn>
                <v-btn
                  variant="outlined"
                  prepend-icon="mdi-folder-plus"
                  @click="showCreateFolderDialog = true"
                >
                  {{ tm('folder.createButton') }}
                </v-btn>
              </div>
            </div>
          </template>
        </div>
      </main>
    </div>

    <!-- 创建/编辑 Prompt 对话框 -->
    <PromptForm
      v-model="showPromptDialog"
      :editing-prompt="editingPrompt ?? undefined"
      :current-folder-id="currentFolderId ?? undefined"
      :current-folder-name="currentFolderName ?? undefined"
      @saved="handlePromptSaved"
      @deleted="handlePromptDeleted"
      @error="showError"
    />

    <!-- 查看 Prompt 详情对话框 -->
    <PromptPreviewDialog
      v-model="showViewDialog"
      :prompt="viewingPrompt"
      @edit="openEditFromViewDialog"
    />

    <!-- 创建文件夹对话框 -->
    <CreateFolderDialog
      v-model="showCreateFolderDialog"
      :parent-folder-id="currentFolderId"
      @created="showSuccess"
      @error="showError"
    />

    <!-- 重命名文件夹对话框 -->
    <v-dialog
      v-model="showRenameFolderDialog"
      max-width="400px"
      :aria-label="tm('folder.renameDialog.title')"
    >
      <v-card class="app-dialog">
        <v-card-title class="text-title-small">
          {{ tm('folder.renameDialog.title') }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="renameFolderData.name"
            :label="tm('folder.form.name')"
            :rules="[(v) => !!v || tm('folder.validation.nameRequired')]"
            variant="outlined"
            density="comfortable"
            autofocus
            @keyup.enter="submitRenameFolder"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRenameFolderDialog = false">
            {{ tm('buttons.cancel') }}
          </v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :loading="renameLoading"
            :disabled="!renameFolderData.name"
            @click="submitRenameFolder"
          >
            {{ tm('buttons.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 移动对话框 -->
    <MoveToFolderDialog
      v-model="showMoveDialog"
      :item-type="moveDialogType"
      :item="moveDialogItem"
      @moved="showSuccess"
      @error="showError"
    />

    <!-- 删除文件夹确认对话框 -->
    <v-dialog
      v-model="showDeleteFolderDialog"
      max-width="450px"
      :aria-label="tm('folder.deleteDialog.title')"
    >
      <v-card class="app-dialog">
        <v-card-title class="text-title-small">
          <v-icon class="mr-2" color="error">mdi-alert</v-icon>
          {{ tm('folder.deleteDialog.title') }}
        </v-card-title>
        <v-card-text>
          <p>
            {{
              tm('folder.deleteDialog.message', {
                name: deleteFolderData?.name ?? '',
              })
            }}
          </p>
          <p class="text-warning mt-2">
            <v-icon size="small" class="mr-1">mdi-information</v-icon>
            {{ tm('folder.deleteDialog.warning') }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteFolderDialog = false">
            {{ tm('buttons.cancel') }}
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            :loading="deleteLoading"
            @click="submitDeleteFolder"
          >
            {{ tm('buttons.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 消息提示 -->
    <v-snackbar
      v-model="showMessage"
      :timeout="3000"
      elevation="4"
      :color="messageType"
      location="top"
    >
      {{ message }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useModuleI18n } from '@/i18n/composables';
import { usePromptStore } from '@/stores/promptStore';
import { promptApi } from '@/api/v1';
import { resolveErrorMessage } from '@/utils/errorUtils';
import { storeToRefs } from 'pinia';

import FolderTree from './FolderTree.vue';
import FolderBreadcrumb from './FolderBreadcrumb.vue';
import FolderCard from './FolderCard.vue';
import PromptCard from './PromptCard.vue';
import PromptPreviewDialog from './PromptPreviewDialog.vue';
import PromptForm from '@/components/shared/PromptForm.vue';
import CreateFolderDialog from './CreateFolderDialog.vue';
import MoveToFolderDialog from './MoveToFolderDialog.vue';
import {
  askForConfirmation as askForConfirmationDialog,
  useConfirmDialog,
} from '@/utils/confirmDialog';

import type { Folder, FolderTreeNode } from '@/components/folder/types';
import type { Prompt as StorePrompt } from '@/stores/promptStore';

type MoveDialogType = 'prompt' | 'folder';
type SnackbarType = 'success' | 'error';

const { tm } = useModuleI18n('features/prompt');
const confirmDialog = useConfirmDialog();
const promptStore = usePromptStore();
const { folderTree, currentFolderId, currentFolders, currentPrompts, loading } =
  storeToRefs(promptStore);

const showPromptDialog = ref(false);
const importFileInput = ref<HTMLInputElement | null>(null);
const showViewDialog = ref(false);
const editingPrompt = ref<StorePrompt | null>(null);
const viewingPrompt = ref<StorePrompt | null>(null);

const showCreateFolderDialog = ref(false);
const showRenameFolderDialog = ref(false);
const showDeleteFolderDialog = ref(false);
const renameFolderData = ref<{ folder: Folder | null; name: string }>({
  folder: null,
  name: '',
});
const deleteFolderData = ref<Folder | null>(null);
const renameLoading = ref(false);
const deleteLoading = ref(false);

const showMoveDialog = ref(false);
const moveDialogType = ref<MoveDialogType>('prompt');
const moveDialogItem = ref<StorePrompt | Folder | null>(null);

const showMessage = ref(false);
const message = ref('');
const messageType = ref<SnackbarType>('success');

const showSkeleton = ref(false);
const skeletonTimer = ref<ReturnType<typeof setTimeout> | null>(null);

const currentFolderName = computed(() => {
  if (!currentFolderId.value) {
    return null;
  }

  const findName = (nodes: FolderTreeNode[], id: string): string | null => {
    for (const node of nodes) {
      if (node.folder_id === id) {
        return node.name;
      }
      if (node.children.length > 0) {
        const found = findName(node.children, id);
        if (found) {
          return found;
        }
      }
    }
    return null;
  };

  return findName(folderTree.value, currentFolderId.value);
});

watch(
  loading,
  (newVal) => {
    if (newVal) {
      skeletonTimer.value = setTimeout(() => {
        if (loading.value) {
          showSkeleton.value = true;
        }
      }, 150);
      return;
    }

    if (skeletonTimer.value) {
      clearTimeout(skeletonTimer.value);
      skeletonTimer.value = null;
    }
    showSkeleton.value = false;
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (skeletonTimer.value) {
    clearTimeout(skeletonTimer.value);
  }
});

onMounted(async () => {
  await initialize();
});

async function initialize() {
  await Promise.all([
    promptStore.loadFolderTree(),
    promptStore.navigateToFolder(null),
  ]);
}

function openCreatePromptDialog() {
  editingPrompt.value = null;
  showPromptDialog.value = true;
}

function handlePromptExport(exportMessage: string, isError: boolean) {
  if (isError) {
    showError(exportMessage);
    return;
  }
  showSuccess(exportMessage);
}

function triggerImport() {
  if (importFileInput.value) {
    importFileInput.value.value = '';
    importFileInput.value.click();
  }
}

function nextAvailablePromptId(baseId: string, existingIds: Set<string>) {
  let promptId = baseId;
  let suffix = 1;
  while (existingIds.has(promptId)) {
    const suffixLabel = suffix === 1 ? '' : `_${suffix}`;
    promptId = `${baseId}_imported${suffixLabel}`;
    suffix += 1;
  }
  return promptId;
}

async function handleImportFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  try {
    const data: unknown = JSON.parse(await file.text());
    if (!data || typeof data !== 'object' || !('system_prompt' in data)) {
      showError(tm('messages.importMissingPrompt'));
      return;
    }
    const imported = data as {
      prompt_id?: unknown;
      system_prompt?: unknown;
      begin_dialogs?: unknown;
    };
    if (typeof imported.system_prompt !== 'string' || !imported.system_prompt) {
      showError(tm('messages.importMissingPrompt'));
      return;
    }

    const response = await promptApi.list();
    const existingIds = new Set(
      response.data.status === 'ok'
        ? (response.data.data || []).map((prompt) => prompt.prompt_id)
        : [],
    );
    const baseId =
      typeof imported.prompt_id === 'string' && imported.prompt_id
        ? imported.prompt_id
        : 'imported_prompt';
    const promptId = nextAvailablePromptId(baseId, existingIds);

    const createResponse = await promptApi.create({
      prompt_id: promptId,
      system_prompt: imported.system_prompt,
      begin_dialogs: Array.isArray(imported.begin_dialogs)
        ? imported.begin_dialogs.filter(
            (item): item is string => typeof item === 'string',
          )
        : [],
      tools: null,
      skills: null,
      folder_id: currentFolderId.value,
    });
    if (createResponse.data.status !== 'ok') {
      throw new Error(
        createResponse.data.message || tm('messages.importError'),
      );
    }
    await promptStore.refreshCurrentFolder();
    if (promptId !== baseId) {
      showSuccess(tm('messages.importIdExists', { id: promptId }));
    } else {
      showSuccess(tm('messages.importSuccess'));
    }
  } catch (error) {
    if (error instanceof SyntaxError) {
      showError(tm('messages.importFormatError'));
      return;
    }
    console.error('Failed to import prompt:', error);
    showError(resolveErrorMessage(error, tm('messages.importError')));
  }
}

function editPrompt(prompt: StorePrompt) {
  editingPrompt.value = prompt;
  showPromptDialog.value = true;
}

function viewPrompt(prompt: StorePrompt) {
  viewingPrompt.value = prompt;
  showViewDialog.value = true;
}

function openEditFromViewDialog() {
  if (!viewingPrompt.value) {
    return;
  }
  editingPrompt.value = viewingPrompt.value;
  showViewDialog.value = false;
  showPromptDialog.value = true;
}

function handlePromptSaved(successMessage: string) {
  showSuccess(successMessage);
  void promptStore.refreshCurrentFolder();
}

function handlePromptDeleted(successMessage: string) {
  showSuccess(successMessage);
  void promptStore.refreshCurrentFolder();
}

async function confirmDeletePrompt(prompt: StorePrompt) {
  if (
    !(await askForConfirmationDialog(
      tm('messages.deleteConfirm', { id: prompt.prompt_id }),
      confirmDialog,
    ))
  ) {
    return;
  }

  try {
    await promptStore.deletePrompt(prompt.prompt_id);
    showSuccess(tm('messages.deleteSuccess'));
  } catch (error) {
    showError(resolveErrorMessage(error, tm('messages.deleteError')));
  }
}

function openMovePromptDialog(prompt: StorePrompt) {
  moveDialogType.value = 'prompt';
  moveDialogItem.value = prompt;
  showMoveDialog.value = true;
}

async function handlePromptDropped({
  prompt_id,
  target_folder_id,
}: {
  prompt_id: string;
  target_folder_id: string | null;
}) {
  try {
    await promptStore.movePromptToFolder(prompt_id, target_folder_id);
    showSuccess(tm('prompt.messages.moveSuccess'));
    await promptStore.navigateToFolder(target_folder_id);
  } catch (error) {
    showError(resolveErrorMessage(error, tm('prompt.messages.moveError')));
  }
}

function openRenameFolderDialog(folder: Folder) {
  renameFolderData.value = { folder, name: folder.name };
  showRenameFolderDialog.value = true;
}

async function submitRenameFolder() {
  if (!renameFolderData.value.name || !renameFolderData.value.folder) {
    return;
  }

  renameLoading.value = true;
  try {
    await promptStore.updateFolder({
      folder_id: renameFolderData.value.folder.folder_id,
      name: renameFolderData.value.name,
    });
    showSuccess(tm('folder.messages.renameSuccess'));
    showRenameFolderDialog.value = false;
  } catch (error) {
    showError(resolveErrorMessage(error, tm('folder.messages.renameError')));
  } finally {
    renameLoading.value = false;
  }
}

function openMoveFolderDialog(folder: Folder) {
  moveDialogType.value = 'folder';
  moveDialogItem.value = folder;
  showMoveDialog.value = true;
}

function confirmDeleteFolder(folder: Folder) {
  deleteFolderData.value = folder;
  showDeleteFolderDialog.value = true;
}

async function submitDeleteFolder() {
  if (!deleteFolderData.value) {
    return;
  }

  deleteLoading.value = true;
  try {
    await promptStore.deleteFolder(deleteFolderData.value.folder_id);
    showSuccess(tm('folder.messages.deleteSuccess'));
    showDeleteFolderDialog.value = false;
  } catch (error) {
    showError(resolveErrorMessage(error, tm('folder.messages.deleteError')));
  } finally {
    deleteLoading.value = false;
  }
}

function showSuccess(successMessage: string) {
  message.value = successMessage;
  messageType.value = 'success';
  showMessage.value = true;
}

function showError(errorMessage: string) {
  message.value = errorMessage;
  messageType.value = 'error';
  showMessage.value = true;
}
</script>

<style scoped>
.prompt-manager {
  --prompt-border: rgb(var(--v-theme-outline-variant));
  --prompt-surface: rgb(var(--v-theme-surface));
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  width: 100%;
}

.prompt-workbench {
  background: var(--prompt-surface);
  border: 1px solid var(--prompt-border);
  border-radius: 12px;
  display: grid;
  flex: 1;
  grid-template-columns: minmax(260px, 300px) 1px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  width: 100%;
}

.prompt-workbench__sidebar,
.prompt-workbench__main {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

.prompt-workbench__sidebar {
  display: flex;
  flex-direction: column;
}

.prompt-workbench__divider {
  background: var(--prompt-border);
}

.prompt-workbench__main {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.prompt-panel__head {
  align-items: center;
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
  justify-content: space-between;
  padding: 16px 12px 8px;
}

.prompt-panel__title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  margin: 0;
}

.prompt-panel__tree {
  flex: 1 1 auto;
  min-height: 0;
  padding: 0 12px 12px;
}

.prompt-main__head {
  align-items: center;
  border-bottom: 1px solid var(--prompt-border);
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
  padding: 12px 20px;
}

.prompt-main__breadcrumb {
  min-width: 0;
}

.prompt-main__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.prompt-main__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 20px;
}

.prompt-section + .prompt-section {
  margin-top: 24px;
}

.prompt-section__title {
  align-items: center;
  color: rgb(var(--v-theme-on-surface-variant));
  display: flex;
  font-size: 13px;
  font-weight: 600;
  gap: 6px;
  letter-spacing: 0.02em;
  margin: 0 0 12px;
}

.prompt-grid,
.prompt-skeleton {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}

.prompt-empty {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
  min-height: 320px;
  padding: 32px 16px;
  text-align: center;
}

.prompt-empty__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.prompt-empty__text {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 14px;
  margin: 0 0 8px;
}

.prompt-empty__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

@media (max-width: 960px) {
  .prompt-workbench {
    grid-template-columns: 1fr;
  }

  .prompt-workbench__sidebar,
  .prompt-workbench__divider {
    display: none;
  }

  .prompt-main__body {
    padding: 16px;
  }
}
</style>
