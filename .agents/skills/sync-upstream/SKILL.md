---
name: sync-upstream
description: Review, audit, or integrate AstrBot upstream commits with per-commit provenance and a searchable decision ledger. Use for upstream sync, cherry-pick adaptation, conflict resolution, auditing recorded decisions, or revisiting recorded sync decisions.
---

# Sync AstrBot upstream

Use this skill to keep the fork's upstream cursor and integration decisions
auditable without repeatedly loading the entire sync history into context.
Treat `AGENTS.md` as the policy source of truth and
`upstream-decisions.jsonl` as the durable decision ledger.

Use the requested mode and existing conversation authorization. Review requests
end with a plan; requests to execute an approved plan continue through integration
and verification. Both Codex CLI and OpenCode use the same scripts and ledger.

Cite `.agents/shared/ai-contribution/REFERENCE.md` and `AI_POLICY.md` when
opening a branch, Issue, or PR. Paste-ready apply prompt:
`APPLY_PROMPT.md` in this folder.

## Locked

- Default method is **cherry-pick**, not merge of `upstream/master`.
- One implementation commit per absorbed upstream commit. Skip/revisit make
  none.
- Preserve upstream subjects on `cherry-pick -x`. Adapt uses upstream author
  plus hyphenated trailers.
- Every applied, skipped, or revisited commit gets an independent review from
  a fresh Codex session before its ledger record. The actor may be Codex or
  OpenCode; the reviewer is Codex. The actor's own write-up is not a review.
- Python 3.15+, no legacy shims, source-build compose, in-app `/help/` docs.
- Do not merge the resulting PR, push `master`, tag, or release. A human
  maintainer does those actions; do not treat a verbal exception as
  authorization.
- Open absorb PRs against `Xero-Team/AstrBot` with `--repo Xero-Team/AstrBot`.
  Confirm the created URL is under `github.com/Xero-Team/AstrBot`. Do not open
  an Issue or PR on `AstrBotDevs/AstrBot` unless the user explicitly confirms
  that upstream target.

## Open

Which commits to absorb in this window, and whether to open the PR in this
session, unless the user already froze the plan in this conversation.

## Do not

- `git merge` / `rebase` onto `upstream/master`.
- Combine several upstream feature/fix commits into one implementation commit.
- Re-run an interval whose SHAs are already in the ledger.
- File a public security Issue for an upstream vuln; follow `SECURITY.md`.
- Open an Issue or PR on `AstrBotDevs/AstrBot` without explicit user
  confirmation for that upstream target.
- Invent a `pending` field in `upstream-sync.yaml`. Apply only the plan the
  user approved in this conversation.

## Handoff

- Commit messages: `.agents/shared/conventional-commit/REFERENCE.md`.
- Agent merge bar: `.agents/shared/ai-contribution/REFERENCE.md`.
- Apply paste prompt: `.agents/skills/sync-upstream/APPLY_PROMPT.md`.
- Reviewer paste prompt: `.agents/skills/sync-upstream/REVIEW_PROMPT.md`.
- Full-ledger re-audit prompt: `.agents/skills/sync-upstream/FULL_AUDIT_PROMPT.md`.
- Path-specific review rules: `.agents/skills/sync-upstream/REVIEW_RULES.md`.

## Operating modes

- **Review mode (default):** inspect the repository, fetch and compare
  `upstream/master`, classify every pending commit, query prior decisions, and
  return a focused plan. Do not cherry-pick, edit files, commit, or push.
- **Apply mode:** use when the user has asked to execute the approved plan in
  this conversation; do not ask for that authorization again. Apply commits
  oldest-first, one at a time, run the independent review, and record each
  final decision. Stay on a feature branch. You may open a pull request on
  `Xero-Team/AstrBot` with `--repo Xero-Team/AstrBot`. Do not merge, push
  `master`, release, or tag.

## Preflight

1. Read the upstream-synchronization, generated-artifact, security, and
   toolchain rules in the repository `AGENTS.md`.
