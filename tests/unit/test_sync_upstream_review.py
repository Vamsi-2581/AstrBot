import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

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


def _namespace(**overrides):
    values = {
        "commit": "a" * 40,
        "disposition": "adapt",
        "summary": "subject",
        "status": "active",
        "source_pr": [],
        "reason_code": [],
        "affected_paths": [],
        "integration_commit": ["b" * 40],
        "follow_up_commit": [],
        "test": [],
        "supersedes": [],
        "fork_adaptation": "",
        "revisit_when": "",
        "notes": "",
        "review_verdict": "pass",
        "reviewer": "codex/gpt-5.6-sol:high",
        "review_notes": "checked",
        "review_rounds": 1,
        "reviewed_at_utc": "2026-10-19T00:00:00Z",
        "source": "manual",
        "recorded_at_utc": "2026-10-19T00:00:00Z",
    }
    values.update(overrides)
    return Namespace(**values)


def test_ledger_records_final_review_fields():
    ledger = _load("upstream_decisions")
    event = ledger.make_upsert(_namespace(), [], "add")
    ledger.validate_event(event)
    assert event["review_verdict"] == "pass"
    assert event["reviewer"] == "codex/gpt-5.6-sol:high"
    assert event["review_rounds"] == 1


def test_ledger_rejects_review_without_notes():
    ledger = _load("upstream_decisions")
    event = ledger.make_upsert(_namespace(review_notes=""), [], "add")
    with pytest.raises(ledger.LedgerError, match="review_notes"):
        ledger.validate_event(event)


def test_checkpoint_requires_passing_review_before_complete(tmp_path: Path):
    module = _load("sync_run_state")
    state_path = tmp_path / "state.json"
    state = module.new_state("c" * 40, "d" * 40)
    module.save_state(state_path, state)

    module.cmd_start(Namespace(state=state_path, commit="a" * 40, json=False))
    with pytest.raises(module.StateError, match="no independent review"):
        module.cmd_complete(
            Namespace(
                state=state_path,
                commit="a" * 40,
                disposition="adapt",
                integration_commit=["b" * 40],
                test=[],
                risk=None,
                json=False,
            )
        )

    with pytest.raises(module.StateError, match="Codex"):
        module.cmd_review(
            Namespace(
                state=state_path,
                commit="a" * 40,
                findings="looks wrong",
                findings_file=None,
                verdict="fix",
                reviewer="opencode/some-model",
                test=[],
                json=False,
            )
        )

    module.cmd_review(
        Namespace(
            state=state_path,
            commit="a" * 40,
            findings="fix the trailer",
            findings_file=None,
            verdict="fix",
            reviewer="codex",
            test=["uv run pytest tests/unit"],
            json=False,
        )
    )
    with pytest.raises(module.StateError, match="passing review"):
        module.cmd_complete(
            Namespace(
                state=state_path,
                commit="a" * 40,
                disposition="adapt",
                integration_commit=["b" * 40],
                test=[],
                risk=None,
                json=False,
            )
        )

    module.cmd_review(
        Namespace(
            state=state_path,
            commit="a" * 40,
            findings="trailer fixed",
            findings_file=None,
            verdict="pass",
            reviewer="codex/gpt-5.6-sol:high",
            test=[],
            json=False,
        )
    )
    module.cmd_complete(
        Namespace(
            state=state_path,
            commit="a" * 40,
            disposition="adapt",
            integration_commit=["b" * 40],
            test=[],
            risk="Windows-only path remains unverified",
            json=False,
        )
    )

    saved = module.load_state(state_path)
    entry = saved["commits"]["a" * 40]
    assert entry["status"] == "complete"
    assert entry["review"]["rounds"] == 2
    assert entry["integration_commits"] == ["b" * 40]
    assert entry["residual_risk"].startswith("Windows-only")


def test_checkpoint_revisit_and_skip_rules(tmp_path: Path):
    module = _load("sync_run_state")
    state_path = tmp_path / "state.json"
    module.save_state(state_path, module.new_state("c" * 40, "d" * 40))

    module.cmd_start(Namespace(state=state_path, commit="a" * 40, json=False))
    module.cmd_review(
        Namespace(
            state=state_path,
            commit="a" * 40,
            findings="cannot establish intent",
            findings_file=None,
            verdict="revisit",
            reviewer="codex",
            test=[],
            json=False,
        )
    )
    module.cmd_complete(
        Namespace(
            state=state_path,
            commit="a" * 40,
            disposition="revisit",
            integration_commit=[],
            test=[],
            risk=None,
            json=False,
        )
    )
    assert module.load_state(state_path)["commits"]["a" * 40]["status"] == "revisit"

    module.cmd_start(Namespace(state=state_path, commit="e" * 40, json=False))
    module.cmd_review(
        Namespace(
            state=state_path,
            commit="e" * 40,
            findings="fork already has this behavior",
            findings_file=None,
            verdict="pass",
            reviewer="codex",
            test=[],
            json=False,
        )
    )
    module.cmd_complete(
        Namespace(
            state=state_path,
            commit="e" * 40,
            disposition="skip",
            integration_commit=[],
            test=[],
            risk=None,
            json=False,
        )
    )
    assert module.load_state(state_path)["commits"]["e" * 40]["status"] == "complete"


