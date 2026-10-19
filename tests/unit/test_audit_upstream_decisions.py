import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = REPO_ROOT / ".agents" / "skills" / "sync-upstream" / "scripts"


def _load(name: str):
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    path = SKILL_SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Failed to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(**overrides):
    record = {
        "upstream_commit": "a" * 40,
        "disposition": "adapt",
        "summary": "subject",
        "source_pr": ["123"],
        "reason_codes": ["security"],
        "affected_paths": ["astrbot/core/example.py"],
        "integration_commits": ["b" * 40],
        "tests": ["uv run pytest tests/unit"],
        "fork_adaptation": "kept the fork boundary",
        "review_verdict": "pass",
        "reviewer": "codex/gpt-5.6-sol:high",
        "review_notes": "checked",
        "review_rounds": 1,
        "reviewed_at_utc": "2026-10-19T00:00:00Z",
    }
    record.update(overrides)
    return record


def _audit(record, **flags):
    module = _load("audit_upstream_decisions")
    options = {
        "check_git": False,
        "require_review": True,
        "strict_provenance": False,
        "origin_recorded_at_utc": "2026-10-20T00:00:00Z",
    }
    options.update(flags)
    return module.audit_record(record, Path("."), **options)


def test_complete_decision_has_no_findings():
    assert _audit(_record()) == []


def test_missing_review_is_warning_until_required():
    record = _record()
    for key in (
        "review_verdict",
        "reviewer",
        "review_notes",
        "review_rounds",
        "reviewed_at_utc",
    ):
        del record[key]
    warning = _audit(record, require_review=False)
    assert [item["code"] for item in warning] == ["missing-review"]
    assert warning[0]["severity"] == "warning"
    error = _audit(record, require_review=True)
    assert error[0]["severity"] == "error"


def test_legacy_decision_reports_review_exemption():
    record = _record()
    for key in (
        "review_verdict",
        "reviewer",
        "review_notes",
        "review_rounds",
        "reviewed_at_utc",
    ):
        del record[key]
    findings = _audit(
        record,
        origin_recorded_at_utc="2026-10-18T00:00:00Z",
    )
    assert [item["code"] for item in findings] == ["legacy-review-exempt"]
    assert findings[0]["severity"] == "info"


def test_post_cutoff_revisit_is_not_legacy_review_exempt():
    record = _record(
        disposition="revisit",
        integration_commits=[],
        recorded_at_utc="2026-10-20T00:00:00Z",
        revisit_when="fork architecture changed",
    )
    for key in (
        "review_verdict",
        "reviewer",
        "review_notes",
        "review_rounds",
        "reviewed_at_utc",
    ):
        del record[key]
    findings = _audit(
        record,
        origin_recorded_at_utc="2026-10-18T00:00:00Z",
        baseline_disposition="adapt",
    )
    assert [item["code"] for item in findings] == ["missing-review"]
    assert findings[0]["severity"] == "error"


def test_legacy_review_exemption_restarts_after_delete(tmp_path: Path, capsys):
    module = _load("audit_upstream_decisions")
    commit = "a" * 40
    common = {
        "schema_version": 1,
        "event_type": "upsert",
        "operation": "add",
        "upstream_commit": commit,
        "source": "manual",
        "disposition": "adapt",
        "status": "active",
        "summary": "subject",
        "source_pr": ["123"],
        "reason_codes": ["security"],
        "affected_paths": ["astrbot/core/example.py"],
        "fork_adaptation": "Keep the current fork implementation.",
        "integration_commits": ["b" * 40],
        "tests": ["uv run pytest tests/unit"],
    }
    add = {
        **common,
        "record_id": f"2026-10-18T00:00:00Z-{commit[:12]}-1",
        "revision": 1,
        "recorded_at_utc": "2026-10-18T00:00:00Z",
    }
    delete = {
        "schema_version": 1,
        "event_type": "delete",
        "operation": "delete",
        "upstream_commit": commit,
        "revision": 2,
        "recorded_at_utc": "2026-10-20T00:00:00Z",
        "source": "manual",
        "reason": "superseded record",
    }
    readd = {
        **common,
        "operation": "update",
        "record_id": f"2026-10-20T00:00:00Z-{commit[:12]}-3",
        "revision": 3,
        "recorded_at_utc": "2026-10-20T00:00:00Z",
    }
    ledger = tmp_path / "upstream-decisions.jsonl"
    ledger.write_text(
        "\n".join(json.dumps(item) for item in (add, delete, readd)) + "\n",
        encoding="utf-8",
    )

    exit_code = module.main(
        ["--file", str(ledger), "--no-git", "--require-review", "--json"]
    )

    assert exit_code == 1
    codes = {item["code"] for item in json.loads(capsys.readouterr().out)["findings"]}
    assert "missing-review" in codes
    assert "legacy-review-exempt" not in codes