2. Inspect `git status --short --branch` and remotes. Do not silently stash,
   reset, checkout, or discard unrelated work.
3. Verify the `upstream` URL and branch from `upstream-sync.yaml`, then fetch:

   ```bash
   git fetch --prune --tags upstream
   ```

4. Inspect the interval and historical decisions with the bundled tools:

   ```bash
   python .agents/skills/sync-upstream/scripts/inspect_upstream.py
   python .agents/skills/sync-upstream/scripts/upstream_decisions.py list --query "..."
   ```

   The inspector validates that the full marker is an ancestor of
   `upstream/master`. If it is not, stop and report the history mismatch.

## Commit decision workflow

For each commit from the marker to the fetched upstream head, in oldest-first
topological order:

1. Read the commit, patch, changed paths, source PR, and relevant current fork
   implementation.
2. Query the ledger by exact SHA, source PR, affected path, and feature terms.
3. Reuse a prior decision only when the current fork architecture and policies
   still match. Mark it `revisit` when the architecture, security posture,
   generated contract, or toolchain has changed.
4. Choose exactly one disposition:
   - `cherry-pick`: the upstream commit is compatible as-is;
   - `adapt`: implement the behavior against current fork boundaries;
   - `skip`: intentionally exclude it and state why;
   - `replay`: apply a historical upstream commit only when the repository
     record explicitly authorizes replay;
   - `revisit`: defer because an earlier decision is no longer reliable.
5. In apply mode, cherry-pick compatible commits with provenance, and manually
   adapt the rest. Never resolve a conflict by blindly choosing ours/theirs.
   Stop on an unresolved conflict and show the user the exact state.
6. Run the independent review for the commit. Only a `pass` review may complete
   a `cherry-pick`, `adapt`, `replay`, or `skip` decision; `revisit` needs a
   `revisit` verdict. Record the review before moving to the next commit.

Use reason codes such as `security`, `fork-architecture`, `no-legacy`,
`toolchain`, `source-build`, `openapi`, `generated-model`, `docs-scope`,
`release-policy`, and `upstream-compatible` so future searches remain cheap.
Use `upstream-compatible` for a `cherry-pick` that needs no fork adaptation.

## Integration commit strategy

In apply mode, create at most one implementation commit for each upstream
commit with disposition `cherry-pick`, `adapt`, or `replay`. Process them in
oldest-first topological order. Do not combine several upstream feature or fix
commits into one implementation commit. Commits with disposition `skip` or
`revisit` produce no implementation commit.

Preserve the upstream subject verbatim whenever possible, including its
Conventional Commit type, scope, description, and existing `(#number)` PR
suffix. If the upstream subject has no PR suffix, do not invent one. Change a
subject only when the fork's user-visible semantics materially differ, and
explain that change in the commit body.

Generated or rewritten messages must follow
`.agents/shared/conventional-commit/REFERENCE.md`, including
`AI-Generated: true` and a UTC `Generated-At:` footer from
`date -u '+%Y-%m-%dT%H:%M:%SZ'`. Do not rewrite a preserved upstream
subject to satisfy that reference. Do not add AI metadata to a message
that `git cherry-pick -x` kept verbatim.

Use the following method for each disposition:

- `cherry-pick`: use `git cherry-pick -x <full-upstream-sha>`. This preserves
  the upstream author and records Git's standard `(cherry picked from commit
...)` provenance line. Do not duplicate that line with another
  `Upstream-Commit` trailer unless a conflict or message rewrite removes it.
- `adapt`: apply the behavior manually against the current fork boundaries,
  then commit with `git commit --author="<upstream author>"`. Preserve the
  upstream subject and add the trailers below.
- `replay`: use only when the ledger explicitly authorizes replay. Treat it as
  a manual adaptation for author and provenance purposes, and cite the
  authorizing historical record in the body or trailers.

For adapted, replayed, or conflict-rewritten commits, use standard Git
trailers with hyphenated tokens:

```text
Upstream-Commit: <full upstream SHA>
Upstream-Author: <name> <email>
Upstream-PR: AstrBotDevs#<number>
Sync-Disposition: adapt
Fork-Adaptation: <concise explanation of the fork-specific implementation>
Tested: <focused validation command>
```

Omit a trailer when its value is unavailable; never use non-standard tokens
with spaces such as `Source PR`. Keep `Signed-off-by` separate from sync
provenance and do not add it unless repository policy or the user explicitly
requires a developer certificate.

Recommended adapted-commit shape:

```text
<upstream subject>

