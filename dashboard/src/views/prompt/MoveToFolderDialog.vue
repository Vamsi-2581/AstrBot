<template>
  <BaseMoveToFolderDialog
    ref="baseDialog"
    v-model="showDialog"
    :folder-tree="folderTree"
    :tree-loading="treeLoading"
    :current-folder-id="currentFolderId"
    :item-current-folder-id="itemCurrentFolderId"
    :is-moving-folder="isMovingFolder"
    :labels="labels"
    @move="handleMove"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useModuleI18n } from '@/i18n/composables';
import { usePromptStore } from '@/stores/promptStore';
import BaseMoveToFolderDialog from '@/components/folder/BaseMoveToFolderDialog.vue';
import { resolveErrorMessage } from '@/utils/errorUtils';

interface PromptItem {
  prompt_id: string;
  folder_id?: string | null;
}

interface FolderItem {
  folder_id: string;
  name: string;
  parent_id?: string | null;
}

type BaseMoveToFolderDialogExposed = {
  setLoading: (value: boolean) => void;
};

function isPromptItem(
  item: PromptItem | FolderItem | null | undefined,
): item is PromptItem {
  return item !== null && item !== undefined && 'prompt_id' in item;
}

function isFolderItem(
  item: PromptItem | FolderItem | null | undefined,
): item is FolderItem {
  return item !== null && item !== undefined && 'name' in item;
}

const props = withDefaults(
  defineProps<{
    modelValue?: boolean;
    itemType: 'prompt' | 'folder';
    item?: PromptItem | FolderItem | null;
  }>(),
  {
    modelValue: false,
    item: null,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  moved: [message: string];
  error: [message: string];
}>();

const { tm } = useModuleI18n('features/prompt');
const promptStore = usePromptStore();
const { folderTree, treeLoading } = storeToRefs(promptStore);
const baseDialog = ref<BaseMoveToFolderDialogExposed | null>(null);

const showDialog = computed({
  get: () => props.modelValue,
  set: (value: boolean) => void emit('update:modelValue', value),
});

const itemName = computed(() => {
  if (!props.item) {
    return '';
  }
  if (props.itemType === 'prompt' && isPromptItem(props.item)) {
    return props.item.prompt_id;
  }
  return isFolderItem(props.item) ? props.item.name : '';
});

const isMovingFolder = computed(
  () => props.itemType === 'folder' && isFolderItem(props.item),
);

const currentFolderId = computed(() =>
  isFolderItem(props.item) ? props.item.folder_id : null,
);

const itemCurrentFolderId = computed(() => {
  if (!props.item) {
    return null;
  }
  if (props.itemType === 'prompt' && isPromptItem(props.item)) {
    return props.item.folder_id ?? null;
  }
  if (isFolderItem(props.item)) {
    return props.item.parent_id ?? null;
  }
  return null;
});

const labels = computed(() => ({
  title: tm('moveDialog.title'),
  description: tm('moveDialog.description', { name: itemName.value }),
  rootFolder: tm('folder.rootFolder'),
  cancelButton: tm('buttons.cancel'),
  moveButton: tm('buttons.move'),
}));

async function handleMove(folderId: string | null) {
  if (!props.item) {
    return;
  }

  baseDialog.value?.setLoading(true);
  try {
    if (props.itemType === 'prompt' && isPromptItem(props.item)) {
      await promptStore.movePromptToFolder(props.item.prompt_id, folderId);
    } else if (isFolderItem(props.item)) {
      await promptStore.moveFolderToFolder(props.item.folder_id, folderId);
    } else {
      return;
    }
    emit('moved', tm('moveDialog.success'));
    showDialog.value = false;
  } catch (error) {
    emit('error', resolveErrorMessage(error, tm('moveDialog.error')));
  } finally {
    baseDialog.value?.setLoading(false);
  }
}
</script>
