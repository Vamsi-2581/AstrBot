import importlib.util
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


def test_provenance_accepts_trailer_and_cherry_pick_line():
    module = _load("audit_upstream_decisions")
    sha = "a" * 40
    assert module.provenance_commits(f"Upstream-Commit: {sha}") == {sha}
    assert module.provenance_commits(f"(cherry picked from commit {sha})") == {sha}