<optional fork-specific explanation>

Upstream-Commit: <full upstream SHA>
Upstream-Author: <name> <email>
Upstream-PR: AstrBotDevs#<number>
Sync-Disposition: adapt
Fork-Adaptation: <what changed for this fork>
Tested: <command>
AI-Generated: true
Generated-At: <UTC ISO 8601 timestamp>
```

The final cursor update is a separate metadata-only commit with subject
`chore(sync): record upstream integration`. Generate that message from
the conventional-commit reference, including a body and AI footers. Do
not hide implementation changes inside this cursor commit. A
release/version bump that is intentionally skipped still advances the
cursor only after its `skip` decision is recorded and the skip rationale
is written to `upstream-sync.yaml`.

After each implementation commit, verify the mapping before moving on:

```bash
git show -s --format='%H%n%an <%ae>%n%cn <%ce>%n%s%n%B' HEAD
git show --stat --oneline HEAD
```

The integration commit must be attributable to exactly one upstream SHA, and
its author must be the upstream author for `cherry-pick`, `adapt`, and
`replay` unless the user explicitly directs otherwise. The fork maintainer is
normally the committer.

Keep `integration_commits` for primary implementation commits with provenance.
Record shared lint, lockfile, generated-asset, or review-fix commits that
support more than one upstream decision in `follow_up_commits` instead. A
follow-up commit may be attributed to several decisions; it must exist and be
reachable, but it is not counted as a duplicate integration commit.

## Per-commit independent review

Every commit in the audited interval, including `skip` and `revisit`, gets a
fresh review before it is recorded. The actor may be Codex or OpenCode; the
reviewer is always Codex. The reviewer must be a separate session from the
actor, and should use a different model or effort where available. The actor's
own write-up does not count.

Give the reviewer the upstream SHA, its full patch and stat, the fork diff
against the integration base, the integration commit message and trailers,
`AGENTS.md`, this skill, the current ledger entry, the affected paths, and the
tests actually run. The reviewer is read-only and must not edit files. Use the
paste-ready prompt in `REVIEW_PROMPT.md`; it carries the full checklist and the
JSON answer shape. Apply the path rules in `REVIEW_RULES.md`.

The reviewer accounts for every changed file from
`git diff-tree --no-commit-id --name-only -r <upstream-sha>`. Each path is
either in `reviewed_files` or in `skipped_files` with a reason. Group related
files by contract before judging them. The checkpoint command enforces this
coverage when `--changed-files-from` is passed.

The reviewer reruns the focused tests itself. It does not trust the actor's
summary. Treat a weakened or skipped test, a special-cased input, a stub, a
hard-coded return, a swallowed error, or an unreachable file as the main
failure modes: any one means the work only looks done. Prefer precision over
recall: if the diff and repository do not prove the defect, do not report it.

The reviewer checks:

- one upstream SHA maps to one integration commit, or to an explicit
  `skip`/`revisit`;
- author, subject, provenance trailers, and commit count are correct, with no
  duplicate integration;
- conflicts preserve upstream intent and were not resolved by blindly choosing
  ours or theirs;
- the fork-specific gates and security invariants hold;
- generated artifacts, OpenAPI, NapCat models, and bilingual docs moved together
  where required;
- the tests are real, relevant, and pass; no test was weakened to hide a
  failure;
- a `skip` or `revisit` rationale is honest and complete.

The reviewer returns a structured verdict:

```json
{
  "summary": "One paragraph: what changed, what was checked, and how it ended.",
  "reviewed_files": ["astrbot/core/example.py", "tests/unit/test_example.py"],
  "skipped_files": [{ "path": "docs/old.md", "reason": "deleted" }],
  "verdict": "pass",
  "findings": [
    {
      "severity": "high",
      "category": "provenance",
      "path": "tests/unit/example.py",
      "line": 42,
      "summary": "What is wrong.",
      "instruction": "What the actor must do next."
    }
  ],
  "tests": [
    { "command": "uv run pytest tests/unit/example.py", "result": "pass" }
  ],
  "residual_risk": "none"
}
```

`fix` sends the findings back to the actor word for word. Cite the file and
line, say what is wrong, and say what to do next; the actor cannot ask a
follow-up question. Re-review after the fix. After two `fix` rounds without a
`pass`, record `revisit` instead of guessing. A `revisit` verdict records no
integration commit. Only `pass` may complete a `cherry-pick`, `adapt`,
`replay`, or `skip` decision.

Record the verdict in the checkpoint and, once final, in the ledger review
fields. Use a Codex agent spec such as `codex/<model>:<effort>` for the
reviewer.

### Legacy ledger review policy

The independent-review gate applies to decisions first recorded on or after
`2026-10-19T17:38:28Z` (the commit that introduced the gate). Decisions first
recorded before that cutoff are explicitly grandfathered: they are reported as
`legacy-review-exempt` with `info` severity instead of a missing-review error.
The exemption follows the first ledger event for an upstream commit, so later
metadata-only revisions remain grandfathered without pretending they were
reviewed. Do not backfill `reviewer` or `review_notes` for a review that did
not happen. A new decision or revisit after the cutoff still requires the full
review fields.

## Checkpoint and report

The checkpoint is ephemeral working state; `upstream-decisions.jsonl` remains
the authoritative decision ledger. Keep checkpoints under `.tmp/sync-run/`,
which is gitignored, and never commit them.

Initialize the checkpoint before the first commit. It reads the marker from
`upstream-sync.yaml` and the head from `upstream/master` by default:

```bash
STATE=$(python .agents/skills/sync-upstream/scripts/sync_run_state.py init)
```

For each commit, record progress around the actor and reviewer:

```bash
python .agents/skills/sync-upstream/scripts/sync_run_state.py start \
  --state "$STATE" --commit <full-upstream-sha>