def test_init_creates_checkpoint_from_marker_and_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    module = _load("sync_run_state")
    marker = "c" * 40
    head = "d" * 40
    monkeypatch.setattr(module, "read_marker", lambda _path: marker)
    monkeypatch.setattr(module, "run_git", lambda _repo, *_args: head)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    module.cmd_init(
        Namespace(
            repo=tmp_path,
            sync_file=Path("upstream-sync.yaml"),
            marker=None,
            head="upstream/master",
            state=None,
            force=False,
            json=False,
        )
    )
    state_file = tmp_path / ".tmp" / "sync-run" / f"{marker[:12]}-{head[:12]}.json"
    state = module.load_state(state_file)
    assert state["marker"] == marker
    assert state["head"] == head


def test_report_includes_review_and_residual_risk(tmp_path: Path, monkeypatch):
    module = _load("sync_run_state")
    state_path = tmp_path / "state.json"
    state = module.new_state("c" * 40, "d" * 40)
    module.save_state(state_path, state)
    commit = "a" * 40
    module.cmd_start(Namespace(state=state_path, commit=commit, json=False))
    module.cmd_review(
        Namespace(
            state=state_path,
            commit=commit,
            findings="checked upstream intent and fork gates",
            findings_file=None,
            verdict="pass",
            reviewer="codex/gpt-5.6-sol:high",
            test=["uv run pytest tests/unit"],
            json=False,
        )
    )
    module.cmd_complete(
        Namespace(
            state=state_path,
            commit=commit,
            disposition="adapt",
            integration_commit=["b" * 40],
            test=[],
            risk="manual Windows check remains",
            json=False,
        )
    )
    monkeypatch.setattr(
        module, "git_commits", lambda *_args: [(commit, "upstream subject")]
    )
    monkeypatch.setattr(module, "load_events", lambda _path: [])
    output = tmp_path / "report.md"
    module.cmd_report(
        Namespace(
            state=state_path,
            repo=tmp_path,
            ledger=tmp_path / "missing.jsonl",
            output=output,
        )
    )
    report = output.read_text(encoding="utf-8")
    assert "upstream subject" in report
    assert "pass by codex/gpt-5.6-sol:high" in report
    assert "manual Windows check remains" in report


def test_ledger_records_follow_up_commits():
    ledger = _load("upstream_decisions")
    event = ledger.make_upsert(
        _namespace(follow_up_commit=["c" * 40]),
        [],
        "add",
    )
    ledger.validate_event(event)
    assert event["follow_up_commits"] == ["c" * 40]


def test_import_git_records_decisions_without_follow_up_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ledger = _load("upstream_decisions")
    ledger_path = tmp_path / "upstream-decisions.jsonl"
    upstream = "a" * 40
    integration = "b" * 40
    monkeypatch.setattr(
        ledger,
        "git_log_records",
        lambda _repo, _range: [
            {
                "upstream_commit": upstream,
                "disposition": "adapt",
                "summary": "subject",
                "source_pr": ["123"],
                "reason_codes": ["security"],
                "git_commit": integration,
                "tests": ["uv run pytest tests/unit"],
                "fork_deviations": "adapted",
            }
        ],
    )

    ledger.command_import_git(
        Namespace(
            file=ledger_path,
            repo=tmp_path,
            range="old..new",
            recorded_at_utc="2026-10-20T00:00:00Z",
            dry_run=False,
            json=False,
        )
    )

    event = ledger.latest_by_commit(ledger.load_events(ledger_path))[upstream]
    assert event["integration_commits"] == [integration]
    assert "follow_up_commits" not in event


def test_ledger_update_preserves_review_fields(tmp_path: Path):
    ledger = _load("upstream_decisions")
    ledger_path = tmp_path / "upstream-decisions.jsonl"
    commit = "a" * 40
    add = _namespace(file=ledger_path, json=False, follow_up_commit=["c" * 40])
    ledger.command_add_or_update(add, "add")

    update = Namespace(
        file=ledger_path,
        json=False,
        commit=commit,
        disposition=None,
        summary=None,
        status=None,
        source_pr=None,
        reason_code=None,
        affected_paths=None,
        integration_commit=None,
        follow_up_commit=None,
        test=None,
        supersedes=None,
        fork_adaptation=None,
        revisit_when=None,
        notes=None,
        review_verdict=None,
        reviewer=None,
        review_notes=None,
        review_rounds=None,
        reviewed_at_utc=None,
        source="manual",
        recorded_at_utc=None,
    )
    ledger.command_add_or_update(update, "update")

    current = ledger.latest_by_commit(ledger.load_events(ledger_path))[commit]
    assert current["review_verdict"] == "pass"
    assert current["reviewer"] == "codex/gpt-5.6-sol:high"
    assert current["review_notes"] == "checked"
    assert current["review_rounds"] == 1
    assert current["follow_up_commits"] == ["c" * 40]


