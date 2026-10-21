<script setup lang="ts">
withDefaults(
  defineProps<{
    label?: string;
    inlineOnMobile?: boolean;
  }>(),
  {
    label: 'Page actions',
    inlineOnMobile: false,
  },
);
</script>

<template>
  <div
    class="floating-action-stack"
    :class="{ 'floating-action-stack--inline-mobile': inlineOnMobile }"
    :aria-label="label"
    role="group"
  >
    <slot />
  </div>
</template>

<style scoped>
.floating-action-stack {
  position: fixed;
  right: max(16px, env(safe-area-inset-right));
  bottom: max(16px, env(safe-area-inset-bottom));
  z-index: 6;
  display: flex;
  flex-direction: column-reverse;
  gap: 12px;
}

.floating-action-stack :slotted(.v-btn) {
  box-shadow: 0 4px 12px rgb(24 33 43 / 18%);
}

@media (max-width: 600px) {
  .floating-action-stack:not(.floating-action-stack--inline-mobile) {
    bottom: max(8px, env(safe-area-inset-bottom));
    flex-direction: row-reverse;
    justify-content: flex-end;
    left: max(12px, env(safe-area-inset-left));
    right: max(12px, env(safe-area-inset-right));
  }

  .floating-action-stack :slotted(.v-btn) {
    flex: 0 0 auto;
    min-width: var(--astrbot-control-size);
  }

  .floating-action-stack :slotted(.v-btn--icon) {
    flex: 0 0 var(--astrbot-control-size);
  }

  .floating-action-stack--inline-mobile {
    flex-direction: row-reverse;
    gap: var(--astrbot-space-2);
    justify-content: flex-start;
    margin-top: var(--astrbot-space-6);
    position: static;
    width: 100%;
  }
}
</style>
