import base from './eslint.config.mjs';

// Advisory configuration. Extends the blocking config and re-enables the
// higher-signal smell rules that currently have a large backlog, so they are
// reported without failing the `check-web-eslint` gate. Run with:
//   pnpm run lint:report
//
// `sonarjs/deprecation` and `sonarjs/post-message` stay off (as in the blocking
// config) because their remaining hits are deliberate: the clipboard fallback
// needs `document.execCommand`, and the plugin-page host talks to an
// opaque-origin sandboxed frame via a validated MessageChannel handshake.
export default [
  ...base,
  {
    files: ['src/**/*.{ts,mts,cts,vue}'],
    rules: {
      'sonarjs/cognitive-complexity': ['warn', 15],
      'sonarjs/different-types-comparison': 'warn',
      'sonarjs/super-linear-regex': 'warn',
      'import-x/no-cycle': [
        'warn',
        {
          ignoreExternal: true,
          maxDepth: 8,
          allowUnsafeDynamicCyclicDependency: true,
        },
      ],
    },
  },
];