def test_checkpoint_caps_fix_rounds(tmp_path: Path):
    module = _load("sync_run_state")
    state_path = tmp_path / "state.json"
    module.save_state(state_path, module.new_state("c" * 40, "d" * 40))
    commit = "a" * 40
    module.cmd_start(Namespace(state=state_path, commit=commit, json=False))
    for _ in range(2):
        module.cmd_review(
            Namespace(
                state=state_path,
                commit=commit,
                findings="still wrong",
                findings_file=None,
                verdict="fix",
                reviewer="codex",
                test=[],
                json=False,
            )
        )
    with pytest.raises(module.StateError, match="two fix rounds"):
        module.cmd_review(
            Namespace(
                state=state_path,
                commit=commit,
                findings="still wrong",
                findings_file=None,
                verdict="fix",
                reviewer="codex",
                test=[],
                json=False,
            )
        )


def test_review_json_is_rendered_and_stored(tmp_path: Path):
    module = _load("sync_run_state")
    state_path = tmp_path / "state.json"
    module.save_state(state_path, module.new_state("c" * 40, "d" * 40))
    commit = "a" * 40
    module.cmd_start(Namespace(state=state_path, commit=commit, json=False))
    review_path = tmp_path / "review.json"
    review_path.write_text(
        """{
  "summary": "Adapted the upstream behavior to the fork boundary.",
  "reviewed_files": ["astrbot/core/example.py"],
  "skipped_files": [{"path": "docs/legacy.md", "reason": "deleted"}],
  "verdict": "pass",
  "findings": [
    {
      "severity": "major",
      "category": "provenance",
      "path": "astrbot/core/example.py",
      "line": 42,
      "summary": "trailer is missing",
      "instruction": "add Upstream-Commit"
    }
  ],
  "tests": [{"command": "uv run pytest", "result": "passed"}],
  "residual_risk": "none"
}
""",
        encoding="utf-8",
    )
    module.cmd_review(
        Namespace(
            state=state_path,
            commit=commit,
            findings=None,
            findings_file=None,
            review_json=review_path,
            verdict=None,
            reviewer="codex/gpt-5.6-sol:high",
            test=[],
            json=False,
        )
    )
    entry = module.load_state(state_path)["commits"][commit]
    assert entry["review"]["verdict"] == "pass"
    assert entry["review"]["summary"].startswith("Adapted")
    assert entry["review"]["reviewed_files"] == ["astrbot/core/example.py"]
    assert entry["review"]["skipped_files"] == [
        {"path": "docs/legacy.md", "reason": "deleted"}
    ]
    assert (
        "[major/provenance] astrbot/core/example.py:42" in entry["review"]["findings"]
    )
    assert entry["tests"] == ["uv run pytest: passed"]
    assert entry["residual_risk"] == "none"


def test_review_json_enforces_changed_file_coverage(tmp_path: Path, monkeypatch):
    module = _load("sync_run_state")
    state_path = tmp_path / "state.json"
    module.save_state(state_path, module.new_state("c" * 40, "d" * 40))
    commit = "a" * 40
    module.cmd_start(Namespace(state=state_path, commit=commit, json=False))
    review_path = tmp_path / "review.json"

    def write(reviewed_files):
        review_path.write_text(
            __import__("json").dumps(
                {
                    "summary": "Reviewed the change.",
                    "reviewed_files": reviewed_files,
                    "skipped_files": [],
                    "verdict": "pass",
                    "findings": [],
                    "tests": [{"command": "uv run pytest", "result": "pass"}],
                    "residual_risk": "none",
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(module, "changed_files", lambda _repo, _ref: ["a.py", "b.py"])
    write(["a.py"])
    with pytest.raises(module.StateError, match="did not cover changed files: b.py"):
        module.cmd_review(
            Namespace(
                state=state_path,
                commit=commit,
                findings=None,
                findings_file=None,
                review_json=review_path,
                verdict=None,
                reviewer="codex",
                test=[],
                repo=tmp_path,
                changed_files_from=commit,
                json=False,
            )
        )

    write(["a.py", "b.py"])
    module.cmd_review(
        Namespace(
            state=state_path,
            commit=commit,
            findings=None,
            findings_file=None,
            review_json=review_path,
            verdict=None,
            reviewer="codex",
            test=[],
            repo=tmp_path,
            changed_files_from=commit,
            json=False,
        )
    )
    assert (
        module.load_state(state_path)["commits"][commit]["review"]["verdict"] == "pass"
    )


def test_review_findings_reject_unknown_severity_and_category():
    module = _load("sync_run_state")
    finding = {
        "severity": "urgent",
        "category": "bug",
        "path": "a.py",
        "line": 1,
        "summary": "what",
        "instruction": "fix",
    }
    with pytest.raises(module.StateError, match="severity"):
        module.render_findings([finding])
    finding["severity"] = "high"
    finding["category"] = "vibes"
    with pytest.raises(module.StateError, match="category"):
        module.render_findings([finding])
