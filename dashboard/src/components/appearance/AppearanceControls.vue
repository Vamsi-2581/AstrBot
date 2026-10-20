<script setup lang="ts">
import { computed } from 'vue';

import { useModuleI18n } from '@/i18n/composables';
import { useAppearanceStore } from '@/stores/appearance';

const appearance = useAppearanceStore();
const { tm } = useModuleI18n('features/settings');

const fitOptions = computed(() => [
  { title: tm('appearance.fit.cover'), value: 'cover' },
  { title: tm('appearance.fit.contain'), value: 'contain' },
]);
const positionOptions = computed(() => [
  { title: tm('appearance.position.center'), value: 'center center' },
  { title: tm('appearance.position.top'), value: 'center top' },
  { title: tm('appearance.position.bottom'), value: 'center bottom' },
  { title: tm('appearance.position.left'), value: 'left center' },
  { title: tm('appearance.position.right'), value: 'right center' },
]);
const textEnhancementOptions = computed(() => [
  { title: tm('appearance.textEnhancementModes.off'), value: 'off' },
  {
    title: tm('appearance.textEnhancementModes.soft_shadow'),
    value: 'soft_shadow',
  },
  { title: tm('appearance.textEnhancementModes.stroke'), value: 'stroke' },
]);
</script>

<template>
  <section class="appearance-controls">
    <div class="appearance-controls__switches">
      <v-switch
        :model-value="appearance.settings.enabled"
        color="primary"
        hide-details
        :label="tm('appearance.enable')"
        @update:model-value="appearance.update({ enabled: $event === true })"
      />
      <v-switch
        :model-value="appearance.settings.random_on_load"
        color="primary"
        hide-details
        :label="tm('appearance.randomOnLoad')"
        @update:model-value="
          appearance.update({ random_on_load: $event === true })
        "
      />
      <v-switch
        :model-value="appearance.settings.rotation_enabled"
        color="primary"
        hide-details
        :label="tm('appearance.rotationEnabled')"
        @update:model-value="
          appearance.update({ rotation_enabled: $event === true })
        "
      />
      <v-switch
        :model-value="appearance.settings.auto_theme"
        color="primary"
        hide-details
        :label="tm('appearance.autoTheme')"
        @update:model-value="appearance.update({ auto_theme: $event === true })"
      />
    </div>

    <p class="appearance-controls__hint">
      {{ tm('appearance.surfaceHint') }}
    </p>

    <div class="appearance-controls__selects">
      <v-select
        :model-value="appearance.settings.fit"
        :items="fitOptions"
        :label="tm('appearance.fit.label')"
        density="compact"
        hide-details
        variant="outlined"
        @update:model-value="appearance.update({ fit: $event })"
      />
      <v-select
        :model-value="appearance.settings.position"
        :items="positionOptions"
        :label="tm('appearance.position.label')"
        density="compact"
        hide-details
        variant="outlined"
        @update:model-value="appearance.update({ position: $event })"
      />
      <v-select
        :model-value="appearance.settings.text_enhancement"
        :items="textEnhancementOptions"
        :label="tm('appearance.textEnhancement')"
        density="compact"
        hide-details
        variant="outlined"
        @update:model-value="appearance.update({ text_enhancement: $event })"
      />
    </div>

    <div class="appearance-controls__sliders">
      <v-slider
        :model-value="appearance.settings.blur"
        :label="tm('appearance.blur')"
        :min="0"
        :max="40"
        :step="1"
        thumb-label
        @update:model-value="appearance.update({ blur: Number($event) })"
      />
      <v-slider
        :model-value="appearance.settings.brightness"
        :label="tm('appearance.brightness')"
        :min="0.5"
        :max="1.5"
        :step="0.05"
        thumb-label
        @update:model-value="appearance.update({ brightness: Number($event) })"
      />
      <v-slider
        :model-value="appearance.settings.dim"
        :label="tm('appearance.dim')"
        :min="0"
        :max="0.9"
        :step="0.05"
        thumb-label
        @update:model-value="appearance.update({ dim: Number($event) })"
      />
      <v-slider
        :model-value="appearance.settings.surface_opacity"
        :label="tm('appearance.surfaceOpacity')"
        :min="0"
        :max="1"
        :step="0.05"
        thumb-label
        @update:model-value="
          appearance.update({ surface_opacity: Number($event) })
        "
      />
      <v-slider
        :model-value="appearance.settings.surface_blur"
        :label="tm('appearance.surfaceBlur')"
        :min="0"
        :max="40"
        :step="1"
        thumb-label
        @update:model-value="
          appearance.update({ surface_blur: Number($event) })
        "
      />
      <v-slider
        :model-value="appearance.settings.saturation"
        :label="tm('appearance.saturation')"
        :min="0"
        :max="2"
        :step="0.05"
        thumb-label
        @update:model-value="appearance.update({ saturation: Number($event) })"
      />
      <v-slider
        :model-value="appearance.settings.grayscale"
        :label="tm('appearance.grayscale')"
        :min="0"
        :max="1"
        :step="0.05"
        thumb-label
        @update:model-value="appearance.update({ grayscale: Number($event) })"
      />
      <v-slider
        :model-value="appearance.settings.text_enhancement_strength"
        :label="tm('appearance.textEnhancementStrength')"
        :min="0"
        :max="2"
        :step="0.05"
        thumb-label
        @update:model-value="
          appearance.update({ text_enhancement_strength: Number($event) })
        "
      />
      <v-slider
        :model-value="appearance.settings.rotation_interval_minutes"
        :label="tm('appearance.rotationInterval')"
        :min="1"
        :max="1440"
        :step="1"
        thumb-label
        @update:model-value="
          appearance.update({ rotation_interval_minutes: Number($event) })
        "
      />
      <v-slider
        :model-value="appearance.settings.mobile_sidebar_blur"
        :label="tm('appearance.mobileSidebarBlur')"
        :min="0"
        :max="40"
        :step="1"
        thumb-label
        @update:model-value="
          appearance.update({ mobile_sidebar_blur: Number($event) })
        "
      />
    </div>

    <div class="appearance-controls__notes">
      <p>{{ tm('appearance.randomHint') }}</p>
      <p>{{ tm('appearance.rotationHint') }}</p>
      <p>{{ tm('appearance.autoThemeHint') }}</p>
    </div>
  </section>
</template>

<style scoped>
.appearance-controls {
  display: grid;
  gap: 18px;
}

.appearance-controls__switches {
  display: grid;
  gap: 0 24px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.appearance-controls__selects,
.appearance-controls__sliders {
  display: grid;
  gap: 12px 24px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.appearance-controls__hint,
.appearance-controls__notes p {
  margin: 0;
  color: rgb(var(--v-theme-on-surface) / 66%);
  font-size: 13px;
  line-height: 1.5;
}

.appearance-controls__notes {
  display: grid;
  gap: 4px;
}

@media (max-width: 720px) {
  .appearance-controls__selects,
  .appearance-controls__sliders {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