python .agents/skills/sync-upstream/scripts/sync_run_state.py review \
  --state "$STATE" --commit <full-upstream-sha> --repo . \
  --changed-files-from <full-upstream-sha> \
  --reviewer codex/<model>:<effort> --review-json .tmp/sync-run/review.json

python .agents/skills/sync-upstream/scripts/sync_run_state.py complete \
  --state "$STATE" --commit <full-upstream-sha> --disposition adapt \
  --integration-commit <full-fork-sha> --test "uv run pytest ..." \
  --risk "what remains unverified"
```

`review` accepts the JSON returned by `REVIEW_PROMPT.md` through
`--review-json`; `--verdict` is optional when the JSON carries it. With
`--changed-files-from`, it refuses a review that did not cover every changed
file. The JSON summary, findings, reviewed and skipped files, tests, and
residual risk are kept. `--findings-file` remains available for a prose
review.

`complete` refuses a non-revisit disposition without a `pass` review, and
requires an integration commit for `cherry-pick`, `adapt`, and `replay`. After
a `fix` review, fix the work and review again; the checkpoint keeps the round
count. On resume, read the checkpoint, ledger, and `git status`; do not re-run
completed commits.

After all commits, render the report and use it for the pull request body. Do
not commit the report:

```bash
python .agents/skills/sync-upstream/scripts/sync_run_state.py report \
  --state "$STATE" --output .tmp/sync-run/report.md
```

The report lists every upstream commit, disposition, status, review verdict,
integration commits, tests, findings, and residual risk.

## Audit existing decisions

The audit is read-only. It checks the current ledger for internal consistency,
review completeness, Git provenance, and the fork-specific decision rules. It
does not rewrite the ledger.

```bash
python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py

python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py \
  --range <marker>..<head> --require-review --strict-provenance

