<script setup lang="ts">
import { LazyMonacoEditor as VueMonacoEditor } from '@/components/shared/LazyMonacoEditor';
import { useModuleI18n } from '@/i18n/composables';

const modelValue = defineModel<boolean>({ required: true });

defineProps<{
  text: string;
}>();

const emit = defineEmits<{
  copy: [];
}>();

const { tm } = useModuleI18n('features/conversation');
</script>

<template>
  <v-dialog
    v-model="modelValue"
    max-width="900"
    scrollable
    :aria-label="tm('workspace.preview.rawData')"
  >
    <v-card class="raw-data-card">
      <v-card-title class="text-h3 pa-4 pb-0 pl-6 raw-data-title">
        <span>{{ tm('workspace.preview.rawData') }}</span>
        <v-btn
          icon
          size="small"
          variant="text"
          :aria-label="tm('workspace.preview.copyRawData')"
          @click="emit('copy')"
        >
          <v-icon size="17" aria-hidden="true">mdi-content-copy</v-icon>
          <v-tooltip activator="parent" location="top">
            {{ tm('workspace.preview.copyRawData') }}
          </v-tooltip>
        </v-btn>
      </v-card-title>
      <v-card-text class="pa-6">
        <div class="raw-data-editor">
          <VueMonacoEditor
            :value="text"
            theme="vs-dark"
            language="json"
            :options="{
              automaticLayout: true,
              domReadOnly: true,
              fontSize: 13,
              minimap: { enabled: false },
              readOnly: true,
              scrollBeyondLastLine: false,
              tabSize: 2,
              wordWrap: 'on',
              wrappingIndent: 'indent',
            }"
          />
        </div>
      </v-card-text>
      <v-card-actions class="pa-4 pt-0">
        <v-spacer />
        <v-btn variant="text" @click="modelValue = false">
          {{ tm('dialogs.view.close') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.raw-data-card {
  max-height: min(82dvh, 760px);
}

.raw-data-title {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.raw-data-editor {
  border-radius: 12px;
  height: min(62dvh, 580px);
  min-height: 360px;
  overflow: hidden;
}
</style>
