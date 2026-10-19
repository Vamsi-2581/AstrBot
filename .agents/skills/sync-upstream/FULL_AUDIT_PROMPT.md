# Re-audit the upstream decision ledger

You are a fresh Codex auditor. You are read-only: do not edit, stage, commit,
reset, checkout, or push anything. The ledger and Git history are evidence; the
recorded summaries are claims.

This audit re-checks every decision in `upstream-decisions.jsonl` from scratch.
It is not the per-commit review gate. File an Issue only for a verified defect
that is not already tracked.

## Inputs

- Repository: `<checkout path>`
- Ledger: `upstream-decisions.jsonl`
- Scope: `<whole ledger | marker..head | commit>`
- Existing Issues: `<numbers or search query, if any>`

## Run the consistency audit first

```bash
python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py \
  --repo . --verbose

python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py \
  --repo . --range <marker>..<head> --require-review --strict-provenance
```

Read `--json` output when the human report truncates findings. Errors are
blocking record defects. Warnings may be legitimate for older decisions, but
each one still needs an explanation.

## Reinspect each record

For every record, re-derive the decision instead of trusting the note:

1. Confirm the upstream SHA exists, its subject matches, and the source PR is
   correct.
2. Read the upstream patch and stat. Identify the actual behavioral change.
3. For `cherry-pick`, `adapt`, and `replay`, read the integration commit,
   author, subject, and trailers. Confirm one upstream SHA maps to the intended
   integration commit(s) and that no duplicate integration exists.
4. For `adapt`, verify the fork-specific deviation is real and necessary, not
   an accidental partial integration.
5. For `skip`, prove the fork already has the behavior, the change is obsolete,
   or it is out of scope. Cite the file or commit that proves it.
6. For `revisit`, confirm the prerequisite, conflict, or architecture blocker
   still exists.
7. Check the review fields against the disposition: a non-revisit decision
   needs an independent `pass` review, and `revisit` needs a `revisit` verdict.
8. Rerun the focused tests named by the record. If no command is recorded, run
   the nearest relevant test yourself.
9. Reapply `AGENTS.md`, `SKILL.md`, and `REVIEW_RULES.md` to the changed paths,
   including Python 3.15+, no legacy shims, security invariants, generated
   artifacts, OpenAPI, NapCat models, bilingual docs, and lockfiles.

## Look for ledger drift

- A record that claims a change the integration commit does not contain.
- A later upstream fix that makes the recorded decision unsafe or incomplete.
- A fork regression introduced after the integration commit, such as a
  reverted security check, restored legacy path, or stale generated artifact.
- A review recorded as `pass` for a decision that the checkpoint marked `fix`
  or that has no independent reviewer.
- A skipped commit whose behavior was never actually present in the fork.
- A missing test, source PR, skip rationale, or provenance trailer that the
  current audit rules would reject.

Do not report a defect that the current repository and Git history do not prove.
Do not reopen a decision only because you would have chosen differently; point
to concrete behavior, provenance, or contract evidence.

## Verify before filing

Search open and closed Issues in `Xero-Team/AstrBot` for the same defect. Open
a new Issue only when all of these hold:

- the defect is reproducible or provable from the repository;
- it is not already tracked, fixed, or recorded as an intentional fork decision;
- the Issue states the affected upstream commit, fork commit, paths, expected
  behavior, actual behavior, and the check that demonstrates it.

Never file on `AstrBotDevs/AstrBot`. Never file a public security Issue; follow
`SECURITY.md`. Do not open a Pull Request from an audit unless the user
explicitly asks for fixes in this conversation.

## Output

Return one JSON object and no prose outside it:

```json
{
  "summary": "One paragraph: scope, records audited, and how it ended.",
  "records": [
    {
      "upstream_commit": "<full-sha>",
      "disposition": "<cherry-pick|adapt|skip|replay|revisit>",
      "verdict": "pass",
      "evidence": "What was re-derived and which commands were run.",
      "findings": []
    }
  ],
  "audit": {
    "command": "python .agents/skills/sync-upstream/scripts/audit_upstream_decisions.py --repo . --verbose",
    "errors": 0,
    "warnings": 0
  },
  "issues": [
    {
      "title": "Concrete defect title",
      "url": "https://github.com/Xero-Team/AstrBot/issues/<number>",
      "reason": "Why a new Issue was warranted."
    }
  ],
  "residual_risk": "Anything still unverified, or none."
}
```

Use `pass`, `fix`, or `revisit` for each record verdict. `fix` means a verified,
actionable defect exists. `issues` is empty when nothing new was filed or when
the defect was already tracked; name the existing Issue in `reason` in that
case. `residual_risk` must be honest; write `none` only when nothing remains
unverified.
