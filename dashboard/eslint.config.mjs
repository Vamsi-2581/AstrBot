import path from 'node:path';
import { fileURLToPath } from 'node:url';
import js from '@eslint/js';
import globals from 'globals';
import eslintConfigPrettier from 'eslint-config-prettier';
import tseslint from 'typescript-eslint';
import pluginVue from 'eslint-plugin-vue';
import vueParser from 'vue-eslint-parser';
import sonarjs from 'eslint-plugin-sonarjs';
import importX from 'eslint-plugin-import-x';

const tsconfigRootDir = path.dirname(fileURLToPath(import.meta.url));

export default tseslint.config(
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'src/api/generated/**',
      'src/assets/mdi-subset/**',
      'coverage/**',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    ...sonarjs.configs.recommended,
    files: ['src/**/*.{ts,mts,cts,vue}'],
  },
  {
    files: ['**/*.{js,mjs,cjs,ts,mts,cts}'],
    languageOptions: {
      parser: tseslint.parser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      'no-undef': 'off',
      'no-prototype-builtins': 'off',
      'no-useless-escape': 'off',
      'no-useless-assignment': 'off',
      'preserve-caught-error': 'off',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        {
          'ts-ignore': true,
          'ts-expect-error': 'allow-with-description',
          minimumDescriptionLength: 3,
        },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrors: 'all',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
    },
  },
  {
    files: ['env.d.ts', 'src/**/*.{js,mjs,cjs,ts,mts,cts}'],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir,
      },
    },
  },
  {
    files: ['env.d.ts', 'src/**/*.{js,mjs,cjs,ts,mts,cts}'],
    rules: {
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/consistent-type-exports': 'error',
      '@typescript-eslint/no-import-type-side-effects': 'error',
      eqeqeq: 'error',
      'no-implicit-coercion': 'error',
      'dot-notation': 'error',
      'no-empty-function': 'error',
      'no-else-return': 'error',
      'no-lonely-if': 'error',
      'no-nested-ternary': 'error',
      'no-unreachable-loop': 'error',
      'no-useless-concat': 'error',
      'no-useless-catch': 'error',
      'no-useless-rename': 'error',
      'no-useless-return': 'error',
      '@typescript-eslint/no-confusing-void-expression': [
        'error',
        { ignoreVoidOperator: true },
      ],
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/only-throw-error': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/prefer-promise-reject-errors': 'error',
      '@typescript-eslint/return-await': 'error',
      '@typescript-eslint/require-array-sort-compare': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      'object-shorthand': 'error',
      'prefer-arrow-callback': 'error',
      'prefer-template': 'error',
      yoda: 'error',
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
        projectService: true,
        tsconfigRootDir,
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      'no-undef': 'off',
      'no-prototype-builtins': 'off',
      'no-useless-assignment': 'off',
      'preserve-caught-error': 'off',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        {
          'ts-ignore': true,
          'ts-expect-error': 'allow-with-description',
          minimumDescriptionLength: 3,
        },
      ],
      '@typescript-eslint/await-thenable': 'error',
      eqeqeq: 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-confusing-void-expression': [
        'error',
        { ignoreVoidOperator: true },
      ],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/consistent-type-exports': 'error',
      '@typescript-eslint/no-import-type-side-effects': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/only-throw-error': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/prefer-promise-reject-errors': 'error',
      '@typescript-eslint/return-await': 'error',
      '@typescript-eslint/require-array-sort-compare': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrors: 'all',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
      'vue/attributes-order': 'off',
      'vue/no-deprecated-v-on-native-modifier': 'off',
      'vue/no-dupe-keys': 'off',
      'vue/no-mutating-props': ['error', { shallowOnly: true }],
      'vue/no-required-prop-with-default': 'off',
      'vue/no-template-shadow': 'error',
      'vue/no-unused-components': 'error',
      'vue/no-unused-vars': 'error',
      'vue/no-v-html': 'error',
      'no-implicit-coercion': 'error',
      'dot-notation': 'error',
      'no-empty-function': 'error',
      'no-else-return': 'error',
      'no-lonely-if': 'error',
      'no-nested-ternary': 'error',
      'no-unreachable-loop': 'error',
      'no-useless-concat': 'error',
      'no-useless-catch': 'error',
      'no-useless-rename': 'error',
      'no-useless-return': 'error',
      'object-shorthand': 'error',
      'prefer-arrow-callback': 'error',
      'prefer-template': 'error',
      'prefer-object-has-own': 'error',
      yoda: 'error',
      '@typescript-eslint/prefer-includes': 'error',
      'vue/prop-name-casing': 'error',
      'vue/require-default-prop': 'off',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      'vue/valid-v-slot': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    // SonarJS/import-x smell rules. Entries turned off here do not fit the
    // codebase's established conventions; each has a documented reason and
    // should be revisited if the underlying pattern changes. The rules that
    // are only advisory (large existing backlogs) live in
    // `eslint.report.config.mjs`.
    files: ['src/**/*.{ts,mts,cts,vue}'],
    plugins: {
      'import-x': importX,
    },
    settings: {
      'import-x/resolver': {
        typescript: { project: './tsconfig.json' },
      },
      'import-x/extensions': ['.ts', '.mts', '.vue'],
    },
    rules: {
      // `void` is used deliberately for fire-and-forget promises;
      // `@typescript-eslint/no-confusing-void-expression` owns that check.
      'sonarjs/void-use': 'off',
      // Duplicate of `@typescript-eslint/no-unused-vars`.
      'sonarjs/no-unused-vars': 'off',
      // `Math.random` is only used for UI affordances (ids, animations),
      // never for security-sensitive values.
      'sonarjs/pseudo-random': 'off',
      // Defensive runtime guards against values whose declared types are
      // narrower than their runtime reality (e.g. `id === undefined`).
      'sonarjs/different-types-comparison': 'off',
      // Browser-compatibility-sensitive legacy APIs; deprecation is tracked
      // through the TypeScript `@deprecated` surface instead.
      'sonarjs/deprecation': 'off',
      // The flagged expressions are anchored/simple; the rule is
      // over-conservative for this codebase.
      'sonarjs/super-linear-regex': 'off',
      // The plugin-page host validates the session origin and transfers a
      // MessageChannel port to a same-origin sandboxed iframe.
      'sonarjs/post-message': 'off',
      // Existing long dispatch functions predate this gate; tracked by the
      // advisory `lint:report` target until they are refactored.
      'sonarjs/cognitive-complexity': 'off',
    },
  },
  eslintConfigPrettier,
);
