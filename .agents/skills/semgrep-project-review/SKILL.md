---
name: semgrep-project-review
description: Run a Semgrep whole-project audit, independently verify every finding, and file deduped GitHub Issues for confirmed non-security defects. Use for static-analysis security sweeps, whole-repository review, or pre-release hardening. Not for diff-only review, runtime debugging, product audits, or plugin scaffolding.
license: AGPL-3.0-or-later
compatibility: >
  Codex CLI or OpenCode in the Xero-Team/AstrBot checkout. Requires Python
  3.15+, uv/uvx, Git, and gh for Issue filing. Podman or Docker is optional
  and is used as a fallback when the local semgrep-core binary crashes.
metadata:
  author: Xero-Team
  checkout: Xero-Team/AstrBot
  based_on: semgrep/semgrep
---

# Semgrep Project Review

Use [Semgrep](https://github.com/semgrep/semgrep) as an independent,
whole-repository reviewer, then verify every finding yourself. Semgrep is a
hypothesis generator: a rule match is not proof. Re-read the code, its callers,
and its tests, and record a verdict before reporting anything as real.

The wrapper lives in `scripts/semgrep_skill.py`. It runs the pinned Semgrep CLI
through `uvx`, mirrors the worktree with Python 3.15 syntax normalized, runs the
registry packs plus the AstrBot rule pack, writes normalized findings, and
renders audited reports. It also files deduped Issues for confirmed
non-security defects.

## Locked

- Run Semgrep through `uvx`; never add it to `pyproject.toml`, `uv.lock`, or the
  runtime image. The default is `uvx --from semgrep==1.157.0 semgrep`.
- Metrics are off and `--config auto` is forbidden. Auto-config logs in to the
  Semgrep registry and sends the project URL. Use explicit registry packs and
  the local rule file.
- Do not use `--autofix`, `--pro`, or the Semgrep Secrets product. The audit is
  read-only: no source edits, staging, commits, or pushes while reviewing.
- Semgrep findings are untrusted until independently audited. The deliverable is
  `report-final.md`; `report-semgrep.md` is raw evidence.
- Scope out compiler, parser, type, import, lint, and formatting complaints.
  Semgrep is here for semantic, security, and behavioral defects.
- Public Issues are for confirmed non-security defects only. Any finding with
  `category=security`, a CWE/OWASP tag, or an exploitable failure mode goes to
  `security-findings.md` and the private advisory channel from `SECURITY.md`.
- Search open and closed Issues **and** PRs before filing. Never duplicate an
  exact title; never file on `AstrBotDevs/AstrBot`.
- Do not edit the repository's rules or ignore files to silence a finding. Triage
  the finding instead. The generated mirror and `.tmp/` output are disposable.
- Python 3.15 `except A, B:` syntax is not understood by Semgrep's parser. The
  wrapper rewrites those clauses in a mirror to `except (A, B):`; never disable
  that normalization for a real audit.

## Workflow

### 1. Check prerequisites

```bash
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py doctor
```

This checks `uvx`, the pinned Semgrep CLI, Git, `gh`, the local rule file, the
container fallback, and the newest run. `gh` is only required to search or file
Issues. If the local `semgrep-core` binary segfaults, keep `--engine auto`: the
wrapper retries with the pinned container image. When neither Podman nor Docker
is available, fix the local binary or accept and state the resulting parse gap.

### 2. Build review context

Read the parts of the repository that the scan will touch: `AGENTS.md`
(especially the security invariants), the pipeline and Dashboard boundaries,
the provider/agent runner lifecycle, persistence, and the security-sensitive
code paths. Decide whether this is a whole-repository sweep or a focused module
audit. Use `--path` to scope a large sweep instead of silently shrinking the
rule set.

Do not paste source, secrets, or credentials into prompts or reports. The local
rule pack already encodes the fork's TLS, subprocess, YAML, and XML invariants.

### 3. Run the scan

```bash
# Whole repository, default packs plus local rules
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py run

# Focused module, only high/medium findings
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py run \
  --path astrbot/dashboard --severity ERROR --severity WARNING

# Local rules only, no registry fetch
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py run \
  --local-only
```

Defaults are `p/python`, `p/typescript`, `p/security-audit`, and
`rules/astrbot.yml`. `--config` replaces the registry packs; the local pack is
still added unless `--no-local-rules` is passed. Registry packs require network
access. Every run writes a new timestamped directory under
`.tmp/semgrep-project-review/`, so earlier runs are preserved.

The wrapper mirrors the worktree under the run directory, rewrites Python 3.15
`except A, B:` clauses to `except (A, B):` without changing line numbers, and
copies unchanged files. Findings are mapped back to the original paths.
`--no-parse-normalization` scans the worktree directly and is only for
debugging.

A run writes `semgrep-raw.json` (redacted), `findings.json`,
`audit-template.json`, `report-semgrep.md`, `run.json`, `scan.log`, and
`tree/`. If a Python parse error remains, the wrapper retries with the container
engine. Non-Python parser gaps (for example TypeScript `export type * from` or
some `.mjs` regex forms) remain in both engines; the report marks coverage as
partial. State that gap; do not imply the unreviewed region was clean.

Useful run flags:

| Flag                                | Effect                                                          |
| ----------------------------------- | --------------------------------------------------------------- |
| `--engine auto\|local\|container`   | Auto retries the pinned container on a local crash or parse gap |
| `--path PATH`                       | Scope to a repository-relative path (repeatable)                |
| `--config PACK`                     | Registry pack or local rule file (repeatable)                   |
| `--exclude GLOB`                    | Extra exclude pattern (repeatable; comma-separated allowed)     |
| `--severity ERROR\|WARNING\|INFO`   | Keep only that Semgrep severity (repeatable)                    |
| `--jobs N`                          | Semgrep worker count                                            |
| `--timeout N`                       | Per-rule timeout in seconds                                     |
| `--out-dir PATH`                    | Reuse an explicit run directory                                 |
| `--local-only` / `--no-local-rules` | Rule-pack selection                                             |

### 4. Audit every finding

List the work:

```bash
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py list --pending
```

For each finding, independently check:

1. Open the referenced file and read the surrounding function, not only the
   quoted line. If the line range is empty, locate it by the rule message.
2. Trace callers, configuration, and tests. Check whether the input is
   reachable and whether the condition is guarded elsewhere.
3. Check that the rule fits the language and framework. Flask/Jinja rules
   frequently fire on unrelated HTML templates; a match is not a vulnerability
   unless the sink is reachable with untrusted data.
4. Run the narrowest relevant check when behavior is uncertain: a focused
   pytest/vitest file, a type check, or a small reproduction.
5. Decide exactly one verdict:
   - `confirmed` — real and reachable; set an audited severity and cite
     `path:line` evidence.
   - `false-positive` — wrong language, already guarded, unreachable,
     duplicated, or lint/style-only; state why.
   - `uncertain` — evidence is insufficient; state exactly what is missing.
6. Group duplicate findings by root cause and mark the duplicates
   `false-positive` with a pointer to the primary ID.
7. Re-rate severity from the actual blast radius. Semgrep's `ERROR`/`WARNING`
   label is input, not the verdict.

Start from `audit-template.json`, fill every entry, and save it as
`.tmp/semgrep-project-review/audit.json`:

```json
[
  {
    "id": "SEM-001",
    "verdict": "confirmed",
    "severity": "high",
    "category": "security",
    "evidence": "astrbot/core/x.py:42 passes untrusted text to the sink; two callers reach it from adapter input.",
    "notes": "Reproduced with a focused test.",
    "checks": ["read callers", "tests/unit/test_x.py"]
  },
  {
    "id": "SEM-002",
    "verdict": "false-positive",
    "evidence": "astrbot/core/x.py:88 is a Jinja template with autoescape enabled; the matched `| safe` is a fixed literal.",
    "notes": "Rule is a Flask template rule applied to a non-Flask template."
  }
]
```

```bash
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py \
  apply-audit .tmp/semgrep-project-review/audit.json --require-all
```

`--require-all` fails until every finding has a verdict. Set `category` when
reclassifying, especially when the root cause is security. You may edit
`findings.json` directly, but keep the same fields.

### 5. Finalize the audited report

```bash
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py finalize
```

This writes `report-final.md` with the coverage table, per-verdict counts,
confirmed findings first, uncertain findings separately, and false positives in
an appendix. Report the confirmed issues and the coverage to the user in their
language. If nothing is confirmed, say so explicitly and state the scan scope,
engine, and any parse warnings.

### 6. File Issues for confirmed defects

The default end state for this skill is: audited report **and** deduped Issues
for confirmed non-security defects. If the user asked for a report only, stop
after `finalize`.

1. Draft and inspect:

   ```bash
   uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py issues
   ```

   The command searches open and closed Issues and PRs with `gh`, skips exact
   title matches, and writes `issues/ISSUE-<id>.md` plus `issues/index.md`.
   Review the drafts, the related candidates, and the title/scope before
   creating anything.

2. Create after review:

   ```bash
   uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py \
     issues --create
   ```

   Creation targets `Xero-Team/AstrBot`, verifies the returned URL, and uses the
   `bug` label and `[bug]` title prefix from
   `.github/ISSUE_TEMPLATE/bug_report.yml`. It creates the Issue only when no
   exact title exists and no related report is found, unless you explicitly pass
   `--allow-related` after deciding this is a distinct defect.

3. Deduplicate by root cause, not just title:
   - Exact Issue title or matching PR: do not create. Report and link it.
   - Related Issue or PR that already covers the defect: do not create. Report
     and link it.
   - Related but genuinely distinct: read the existing report, then pass
     `--allow-related` after confirming it is a separate defect.
   - The command never closes or supersedes existing Issues. Do that manually
     only if the user asks.

4. Security findings never become public Issues. They are written to
   `security-findings.md`; follow `SECURITY.md` and submit through
   <https://github.com/Xero-Team/AstrBot/security/advisories/new>. If the audit
   reveals a security root cause that Semgrep labeled differently, set that
   finding's `category` to `security` in `findings.json` before `issues`.

5. Never file on `AstrBotDevs/AstrBot` without explicit confirmation for that
   upstream target. The helper hardcodes the fork repository.

6. Follow `AI_POLICY.md`. The Issue body already ends with `## Agent note`;
   never fabricate a `## Human note`.

### 7. Fix only when asked

If the user asked for fixes, fix confirmed findings in severity order, add or
update the nearest regression test, and rerun the relevant checks. Do not
silently change behavior that the audit marked uncertain. After fixes, rerun the
scan or the focused checks and update the audit evidence. Never commit or push
unless the user asks.

## Audit bar

- A confirmed finding needs source evidence, reachability, and a concrete
  failure mode. "Semgrep said so" is not evidence.
- A false positive needs a specific reason, not a dismissive label.
- Keep `report-semgrep.md` for traceability and show the difference between raw
  and audited counts.
- If a file could not be parsed, state the coverage gap instead of implying full
  coverage. Rerun with `--engine container` when the local parser is the cause.
- Do not report secrets, tokens, or private data in a public Issue or chat.
  Redact before drafting.

## Handoff

- Semgrep CLI, pinned versions, rule behavior, and output schema:
  [REFERENCE.md](./REFERENCE.md)
- Repository policy: `AGENTS.md`
- Issue/PR contribution policy: `AI_POLICY.md`
- Private security reporting: `SECURITY.md`
- Issue forms: `.github/ISSUE_TEMPLATE/bug_report.yml` and `task.yml`
- Broader product/security audit: `audit-product`
- Issue planning: `plan-issue`
- Smallest-change review: `simplifier`

## Verify

```bash
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py doctor
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py list --pending
uv run python .agents/skills/semgrep-project-review/scripts/semgrep_skill.py finalize
```

`finalize` must succeed and `report-final.md` must exist before calling the
review complete. If Issues are in scope, inspect the drafts and the related
candidates from `issues` before running `issues --create`; do not create anything
without that review.
