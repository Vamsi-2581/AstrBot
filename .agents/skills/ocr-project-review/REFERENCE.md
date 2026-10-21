# OCR Project Review Reference

Facts about the `ocr` CLI, the wrapper, and this checkout's review surface.
Load this file when you need exact flags, config keys, rule behavior, or
troubleshooting. Policy lives in [SKILL.md](./SKILL.md).

## Provenance

- Upstream: [alibaba/open-code-review](https://github.com/alibaba/open-code-review)
- License: Apache-2.0
- Pinned while writing this skill: `375f64cd6f67a48a135da83cfcf59c52669a09cb`
  (2026-10-20T09:50:03Z)
- This skill is an AstrBot overlay, not a copy of the upstream agent skill. It
  adds `.env` credential loading, a dedicated provider, a whole-repository scan
  workflow, a syntax/compiler exclusion rule, a custom Markdown report, and a
  mandatory independent audit loop.

## Install and configure

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py install
```

The installer:

1. Reads `.env` from the skill directory (or `--env-file`).
2. Installs `@alibaba-group/open-code-review@latest` globally with npm when
   `ocr` is missing.
3. Deletes and recreates the dedicated custom provider (`astrbot-ocr` by
   default) with protocol `openai`, the URL and model from `.env`, and an
   `api_key_cmd` that runs this script's hidden `print-key` subcommand.
4. Sets the review language and effort, runs `ocr llm test`, and restricts the
   OCR config file to mode `0600` on POSIX.

The API key is never copied into the OCR config. `api_key_cmd` re-reads `.env`
on each run, so rotating the key needs no reinstall. `run` also refreshes the
provider's URL and model from `.env` before scanning, so changing those values
does not require reinstall either. Moving the skill directory, checkout, or virtualenv breaks the
command path; rerun `install`.

Useful install flags:

| Flag              | Effect                                              |
| ----------------- | --------------------------------------------------- |
| `--env-file PATH` | Read another dotenv file                            |
| `--upgrade`       | Reinstall `ocr@latest` even when already present    |
| `--no-install`    | Fail instead of running npm when `ocr` is missing   |
| `--no-test`       | Skip `ocr llm test`                                 |
| `--check-only`    | Validate `.env` and report the binary without setup |

`OCR_BIN` overrides binary discovery, which is useful for a GitHub release
binary or a test double.

### `.env` keys

Required (first non-empty alias wins):

| Purpose              | Accepted keys                                                                 |
| -------------------- | ----------------------------------------------------------------------------- |
| Chat completions URL | `OCR_LLM_URL`, `OPENAI_BASE_URL`, `OPENAI_URL`, `OPENAI_CHAT_COMPLETIONS_URL` |
| API key              | `OCR_LLM_API_KEY`, `OCR_LLM_TOKEN`, `OPENAI_API_KEY`                          |
| Model                | `OCR_LLM_MODEL`, `OPENAI_MODEL`                                               |

Optional:

| Key                     | Default                           | Meaning                                               |
| ----------------------- | --------------------------------- | ----------------------------------------------------- |
| `OCR_PROVIDER_NAME`     | `astrbot-ocr`                     | Dedicated OCR provider name                           |
| `OCR_REVIEW_LANGUAGE`   | `中文`                            | Review comment language                               |
| `OCR_EFFORT`            | `medium`                          | `low`, `medium`, or `high` (diff review only)         |
| `OCR_CONCURRENCY`       | `8`                               | Parallel scan items                                   |
| `OCR_TIMEOUT`           | `15`                              | Per-item budget in minutes; `0` disables the deadline |
| `OCR_MAX_TOKENS_BUDGET` | `0`                               | Total token cap; `0` is unlimited                     |
| `OCR_BATCH`             | empty                             | `none`, `by-language`, or `by-directory`              |
| `OCR_EXCLUDE`           | empty                             | Extra comma-separated excludes                        |
| `OCR_DEFAULT_EXCLUDES`  | `1`                               | Set `0` to disable built-in excludes                  |
| `OCR_NPM_PACKAGE`       | `@alibaba-group/open-code-review` | npm package to install                                |
| `OCR_BIN`               | unset                             | Explicit `ocr` binary path                            |

The URL may be a base URL (`https://host/v1`) or the full
`.../v1/chat/completions` endpoint. The OpenAI client normalizes both.

## Provider and config facts

OCR's user config is `~/.opencodereview/config.json`. The dedicated provider
lives under `custom_providers.<name>` and uses these keys:

- `url`
- `protocol` (`openai` for Chat Completions)
- `model`
- `api_key_cmd` (preferred here) or `api_key`
- optional `timeout_sec`, `extra_body`, `extra_headers`, `retry_codes`

Provider selection order is: explicit `--provider`, then the saved config,
then `OCR_LLM_*`, then Claude Code variables, then shell rc files. This skill
always passes `--provider` and `--model`, so the `.env`-backed provider wins
even when another OCR config exists.

`ocr llm test` tests the active provider. `ocr llm providers` lists presets.
For a custom provider, `url` and `protocol` are mandatory and there is no
environment fallback for the key outside our `api_key_cmd`.

## Whole-repository scan

`ocr scan` reads current files, not a diff. With no `--path`, it scans the
whole repository. Relevant flags:

| Flag                                      | Notes                                                               |
| ----------------------------------------- | ------------------------------------------------------------------- |
| `--path a,b`                              | Repo-relative directories or files; nonexistent paths are errors    |
| `--exclude globs`                         | Comma-separated gitignore-style patterns, merged with rule excludes |
| `--rule PATH`                             | Highest-priority rule file                                          |
| `--provider`, `--model`                   | Per-run provider/model override                                     |
| `--background TEXT`                       | Business context; **scan has no `--background-file`**               |
| `--concurrency N`                         | Parallel items, default 8                                           |
| `--timeout N`                             | Per-item minutes, default 15; `0` disables the task deadline        |
| `--max-tokens N`                          | Per-file prompt ceiling                                             |
| `--max-tokens-budget N`                   | Total input + output cap; partial results are published             |
| `--format text\|json\|sarif`              | JSON is required by this skill                                      |
| `--audience human\|agent`                 | `agent` suppresses progress; always use it                          |
| `--output PATH`                           | Write results to a file; use this for large scans                   |
| `--preview`                               | Enumerate and filter without calling the LLM                        |
| `--no-plan`, `--no-dedup`, `--no-summary` | Skip optional phases                                                |
| `--batch none\|by-language\|by-directory` | Batch strategy                                                      |
| `--resume ID`                             | Resume an interrupted scan                                          |

`ocr scan` does **not** accept `--effort` or `--background-file`; those belong
to `ocr review`. Keep background context concise.

### Sharded runs

For a large repository, `run --jobs N` (1-8) splits the scope into balanced
module shards instead of running one long scan:

1. It runs `ocr scan --preview` with the same paths and excludes.
2. It keeps only entries with `will_review: true`.
3. It groups files by their leaf directory (root files stay individual paths).
4. It greedily assigns groups to `N` buckets, balancing by preview `insertions`
   and then by file count.
5. It runs each bucket as a separate `ocr scan --path ...` process, up to 8 at
   a time.

`--shard-file` skips the preview and uses explicit groups:

```json
{
  "shards": [
    ["astrbot/core/auth", "astrbot/dashboard/api"],
    ["astrbot/core/platform", "astrbot/core/agent"]
  ]
}
```

Shards must be disjoint and at most 8. Exact duplicate paths are rejected;
overlapping parent/child paths are the caller's responsibility.

Each shard writes `shards/shard-NN/ocr-raw.json` and `run.log`. The wrapper
merges comments, summaries, warnings, and LLM identity into
`ocr-raw-merged.json`; `ocr-raw.json` also holds the merged raw result. Findings
keep a `shard` field, and the document carries a `coverage` object with shard
status, paths, log paths, and failed shards.

`--max-tokens-budget` is a total ceiling and is divided across shards. The
per-process internal concurrency is `--concurrency` (default 8), so total
parallel tasks are `jobs × concurrency`; lower `--concurrency` if the endpoint
rate-limits. `--resume` is only supported for a single scan.

A failed shard does not discard the others: the merged report is marked
`partial`, the command exits non-zero, and the failed shard's log is linked in
the coverage table.

## Rule resolution

Priority is first match wins:

1. `--rule` (the generated temporary rule)
2. `<repo>/.opencodereview/rule.json`
3. `~/.opencodereview/rule.json`
4. Embedded system rules

A user rule replaces the matched system rule unless `merge_system_rule: true`.
The wrapper copies project rules in order, appends the compiler-exclusion
block to each rule text, preserves `merge_system_rule`, copies project
`include`/`exclude`, and adds a final `**/*` catch-all with
`merge_system_rule: true`. This guarantees the exclusion applies to every file
while retaining project-specific and language-specific system rules. The
project file is never modified.

The exclusion block tells OCR to omit parse/syntax errors, type mismatches,
unresolved names, missing or unused imports, unused variables, unreachable
code, formatting, naming, import ordering, and other compiler/linter/style
diagnostics. Semantic defects remain in scope.

`ocr rules check <file>` shows which rule matches a path and where it came
from.

## JSON and sessions

A successful run emits one JSON object:

- `status`: `success`, `completed_with_warnings`, `completed_with_errors`,
  `complete`, `partial`, `failed`, or `skipped`
- `llm`: resolved provider/model
- `summary`: `files_reviewed`, `comments`, token counts, `elapsed`
- `comments`: `path`, `content`, `start_line`, `end_line`, `category`,
  `severity`, optional `existing_code`, `suggestion_code`, `thinking`
- `warnings`, `session_id`, optional `manifest`, `resume`

Exit code `0` means the review finished, possibly with no comments and possibly
with per-file warnings. Exit code `1` is a fatal error. Partial results may
still be published and exit `0`.

`run` also accepts `--resume <session-id>` for an interrupted scan. Resume
validates the mode, path set, rules, and provider/model; changing them rejects
the resume. Workspace/diff reviews are not resumed by this skill.

Sessions live under `~/.opencodereview/sessions/`. Use `ocr session list`,
`ocr session show <id>`, `ocr session comments <id>`, and `ocr scan --resume
<id>`. A scan resume validates the path set; changing rules or paths rejects
the resume.

## Wrapper data model

`run` writes each invocation to a new timestamped directory under
`.tmp/ocr-project-review/` (gitignored). The directory name is UTC
`YYYY-MM-DDTHH-MM-SSZ`, with `-01`, `-02`, ... added if two runs start in the
same second. Earlier runs are never overwritten. `preview` uses a separate
`preview-<timestamp>/` directory.

`list`, `apply-audit`, `finalize`, and `issues` default to the newest directory
containing `findings.json`. Pass `--out-dir PATH` to target an older run. For
`run`, `--out-dir PATH` means exactly that directory; an existing directory is
reused only when explicitly requested, and a warning is printed when it already
contains findings. `--resume` also creates a new timestamped directory unless
`--out-dir` names the original run.

| File                     | Role                                                         |
| ------------------------ | ------------------------------------------------------------ |
| `ocr-raw.json`           | OCR output; merged raw result for sharded runs               |
| `ocr-raw-merged.json`    | Merged raw result for sharded runs                           |
| `shards/shard-NN/`       | Per-shard `ocr-raw.json` and `run.log`                       |
| `findings.json`          | Normalized findings plus `audit` fields                      |
| `findings.previous.json` | Prior findings, kept when a rerun overwrites the working set |
| `audit-template.json`    | Blank verdict template for every finding                     |
| `report-ocr.md`          | Pre-audit report; not a deliverable                          |
| `rule.json`              | Generated merged rule                                        |
| `background.md`          | Context passed to OCR                                        |
| `preview.json`           | Preview output when `preview` is used                        |
| `report-final.md`        | Audited deliverable after `finalize`                         |
| `run.json`               | Run ID, commit, status, coverage mode, and finding count     |

Each normalized finding has `id`, `path`, line range, `category`, `severity`,
`content`, optional `shard` and code fields, and an `audit` object:

```json
{
  "verdict": "pending",
  "severity": null,
  "category": null,
  "evidence": "",
  "notes": "",
  "checks": []
}
```

`apply-audit` accepts a list, an object keyed by finding ID, or an object with
a `findings` list. Verdicts are `confirmed`, `false-positive`, and `uncertain`;
`pending` is the initial state. An optional `category` reclassifies the
finding; allowed values are `bug`, `security`, `performance`, `maintainability`,
`test`, `style`, `documentation`, and `other`. Use `security` when the audit
finds a security root cause that OCR labeled differently. `--require-all` fails
while any remain pending. `finalize` refuses pending findings unless
`--allow-pending` is passed.

The document also carries `coverage`:

- `mode`: `single` or `sharded`
- `jobs`: number of shard processes
- `completed` / `failed`: shard counts
- `shards`: per-shard `id`, `status`, `returncode`, `files_reviewed`,
  `paths`, `elapsed_sec`, `log`, and `raw`
- `note`: merge or coverage note

`report-final.md` renders this table before the findings so a partial run is
visible in the deliverable. `finalize` and `issues` refuse a document whose
`coverage.failed` is non-empty; pass `--allow-partial` only after the user
explicitly accepts the gap, or rerun the failed modules first.

## Issue drafting and filing

Reporting is the default. Only after the user explicitly asks should the agent
draft or open Issues. The helper command reads `findings.json` and refuses to
run while any finding is still `pending`.

```bash
# Draft locally; does not touch GitHub
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py issues

# After the user confirms the drafts and target
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py issues --create
```

Facts enforced by the helper:

- Only `confirmed` findings become drafts. `uncertain` and `false-positive`
  items are ignored.
- `security` categories and findings whose content or audit evidence mentions
  common vulnerability classes are written to `security-findings.md`, never to
  a public Issue. The keyword check is only a safety net; if the audit finds a
  security root cause, set that finding's `category` to `security` in
  `findings.json` before running `issues`. Follow `SECURITY.md` and the private
  advisory channel:
  <https://github.com/Xero-Team/AstrBot/security/advisories/new>.
- Drafts land in the selected run directory's `issues/` folder as
  `ISSUE-<id>.md` with an `index.md`. The title prefix is `[bug]` and the label is `bug`, matching
  `.github/ISSUE_TEMPLATE/bug_report.yml`.
- `--create` hardcodes `--repo Xero-Team/AstrBot`, checks GitHub for an exact
  title match before creating, and verifies the returned URL is under
  `https://github.com/Xero-Team/AstrBot/issues/`. It never targets upstream.
- Maintenance-only work that is not a defect should use
  `.github/ISSUE_TEMPLATE/task.yml` manually (`[chore]` title prefix, `task`
  label).
- Drafts are refused when they match common secret patterns (API keys,
  GitHub tokens, AWS keys, private-key headers). Redact the finding before
  retrying; never paste raw config, logs, or credentials into an Issue.
- Every Issue body ends with `## Agent note` per `AI_POLICY.md`; never
  fabricate a `## Human note`.
- Deduplicate by root cause before creation. `--create` searches open and
  closed Issues with `gh issue list --search <title>`. The agent must also
  check PRs with `gh pr list --repo Xero-Team/AstrBot --state all --search
  <title>`; a PR that already covers the defect means no Issue. An exact title
  match is skipped. Other issue candidates block creation unless the agent
  reviews them and chooses one of these explicit paths:
  - `--supersede ISSUE_NUMBER:DRAFT_ID` consolidates the existing Issue into
    the draft. Example: `issues --supersede 123:OCR-001` drafts the merged
    content for review; add `--create` to create it after confirmation.
  - `--allow-related` proceeds when the candidates are genuinely unrelated.
- A superseded Issue is read with `gh issue view`, its intent note is omitted,
  and its remaining report is embedded in a collapsed section of the new
  draft. The helper creates the new Issue first, verifies the URL, then closes
  the original with a comment linking the replacement. This order prevents a
  failed create from leaving only a closed Issue. It never closes an Issue
  without the explicit `--supersede` mapping.
- Multiple mappings are allowed, including several originals for one draft:
  `--supersede 123:OCR-001 --supersede 124:OCR-001`. A mapped finding must have
  a public draft; security findings cannot be superseded this way. Draft-only
  supersede runs require `gh` to read the original Issues but do not write to
  GitHub.

## AstrBot-specific review surface

Prioritize these areas in `background.md`:

- `astrbot/core/pipeline/` stage ordering, stop propagation, cancellation, and
  the bounded scheduler queues.
- `astrbot/core/agent/` tool loop, runner lifecycle, handoffs, MCP, context
  management, and provider request/response mapping.
- `astrbot/core/platform/sources/` adapter normalization and untrusted input.
- `astrbot/dashboard/api/` and `astrbot/dashboard/services/` authorization,
  request models, WebSocket request identity, and raw-response boundaries.
- `astrbot/core/config/` revisioned saves and atomic replacement.
- `astrbot/core/knowledge_base/` multi-store upload consistency and vector
  shape validation.
- `astrbot/core/star/` plugin loading and Dashboard Extension sandbox.
- Security invariants in `AGENTS.md`: TLS verification, SSRF/private-network
  checks, proxy-header trust, secret redaction, DOMPurify, and `defusedxml`.

Useful focused checks after auditing a finding (run only what applies):

```bash
uv run pytest tests/unit/<nearest_test>.py
uv run pytest tests/agent/
uv run pyright
cd dashboard && pnpm test
```

Do not run the full suite for a single finding unless the change or uncertainty
justifies it.

## Troubleshooting

- `ocr: command not found`: run `install`, install Node/npm, or set `OCR_BIN`.
- `missing .../.env`: copy `.env.example` and fill the three required keys.
- `ocr llm test` fails: check URL, key, model, gateway path, and whether the
  endpoint requires extra headers. The vendor error is in the command output.
- `unknown flag: --output` or other missing flags: the CLI is old; run
  `install --upgrade` or `npm i -g @alibaba-group/open-code-review@latest`.
- `provider ... is not configured`: rerun `install`; the dedicated provider was
  removed or the config file was replaced.
- `--background-file` is rejected by `scan`: expected; pass `--background`.
- Token/budget skips: reduce scope with `--path`, raise
  `OCR_MAX_TOKENS_BUDGET`, or resume with `ocr scan --resume <id>`.
- Rate limits: lower `OCR_CONCURRENCY` or use a provider with higher limits.
- A sharded run exits non-zero: inspect `shards/shard-NN/run.log`, then rerun
  the failed module with `--shard-file` or a larger `--jobs`. Partial findings
  are already merged into `findings.json`. `finalize` and `issues` refuse that
  partial coverage unless `--allow-partial` is passed.
- `--jobs` produces only one shard: the reviewable files share one directory
  group; use `--shard-file` to split that directory manually.
- `finalize` refuses pending findings: run `list --pending`, apply verdicts, or
  use `--allow-pending` only when the user accepts incomplete coverage.

## Security notes

- A full scan sends source text to the configured endpoint. Do not scan code
  the endpoint is not authorized to receive.
- Default excludes omit `.env*`, private keys, certificates, runtime `data/`,
  logs, and generated/build output. Add repository-specific secret paths with
  `--exclude` or `OCR_EXCLUDE`.
- The key stays in `.env`; OCR config stores only the `api_key_cmd`. The
  wrapper redacts the key from subprocess output it captures.
- Generated reports redact common API-key patterns. Raw working data
  (`ocr-raw.json`, `findings.json`, `findings.previous.json`) can still contain
  sensitive snippets; `.tmp/ocr-project-review/` is gitignored and must not be
  committed or shared.
- Do not put credentials, tokens, or customer data in `background.md`; it is
  sent to the model.
