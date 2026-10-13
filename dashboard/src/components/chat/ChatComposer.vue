<template>
  <section :class="project ? 'project-composer-shell' : 'composer-shell'">
    <button
      v-if="showScrollToBottom"
      class="scroll-to-bottom-btn"
      type="button"
      :aria-label="tm('input.scrollToBottom')"
      @click="emit('scroll-to-bottom')"
    >
      <v-icon size="20">mdi-chevron-down</v-icon>
    </button>
    <ChatInput
      ref="inputRef"
      v-bind="chatInputProps"
      v-on="chatInputListeners"
      :placeholder="placeholder"
    />
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import ChatInput from '@/components/chat/ChatInput.vue';
import { useModuleI18n } from '@/i18n/composables';

interface Props {
  project?: boolean;
  chatInputProps: InstanceType<typeof ChatInput>['$props'];
  chatInputListeners: Record<string, (...args: never[]) => void>;
  showScrollToBottom?: boolean;
  placeholder?: string;
}

withDefaults(defineProps<Props>(), {
  project: false,
  showScrollToBottom: false,
  placeholder: undefined,
});

const emit = defineEmits<{
  'scroll-to-bottom': [];
}>();

const { tm } = useModuleI18n('features/chat');

const inputRef = ref<InstanceType<typeof ChatInput> | null>(null);

function getCurrentSelection() {
  return inputRef.value?.getCurrentSelection() ?? null;
}

function focusInput() {
  inputRef.value?.focusInput();
}

defineExpose({ getCurrentSelection, focusInput });
</script>

<style scoped>
.composer-shell {
  position: relative;
  z-index: 1;
  background: var(--chat-page-bg);
  padding: 0 0 18px;
}

.scroll-to-bottom-btn {
  position: absolute;
  z-index: 2;
  left: 50%;
  top: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 50%;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  box-shadow: 0 2px 4px rgb(24 33 43 / 10%);
  transform: translate(-50%, -50%);
  cursor: pointer;
}

.scroll-to-bottom-btn:hover {
  background: rgb(var(--v-theme-surface-variant));
}

.composer-shell::before {
  content: '';
  position: absolute;
  z-index: -1;
  left: 0;
  right: 0;
  top: -36px;
  height: 36px;
  pointer-events: none;
  background: linear-gradient(
    to bottom,
    rgba(var(--v-theme-background), 0),
    var(--chat-page-bg)
  );
}

.composer-shell :deep(.input-area) {
  border-top: 0;
}

.empty-chat .composer-shell {
  padding-bottom: 0;
}

.empty-chat .composer-shell::before {
  display: none;
}

@media (max-width: 760px) {
  .composer-shell,
  .project-composer-shell {
    padding: 0;
  }
}
</style>
