# Apply a reviewed upstream integration plan

Use the sync-upstream skill in apply mode. In Codex CLI, invoke it as
`$sync-upstream`; in OpenCode, load `sync-upstream` with the skill tool.
Execute the reviewed plan supplied in this conversation and carry it through
integration, ledger updates, and verification.

## Inputs and authorization

Find the reviewed commit list, dispositions, interval, and push/PR instructions
in the current conversation or the supplied plan artifact. Reuse decisions and
authorization already given. If the plan is missing, inspect the cursor and
ledger, then ask for the missing plan before applying commits. Do not invent
approved dispositions.

Read these sources as needed; cite them instead of pasting them:

- `AGENTS.md`: fork invariants, toolchain, generated artifacts, and git policy.
- `.agents/skills/sync-upstream/SKILL.md`: apply workflow and provenance.
- `.agents/shared/conventional-commit/REFERENCE.md`: generated commit messages.
- `.agents/shared/ai-contribution/REFERENCE.md` and `AI_POLICY.md`: contribution boundaries.
- `upstream-sync.yaml`: cursor; there is no `pending` field.
- `upstream-decisions.jsonl`: durable decisions and replay authorization.
- `.agents/skills/sync-upstream/scripts/sync_run_state.py`: ephemeral
  checkpoint and report tool for this interval.
- `.agents/skills/sync-upstream/REVIEW_PROMPT.md`: paste-ready reviewer prompt.
- `.agents/skills/sync-upstream/REVIEW_RULES.md`: path-specific fork checks.
- `.agents/skills/sync-upstream/scripts/audit_upstream_decisions.py`: read-only
  ledger audit.

## Prepare

Inspect `git status --short --branch` and `git remote -v`. Preserve unrelated
work and use a feature branch or isolated worktree. Verify `upstream` points to
`https://github.com/AstrBotDevs/AstrBot.git`; add the remote if absent or correct
its URL if needed. Run:

```bash
git fetch --prune --tags upstream
uv run python .agents/skills/sync-upstream/scripts/inspect_upstream.py
```

Read patches with `git show <sha>`. Keep the fork branch as the integration
base. Check the ledger before repeating any prior integration. Initialize the
ephemeral checkpoint after `inspect_upstream.py` confirms the interval:

```bash
STATE=$(python .agents/skills/sync-upstream/scripts/sync_run_state.py init)
```

The checkpoint lives under `.tmp/sync-run/` and is never committed. The ledger
remains authoritative.

## Apply and verify

Process the reviewed interval oldest-first. Mark each commit in the
checkpoint, create one implementation commit per `cherry-pick`, `adapt`, or
`replay` item, and create none for `skip` or `revisit`. Preserve upstream
subjects and authors, with the skill's provenance trailers for adaptations.
Resolve routine conflicts against current fork behavior. Record unresolved
intent as `revisit` instead of guessing.

For every commit, run an independent review in a fresh session before the
ledger record. The actor may be Codex or OpenCode; the reviewer is always
Codex. The actor's own write-up is not a review. Use `REVIEW_PROMPT.md` as the
reviewer's prompt, with `REVIEW_RULES.md` applied to the changed paths. The
reviewer is read-only, reads the upstream patch, the fork diff, `AGENTS.md`,
this skill, the ledger entry, and the tests, reruns the focused tests itself,
accounts for every changed file, and returns `pass`, `fix`, or `revisit` as
JSON. Use a Codex agent spec such as `codex/<model>:<effort>` for the reviewer.

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

The `--changed-files-from` check refuses a review that did not account for
every changed file. `fix` returns findings to the actor; fix and review again.
After two `fix` rounds without a `pass`, record `revisit`. `complete` refuses
a non-revisit disposition without a `pass` review. `revisit` requires a
`revisit` verdict and names no integration commit.

Run focused tests, then the relevant gates in `AGENTS.md`. Record each final
disposition in the ledger with `--review-verdict`, `--reviewer`,
`--review-notes`, `--review-rounds`, and `--reviewed-at-utc`. Audit the interval
and the whole ledger:

```bash
python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py \
  --range <marker>..<head> --require-review --strict-provenance

python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py
```

Advance the cursor only after every SHA has a disposition, the interval audit
has no errors, and the interval is complete, using the metadata-only commit
`chore(sync): record upstream integration`.

Push a feature branch only when already requested. Follow the conversation's
PR instructions and target `Xero-Team/AstrBot` with
`--repo Xero-Team/AstrBot`; verify the returned URL. An upstream PR requires
explicit confirmation of that target. A human maintainer performs merges,
pushes to `master`, tags, and releases under repository policy.

## Deliver

Return the branch, commit/disposition mapping, ledger and cursor status,
audit result, checks actually run, remaining risks, and PR URL if one was
opened. Render the interval report before the PR body:

```bash
python .agents/skills/sync-upstream/scripts/sync_run_state.py report \
  --state "$STATE" --output .tmp/sync-run/report.md
```

Use the report for the PR body and do not commit it. Preserve checkpoint state
if blocked so the next session can resume without repeating completed commits.
