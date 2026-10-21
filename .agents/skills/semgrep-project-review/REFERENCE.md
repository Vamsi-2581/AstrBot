# Semgrep Project Review Reference

Facts about the Semgrep CLI, the wrapper, and this checkout's review surface.
Load this file when you need exact flags, versions, output fields, or
troubleshooting. Policy lives in [SKILL.md](./SKILL.md).

## Provenance

- Upstream: [semgrep/semgrep](https://github.com/semgrep/semgrep)
- Upstream license: LGPL-2.1 for Semgrep OSS. The wrapper does not vendor the
  upstream source tree; it invokes the published CLI and container image. The
  wrapper code in this repository is AGPL-3.0-or-later like the rest of the
  checkout.
- Local CLI pin while writing this skill: `semgrep==1.157.0`.
- Container fallback pin: `docker.io/semgrep/semgrep:1.182.0`.
- This skill is an AstrBot overlay, not a copy of an upstream agent skill. It
  adds the `uvx` invocation, a Python 3.15 parse mirror, a local AstrBot rule
  pack, normalized findings, a mandatory audit loop, and deduped Issue filing.

## Why two versions are pinned

On the maintainer's Fedora 46 / glibc 2.44 development environment, Semgrep
`1.158.0` through `1.182.0` crashed `semgrep-core` with `SIGSEGV` even on a
one-line file. `1.157.0` was the newest local release that completed a scan.
The container image `1.182.0` works and provides the newest parser available
without the host binary crash.

Use the defaults. Bump either pin only after running `doctor`, a one-file scan,
and a repository scan with `--severity ERROR` on the target host.

Override points:

| Variable                  | Default                             | Meaning                                                                |
| ------------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| `SEMGREP_VERSION`         | `1.157.0`                           | Local `uvx --from semgrep==<version>` pin; `latest` uses `uvx semgrep` |
| `SEMGREP_BIN`             | unset                               | Explicit CLI path or wrapper; bypasses `uvx`                           |
| `SEMGREP_ENGINE`          | `auto`                              | `auto`, `local`, or `container`                                        |
| `SEMGREP_CONTAINER_IMAGE` | `docker.io/semgrep/semgrep:1.182.0` | Container fallback image                                               |

`SEMGREP_BIN` is useful for a release binary or a test double. When it is set,
`SEMGREP_VERSION` and `uvx` are ignored.

## Commands

```bash
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py doctor
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py run
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py list --pending
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py \
  apply-audit .tmp/semgrep-project-review/audit.json --require-all
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py finalize
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py issues
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py issues --create
```

`--repo PATH` selects a checkout; `--out-dir PATH` targets a previous run for
`list`, `apply-audit`, `finalize`, and `issues`.

## Rule selection

Defaults:

- `p/python`
- `p/typescript`
- `p/security-audit`
- `rules/astrbot.yml`

`--config` replaces the three registry packs. The local pack is still appended
unless `--no-local-rules` is set. `--local-only` uses only the local pack and
does not touch the network. Registry packs are fetched from semgrep.dev and
require network access.

Do **not** use `--config auto`. It logs in to the registry with the project URL
and defeats the explicit rule set. Metrics are always passed as `off`, and the
version check is disabled.

The local pack contains four fork-specific rules:

| Rule                                | Severity | What it catches                                                            |
| ----------------------------------- | -------- | -------------------------------------------------------------------------- |
| `astrbot-tls-verification-disabled` | ERROR    | `verify=False`, `CERT_NONE`, `check_hostname = False`, unverified contexts |
| `astrbot-subprocess-shell-true`     | ERROR    | `shell=True` and `create_subprocess_shell`                                 |
| `astrbot-yaml-unsafe-load`          | ERROR    | `yaml.load` without a safe loader                                          |
| `astrbot-stdlib-xml-parse`          | WARNING  | Standard-library XML parsing instead of `defusedxml`                       |

The local pack intentionally overlaps registry rules. Deduplicate by root cause
during the audit; do not file the same defect twice.

## Python 3.15 parse normalization

Semgrep's Python grammar does not understand PEP 758 `except A, B:` clauses even
in 1.182.0. This repository uses that syntax in about 100 files, so a direct
scan reports `PartialParsing` and can miss findings after the clause.

The wrapper therefore:

1. Creates `tree/` under the run directory.
2. Copies every source file, excluding VCS data, dependencies, build output,
   runtime `data/`, logs, generated files, `.env*`, private keys, and
   certificates. Copies, not hardlinks, so a stray write in the mirror cannot
   touch the worktree.
3. Copies any Python file containing `except A, B:` and rewrites only those
   clauses to `except (A, B):`. Line numbers and the rest of the file are
   unchanged.
4. Runs Semgrep with the mirror as the working directory and
   `--no-git-ignore`, because the mirror lives under the gitignored `.tmp/`.
5. Maps finding paths back to the original repository and reads code excerpts
   from the original file.

`--no-parse-normalization` disables the mirror. Use it only to debug the wrapper
or on a repository without PEP 758 syntax. A real audit must keep normalization
enabled, or the report must explicitly state the parse gap.

The mirror is disposable and lives under `.tmp/semgrep-project-review/`, which
is gitignored. Do not commit it or copy it elsewhere.

## Engines

`--engine auto` (the default) runs the local pinned CLI first. It retries with
the container image when:

- the local command fails with `semgrep-core exited` (a core crash); or
- the local run succeeds but reports **Python** parse errors, which is the
  expected PEP 758 symptom with an older local parser.

`--engine local` and `--engine container` force one path. The container path
uses `podman` first, then `docker`:

```bash
podman run --rm -v <mirror>:/src:Z -w /src --userns=keep-id \
  docker.io/semgrep/semgrep:1.182.0 semgrep scan ...
```

For Docker it passes `--user $(id -u):$(id -g)` instead of
`--userns=keep-id`. This keeps output files owned by the invoking user. The
container needs network access only when registry packs are requested. Local
rule files outside the repository are copied into the mirror under
`.semgrep-configs/`.

## Excludes

Default excludes cover VCS data, virtualenvs, `node_modules`, `data/`, logs,
build/dist output, caches, coverage, generated NapCat models, the generated
OpenAPI client, minified assets, source maps, `.env*`, private keys, and
certificates. Add repository-specific paths with `--exclude` or remove them
from `DEFAULT_EXCLUDES` only with a reason.

The scan mirror skips secret files entirely; they are not copied into the
temporary tree.

## Run outputs

Each run writes a new directory under `.tmp/semgrep-project-review/`, named with
a UTC `YYYY-MM-DDTHH-MM-SSZ` timestamp. Earlier runs are never overwritten.
`--out-dir` writes exactly there and warns if it already contains findings.

| File                   | Role                                                          |
| ---------------------- | ------------------------------------------------------------- |
| `semgrep-raw.json`     | Redacted Semgrep JSON, kept for traceability                  |
| `findings.json`        | Normalized findings plus audit fields                         |
| `audit-template.json`  | Blank verdict template for every finding                      |
| `report-semgrep.md`    | Pre-audit report; not the deliverable                         |
| `report-final.md`      | Audited deliverable after `finalize`                          |
| `run.json`             | Run metadata without the findings array                       |
| `scan.log`             | Every engine attempt, command, exit code, and captured output |
| `tree/`                | Parse-normalized mirror used for the scan                     |
| `issues/`              | Draft Issue bodies and `index.md`                             |
| `security-findings.md` | Private security evidence; never file publicly                |

`run.json` records the run ID, commit, status, engine and attempts, Semgrep
version, configs, paths, excludes, parse-normalization count, coverage, and
error paths.

## Finding model

```json
{
  "id": "SEM-001",
  "rule_id": "python.lang.security....",
  "path": "astrbot/core/example.py",
  "start_line": 42,
  "end_line": 44,
  "severity": "high",
  "category": "security",
  "content": "Rule message",
  "code": "source excerpt from the original file",
  "fix": "rule autofix text, when present",
  "fingerprint": "...",
  "metadata": {
    "cwe": "...",
    "owasp": "...",
    "confidence": "HIGH",
    "impact": "HIGH",
    "likelihood": "MEDIUM",
    "references": ["..."]
  },
  "audit": {
    "verdict": "pending",
    "severity": null,
    "category": null,
    "evidence": "",
    "notes": "",
    "checks": []
  }
}
```

Severity mapping: Semgrep `ERROR` → `high`, `WARNING` → `medium`, `INFO` →
`low`. The audit may re-rate. Category aliases map `correctness` → `bug`,
`best-practice` → `maintainability`, and `portability`/`compatibility` →
`maintainability`. Security rules and rules whose id contains `secret` map to
`security`.

Verdicts are `pending`, `confirmed`, `false-positive`, and `uncertain`.
`apply-audit` accepts a list, an object with a `findings` list, or an object
keyed by finding ID. `--require-all` fails while any finding is pending.
`finalize` refuses pending findings unless `--allow-pending` is passed.

Coverage fields:

- `files_scanned`, `files_skipped`
- `errors`: total Semgrep error entries
- `parse_errors`: syntax/partial-parse subset
- `partial`: true when any error exists

## Issue drafting and filing

`issues` refuses to run until every finding has a verdict. It only drafts
`confirmed` findings. `security-findings.md` receives any finding with
`category=security`, a CWE/OWASP tag, or an exploitable security term in the
message or audit evidence.

The helper:

- Hardcodes `--repo Xero-Team/AstrBot`.
- Searches open and closed Issues and PRs with `gh issue list` and `gh pr list`.
- Skips exact title matches and writes them to `issues/index.md` as already
  reported.
- Writes drafts for other findings and lists related candidates in `index.md`.
- Refuses to create an Issue when related candidates exist unless
  `--allow-related` is passed. Use it only after reading the related report and
  deciding this is a distinct defect.
- Creates with `[bug]` title prefix, `bug` label, and a body matching
  `.github/ISSUE_TEMPLATE/bug_report.yml`.
- Verifies the returned URL starts with
  `https://github.com/Xero-Team/AstrBot/issues/`.
- Never closes or supersedes existing Issues.

Drafts are refused when they contain common secret patterns (`sk-`, GitHub
tokens, AWS access keys, private-key headers). Redact the finding and retry;
never paste raw logs or credentials into an Issue.

Security findings must not be filed publicly. Follow `SECURITY.md` and
<https://github.com/Xero-Team/AstrBot/security/advisories/new>.

## AstrBot-specific review surface

Prioritize these areas in scoped runs:

- `astrbot/core/pipeline/`: stage ordering, stop propagation, cancellation, and
  bounded scheduler queues.
- `astrbot/core/agent/`: tool loop, runner lifecycle, handoffs, MCP, context
  management, and provider request/response mapping.
- `astrbot/core/platform/sources/`: adapter normalization and untrusted input.
- `astrbot/dashboard/api/` and `astrbot/dashboard/services/`: authorization,
  request models, WebSocket request identity, and raw-response boundaries.
- `astrbot/core/config/`: revisioned saves and atomic replacement.
- `astrbot/core/knowledge_base/`: multi-store upload consistency and vector
  shape validation.
- `astrbot/core/star/`: plugin loading and Dashboard Extension sandbox.
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

- `semgrep-core exited with -11` or `Segmentation fault`: the local binary is
  incompatible with the host; keep `--engine auto` or use
  `--engine container`.
- Local scan reports `PartialParsing` after normalization: inspect the rule and
  file. If it is a Python syntax form other than PEP 758, rerun with
  `--engine container`; if the container also fails, state the gap. TypeScript
  `export type * from` and some `.mjs` regex/template forms are parser
  limitations in both engines; record them as coverage gaps, not as clean files.
- `0 files scanned`: the mirror is probably being excluded by an absolute-path
  pattern. The wrapper removes the default `.tmp` exclude for mirror scans; do
  not add a broad custom exclude that matches the mirror root.
- Registry fetch fails: retry, or use `--local-only` and state that registry
  packs were unavailable.
- `uvx: command not found`: install `uv`; the skill does not install Semgrep
  into the project.
- `unknown option --no-git-ignore` or other flag errors: the CLI is older than
  the pin; run `doctor` and fix `SEMGREP_VERSION`.
- Container pull or permission failure: confirm `podman`/`docker` works, the
  image tag exists, and SELinux accepts `:Z`. On rootless Podman, keep
  `--userns=keep-id`.
- `gh: not authenticated`: run `gh auth login` before `issues --create`.
- `finalize` refuses pending findings: run `list --pending`, apply verdicts, or
  use `--allow-pending` only when the user accepts incomplete coverage.

## Security notes

- Semgrep sends only rule metadata and metrics; metrics are off. Source text
  stays local unless a registry fetch or container network request is made for
  rules.
- Raw reports can contain sensitive code snippets. The wrapper redacts common
  key patterns and the mirror skips secret files, but `.tmp/` is still
  gitignored and must not be committed or shared.
- The container image is third-party code. Pull it from the pinned
  `docker.io/semgrep/semgrep` tag and do not substitute an unverified image.
- A confirmed security finding belongs in a private advisory, not a public
  Issue, chat message, or PR description.
