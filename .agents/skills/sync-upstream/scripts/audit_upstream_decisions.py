#!/usr/bin/env python3
"""Audit the upstream decision ledger for consistency and provenance."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from upstream_decisions import LedgerError, latest_by_commit, load_events

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TRAILER_RE = re.compile(r"(?im)^\s*Upstream(?:-| )Commit\s*:\s*([0-9a-f]{40})\b")
CHERRY_RE = re.compile(r"(?im)\(cherry picked from commit ([0-9a-f]{40})\)")
ADAPTED_RE = re.compile(r"(?im)^\s*Adapted from upstream ([0-9a-f]{40})\b")
SUMMARY_PR_RE = re.compile(r"\(#(\d+)\)\.?\s*$")
REVIEW_FIELDS = (
    "review_verdict",
    "reviewer",
    "review_notes",
    "review_rounds",
    "reviewed_at_utc",
)
LEGACY_REVIEW_CUTOFF_UTC = "2026-10-19T17:38:28Z"
CODE_DISPOSITIONS = {"cherry-pick", "adapt", "replay"}
NO_CODE_DISPOSITIONS = {"skip", "revisit"}


def git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
    )


def commit_exists(repo: Path, sha: str) -> bool:
    if not SHA_RE.fullmatch(sha):
        return False
    return git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def commit_body(repo: Path, sha: str) -> str:
    result = git(repo, "show", "-s", "--format=%B", sha)
    return result.stdout if result.returncode == 0 else ""


def commit_is_ancestor(repo: Path, sha: str, ref: str = "HEAD") -> bool:
    if not commit_exists(repo, sha):
        return False
    return git(repo, "merge-base", "--is-ancestor", sha, ref).returncode == 0


def provenance_commits(body: str) -> set[str]:
    return (
        set(TRAILER_RE.findall(body))
        | set(CHERRY_RE.findall(body))
        | set(ADAPTED_RE.findall(body))
    )


def is_legacy_review_record(
    origin_recorded_at_utc: str | None,
    *,
    disposition: str = "",
    baseline_disposition: str | None = None,
    post_cutoff_disposition_changed: bool = False,
) -> bool:
    if not origin_recorded_at_utc:
        return False
    if origin_recorded_at_utc >= LEGACY_REVIEW_CUTOFF_UTC:
        return False
    if post_cutoff_disposition_changed:
        return False
    return baseline_disposition is None or disposition == baseline_disposition


def add_finding(
    findings: list[dict[str, Any]],
    record: dict[str, Any] | None,
    severity: str,
    code: str,
    message: str,
    **extra: Any,
) -> None:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
        "upstream_commit": (record or {}).get("upstream_commit", ""),
        "disposition": (record or {}).get("disposition", ""),
    }
    item.update(extra)
    findings.append(item)


def audit_record(
    record: dict[str, Any],
    repo: Path,
    *,
    check_git: bool,
    require_review: bool,
    strict_provenance: bool,
    origin_recorded_at_utc: str | None = None,
    baseline_disposition: str | None = None,
    post_cutoff_disposition_changed: bool = False,
    ref: str = "HEAD",
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    disposition = record.get("disposition", "")
    integration = record.get("integration_commits", [])
    follow_ups = record.get("follow_up_commits", [])
    summary = record.get("summary", "")

    def add(severity: str, code: str, message: str, **extra: Any) -> None:
        add_finding(findings, record, severity, code, message, **extra)

    if not record.get("source_pr"):
        add("warning", "missing-source-pr", "no source PR is recorded")
    if not record.get("reason_codes"):
        add("warning", "missing-reason-codes", "no reason code is recorded")
    if not record.get("affected_paths"):
        add("warning", "missing-affected-paths", "no affected path is recorded")
    pr_match = SUMMARY_PR_RE.search(summary)
    if pr_match and pr_match.group(1) not in record.get("source_pr", []):
        add(
            "warning",
            "summary-pr-mismatch",
            f"summary names PR #{pr_match.group(1)} but source_pr does not",
        )

    if disposition in CODE_DISPOSITIONS and not integration:
        add(
            "error", "missing-integration", f"{disposition} names no integration commit"
        )
    if disposition in NO_CODE_DISPOSITIONS and integration:
        add(
            "error",
            "unexpected-integration",
            f"{disposition} must name no integration commit",
        )
    if disposition == "adapt" and not str(record.get("fork_adaptation", "")).strip():
        add("error", "missing-fork-adaptation", "adapt has no fork adaptation note")
    if disposition in CODE_DISPOSITIONS and not record.get("tests"):
        add("warning", "missing-tests", f"{disposition} records no tests")
    if disposition == "skip" and not (
        str(record.get("notes", "")).strip()
        or str(record.get("revisit_when", "")).strip()
    ):
        add(
            "warning",
            "missing-skip-rationale",
            "skip has no notes or revisit condition",
        )
    if disposition == "revisit" and not str(record.get("revisit_when", "")).strip():
        add("warning", "missing-revisit-condition", "revisit has no revisit condition")

    present_review_fields = [key for key in REVIEW_FIELDS if key in record]
    if not present_review_fields:
        if is_legacy_review_record(
            origin_recorded_at_utc,
            disposition=disposition,
            baseline_disposition=baseline_disposition,
            post_cutoff_disposition_changed=post_cutoff_disposition_changed,
        ):
            add(
                "info",
                "legacy-review-exempt",
                "decision predates the independent-review policy; "
                f"legacy records before {LEGACY_REVIEW_CUTOFF_UTC} are exempt",
            )
        else:
            add(
                "error" if require_review else "warning",
                "missing-review",
                "no independent review is recorded",
            )
    elif len(present_review_fields) != len(REVIEW_FIELDS):
        missing = sorted(set(REVIEW_FIELDS) - set(present_review_fields))
        add("error", "incomplete-review", f"review is missing: {', '.join(missing)}")
    else:
        verdict = record.get("review_verdict")
        reviewer = str(record.get("reviewer", ""))
        if verdict == "fix":
            add(
                "error",
                "final-review-fix",
                "a final decision cannot keep a fix verdict",
            )
        if disposition == "revisit" and verdict != "revisit":
            add(
                "error",
                "review-verdict-mismatch",
                "revisit needs a revisit review verdict",
            )
        if disposition != "revisit" and verdict == "revisit":
            add(
                "error",
                "review-verdict-mismatch",
                "non-revisit decision has a revisit verdict",
            )
        if reviewer != "codex" and not reviewer.startswith("codex/"):
            add(
                "warning",
                "reviewer-not-codex",
                f"reviewer is {reviewer or 'empty'}, not Codex",
            )
        rounds = record.get("review_rounds")
        if not isinstance(rounds, int) or rounds < 1:
            add(
                "error",
                "invalid-review-rounds",
                "review_rounds must be a positive integer",
            )

    if check_git:
        if not commit_exists(repo, record.get("upstream_commit", "")):
            add(
                "error",
                "missing-upstream-commit",
                "upstream commit object is not in this repo",
            )
        for integration_commit in integration:
            if not commit_exists(repo, integration_commit):
                add(
                    "error",
                    "missing-integration-commit",
                    "integration commit object is not in this repo",
                    integration_commit=integration_commit,
                )
                continue
            if not commit_is_ancestor(repo, integration_commit, ref):
                add(
                    "error",
                    "unreachable-integration-commit",
                    f"integration commit is not reachable from {ref}",
                    integration_commit=integration_commit,
                )
            found = provenance_commits(commit_body(repo, integration_commit))
            if record.get("upstream_commit") in found:
                continue
            if found:
                add(
                    "error",
                    "provenance-mismatch",
                    "integration commit names a different upstream commit",
                    integration_commit=integration_commit,
                    found=sorted(found),
                )
            else:
                add(
                    "error" if strict_provenance else "warning",
                    "provenance-missing",
                    "integration commit has no upstream provenance trailer",
                    integration_commit=integration_commit,
                )
        for follow_up_commit in follow_ups:
            if not commit_exists(repo, follow_up_commit):
                add(
                    "error",
                    "missing-follow-up-commit",
                    "follow-up commit object is not in this repo",
                    follow_up_commit=follow_up_commit,
                )
                continue
            if not commit_is_ancestor(repo, follow_up_commit, ref):
                add(
                    "error",
                    "unreachable-follow-up-commit",
                    f"follow-up commit is not reachable from {ref}",
                    follow_up_commit=follow_up_commit,
                )

    return findings


def duplicate_integration_findings(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    owners: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for integration_commit in record.get("integration_commits", []):
            owners[integration_commit].add(record["upstream_commit"])
    findings: list[dict[str, Any]] = []
    for integration_commit, upstream_commits in sorted(owners.items()):
        if len(upstream_commits) < 2:
            continue
        add_finding(
            findings,
            None,
            "warning",
            "duplicate-integration",
            "one integration commit is attributed to multiple upstream commits",
            integration_commit=integration_commit,
            upstream_commits=sorted(upstream_commits),
        )
    return findings


def matches_filter(record: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.commit and not record["upstream_commit"].startswith(args.commit.lower()):
        return False
    if args.disposition and record.get("disposition") != args.disposition:
        return False
    if args.status and record.get("status") != args.status:
        return False
    return True


def print_human(
    findings: list[dict[str, Any]],
    records: int,
    *,
    verbose: bool,
    filtered: bool,
) -> None:
    severity_counts = Counter(item["severity"] for item in findings)
    print(f"records: {records}")
    print(
        f"errors: {severity_counts.get('error', 0)}, "
        f"warnings: {severity_counts.get('warning', 0)}, "
        f"legacy/review exceptions: {severity_counts.get('info', 0)}"
    )
    for item in findings:
        if item["severity"] != "error" and not (verbose or filtered):
            continue
        location = (
            item["upstream_commit"][:12] or item.get("integration_commit", "")[:12]
        )
        print(
            f"{item['severity'].upper():7} {item['code']:26} "
            f"{location:12} {item['message']}"
        )
        if item.get("found"):
            print(f"        found: {', '.join(item['found'])}")
    code_counts = Counter(item["code"] for item in findings)
    if code_counts and not (verbose or filtered):
        print("\nfindings by code:")
        for code, count in sorted(code_counts.items()):
            print(f"  {code}: {count}")
        print("Use --verbose to list warnings, or --json for machine output.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path("upstream-decisions.jsonl"))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--commit", help="audit one full SHA or prefix")
    parser.add_argument(
        "--range", help="audit upstream commits in a git revision range"
    )
    parser.add_argument("--disposition")
    parser.add_argument("--status")
    parser.add_argument(
        "--require-review",
        action="store_true",
        help="treat a missing independent review as an error",
    )
    parser.add_argument(
        "--strict-provenance",
        action="store_true",
        help="treat a missing provenance trailer as an error",
    )
    parser.add_argument("--no-git", action="store_true", help="skip git object checks")
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="require integration commits to be ancestors of this ref",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list warnings and legacy review exceptions too",
    )
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        events = load_events(args.file)
    except (LedgerError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    first_recorded: dict[str, str] = {}
    baseline_disposition: dict[str, str] = {}
    post_cutoff_disposition_changed: set[str] = set()
    last_disposition: dict[str, str] = {}
    for event in events:
        commit = event["upstream_commit"]
        if event["event_type"] == "delete":
            first_recorded.pop(commit, None)
            baseline_disposition.pop(commit, None)
            post_cutoff_disposition_changed.discard(commit)
            last_disposition.pop(commit, None)
            continue
        disposition = event.get("disposition", "")
        if commit not in first_recorded:
            first_recorded[commit] = event["recorded_at_utc"]
        elif (
            event["recorded_at_utc"] >= LEGACY_REVIEW_CUTOFF_UTC
            and last_disposition.get(commit) != disposition
        ):
            post_cutoff_disposition_changed.add(commit)
        if event["recorded_at_utc"] < LEGACY_REVIEW_CUTOFF_UTC:
            baseline_disposition[commit] = disposition
        last_disposition[commit] = disposition
    records = [
        record
        for record in latest_by_commit(events).values()
        if record is not None and matches_filter(record, args)
    ]
    if args.range:
        result = git(args.repo.resolve(), "rev-list", args.range)
        if result.returncode:
            print(
                f"error: cannot read range {args.range}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return 2
        allowed = set(result.stdout.split())
        records = [record for record in records if record["upstream_commit"] in allowed]
    findings: list[dict[str, Any]] = []
    for record in records:
        findings.extend(
            audit_record(
                record,
                args.repo.resolve(),
                check_git=not args.no_git,
                require_review=args.require_review,
                strict_provenance=args.strict_provenance,
                origin_recorded_at_utc=first_recorded.get(record["upstream_commit"]),
                baseline_disposition=baseline_disposition.get(
                    record["upstream_commit"]
                ),
                post_cutoff_disposition_changed=(
                    record["upstream_commit"] in post_cutoff_disposition_changed
                ),
                ref=args.ref,
            )
        )
    findings.extend(duplicate_integration_findings(records))
    findings.sort(
        key=lambda item: (
            item["severity"] != "error",
            item["upstream_commit"],
            item["code"],
        )
    )
    counts = Counter(item["severity"] for item in findings)
    if args.json:
        print(
            json.dumps(
                {
                    "records": len(records),
                    "summary": dict(counts),
                    "findings": findings,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print_human(
            findings,
            len(records),
            verbose=args.verbose,
            filtered=bool(args.commit or args.range or args.disposition or args.status),
        )
    if counts.get("error", 0):
        return 1
    if args.fail_on_warning and counts.get("warning", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
