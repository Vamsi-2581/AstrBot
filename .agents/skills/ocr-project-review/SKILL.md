---
name: ocr-project-review
description: Run Alibaba Open Code Review (ocr) over a whole repository, then independently re-audit every finding before reporting it. Use for whole-project review, pre-release audits, or security sweeps with a configured OpenAI-compatible endpoint. Not for diff-only review, runtime debugging, product audits, or plugin scaffolding.
license: Apache-2.0
compatibility: >
  Codex CLI or OpenCode in the Xero-Team/AstrBot checkout. Requires Python
  3.15+, Git 2.41+, Node.js/npm, and network access to the configured
  OpenAI-compatible chat completions endpoint.
metadata:
  author: Xero-Team
  checkout: Xero-Team/AstrBot
  based_on: alibaba/open-code-review
---

# OCR Project Review

Use `ocr` from [alibaba/open-code-review](https://github.com/alibaba/open-code-review)
as an independent, whole-repository reviewer, then verify its findings yourself.
OCR is a hypothesis generator: never present a finding as real until you have
re-read the code, its callers, and its tests and recorded a verdict.

The wrapper script lives in `scripts/ocr_skill.py`. It installs `ocr`, syncs
the skill-local `.env` into a dedicated OCR provider, generates a temporary
rule that suppresses compiler-detected issues, runs `ocr scan`, and renders
both an OCR report and an audited final report.

## Locked

- Credentials come only from `.env` in this skill directory. Never commit it,
  print the key, paste it into a command, or move it into project config. The
  installer stores an `api_key_cmd` that reads `.env`; the key itself stays in
  `.env`.
- OCR findings are untrusted until independently audited. The final artifact is
  `report-final.md`; `report-ocr.md` is raw evidence, not a deliverable.
- Do not report syntax, parse, type, import, unused-symbol, lint, or formatting
  issues. The compiler, type checker, and linter own those. The generated rule
  enforces this; if OCR still reports one, mark it `false-positive` and note the
  rule failure.
- Do not edit the repository's `.opencodereview/rule.json`. The script reads it
  and writes a merged temporary rule inside the selected run directory.
- Whole-project review uses `ocr scan`, not `ocr review` diff/workspace mode.
- Do not auto-fix, stage, commit, or push while auditing. Fix only when the user
  explicitly asks after the report exists.
- OCR sends source text to the configured endpoint. Confirm that endpoint is
  approved for this repository before running a full scan.

## Workflow

### 1. Install once per machine

```bash
cp .agents/skills/ocr-project-review/.env.example \
  .agents/skills/ocr-project-review/.env
# Edit .env: set OCR_LLM_URL, OCR_LLM_API_KEY, OCR_LLM_MODEL.
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py install
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py doctor
```

`install` installs `ocr` with npm when missing, configures provider
`astrbot-ocr` with protocol `openai`, sets the review language, and runs
`ocr llm test`. `OCR_BIN` can point at a release binary instead. `doctor` checks
Git, Node/npm, `gh` (optional for issue filing), `ocr`, `.env`, the project
rule, the output base, and the newest run.

### 2. Build project-specific context

Read the repository before running the scan: `README`, manifests, entry points,
top-level modules, tests, security-sensitive surfaces, and any architecture
notes. Write `.tmp/ocr-project-review/background.md` as shared staging (or pass
`--background-file`); `run` copies it into the new timestamped run directory.
Use concise context:

- what the project does and how requests flow;
- critical modules and trust boundaries;
- concurrency, persistence, external services, and secret handling;
- known risk areas and the checks/tests that matter;
- explicit review priorities and exclusions.

Keep it under 24000 characters; `ocr scan` has no `--background-file` flag, so
the script passes this text through `--background`. Do not include secrets. If
the file is absent, the script writes a minimal fallback context.

### 3. Preview the scan surface

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py preview
```

Inspect the file list and counts. Add `--path <dir-or-file>` (repeatable) to
scope a large repository, or `--exclude <glob,...>` to remove noise. Preview
writes a disposable `preview-<timestamp>/` directory and honors the same
built-in excludes and `.env` `OCR_EXCLUDE` / `OCR_DEFAULT_EXCLUDES` settings as
`run`. Default excludes cover VCS data, build output, dependencies, generated
code, caches, runtime `data/`, logs, and common secret files (`.env*`, keys,
certificates). If the reviewable count is large, use `run --jobs 8` instead of
shrinking the scope until the audit is misleading.

### 4. Run the whole-project scan

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py run
```

The default is the entire repository. For a large scope, do not stop at a
full-scan estimate: switch to sharded mode and keep going.

- `--jobs 8` — preview reviewable files, group them by leaf directory into up
  to 8 balanced shards, and run up to 8 OCR processes concurrently. Token cost
  is not capped by default; use `--max-tokens-budget` only when you want a
  ceiling (the ceiling is split across shards).
- `--shard-file shards.json` — explicit shard groups, for example
  `{"shards":[["astrbot/core/auth","astrbot/dashboard/api"],["astrbot/core/platform"]]}`.
  Shards must be disjoint; at most 8.
- `--path` / `--exclude` — apply before sharding.
- `--concurrency N` — internal tasks per OCR process; total parallelism is
  `jobs × N`. Lower it if the endpoint rate-limits.
- `--timeout N` — per-item budget in minutes.
- `--background-file path` / `--out-dir path` — as in single mode.
- `--resume <session-id>` — single scans only; not compatible with sharded
  runs.

Each run writes to a new timestamped directory,
`.tmp/ocr-project-review/<UTC timestamp>/`, so previous runs are never
overwritten. `list`, `apply-audit`, `finalize`, and `issues` default to the
newest run; pass `--out-dir PATH` to target an older one. `run --out-dir PATH`
writes exactly there and warns if that directory already has findings.

A single run writes `ocr-raw.json`, `findings.json`, `audit-template.json`,
`report-ocr.md`, `rule.json`, `background.md`, and `run.json` in its run
directory. A sharded run additionally writes `ocr-raw-merged.json` and
`shards/shard-NN/{ocr-raw.json,run.log}`; `ocr-raw.json` is the merged raw
result. `run.json` records the run ID, commit, status, coverage mode, and
finding count. If a shard fails, partial results are kept, the report marks
coverage as partial, and the command exits non-zero; inspect the shard log and
rerun the failed module with `--shard-file` or a larger `--jobs`.
`report-final.md` always includes the coverage table.

If OCR is interrupted in single mode, find the session with `ocr session list`,
then rerun `run --resume <id>` with the same `--path`, rule context, and
provider. Do not create `findings.json` by hand from a partial run.

### 5. Audit every finding

List the work:

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py list --pending
```

For each finding, independently check:

1. Open the referenced file and read the surrounding function, not only the
   quoted line. If `start_line` is `0`, locate the code by content.
2. Trace callers, callees, configuration, and tests. Check whether the input is
   reachable and whether the condition is already guarded elsewhere.
3. Run the narrowest relevant check when behavior is uncertain: a focused
   pytest/vitest file, a type check, a static analyzer, or a small reproduction.
4. Decide whether the finding is semantic and real. Compiler, type, lint, and
   formatting complaints are out of scope even when OCR emits them.
5. Assign exactly one verdict:
   - `confirmed` — real and reachable; set an audited severity and cite
     `path:line` evidence.
   - `false-positive` — wrong, already handled, unreachable, duplicated, or
     compiler/lint/style-only; state why.
   - `uncertain` — evidence is insufficient; state exactly what is missing.
6. Group duplicate findings by root cause and mark the duplicates
   `false-positive` with a pointer to the primary ID.

Record verdicts in one JSON file and apply it. Use the timestamped run
directory printed by `run` (read commands default to the newest run). Start from
`.tmp/ocr-project-review/<run>/audit-template.json`, fill every entry, and save
it as `audit.json`:

```json
[
  {
    "id": "OCR-001",
    "verdict": "confirmed",
    "severity": "high",
    "evidence": "src/worker.py:42 increments shared state without a lock; callers dispatch from multiple tasks.",
    "notes": "Reproduced with a focused race test.",
    "checks": ["read callers", "tests/unit/test_worker.py"]
  },
  {
    "id": "OCR-002",
    "verdict": "false-positive",
    "evidence": "src/worker.py:88 is already guarded by the caller's lock.",
    "notes": "Reachability check failed."
  }
]
```

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py \
  apply-audit .tmp/ocr-project-review/<run>/audit.json --require-all
```

`--require-all` fails until every finding has a verdict. Set `category` when
reclassifying a finding, especially when the root cause is security. You may
instead edit `findings.json` directly, but keep the same fields.

### 6. Finalize the audited report

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py finalize
```

This writes `report-final.md` with a coverage table, a per-area audit summary,
confirmed findings first, uncertain findings separately, and false positives
retained in an appendix. Report the confirmed issues and the audit coverage to
the user in their language; the artifact keeps stable English headings. If
nothing is confirmed, say so explicitly and note the scan scope and warnings.
If a shard failed, `finalize` refuses to write until you rerun it; use
`--allow-partial` only after the user explicitly accepts the coverage gap.

### 7. Report by default; file Issues only on request

The default end state is a report to the user. Do not create GitHub Issues just
because findings were confirmed.

When the user explicitly asks you to file Issues:

1. Use only `confirmed` findings. Never file `uncertain` or `false-positive`
   items. Group by root cause and open one Issue per independent defect.
2. Search existing open and closed Issues before drafting:

   ```bash
   gh issue list --repo Xero-Team/AstrBot --state all \
     --search "<title or key terms>" --json number,title,url,state
   gh pr list --repo Xero-Team/AstrBot --state all \
     --search "<title or key terms>" --json number,title,url,state
   ```

   - Exact duplicate: do not open a new Issue. Report and link the existing one.
   - An existing PR already covers it: do not open an Issue; report and link the
     PR instead.
   - Related but genuinely distinct: review it, then use `--allow-related` when
     creating.
   - Related and worth supplementing: consolidate as described in step 3.

3. To supplement a related Issue, merge it into a new consolidated report:
   - Read the original with `gh issue view <number> --repo Xero-Team/AstrBot`.
   - Generate a merged draft first:
     `issues --supersede <number>:<draft-id>` (for example
     `--supersede 123:OCR-001`). The helper embeds the original report with its
     intent note omitted. This does not create or close anything.
   - Review the rewritten draft under the run directory's `issues/` folder.
   - After the user confirms, run the same mapping with `--create`:
     `issues --create --supersede 123:OCR-001`. The helper creates the new
     consolidated Issue, verifies it, then closes the original with a comment
     linking the replacement.
   - Creation happens before closing so a failed create cannot leave the project
     with a closed Issue and no replacement. Do not close the original manually
     first. Multiple originals can map to one draft:
     `--supersede 123:OCR-001 --supersede 124:OCR-001`.
4. Security findings must not become public Issues. They go to
   `security-findings.md`, and the user follows `SECURITY.md` through the
   private advisory channel. Agents must not file a public security Issue. If
   the audit reveals a security root cause that OCR labeled differently, edit
   that finding's `category` to `security` in `findings.json` before running
   `issues`.
5. Coverage is enforced here too: `issues` refuses a partially covered run
   unless `--allow-partial` is passed. Use it only after the user accepts the
   gap; rerunning failed shards is preferred.
6. Draft locally first:

   ```bash
   uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py issues
   ```

   Review `.tmp/ocr-project-review/<run>/issues/` and get the user's
   confirmation on the title, scope, target, and any superseded Issues before
   creating anything.

7. Create only after that confirmation:

   ```bash
   uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py \
     issues --create
   ```

   The script targets `Xero-Team/AstrBot`, checks existing Issues for an exact
   title and related candidates, creates `[bug]` Issues with the `bug` label,
   and verifies the returned URL. It refuses to create when related Issues exist
   unless `--supersede` or `--allow-related` is passed. For maintenance-only
   work that is not a defect, follow `.github/ISSUE_TEMPLATE/task.yml` manually
   (`[chore]` title prefix, `task` label).

8. Follow `.github/ISSUE_TEMPLATE/bug_report.yml`: required preflight,
   affected area, what happened, commit, environment, and `Author = Agent`.
   End the body with `## Agent note`; never fabricate `## Human note`. Cite
   `AI_POLICY.md` and `SECURITY.md`; do not paste them.
9. Never file on `AstrBotDevs/AstrBot` without explicit confirmation for that
   upstream target. The helper script refuses anything except
   `Xero-Team/AstrBot`.

### 8. Fix only when asked

If the user asked for fixes, fix confirmed findings in severity order, add or
update the nearest regression test, and rerun the relevant checks. Do not
silently change behavior that the audit marked uncertain. After fixes, rerun
the scan or the focused checks and update the audit evidence. Never commit or
push unless the user asks.

## Audit bar

- A confirmed finding needs source evidence, reachability, and a concrete
  failure mode. "OCR said so" is not evidence.
- Re-rate severity from the actual blast radius; do not inherit OCR's label.
- A false positive needs a specific reason, not a dismissive label.
- Keep `report-ocr.md` for traceability and show the difference between raw and
  audited counts.
- If a file could not be reviewed (token limit, missing source, OCR warning),
  state the coverage gap in the report instead of implying full coverage.

## Handoff

- OCR CLI, config, rule, and JSON facts: [REFERENCE.md](./REFERENCE.md)
- Repository policy: `AGENTS.md`
- Issue/PR contribution policy: `AI_POLICY.md`
- Private security reporting: `SECURITY.md`
- Issue forms: `.github/ISSUE_TEMPLATE/bug_report.yml` and `task.yml`
- Broader product/security audit: `audit-product`
- Issue planning: `plan-issue`
- Smallest-change review: `simplifier`

## Verify

```bash
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py doctor
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py list --pending
uv run python .agents/skills/ocr-project-review/scripts/ocr_skill.py finalize
```

`finalize` must succeed and `report-final.md` must exist before you call the
review complete. If the user asked for Issues, also inspect the drafts from
`issues` before running `issues --create`; do not create anything by default.