python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py \
  --commit <full-or-prefix> --verbose
```

The default report prints errors and summarizes warnings; `--verbose` lists
warnings and legacy review exceptions too, and `--json` emits every finding.
Exit status is `1` when there is an error, `2` when the ledger cannot be read.
A missing review on a legacy decision is an explicit `legacy-review-exempt`
info finding; `--require-review` makes a missing review an error only after the
legacy cutoff. `--strict-provenance` requires every primary integration commit
to name its upstream SHA in a trailer, Git's `cherry picked from` line, or the
historical `Adapted from upstream <sha>` line. Integration and follow-up
commits must also be reachable from `--ref` (default `HEAD`). Use `--no-git`
when auditing a ledger without the relevant object database.

Audit errors mean the decision record is internally inconsistent: a code
change with no integration commit, a `skip` with an integration commit, an
`adapt` with no adaptation note, a review verdict that contradicts the
disposition, a missing or unreachable Git object, or provenance that names a
different upstream commit. Warnings identify gaps that may be legitimate for
older records, such as a missing test command, a missing source PR, or a
missing skip rationale. Legacy decisions without an independent review are
separate `info` findings and do not fail the audit.

## Conflict and duplicate handling

Never resolve a conflict by blindly choosing ours or theirs. Pause the
sequence, inspect the conflicting path and the missing context, and identify
possible prerequisite commits before editing:

```bash
git log HEAD..<upstream_sha>^ -- <conflicted-path>
git log -G'<relevant-symbol-or-string>' HEAD..<upstream_sha>^ -- <conflicted-path>
```

If the conflict is a mechanical context adjustment and preserves upstream
behavior, continue the `cherry-pick`; inspect the final message and add an
`Upstream-Commit` trailer if Git did not retain `-x` provenance. If the
resolution changes behavior to fit fork architecture, classify the result as
`adapt`, preserve the upstream author with `--author`, and record the reason in
`Fork-Adaptation`. If the prerequisite or intended behavior cannot be
established, run `git cherry-pick --abort` and use `revisit` rather than
guessing.

Before creating a new implementation commit, check whether the change was
already integrated under a different fork commit:

```bash
git cherry upstream/master
git log --all --grep='Upstream-Commit: <full-upstream-sha>' --format='%H %s'
```

An already-equivalent patch needs an explicit ledger decision and provenance;
do not create a duplicate implementation commit merely because the SHA differs.

## Fork-specific gates

Before accepting a decision, check the affected contract:

- update `pyproject.toml`, `requirements.txt`, and `uv.lock` together for
  runtime Python dependencies;
- update OpenAPI source, generated Dashboard client, public JSON, call sites,
  and tests together for Dashboard protocol changes;
- update both `docs/en/` and `docs/zh/` for user-visible behavior;
- keep documentation in-app at `/help/`; do not restore `Dockerfile.docs`, a
  docs Compose service, or `docs.astrbot.app` links;
- regenerate NapCat models only through `make napcat-check`;
- preserve Python 3.15+, the security invariants, current ownership boundaries,
  source-build deployment, and the no-legacy policy;
- if a release/version change is absorbed, update the synchronized version
  files and only the changelog entries actually included by the fork.

## Ledger operations

Initialize the ledger when the first decision is ready:

```bash
python .agents/skills/sync-upstream/scripts/upstream_decisions.py init
```

Add or revise a decision without loading the ledger into context:

```bash
python .agents/skills/sync-upstream/scripts/upstream_decisions.py add \
  --commit <full-sha> --disposition adapt --summary "..." \
  --source-pr 123 --reason-code security --path astrbot/core/... \
  --fork-adaptation "..." --integration-commit <full-sha> \
  --review-verdict pass --reviewer "codex/<model>:<effort>" \
  --review-notes "what the reviewer checked and found" \
  --review-rounds 1 --reviewed-at-utc "<UTC ISO 8601>"

python .agents/skills/sync-upstream/scripts/upstream_decisions.py update \
  --commit <full-sha> --disposition revisit --summary "..." \
  --reason-code fork-architecture --revisit-when "..."
