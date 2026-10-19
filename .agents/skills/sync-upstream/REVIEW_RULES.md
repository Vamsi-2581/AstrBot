# Review rules by path

These rules are additions to `AGENTS.md`, not replacements. Apply every rule whose
path matches the changed file. A real defect outside these rules is still reportable.

| Path pattern                                                                                | Required checks                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `astrbot/**/*.py`                                                                           | Python 3.15+; no legacy shims or compatibility branches; `CancelledError` is re-raised; no import-time side effects; lifecycle ownership and shutdown are explicit; security invariants in `AGENTS.md` hold. |
| `astrbot/api/**`                                                                            | The plugin SDK surface stays stable; do not import Dashboard code or concrete provider/platform sources; plugin-facing changes need a matching SDK test.                                                     |
| `astrbot/core/agent/**`                                                                     | Tool-loop ordering, `agent_stats` emission, MCP remote-URL validation, sub-agent ownership, and runner boundaries stay intact.                                                                               |
| `astrbot/core/platform/sources/napcat/generated/**`                                         | Never hand-edit. Only `make napcat-check` may regenerate the model; review the generator input and the generated diff together.                                                                              |
| `astrbot/core/db/**` migrations                                                             | Never edit an applied revision; add a forward revision. Migrations must preserve upgrade and downgrade behavior.                                                                                             |
| `astrbot/core/knowledge_base/**`                                                            | Upload failure compensation covers parsed media, metadata, document storage, and vectors; validate vector shape before local writes; no partial document stays queryable.                                    |
| `astrbot/dashboard/api/**`, `astrbot/dashboard/services/**`, `astrbot/dashboard/schemas.py` | Use the `/api/v1` router and the shared `status`/`message`/`data` envelope; keep file/export, SSE, WebSocket, webhook, and static responses raw.                                                             |
| `openspec/openapi-v1.yaml`                                                                  | Regenerate the Dashboard client and `docs/public/openapi.json`; update call sites and backend/frontend tests in the same change.                                                                             |
| `dashboard/src/api/generated/**`                                                            | Generated code. Do not hand-edit; rerun the OpenAPI generator and commit the generated diff.                                                                                                                 |
| `dashboard/src/**`                                                                          | Follow the `dashboard-ui` skill, Vuetify 4 conventions, AstrBot theme tokens, and bilingual i18n. Sanitize `v-html` with DOMPurify.                                                                          |
| `docs/en/**`, `docs/zh/**`, `docs/.vitepress/config.mjs`                                    | Keep both languages structurally aligned; use in-app `/help/`; do not restore `docs.astrbot.app`, `Dockerfile.docs`, or a separate docs container.                                                           |
| `pyproject.toml`, `requirements.txt`, `uv.lock`                                             | Update all three together for runtime dependencies; do not add the optional `perf` group to `requirements.txt`; keep the version synced with `astrbot/__init__.py`.                                          |
| `compose.yml`, `compose-with-napcat.yml`, `Dockerfile`, `.dockerignore`                     | Preserve the source-build `astrbot:local` contract; do not replace it with an upstream prebuilt image; keep the runtime image free of `.agents/` and docs build artifacts.                                   |
| `.github/workflows/**`                                                                      | Least-privilege `permissions`; pin third-party actions; never print secrets; avoid unsafe `pull_request_target` checkout of PR head; keep required jobs and toolchain versions aligned.                      |
| `tests/**`                                                                                  | Put the regression test next to the nearest existing coverage; mark async tests; respect the `blocking` profile; use temporary data roots, never the developer's `data/`.                                    |
| `data/plugins/**`, `astrbot/builtin_stars/**`                                               | Use the public `astrbot.api` SDK; Dashboard Extension Protocol v1 stays sandboxed; do not add direct Dashboard auth or arbitrary HTTP proxies.                                                               |
| `changelogs/**`, `astrbot/__init__.py`                                                      | Version files and changelog agree; include only changes actually absorbed by the fork; do not claim upstream artifacts the fork does not publish.                                                            |
| `astrbot/core/config/default.py`                                                            | Do not hardcode `VERSION`; it derives from the package version.                                                                                                                                              |
| `upstream-decisions.jsonl`, `upstream-sync.yaml`                                            | Append-only history; full SHAs; no rewritten ledger lines; the cursor advances only after every interval commit has a disposition.                                                                           |

## Review behavior

- Focus on added and modified lines. Deleted lines are context only.
- A finding must target a changed file or a directly affected contract file. Do not
  report a pre-existing defect unless the change makes it reachable or worse.
- Prefer precision over recall. If the diff and repository do not prove the defect,
  do not report it.
- A failing or missing test is a finding only when the change makes the behavior
  unreachable or untested; state the exact command and result.