def test_legacy_review_exemption_resets_after_post_cutoff_disposition_change(
    tmp_path: Path, capsys
):
    module = _load("audit_upstream_decisions")
    commit = "a" * 40
    common = {
        "schema_version": 1,
        "event_type": "upsert",
        "operation": "update",
        "upstream_commit": commit,
        "source": "manual",
        "status": "active",
        "summary": "subject",
        "source_pr": ["123"],
        "reason_codes": ["security"],
        "affected_paths": ["astrbot/core/example.py"],
        "fork_adaptation": "Keep the current fork implementation.",
        "integration_commits": ["b" * 40],
        "tests": ["uv run pytest tests/unit"],
    }

    def event(
        revision: int,
        recorded_at: str,
        disposition: str,
        operation: str,
    ) -> dict:
        return {
            **common,
            "operation": operation,
            "record_id": f"{recorded_at}-{commit[:12]}-{revision}",
            "revision": revision,
            "recorded_at_utc": recorded_at,
            "disposition": disposition,
        }

    events = [
        event(1, "2026-10-18T00:00:00Z", "adapt", "add"),
        event(2, "2026-10-20T00:00:00Z", "revisit", "update"),
        event(3, "2026-10-21T00:00:00Z", "adapt", "update"),
    ]
    ledger = tmp_path / "upstream-decisions.jsonl"
    ledger.write_text(
        "\n".join(json.dumps(item) for item in events) + "\n",
        encoding="utf-8",
    )

    exit_code = module.main(
        ["--file", str(ledger), "--no-git", "--require-review", "--json"]
    )

    assert exit_code == 1
    codes = {item["code"] for item in json.loads(capsys.readouterr().out)["findings"]}
    assert "missing-review" in codes
    assert "legacy-review-exempt" not in codes


def test_adapt_requires_fork_adaptation_and_tests():
    findings = _audit(_record(fork_adaptation="", tests=[]))
    codes = {item["code"] for item in findings}
    assert "missing-fork-adaptation" in codes
    assert "missing-tests" in codes


def test_skip_must_not_name_integration_and_needs_rationale():
    findings = _audit(
        _record(
            disposition="skip",
            integration_commits=["b" * 40],
            tests=[],
            fork_adaptation="",
            notes="",
            revisit_when="",
        )
    )
    codes = {item["code"] for item in findings}
    assert "unexpected-integration" in codes
    assert "missing-skip-rationale" in codes


def test_revisit_needs_revisit_verdict_and_condition():
    findings = _audit(
        _record(
            disposition="revisit",
            integration_commits=[],
            tests=[],
            fork_adaptation="",
            review_verdict="pass",
            revisit_when="",
        )
    )
    codes = {item["code"] for item in findings}
    assert "review-verdict-mismatch" in codes
    assert "missing-revisit-condition" in codes


def test_duplicate_integration_is_reported():
    module = _load("audit_upstream_decisions")
    first = _record(upstream_commit="a" * 40)
    second = _record(upstream_commit="c" * 40)
    findings = module.duplicate_integration_findings([first, second])
    assert [item["code"] for item in findings] == ["duplicate-integration"]
    assert findings[0]["upstream_commits"] == ["a" * 40, "c" * 40]


def test_provenance_accepts_trailer_cherry_pick_and_legacy_adapted_line():
    module = _load("audit_upstream_decisions")
    sha = "a" * 40
    assert module.provenance_commits(f"Upstream-Commit: {sha}") == {sha}
    assert module.provenance_commits(f"(cherry picked from commit {sha})") == {sha}
    assert module.provenance_commits(f"Adapted from upstream {sha} (#1).") == {sha}


def test_unreachable_integration_commit_is_an_error(monkeypatch):
    module = _load("audit_upstream_decisions")
    monkeypatch.setattr(module, "commit_exists", lambda *_args: True)
    monkeypatch.setattr(module, "commit_is_ancestor", lambda *_args: False)
    monkeypatch.setattr(
        module,
        "commit_body",
        lambda *_args: f"Upstream-Commit: {'a' * 40}",
    )

    findings = module.audit_record(
        _record(),
        Path("."),
        check_git=True,
        require_review=True,
        strict_provenance=False,
        origin_recorded_at_utc="2026-10-20T00:00:00Z",
    )

    assert [item["code"] for item in findings] == ["unreachable-integration-commit"]


def test_follow_up_commit_must_exist_and_be_reachable(monkeypatch):
    module = _load("audit_upstream_decisions")
    follow_up = "c" * 40
    monkeypatch.setattr(
        module,
        "commit_exists",
        lambda _repo, sha: sha != follow_up,
    )

    def audit(record):
        return module.audit_record(
            record,
            Path("."),
            check_git=True,
            require_review=True,
            strict_provenance=False,
            origin_recorded_at_utc="2026-10-20T00:00:00Z",
        )

    missing = audit(_record(follow_up_commits=[follow_up]))
    assert "missing-follow-up-commit" in {item["code"] for item in missing}

    monkeypatch.setattr(module, "commit_exists", lambda *_args: True)
    monkeypatch.setattr(
        module,
        "commit_is_ancestor",
        lambda _repo, sha, _ref: sha != follow_up,
    )
    monkeypatch.setattr(
        module,
        "commit_body",
        lambda *_args: f"Upstream-Commit: {'a' * 40}",
    )

    unreachable = audit(_record(follow_up_commits=[follow_up]))
    assert "unreachable-follow-up-commit" in {item["code"] for item in unreachable}