```

Query current decisions, full event history, or validate the append-only log:

```bash
python .agents/skills/sync-upstream/scripts/upstream_decisions.py get --commit <sha>
python .agents/skills/sync-upstream/scripts/upstream_decisions.py get --commit <sha> --history
python .agents/skills/sync-upstream/scripts/upstream_decisions.py list --path dashboard/src
python .agents/skills/sync-upstream/scripts/upstream_decisions.py validate
```

Use `delete --reason` only to append a tombstone; never remove historical JSONL
lines. Use `import-git --range <old>..<new>` to recover structured decisions
from existing sync commit messages. Imported records are marked as inferred
and must be reviewed before being treated as authoritative.

## Version and changelog finalization

After the audited upstream interval has been integrated, finish the release
metadata before advancing the cursor:

1. Read the version represented by the absorbed upstream release. Keep the
   fork's `[project].version` in `pyproject.toml` and `astrbot.__version__`
   synchronized with that version; do not hardcode the derived
   `astrbot/core/config/default.py` value.
2. Create or update `changelogs/vX.Y.Z.md` for that version. Include only
   changes actually absorbed by this fork, group them by user-visible impact,
   and call out manual adaptations, skipped upstream work, and fork-specific
   deviations. Do not copy upstream release text wholesale or claim artifacts
   that this fork does not publish.
3. If the reviewed interval contains no upstream release/version change, do
   not invent a new version; still write the changelog entry required for the
   absorbed fork changes when the repository's release convention calls for
   one.

## Verify

Advance `upstream-sync.yaml` only after every commit in the audited interval has
an explicit disposition and the implementation/skip rationale is complete. Use
the full `git rev-parse upstream/master` SHA, UTC time, source PR provenance,
and an honest summary of adaptations, skips, replays, conflicts, and tests.
If the interval is incomplete, leave the cursor unchanged.

Run focused tests first, then the relevant repository gates (`make check`,
`make quality`, Dashboard build, or docs build). Confirm every commit has a
checkpoint review that is `pass` or `revisit`, and that the ledger review fields
are present for completed decisions. Audit the interval with
`--require-review --strict-provenance`, then audit the whole ledger for
regressions. Render the interval report before opening or updating the pull
request. Finish with a concise mapping of upstream commits to dispositions,
changed files, checks run, and residual risk. Do not claim that an upstream
commit was integrated merely because it was reviewed or recorded.

## Bundled tools

- `scripts/inspect_upstream.py`: read-only cursor/ref validation and pending
  commit report, with optional JSON output.
- `scripts/upstream_decisions.py`: append-only JSONL ledger CLI for init, add,
  update, soft-delete, get, list/filter, validation, and Git-history import.
  Records final review verdicts through `--review-verdict`, `--reviewer`,
  `--review-notes`, `--review-rounds`, and `--reviewed-at-utc`.
- `scripts/sync_run_state.py`: ephemeral per-interval checkpoint CLI and
  Markdown report renderer. It tracks `start`, `review`, `complete`, `show`,
  and `report`, accepts the structured `REVIEW_PROMPT.md` answer through
  `--review-json`, and refuses completion without the required review.
- `scripts/audit_upstream_decisions.py`: read-only audit of the current ledger
  for consistency, review completeness, Git provenance, and decision rules.
- `REVIEW_PROMPT.md`: paste-ready Codex reviewer prompt with the reinspection,
  reward-hacking, provenance, fork-gate, coverage, and JSON-answer
  requirements.
- `FULL_AUDIT_PROMPT.md`: paste-ready prompt for re-auditing every ledger
  record from scratch and filing verified, de-duplicated Issues.
- `REVIEW_RULES.md`: path-specific fork checks for Python, Dashboard, OpenAPI,
  NapCat, docs, dependencies, workflows, tests, plugins, and release metadata.

All tools use only the Python standard library and accept explicit paths, so
they do not add project dependencies or require loading the complete ledger.
