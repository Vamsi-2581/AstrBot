import { createApp, watch } from 'vue';
import type { Component } from 'vue';
import { createPinia, type Pinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import vuetify from './plugins/vuetify';
import confirmPlugin from './plugins/confirmPlugin';
import { setupI18n } from './i18n/composables';
import { applyUserThemeColors } from './design/theme';

interface AppLike {
  use(plugin: unknown): AppLike;
  mount(selector: string): unknown;
}

interface BootstrapDependencies {
  setupI18n: () => Promise<unknown>;
  createApp: (root: Component) => AppLike;
  createPinia: () => Pinia;
  router: { isReady: () => Promise<void> };
  vuetify: unknown;
  confirmPlugin: unknown;
  setupThemeSync: (pinia: Pinia) => void;
}

function setupThemeSync(pinia: Pinia) {
  void import('./stores/customizer').then(({ useCustomizerStore }) => {
    const customizer = useCustomizerStore(pinia);
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    customizer.SET_SYSTEM_PREFERS_DARK(mediaQuery.matches);

    watch(
      () => customizer.uiTheme,
      (themeName) => {
        void vuetify.theme.change(themeName);
      },
      { immediate: true },
    );

    const storedPrimary = localStorage.getItem('themePrimary');
    const storedSecondary = localStorage.getItem('themeSecondary');
    if (storedPrimary || storedSecondary) {
      applyUserThemeColors(
        vuetify.theme.themes.value,
        storedPrimary,
        storedSecondary,
      );
    }

    mediaQuery.addEventListener('change', (event) => {
      customizer.SET_SYSTEM_PREFERS_DARK(event.matches);
    });
  });
}

const defaultDependencies: BootstrapDependencies = {
  setupI18n,
  createApp: (root) => createApp(root),
  createPinia,
  router,
  vuetify,
  confirmPlugin,
  setupThemeSync,
};

/**
 * Initialize i18n and mount the Dashboard exactly once.
 *
 * Only i18n initialization is recovered from: mount/router failures propagate
 * instead of creating a second Vue application on the same root element.
 */
export async function bootstrapDashboard(
  overrides: Partial<BootstrapDependencies> = {},
): Promise<void> {
  const dependencies = { ...defaultDependencies, ...overrides };

  try {
    await dependencies.setupI18n();
    console.log('🌍 新i18n系统初始化完成');
  } catch (error) {
    console.error('❌ 新i18n系统初始化失败:', error);
  }

  const app = dependencies.createApp(App);
  const pinia = dependencies.createPinia();
  app.use(pinia);
  app.use(dependencies.router);
  app.use(dependencies.vuetify);
  app.use(dependencies.confirmPlugin);
  await dependencies.router.isReady();
  app.mount('#app');
  dependencies.setupThemeSync(pinia);
}
