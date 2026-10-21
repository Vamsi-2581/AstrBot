#!/usr/bin/env python3
"""Install, configure, run, and audit an Open Code Review whole-project scan."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = SKILL_DIR / ".env"
DEFAULT_OUTPUT_DIR = Path(".tmp") / "ocr-project-review"
DEFAULT_PROVIDER = "astrbot-ocr"
DEFAULT_NPM_PACKAGE = "@alibaba-group/open-code-review"
SYNTAX_MARKER = "## Out of Scope: Compiler-Detected Issues"
SYNTAX_RULE = f"""{SYNTAX_MARKER}

Do not report any issue that a compiler, parser, type checker, linter, or
formatter can detect. This includes:

- syntax or parse errors, unmatched delimiters, invalid indentation, malformed
  literals, and missing language constructs;
- type mismatches, unresolved names, missing or unused imports, unused
  variables, unreachable code, and other compile-time diagnostics;
- formatting, whitespace, naming, import ordering, and other style or lint
  nits.

Treat all of these as already enforced by the project toolchain. Report only
semantic defects that survive compilation: logic errors, runtime failures,
security vulnerabilities, race conditions, resource leaks, data corruption,
incorrect error handling, API misuse, and performance problems. If a candidate
finding is only about syntax, compilation, linting, or formatting, omit it.
"""

DEFAULT_EXCLUDES = (
    "**/.git/*",
    "**/.tmp/*",
    "**/__pycache__/*",
    "**/.venv/*",
    "**/venv/*",
    "**/node_modules/*",
    "**/dist/*",
    "**/build/*",
    "**/coverage/*",
    "**/.mypy_cache/*",
    "**/.ruff_cache/*",
    "**/generated/*",
    "**/*.min.js",
    "**/*.map",
    "**/.env*",
    "**/*.pem",
    "**/*.key",
    "**/*.p12",
    "**/id_rsa*",
    "data/*",
    "logs/*",
)

SEVERITIES = ("critical", "high", "medium", "low", "unknown")
CATEGORIES = (
    "bug",
    "security",
    "performance",
    "maintainability",
    "test",
    "style",
    "documentation",
    "other",
)
VERDICTS = ("pending", "confirmed", "false-positive", "uncertain")
OWN_ALL_PATTERNS = {"*", "**", "**/*", "*/**", "**/**"}
ISSUE_REPO = "Xero-Team/AstrBot"
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
SECURITY_TERMS = (
    "vulnerability",
    "xss",
    "csrf",
    "ssrf",
    "sql injection",
    "command injection",
    "path traversal",
    "auth bypass",
    "authentication bypass",
    "authorization bypass",
    "remote code execution",
    "rce",
    "privilege escalation",
    "deserialization",
    "secret leak",
    "credential leak",
    "hardcoded key",
    "hardcoded secret",
    "exposed api key",
    "credential exposure",
    "secret exposure",
    "private key",
    "buffer overflow",
    "use after free",
    "integer overflow",
    "open redirect",
    "insecure deserialization",
    "command execution",
    "file inclusion",
    "directory traversal",
    "token leak",
    "api key leak",
    "sensitive data exposure",
)
SECURITY_PATTERNS = tuple(
    re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE) for term in SECURITY_TERMS
)


class SkillError(Exception):
    """User-facing failure with a corrective action in the message."""


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fail(message: str) -> None:
    raise SkillError(message)


def redact(text: str, secret: str | None) -> str:
    if secret:
        text = text.replace(secret, "<redacted>")
    return text


def redact_url(url: str) -> str:
    """Drop credentials and query strings so a URL is safe to print."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(
            f"missing {path}. Copy .env.example to .env in the skill directory "
            "and fill in OCR_LLM_URL, OCR_LLM_API_KEY, and OCR_LLM_MODEL."
        )
    values: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            fail(f"{path}:{lineno}: expected KEY=VALUE")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            comment = re.search(r"\s+#", value)
            if comment:
                value = value[: comment.start()].rstrip()
        if not key:
            fail(f"{path}:{lineno}: empty key")
        values[key] = value
    return values


def first_env(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = values.get(name, "").strip()
        if value:
            return value
    return ""


def require_env(values: dict[str, str], label: str, *names: str) -> str:
    value = first_env(values, *names)
    if not value:
        fail(f"missing {label} in .env (accepted keys: {', '.join(names)})")
    return value


def parse_bool(value: str, default: bool) -> bool:
    if not value:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def parse_int(value: str, label: str, default: int, *, minimum: int = 0) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        fail(f"{label} must be an integer, got {value!r}")
    if parsed < minimum:
        fail(f"{label} must be at least {minimum}")
    return parsed


def split_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def settings_from_env(values: dict[str, str]) -> dict[str, Any]:
    url = require_env(
        values,
        "OpenAI-compatible chat completions URL",
        "OCR_LLM_URL",
        "OPENAI_BASE_URL",
        "OPENAI_URL",
        "OPENAI_CHAT_COMPLETIONS_URL",
    )
    if not url.startswith(("http://", "https://")):
        fail("OCR_LLM_URL must start with http:// or https://")
    key = require_env(
        values,
        "OpenAI-compatible API key",
        "OCR_LLM_API_KEY",
        "OCR_LLM_TOKEN",
        "OPENAI_API_KEY",
    )
    model = require_env(values, "model name", "OCR_LLM_MODEL", "OPENAI_MODEL")
    effort = values.get("OCR_EFFORT", "medium").strip() or "medium"
    if effort not in {"low", "medium", "high"}:
        fail("OCR_EFFORT must be low, medium, or high")
    provider = values.get("OCR_PROVIDER_NAME", DEFAULT_PROVIDER).strip()
    if not provider:
        provider = DEFAULT_PROVIDER
    if (
        provider.startswith(".")
        or provider.endswith(".")
        or ".." in provider
        or re.search(r"\s", provider)
        or any(part == "" for part in provider.split("."))
    ):
        fail(f"OCR_PROVIDER_NAME {provider!r} is not a valid OCR provider name")
    return {
        "url": url,
        "key": key,
        "model": model,
        "provider": provider,
        "language": values.get("OCR_REVIEW_LANGUAGE", "中文").strip() or "中文",
        "effort": effort,
        "concurrency": parse_int(
            values.get("OCR_CONCURRENCY", ""),
            "OCR_CONCURRENCY",
            8,
            minimum=1,
        ),
        "timeout": parse_int(values.get("OCR_TIMEOUT", ""), "OCR_TIMEOUT", 15),
        "max_tokens_budget": parse_int(
            values.get("OCR_MAX_TOKENS_BUDGET", ""), "OCR_MAX_TOKENS_BUDGET", 0
        ),
        "batch": values.get("OCR_BATCH", "").strip(),
        "excludes": split_list(values.get("OCR_EXCLUDE", "")),
        "default_excludes": parse_bool(
            values.get("OCR_DEFAULT_EXCLUDES", ""), default=True
        ),
        "npm_package": values.get("OCR_NPM_PACKAGE", DEFAULT_NPM_PACKAGE).strip()
        or DEFAULT_NPM_PACKAGE,
    }


def resolve_ocr_bin() -> str:
    configured = os.environ.get("OCR_BIN", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return str(path)
        found = shutil.which(configured)
        if found:
            return found
        fail(f"OCR_BIN points to {configured!r}, but it is not executable")
    found = shutil.which("ocr")
    if not found:
        fail(
            "ocr is not installed. Run `python .agents/skills/ocr-project-review/"
            "scripts/ocr_skill.py install` (requires npm), or install it from "
            "https://github.com/alibaba/open-code-review/releases."
        )
    return found


def run_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    secret: str | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=capture,
            check=False,
        )
    except FileNotFoundError:
        fail(f"command not found: {args[0]}")
    except OSError as exc:
        fail(f"failed to run {args[0]}: {exc}")


def print_process_output(result: subprocess.CompletedProcess[str], secret: str) -> None:
    if result.stdout:
        print(redact(result.stdout.rstrip(), secret))
    if result.stderr:
        print(redact(result.stderr.rstrip(), secret), file=sys.stderr)


def ensure_ocr(settings: dict[str, Any], *, upgrade: bool, allow_install: bool) -> str:
    existing = shutil.which("ocr") or os.environ.get("OCR_BIN", "")
    if existing and not upgrade:
        return resolve_ocr_bin()

    package = settings["npm_package"]
    npm = shutil.which("npm")
    if not npm:
        fail(
            "npm is required to install the ocr CLI. Install Node.js/npm, or use "
            "the release binary and set OCR_BIN to its path."
        )
    if not allow_install:
        fail("ocr is not installed and --no-install was given")
    print(f"Installing {package} globally with npm...")
    result = run_process([npm, "install", "-g", f"{package}@latest"], capture=False)
    if result.returncode != 0:
        fail("npm install failed; see the output above")
    return resolve_ocr_bin()


def ocr_config_set(ocr: str, key: str, value: str, secret: str) -> None:
    result = run_process([ocr, "config", "set", key, value], secret=secret)
    if result.returncode != 0:
        print_process_output(result, secret)
        fail(f"ocr config set {key} failed")


def configure_provider(settings: dict[str, Any], ocr: str, env_path: Path) -> None:
    provider = settings["provider"]
    prefix = f"custom_providers.{provider}"
    run_process([ocr, "config", "unset", prefix])
    ocr_config_set(ocr, "provider", provider, settings["key"])
    ocr_config_set(ocr, f"{prefix}.url", settings["url"], settings["key"])
    ocr_config_set(ocr, f"{prefix}.protocol", "openai", settings["key"])
    ocr_config_set(ocr, f"{prefix}.model", settings["model"], settings["key"])
    ocr_config_set(
        ocr,
        f"{prefix}.api_key_cmd",
        key_command(env_path),
        settings["key"],
    )
    ocr_config_set(ocr, "language", settings["language"], settings["key"])
    ocr_config_set(ocr, "effort", settings["effort"], settings["key"])
    config_path = Path.home() / ".opencodereview" / "config.json"
    try:
        config_path.chmod(0o600)
    except OSError:
        pass


def key_command(env_path: Path) -> str:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "print-key",
        "--env-file",
        str(env_path),
    ]
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return " ".join(shlex.quote(part) for part in command)


def cmd_print_key(args: argparse.Namespace) -> int:
    values = load_env_file(Path(args.env_file).expanduser())
    key = first_env(values, "OCR_LLM_API_KEY", "OCR_LLM_TOKEN", "OPENAI_API_KEY")
    if not key:
        fail("no API key found in .env")
    print(key)
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    env_path = Path(args.env_file).expanduser()
    values = load_env_file(env_path)
    settings = settings_from_env(values)
    ocr = ""
    if args.check_only:
        try:
            ocr = resolve_ocr_bin()
        except SkillError:
            ocr = ""
    else:
        ocr = ensure_ocr(
            settings, upgrade=args.upgrade, allow_install=not args.no_install
        )
        configure_provider(settings, ocr, env_path)
        print(
            f"Configured provider {settings['provider']} at "
            f"{redact_url(settings['url'])} with model {settings['model']}."
        )
        print("The API key stays in .env; OCR reads it through api_key_cmd.")
        if not args.no_test:
            print("Testing OCR connectivity...")
            result = run_process([ocr, "llm", "test"], secret=settings["key"])
            print_process_output(result, settings["key"])
            if result.returncode != 0:
                fail(
                    "OCR could not reach the configured endpoint. Check the URL, "
                    "key, model, and any gateway requirements."
                )
    print(f"ocr binary: {ocr or 'not installed'}")
    print(f"credentials: {env_path}")
    print("Next: run the `doctor` command, then `run --preview` before a full scan.")
    return 0


def version_of(command: list[str]) -> str:
    if not Path(command[0]).exists() and not shutil.which(command[0]):
        return "missing"
    result = run_process(command)
    if result.returncode != 0:
        return "unavailable"
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if text else "unknown"


def cmd_doctor(args: argparse.Namespace) -> int:
    env_path = Path(args.env_file).expanduser()
    problems: list[str] = []
    print(f"python: {sys.version.split()[0]}")
    git = version_of(["git", "--version"])
    print(f"git: {git}")
    match = re.search(r"(\d+)\.(\d+)", git)
    if not match or (int(match.group(1)), int(match.group(2))) < (2, 41):
        problems.append("Git >= 2.41 is required by ocr")
    print(f"node: {version_of(['node', '--version'])}")
    print(f"npm: {version_of(['npm', '--version'])}")
    gh_bin = shutil.which("gh")
    print(
        "gh: "
        + (
            version_of([gh_bin, "--version"])
            if gh_bin
            else "missing (issue filing unavailable)"
        )
    )
    if shutil.which("ocr") or os.environ.get("OCR_BIN"):
        print(f"ocr: {version_of([resolve_ocr_bin(), 'version'])}")
    else:
        print("ocr: missing")
        problems.append("ocr is not installed (run the install command)")

    try:
        settings = settings_from_env(load_env_file(env_path))
    except SkillError as exc:
        print(f"env: {exc}")
        problems.append(str(exc))
    else:
        print(f"env: {env_path}")
        print(f"  url: {redact_url(settings['url'])}")
        print(f"  model: {settings['model']}")
        print(f"  provider: {settings['provider']}")
        print(f"  api key: {'set' if settings['key'] else 'missing'}")

    config_path = Path.home() / ".opencodereview" / "config.json"
    print(
        f"ocr config: {config_path} ({'present' if config_path.exists() else 'missing'})"
    )
    repo = repo_root(args.repo)
    print(f"repo: {repo}")
    project_rule = repo / ".opencodereview" / "rule.json"
    print(
        "project rule: "
        f"{project_rule} ({'present' if project_rule.is_file() else 'not present'})"
    )
    print(f"output base: {output_base(repo)}")
    latest = latest_run_dir(repo)
    print(f"latest run: {latest or 'none'}")
    if args.out_dir:
        print(f"requested run: {explicit_output_dir(repo, args.out_dir)}")
    if problems:
        for problem in problems:
            print(f"problem: {problem}", file=sys.stderr)
        return 1
    return 0


def repo_root(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    result = run_process(["git", "rev-parse", "--show-toplevel"])
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return Path.cwd().resolve()


def output_base(repo: Path) -> Path:
    return (repo / DEFAULT_OUTPUT_DIR).resolve()


def explicit_output_dir(repo: Path, raw: str | None) -> Path:
    if not raw:
        fail("internal error: explicit output directory requested without a path")
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (repo / path).resolve()


def unique_run_dir(base: Path, name: str) -> Path:
    candidate = base / name
    if not candidate.exists():
        return candidate
    for index in range(1, 100):
        candidate = base / f"{name}-{index:02d}"
        if not candidate.exists():
            return candidate
    fail(f"could not allocate a unique run directory under {base}")


def new_run_dir(repo: Path, raw: str | None, prefix: str = "") -> Path:
    if raw:
        path = explicit_output_dir(repo, raw)
        path.mkdir(parents=True, exist_ok=True)
        return path
    base = output_base(repo)
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = unique_run_dir(base, f"{prefix}{stamp}")
    path.mkdir(parents=True, exist_ok=False)
    return path


def latest_run_dir(repo: Path) -> Path | None:
    base = output_base(repo)
    if not base.is_dir():
        return None
    candidates = [
        path
        for path in base.iterdir()
        if path.is_dir() and (path / "findings.json").is_file()
    ]
    if candidates:
        return max(candidates, key=lambda path: path.name)
    if (base / "findings.json").is_file():
        return base
    return None


def resolve_read_dir(repo: Path, raw: str | None) -> Path:
    if raw:
        return explicit_output_dir(repo, raw)
    latest = latest_run_dir(repo)
    if latest:
        return latest
    fail(
        f"no OCR run found under {output_base(repo)}; run the `run` command "
        "first or pass --out-dir"
    )


def combine_patterns(values: list[str], extra: list[str], defaults: bool) -> list[str]:
    patterns: list[str] = []
    if defaults:
        patterns.extend(DEFAULT_EXCLUDES)
    for item in values + extra:
        patterns.extend(split_list(item))
    seen: set[str] = set()
    unique: list[str] = []
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique.append(pattern)
    return unique


def augment_rule(rule: str) -> str:
    if SYNTAX_MARKER in rule:
        return rule
    return f"{rule.rstrip()}\n\n{SYNTAX_RULE}"


def build_rule_file(repo: Path, destination: Path) -> dict[str, Any]:
    project_path = repo / ".opencodereview" / "rule.json"
    data: dict[str, Any] = {"rules": []}
    project_present = project_path.is_file()
    if project_present:
        try:
            loaded = json.loads(project_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"{project_path} is not valid JSON: {exc}")
        if not isinstance(loaded, dict):
            fail(f"{project_path} must contain a JSON object")
        rules = loaded.get("rules", [])
        if not isinstance(rules, list):
            fail(f"{project_path}: rules must be a list")
        for entry in rules:
            if not isinstance(entry, dict):
                fail(f"{project_path}: every rule entry must be an object")
            path_pattern = entry.get("path")
            rule_text = entry.get("rule")
            if not isinstance(path_pattern, str) or not isinstance(rule_text, str):
                fail(f"{project_path}: every rule entry needs string path and rule")
            merged = {
                "path": path_pattern,
                "rule": augment_rule(rule_text),
            }
            if entry.get("merge_system_rule") is True:
                merged["merge_system_rule"] = True
            data["rules"].append(merged)
        for key in ("include", "exclude"):
            if key in loaded:
                data[key] = loaded[key]

    has_catch_all = any(
        str(entry.get("path", "")).strip().lower() in OWN_ALL_PATTERNS
        for entry in data["rules"]
    )
    if not has_catch_all:
        data["rules"].append(
            {
                "path": "**/*",
                "rule": SYNTAX_RULE,
                "merge_system_rule": True,
            }
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "path": str(destination),
        "project_rule": str(project_path) if project_present else None,
        "rules": len(data["rules"]),
        "added_catch_all": not has_catch_all,
    }


def auto_background(repo: Path) -> str:
    modules = []
    try:
        for child in sorted(repo.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                modules.append(child.name)
    except OSError:
        pass
    module_line = ", ".join(modules[:20]) if modules else "(none detected)"
    return (
        "# Project review context\n\n"
        f"Repository: {repo.name}\n"
        f"Top-level modules: {module_line}\n\n"
        "Run a whole-repository scan with Open Code Review. Prioritize semantic "
        "defects that can fail in production: logic errors, security issues, "
        "race conditions, resource leaks, data corruption, incorrect error "
        "handling, API misuse, and performance problems.\n\n"
        "Out of scope: syntax, compilation, type-check, lint, and formatting "
        "issues; the project toolchain owns those. Avoid pure style nits.\n"
    )


def read_background(args: argparse.Namespace, repo: Path, out: Path) -> str:
    if args.background_file:
        path = Path(args.background_file).expanduser()
        if not path.is_file():
            fail(f"background file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            fail(f"background file is empty: {path}")
        return text
    if args.background:
        return args.background.strip()
    generated = out / "background.md"
    if generated.is_file():
        text = generated.read_text(encoding="utf-8").strip()
        if text:
            return text
    shared = output_base(repo) / "background.md"
    if shared.is_file():
        text = shared.read_text(encoding="utf-8").strip()
        if text:
            return text
    text = auto_background(repo)
    out.mkdir(parents=True, exist_ok=True)
    generated.write_text(text, encoding="utf-8")
    return text


def scan_command(
    *,
    ocr: str,
    settings: dict[str, Any],
    repo: Path,
    out: Path,
    rule_path: Path,
    background: str,
    paths: list[str],
    excludes: list[str],
    concurrency: int,
    timeout: int,
    max_tokens_budget: int,
    batch: str,
    preview: bool,
    resume: str = "",
) -> list[str]:
    command = [
        ocr,
        "scan",
        "--repo",
        str(repo),
        "--format",
        "json",
        "--audience",
        "agent",
        "--output",
        str(out / ("preview.json" if preview else "ocr-raw.json")),
    ]
    if preview:
        command.append("--preview")
    else:
        command.extend(
            [
                "--rule",
                str(rule_path),
                "--provider",
                settings["provider"],
                "--model",
                settings["model"],
                "--background",
                background,
                "--concurrency",
                str(concurrency),
                "--timeout",
                str(timeout),
            ]
        )
        if max_tokens_budget > 0:
            command.extend(["--max-tokens-budget", str(max_tokens_budget)])
        if batch:
            command.extend(["--batch", batch])
        if resume:
            command.extend(["--resume", resume])
    if paths:
        command.extend(["--path", ",".join(paths)])
    if excludes:
        command.extend(["--exclude", ",".join(excludes)])
    return command


def cmd_preview(args: argparse.Namespace) -> int:
    ocr = resolve_ocr_bin()
    repo = repo_root(args.repo)
    out = new_run_dir(repo, args.out_dir, prefix="preview-")
    env_path = Path(args.env_file).expanduser()
    values = load_env_file(env_path) if env_path.is_file() else {}
    excludes = combine_patterns(
        split_list(values.get("OCR_EXCLUDE", "")) + args.exclude,
        [],
        parse_bool(values.get("OCR_DEFAULT_EXCLUDES", ""), default=True)
        and not args.no_default_excludes,
    )
    paths = []
    for item in args.path:
        paths.extend(split_list(item))
    command = scan_command(
        ocr=ocr,
        settings={},
        repo=repo,
        out=out,
        rule_path=out / "rule.json",
        background="",
        paths=paths,
        excludes=excludes,
        concurrency=8,
        timeout=15,
        max_tokens_budget=0,
        batch="",
        preview=True,
    )
    print("Previewing OCR scan scope...")
    result = run_process(command, cwd=repo)
    print_process_output(result, "")
    if result.returncode != 0:
        fail("ocr scan --preview failed; see the output above")
    path = out / "preview.json"
    if path.is_file():
        print(f"preview written to {path}")
        try:
            preview = load_json(path)
        except SkillError:
            preview = {}
        reviewable = preview.get("reviewable_count")
        if isinstance(reviewable, int) and reviewable > 300:
            print(
                f"hint: {reviewable} reviewable files. For a large scope, "
                f"run `run --jobs {MAX_SHARD_JOBS}` to split by module and "
                "scan up to 8 processes concurrently."
            )
    return 0


def load_json(path: Path) -> Any:
    if not path.is_file():
        fail(f"expected file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")


def line_number(value: Any) -> int:
    try:
        return int(value or 0)
    except TypeError, ValueError:
        return 0


def normalize_findings(raw: dict[str, Any]) -> dict[str, Any]:
    comments = raw.get("comments", [])
    if not isinstance(comments, list):
        fail("ocr JSON has a non-list comments field")
    findings = []
    for index, comment in enumerate(comments, 1):
        if not isinstance(comment, dict):
            fail("ocr JSON contains a non-object comment")
        severity = str(comment.get("severity", "")).strip().lower() or "unknown"
        if severity not in SEVERITIES:
            severity = "unknown"
        findings.append(
            {
                "id": f"OCR-{index:03d}",
                "path": str(comment.get("path", "")),
                "start_line": line_number(comment.get("start_line")),
                "end_line": line_number(comment.get("end_line")),
                "category": str(comment.get("category", "")).strip() or "other",
                "severity": severity,
                "shard": comment.get("_shard"),
                "content": str(comment.get("content", "")).strip(),
                "existing_code": comment.get("existing_code"),
                "suggestion_code": comment.get("suggestion_code"),
                "ocr_reasoning": comment.get("thinking"),
                "audit": {
                    "verdict": "pending",
                    "severity": None,
                    "evidence": "",
                    "notes": "",
                    "checks": [],
                },
            }
        )
    return {
        "schema": 1,
        "source": "ocr scan",
        "generated_at": now_utc(),
        "status": raw.get("status", "unknown"),
        "llm": raw.get("llm", {}),
        "summary": raw.get("summary", {}),
        "warnings": raw.get("warnings", []),
        "session_id": raw.get("session_id"),
        "findings": findings,
    }


def severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(SEVERITIES, 0)
    for finding in findings:
        counts[finding["severity"]] = counts.get(finding["severity"], 0) + 1
    return counts


def verdict_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(VERDICTS, 0)
    for finding in findings:
        verdict = finding.get("audit", {}).get("verdict", "pending")
        counts[verdict] = counts.get(verdict, 0) + 1
    return counts


def location(finding: dict[str, Any]) -> str:
    start = finding.get("start_line", 0)
    end = finding.get("end_line", 0)
    if start and end and start != end:
        return f"{finding['path']}:{start}-{end}"
    if start:
        return f"{finding['path']}:{start}"
    return f"{finding['path']} (position unresolved)"


def fence(text: str) -> str:
    longest = 3
    for run in re.finditer(r"`+", text):
        longest = max(longest, len(run.group(0)))
    marker = "`" * (longest + 1)
    return f"{marker}\n{text.rstrip()}\n{marker}"


def finding_block(finding: dict[str, Any], *, final: bool) -> list[str]:
    audit = finding.get("audit", {})
    severity = audit.get("severity") or finding["severity"]
    lines = [
        f"### {finding['id']} · {severity} · {finding['category']} · "
        f"`{location(finding)}`",
        "",
    ]
    if final:
        lines.append(f"- **Verdict:** {audit.get('verdict', 'pending')}")
        lines.append(f"- **Audited severity:** {severity}")
        if finding.get("shard"):
            lines.append(f"- **Shard:** {finding['shard']}")
        if audit.get("evidence"):
            lines.append(f"- **Evidence:** {redact_secrets(audit['evidence'])}")
        if audit.get("notes"):
            lines.append(f"- **Audit notes:** {redact_secrets(audit['notes'])}")
        checks = audit.get("checks") or []
        if checks:
            lines.append("- **Checks:** " + ", ".join(str(check) for check in checks))
    lines.extend(
        [
            f"- **OCR severity:** {finding['severity']}",
            f"- **Category:** {finding['category']}",
            "- **OCR finding:** "
            + redact_secrets(finding["content"]).replace("\n", " "),
        ]
    )
    if finding.get("existing_code"):
        lines.extend(
            [
                "",
                "**Existing code:**",
                "",
                fence(redact_secrets(str(finding["existing_code"]))),
            ]
        )
    if finding.get("suggestion_code"):
        lines.extend(
            [
                "",
                "**Suggested fix:**",
                "",
                fence(redact_secrets(str(finding["suggestion_code"]))),
            ]
        )
    lines.append("")
    return lines


def render_report(document: dict[str, Any], *, final: bool) -> str:
    findings = document["findings"]
    summary = document.get("summary", {})
    llm = document.get("llm", {})
    counts = severity_counts(findings)
    verdicts = verdict_counts(findings)
    repo = document.get("repo") or "(unknown repository)"
    status = "independently audited" if final else "OCR output, not yet audited"
    lines = [
        f"# OCR Project Review — {repo}",
        "",
        f"> Status: {status}",
        "",
        f"- Generated: {document.get('generated_at')}",
        f"- Run: {document.get('run_id', 'unknown')}",
        f"- Commit: {document.get('commit', 'unknown')}",
        f"- OCR status: {document.get('status')}",
        f"- LLM: {llm.get('provider', 'unknown')} / {llm.get('model', 'unknown')}",
        f"- Files reviewed: {summary.get('files_reviewed', 'unknown')}",
        f"- OCR findings: {len(findings)} "
        f"(critical {counts['critical']}, high {counts['high']}, "
        f"medium {counts['medium']}, low {counts['low']}, "
        f"unknown {counts['unknown']})",
    ]
    if final:
        lines.append(
            "- Audit: "
            f"confirmed {verdicts['confirmed']}, "
            f"uncertain {verdicts['uncertain']}, "
            f"false positives {verdicts['false-positive']}, "
            f"pending {verdicts['pending']}"
        )
    if document.get("session_id"):
        lines.append(f"- OCR session: {document['session_id']}")
    if document.get("status") in {"skipped", "failed", "partial"}:
        lines.append(
            "- Coverage warning: OCR status is "
            f"`{document.get('status')}`; do not treat this as full coverage."
        )
    lines.append("")

    coverage = document.get("coverage")
    if coverage:
        mode = coverage.get("mode", "single")
        lines.extend(["## Coverage", ""])
        if mode == "sharded":
            failed = coverage.get("failed") or []
            lines.append(
                f"- Mode: sharded ({coverage.get('jobs', '?')} OCR process(es))"
            )
            lines.append(
                f"- Shards: {coverage.get('completed', 0)} complete, "
                f"{len(failed)} failed"
            )
            for shard in coverage.get("shards", []):
                paths = [str(path) for path in shard.get("paths", [])]
                summary_paths = ", ".join(f"`{path}`" for path in paths[:4])
                if len(paths) > 4:
                    summary_paths += ", ..."
                lines.append(
                    f"- `{shard.get('id')}` — {shard.get('status')}; "
                    f"files {shard.get('files_reviewed', 'unknown')}; "
                    f"paths {summary_paths or 'unknown'}; "
                    f"log `{shard.get('log', '')}`"
                )
        else:
            lines.append("- Mode: single scan")
            failed = coverage.get("failed") or []
            if failed:
                lines.append("- Shards: 0 complete, 1 failed")
        if coverage.get("note"):
            lines.append(f"- {coverage['note']}")
        lines.append("")

    if final:
        area_counts: dict[str, dict[str, int]] = {}
        for finding in findings:
            area = affected_area(finding["path"])
            bucket = area_counts.setdefault(
                area,
                {
                    "confirmed": 0,
                    "uncertain": 0,
                    "false-positive": 0,
                    "pending": 0,
                },
            )
            verdict = finding["audit"]["verdict"]
            if verdict in bucket:
                bucket[verdict] += 1
        lines.extend(
            [
                "## Findings by area",
                "",
                "| Area | Confirmed | Uncertain | False positives | Pending |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for area, counts in sorted(
            area_counts.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        ):
            lines.append(
                f"| {area} | {counts['confirmed']} | {counts['uncertain']} | "
                f"{counts['false-positive']} | {counts['pending']} |"
            )
        lines.append("")

        confirmed = [
            item for item in findings if item["audit"]["verdict"] == "confirmed"
        ]
        uncertain = [
            item for item in findings if item["audit"]["verdict"] == "uncertain"
        ]
        false_positives = [
            item for item in findings if item["audit"]["verdict"] == "false-positive"
        ]
        pending = [item for item in findings if item["audit"]["verdict"] == "pending"]
        lines.extend(["## Confirmed findings", ""])
        if confirmed:
            for finding in sorted(
                confirmed,
                key=lambda item: (
                    SEVERITIES.index(item["audit"].get("severity") or item["severity"]),
                    item["path"],
                    item["start_line"],
                ),
            ):
                lines.extend(finding_block(finding, final=True))
        else:
            lines.extend(
                [
                    "No OCR finding survived independent verification.",
                    "",
                ]
            )
        if uncertain:
            lines.extend(["## Needs verification", ""])
            for finding in uncertain:
                lines.extend(finding_block(finding, final=True))
        if pending:
            lines.extend(["## Not audited", ""])
            for finding in pending:
                lines.extend(finding_block(finding, final=True))
        if false_positives:
            lines.extend(["## False positives (retained for traceability)", ""])
            for finding in false_positives:
                lines.extend(finding_block(finding, final=True))
    else:
        lines.extend(["## Findings", ""])
        if findings:
            for finding in sorted(
                findings,
                key=lambda item: (
                    SEVERITIES.index(item["severity"]),
                    item["path"],
                    item["start_line"],
                ),
            ):
                lines.extend(finding_block(finding, final=False))
        else:
            lines.extend(["No OCR comments were produced.", ""])
        lines.extend(
            [
                "## Audit status",
                "",
                "Every finding above is a hypothesis from OCR. Independently read "
                "the referenced code, check callers and tests, then record a "
                "verdict in `findings.json` with `apply-audit`.",
                "",
            ]
        )

    warnings = document.get("warnings") or []
    if warnings:
        lines.extend(["## OCR warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(
        [
            "## Method",
            "",
            "OCR generated the candidate findings from a whole-repository scan. "
            "This skill then re-audited each candidate against the source before "
            "treating it as a real issue. Compiler-detected syntax, type, lint, "
            "and formatting problems are out of scope by rule. API-key-like "
            "strings are redacted in this report, but raw working JSON under "
            "`.tmp/` may still contain them.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


MAX_SHARD_JOBS = 8


def format_elapsed(seconds: float) -> str:
    return time.strftime("%H:%M:%S", time.gmtime(max(0, int(seconds))))


def preview_reviewable(
    ocr: str,
    repo: Path,
    out: Path,
    rule_path: Path,
    excludes: list[str],
    paths: list[str],
) -> list[dict[str, Any]]:
    command = scan_command(
        ocr=ocr,
        settings={},
        repo=repo,
        out=out,
        rule_path=rule_path,
        background="",
        paths=paths,
        excludes=excludes,
        concurrency=1,
        timeout=0,
        max_tokens_budget=0,
        batch="",
        preview=True,
    )
    result = run_process(command, cwd=repo)
    if result.returncode != 0:
        print_process_output(result, "")
        fail("shard preview failed; see the output above")
    raw = load_json(out / "preview.json")
    files = raw.get("files", [])
    if not isinstance(files, list):
        fail("shard preview JSON has a non-list files field")
    reviewable = []
    for entry in files:
        if not isinstance(entry, dict) or entry.get("will_review") is not True:
            continue
        path = str(entry.get("path", "")).strip()
        if not path:
            continue
        try:
            weight = int(entry.get("insertions") or 0)
        except TypeError, ValueError:
            weight = 0
        reviewable.append({"path": path, "weight": weight})
    if not reviewable:
        fail("no reviewable files were found for sharding")
    return reviewable


def build_auto_shards(
    reviewable: list[dict[str, Any]], jobs: int
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for entry in reviewable:
        path = entry["path"]
        parent = str(Path(path).parent)
        key = parent if parent != "." else "__root__"
        group = groups.setdefault(key, {"paths": [], "weight": 0, "files": 0})
        if key == "__root__":
            group["paths"].append(path)
        elif key not in group["paths"]:
            group["paths"].append(key)
        group["weight"] += entry["weight"]
        group["files"] += 1

    ordered = sorted(
        groups.items(),
        key=lambda item: (item[1]["weight"], item[1]["files"]),
        reverse=True,
    )
    jobs = max(1, min(jobs, len(ordered)))
    buckets = [
        {"paths": [], "weight": 0, "files": 0, "groups": []} for _ in range(jobs)
    ]
    for key, group in ordered:
        bucket = min(buckets, key=lambda item: (item["weight"], item["files"]))
        bucket["paths"].extend(group["paths"])
        bucket["weight"] += group["weight"]
        bucket["files"] += group["files"]
        bucket["groups"].append(key)

    shards = []
    for index, bucket in enumerate(buckets, 1):
        if not bucket["paths"]:
            continue
        shards.append(
            {
                "id": f"shard-{index:02d}",
                "paths": sorted(set(bucket["paths"])),
                "files": bucket["files"],
                "weight": bucket["weight"],
                "groups": sorted(bucket["groups"]),
            }
        )
    return shards


def load_manual_shards(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    raw_shards = data.get("shards") if isinstance(data, dict) else data
    if not isinstance(raw_shards, list) or not raw_shards:
        fail("shard file must contain a non-empty list of path lists")
    if len(raw_shards) > MAX_SHARD_JOBS:
        fail(f"shard file may contain at most {MAX_SHARD_JOBS} shards")
    seen: set[str] = set()
    shards = []
    for index, paths in enumerate(raw_shards, 1):
        if not isinstance(paths, list) or not paths:
            fail(f"shard {index} must be a non-empty list of paths")
        clean = []
        for raw_path in paths:
            if not isinstance(raw_path, str) or not raw_path.strip():
                fail(f"shard {index} contains a non-string path")
            path_text = raw_path.strip()
            if path_text in seen:
                fail(f"path {path_text!r} appears in more than one shard")
            seen.add(path_text)
            clean.append(path_text)
        shards.append(
            {
                "id": f"shard-{index:02d}",
                "paths": clean,
                "files": 0,
                "weight": 0,
                "groups": [],
            }
        )
    all_paths = [path for shard in shards for path in shard["paths"]]
    for left_index, left in enumerate(all_paths):
        left_path = Path(left)
        for right in all_paths[left_index + 1 :]:
            right_path = Path(right)
            if (
                left_path == right_path
                or left_path.is_relative_to(right_path)
                or right_path.is_relative_to(left_path)
            ):
                fail(
                    f"shard paths overlap: {left!r} and {right!r}; "
                    "shards must be disjoint"
                )
    return shards


def prepare_shards(
    args: argparse.Namespace,
    ocr: str,
    repo: Path,
    out: Path,
    rule_path: Path,
    excludes: list[str],
    paths: list[str],
    jobs: int,
) -> list[dict[str, Any]]:
    if args.shard_file:
        return load_manual_shards(Path(args.shard_file).expanduser())
    reviewable = preview_reviewable(ocr, repo, out, rule_path, excludes, paths)
    print(f"Shard preview: {len(reviewable)} reviewable file(s).")
    return build_auto_shards(reviewable, jobs)


def run_shard(
    *,
    ocr: str,
    settings: dict[str, Any],
    repo: Path,
    out: Path,
    rule_path: Path,
    background: str,
    shard: dict[str, Any],
    excludes: list[str],
    concurrency: int,
    timeout: int,
    max_tokens_budget: int,
    batch: str,
) -> dict[str, Any]:
    shard_dir = out / "shards" / shard["id"]
    shard_dir.mkdir(parents=True, exist_ok=True)
    log_path = shard_dir / "run.log"
    command = scan_command(
        ocr=ocr,
        settings=settings,
        repo=repo,
        out=shard_dir,
        rule_path=rule_path,
        background=background,
        paths=shard["paths"],
        excludes=excludes,
        concurrency=concurrency,
        timeout=timeout,
        max_tokens_budget=max_tokens_budget,
        batch=batch,
        preview=False,
    )
    started = time.monotonic()
    try:
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                command,
                cwd=str(repo),
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        returncode = result.returncode
    except OSError as exc:
        log_path.write_text(f"failed to start ocr: {exc}\n", encoding="utf-8")
        returncode = -1
    elapsed = time.monotonic() - started
    raw_path = shard_dir / "ocr-raw.json"
    status = "complete"
    if returncode != 0:
        status = "failed"
    elif not raw_path.is_file():
        status = "failed"
    else:
        try:
            raw = load_json(raw_path)
        except SkillError:
            status = "failed"
        else:
            if not isinstance(raw, dict):
                status = "failed"
            else:
                raw_status = str(raw.get("status", ""))
                if raw_status in {"failed", "skipped"}:
                    status = "failed"
                elif raw_status in {"partial", "completed_with_errors"}:
                    status = "partial"
    return {
        "id": shard["id"],
        "paths": shard["paths"],
        "status": status,
        "returncode": returncode,
        "elapsed_sec": round(elapsed, 1),
        "log": str(log_path),
        "raw": str(raw_path),
        "file_count": shard.get("files", 0),
    }


def merge_shard_results(
    results: list[dict[str, Any]], wall_elapsed: float
) -> tuple[dict[str, Any], dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    warnings: list[str] = []
    failed: list[str] = []
    llm_variants: list[dict[str, Any]] = []
    token_totals = {
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }
    files_reviewed = 0
    shard_meta = []
    ordered = sorted(results, key=lambda item: item["id"])
    for shard in ordered:
        raw = None
        raw_path = Path(shard["raw"])
        if raw_path.is_file():
            try:
                raw = load_json(raw_path)
            except SkillError as exc:
                warnings.append(f"[{shard['id']}] unreadable result: {exc}")
        if raw is not None and not isinstance(raw, dict):
            warnings.append(f"[{shard['id']}] result is not a JSON object")
            raw = None
        if raw is None:
            if shard["id"] not in failed:
                failed.append(shard["id"])
            warnings.append(
                f"[{shard['id']}] failed with exit {shard['returncode']}; "
                f"see {shard['log']}"
            )
        else:
            raw_comments = raw.get("comments")
            if isinstance(raw_comments, list):
                for comment in raw_comments:
                    if isinstance(comment, dict):
                        copied = dict(comment)
                        copied["_shard"] = shard["id"]
                        comments.append(copied)
            summary = raw.get("summary")
            if not isinstance(summary, dict):
                summary = {}
            try:
                files_reviewed += int(summary.get("files_reviewed") or 0)
            except TypeError, ValueError:
                pass
            for key in token_totals:
                try:
                    token_totals[key] += int(summary.get(key) or 0)
                except TypeError, ValueError:
                    pass
            raw_warnings = raw.get("warnings")
            if isinstance(raw_warnings, list):
                for warning in raw_warnings:
                    warnings.append(f"[{shard['id']}] {warning}")
            llm = raw.get("llm")
            if isinstance(llm, dict) and llm and llm not in llm_variants:
                llm_variants.append(llm)
        if (shard["status"] != "complete" or shard["returncode"] != 0) and (
            shard["id"] not in failed
        ):
            failed.append(shard["id"])
        raw_summary = (raw or {}).get("summary")
        if not isinstance(raw_summary, dict):
            raw_summary = {}
        try:
            shard_files_reviewed = int(raw_summary.get("files_reviewed") or 0)
        except TypeError, ValueError:
            shard_files_reviewed = 0
        shard_meta.append(
            {
                "id": shard["id"],
                "status": shard["status"],
                "returncode": shard["returncode"],
                "files_reviewed": shard_files_reviewed,
                "paths": shard["paths"],
                "elapsed_sec": shard["elapsed_sec"],
                "log": shard["log"],
                "raw": shard["raw"],
            }
        )

    if failed and not comments:
        status = "failed"
    elif failed:
        status = "partial"
    elif warnings:
        status = "completed_with_warnings"
    else:
        status = "success"
    if failed:
        warnings.append(
            "One or more shards failed; results are partial. Inspect the "
            "per-shard logs before treating this report as complete coverage."
        )
    merged = {
        "status": status,
        "llm": llm_variants[0] if llm_variants else {},
        "summary": {
            "files_reviewed": files_reviewed,
            "comments": len(comments),
            **token_totals,
            "elapsed": format_elapsed(wall_elapsed),
            "shards": len(ordered),
        },
        "comments": comments,
        "warnings": warnings,
    }
    if len(llm_variants) > 1:
        merged["llm_variants"] = llm_variants
    coverage = {
        "mode": "sharded",
        "jobs": len(ordered),
        "completed": len(ordered) - len(failed),
        "failed": failed,
        "shards": shard_meta,
        "note": (
            "Merged from sharded OCR scans. Per-shard logs and raw JSON are "
            "under `shards/`."
        ),
    }
    return merged, coverage


def git_commit(repo: Path) -> str:
    result = run_process(["git", "-C", str(repo), "rev-parse", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def write_run_outputs(
    out: Path,
    document: dict[str, Any],
    repo: Path,
    rule_info: dict[str, Any],
) -> None:
    document["repo"] = repo.name
    document["repo_path"] = str(repo)
    document["rule_file"] = rule_info["path"]
    document["run_id"] = out.name
    document["commit"] = git_commit(repo)
    previous = out / "findings.json"
    if previous.is_file():
        shutil.copy2(previous, out / "findings.previous.json")
    write_json(previous, document)
    write_json(
        out / "audit-template.json",
        [
            {
                "id": finding["id"],
                "verdict": "",
                "severity": "",
                "category": "",
                "evidence": "",
                "notes": "",
                "checks": [],
            }
            for finding in document["findings"]
        ],
    )
    (out / "report-ocr.md").write_text(
        render_report(document, final=False), encoding="utf-8"
    )
    coverage = document.get("coverage") or {}
    write_json(
        out / "run.json",
        {
            "run_id": document["run_id"],
            "generated_at": document.get("generated_at") or now_utc(),
            "repo": str(repo),
            "repo_name": repo.name,
            "commit": document["commit"],
            "status": document.get("status"),
            "coverage_mode": coverage.get("mode"),
            "jobs": coverage.get("jobs"),
            "failed_shards": coverage.get("failed") or [],
            "findings": len(document["findings"]),
        },
    )


def cmd_run(args: argparse.Namespace) -> int:
    env_path = Path(args.env_file).expanduser()
    settings = settings_from_env(load_env_file(env_path))
    ocr = resolve_ocr_bin()
    repo = repo_root(args.repo)
    configure_provider(settings, ocr, env_path)
    out = new_run_dir(repo, args.out_dir)
    if args.out_dir and (out / "findings.json").is_file():
        print(
            f"warning: writing into existing run directory {out}; pass a new "
            "--out-dir or omit it for a timestamped run",
            file=sys.stderr,
        )
    print(f"Run directory: {out}")

    jobs = args.jobs
    if jobs < 1 or jobs > MAX_SHARD_JOBS:
        fail(f"--jobs must be between 1 and {MAX_SHARD_JOBS}")
    if args.resume and (jobs > 1 or args.shard_file):
        fail("--resume is only supported for a single (non-sharded) scan")

    rule_info = build_rule_file(repo, out / "rule.json")
    background = read_background(args, repo, out)
    if len(background) > 24000:
        fail(
            "background context is longer than 24000 characters and `ocr scan` "
            "has no --background-file flag; keep it concise"
        )
    (out / "background.md").write_text(background.rstrip() + "\n", encoding="utf-8")
    excludes = combine_patterns(
        settings["excludes"] + args.exclude,
        [],
        settings["default_excludes"] and not args.no_default_excludes,
    )
    paths: list[str] = []
    for item in args.path:
        paths.extend(split_list(item))
    if args.concurrency is not None and args.concurrency < 1:
        fail("--concurrency must be at least 1")
    if args.timeout is not None and args.timeout < 0:
        fail("--timeout must be non-negative")
    if args.max_tokens_budget is not None and args.max_tokens_budget < 0:
        fail("--max-tokens-budget must be non-negative")
    concurrency = (
        settings["concurrency"] if args.concurrency is None else args.concurrency
    )
    timeout = settings["timeout"] if args.timeout is None else args.timeout
    budget = (
        args.max_tokens_budget
        if args.max_tokens_budget is not None
        else settings["max_tokens_budget"]
    )
    batch = args.batch or settings["batch"]
    if batch and batch not in {"none", "by-language", "by-directory"}:
        fail("--batch must be none, by-language, or by-directory")
    if rule_info["project_rule"]:
        print(f"Using project rules from {rule_info['project_rule']}")
    if rule_info["added_catch_all"]:
        print("Added a catch-all rule that suppresses compiler-detected issues.")

    if jobs == 1 and not args.shard_file:
        command = scan_command(
            ocr=ocr,
            settings=settings,
            repo=repo,
            out=out,
            rule_path=out / "rule.json",
            background=background,
            paths=paths,
            excludes=excludes,
            concurrency=concurrency,
            timeout=timeout,
            max_tokens_budget=budget,
            batch=batch,
            preview=False,
            resume=args.resume or "",
        )
        print(
            "Running whole-repository OCR scan "
            f"({len(paths) or 'all'} paths, {len(excludes)} excludes)..."
        )
        raw_path = out / "ocr-raw.json"
        if not args.resume:
            raw_path.unlink(missing_ok=True)
        result = run_process(command, cwd=repo, capture=False)

        if result.returncode != 0 and not raw_path.is_file():
            fail("ocr scan failed and produced no result file; see the output above")
        if result.returncode != 0:
            print(
                "warning: ocr scan exited non-zero; auditing the partial result.",
                file=sys.stderr,
            )
        raw = load_json(raw_path)
        if not isinstance(raw, dict):
            fail(f"{raw_path} does not contain a JSON object")
        document = normalize_findings(raw)
        document["ocr_exit_code"] = result.returncode
        raw_status = str(raw.get("status", ""))
        single_failed = []
        if result.returncode != 0 or raw_status in {
            "partial",
            "failed",
            "completed_with_errors",
            "skipped",
        }:
            single_failed = ["single"]
        document["coverage"] = {
            "mode": "single",
            "jobs": 1,
            "completed": 0 if single_failed else 1,
            "failed": single_failed,
            "shards": [],
            "note": "Single OCR scan over the selected scope.",
        }
        write_run_outputs(out, document, repo, rule_info)
        return report_run_summary(out, document)

    shards = prepare_shards(
        args, ocr, repo, out, out / "rule.json", excludes, paths, jobs
    )
    workers = min(MAX_SHARD_JOBS, len(shards), jobs if jobs > 1 else len(shards))
    workers = max(1, workers)
    shard_budget = max(1, budget // len(shards)) if budget > 0 else 0
    if jobs > 1 and len(shards) == 1:
        print(
            "note: only one shard was produced; use --shard-file to split a "
            "large directory manually.",
            file=sys.stderr,
        )
    print(
        f"Sharding {len(shards)} module group(s) across {workers} OCR "
        f"process(es), {concurrency} internal task(s) each."
    )
    for shard in shards:
        shown = ", ".join(shard["paths"][:4])
        if len(shard["paths"]) > 4:
            shown += ", ..."
        print(f"  {shard['id']}: {shard.get('files', '?')} file(s); paths {shown}")
    if shard_budget:
        print(f"Per-shard token budget: {shard_budget}")
    if workers * concurrency > 32:
        print(
            f"note: total internal concurrency is {workers * concurrency}; "
            "lower --concurrency if the endpoint rate-limits.",
            file=sys.stderr,
        )

    started = time.monotonic()
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                run_shard,
                ocr=ocr,
                settings=settings,
                repo=repo,
                out=out,
                rule_path=out / "rule.json",
                background=background,
                shard=shard,
                excludes=excludes,
                concurrency=concurrency,
                timeout=timeout,
                max_tokens_budget=shard_budget,
                batch=batch,
            ): shard
            for shard in shards
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"[{result['id']}] {result['status']} in "
                f"{format_elapsed(result['elapsed_sec'])}; log {result['log']}"
            )
    wall_elapsed = time.monotonic() - started
    merged, coverage = merge_shard_results(results, wall_elapsed)
    write_json(out / "ocr-raw-merged.json", merged)
    write_json(out / "ocr-raw.json", merged)
    document = normalize_findings(merged)
    document["coverage"] = coverage
    document["ocr_exit_code"] = 0 if not coverage["failed"] else 1
    write_run_outputs(out, document, repo, rule_info)
    code = report_run_summary(out, document)
    if coverage["failed"]:
        print(
            "warning: one or more shards failed; the report is partial. "
            "Inspect `shards/*/run.log` and rerun with `--shard-file` or a "
            "larger `--jobs`.",
            file=sys.stderr,
        )
        return 1
    return code


def report_run_summary(out: Path, document: dict[str, Any]) -> int:
    counts = severity_counts(document["findings"])
    print(
        f"OCR produced {len(document['findings'])} findings "
        f"(critical {counts['critical']}, high {counts['high']}, "
        f"medium {counts['medium']}, low {counts['low']})."
    )
    print(f"Working data: {out}")
    print(f"- {out / 'ocr-raw.json'}")
    print(f"- {out / 'findings.json'}")
    print(f"- {out / 'audit-template.json'}")
    print(f"- {out / 'report-ocr.md'}")
    coverage = document.get("coverage") or {}
    if coverage.get("mode") == "sharded":
        print(f"- {out / 'ocr-raw-merged.json'}")
        print(f"- {out / 'shards'}")
    print("Next: audit every finding, record verdicts, then run `finalize`.")
    return 0


def read_findings(repo: Path, raw_out: str | None) -> tuple[Path, dict[str, Any]]:
    out = resolve_read_dir(repo, raw_out)
    path = out / "findings.json"
    document = load_json(path)
    if not isinstance(document, dict) or not isinstance(document.get("findings"), list):
        fail(f"{path} is not a findings document")
    return path, document


def cmd_list(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    _, document = read_findings(repo, args.out_dir)
    findings = document["findings"]
    if args.pending:
        findings = [item for item in findings if item["audit"]["verdict"] == "pending"]
    if args.verdict:
        findings = [
            item for item in findings if item["audit"]["verdict"] == args.verdict
        ]
    for finding in findings:
        snippet = finding["content"].replace("\n", " ")[:100]
        print(
            f"{finding['id']}\t{finding['severity']}\t"
            f"{finding['audit']['verdict']}\t{location(finding)}\t{snippet}"
        )
    print(f"{len(findings)} finding(s)")
    return 0


def audit_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        return payload["findings"]
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        entries = []
        for key, value in payload.items():
            if isinstance(value, dict):
                entry = dict(value)
                entry.setdefault("id", key)
                entries.append(entry)
        if entries:
            return entries
    fail("audit file must be a list, a findings object, or an id-keyed object")


def cmd_apply_audit(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    path, document = read_findings(repo, args.out_dir)
    if args.audit_file == "-":
        try:
            payload = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            fail(f"stdin is not valid JSON: {exc}")
    else:
        payload = load_json(Path(args.audit_file).expanduser())
    entries = audit_entries(payload)
    by_id = {finding["id"]: finding for finding in document["findings"]}
    for entry in entries:
        finding_id = str(entry.get("id", "")).strip()
        if finding_id not in by_id:
            fail(f"unknown finding id {finding_id!r}")
        verdict = str(entry.get("verdict", "")).strip().lower()
        if verdict not in VERDICTS or verdict == "pending":
            fail(
                f"{finding_id}: verdict must be confirmed, false-positive, or uncertain"
            )
        finding = by_id[finding_id]
        audit = finding["audit"]
        audit["verdict"] = verdict
        raw_category = entry.get("category")
        if raw_category not in (None, ""):
            category = str(raw_category).strip().lower()
            if category not in CATEGORIES:
                fail(f"{finding_id}: invalid category {category!r}")
            finding["category"] = category
        if entry.get("severity"):
            severity = str(entry["severity"]).strip().lower()
            if severity not in SEVERITIES or severity == "unknown":
                fail(f"{finding_id}: invalid audited severity {severity!r}")
            audit["severity"] = severity
        for key in ("evidence", "notes"):
            if entry.get(key) is not None:
                audit[key] = str(entry[key]).strip()
        if entry.get("checks") is not None:
            checks = entry["checks"]
            if not isinstance(checks, list):
                fail(f"{finding_id}: checks must be a list")
            audit["checks"] = [str(check) for check in checks]
    write_json(path, document)
    counts = verdict_counts(document["findings"])
    print(
        f"Updated {len(entries)} finding(s): confirmed {counts['confirmed']}, "
        f"uncertain {counts['uncertain']}, "
        f"false positives {counts['false-positive']}, "
        f"pending {counts['pending']}."
    )
    if args.require_all and counts["pending"]:
        pending = [
            finding["id"]
            for finding in document["findings"]
            if finding["audit"]["verdict"] == "pending"
        ]
        fail("still pending: " + ", ".join(pending))
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    findings_path, document = read_findings(repo, args.out_dir)
    out = findings_path.parent
    failed_shards = (document.get("coverage") or {}).get("failed") or []
    if failed_shards and not args.allow_partial:
        fail(
            "coverage is partial; failed shard(s): "
            + ", ".join(str(item) for item in failed_shards)
            + ". Rerun the failed modules or pass --allow-partial."
        )
    pending = [
        finding["id"]
        for finding in document["findings"]
        if finding["audit"]["verdict"] == "pending"
    ]
    if pending and not args.allow_pending:
        fail(
            "audit is incomplete; still pending: "
            + ", ".join(pending)
            + ". Use --allow-pending to render them as not audited."
        )
    report_path = out / "report-final.md"
    report_path.write_text(render_report(document, final=True), encoding="utf-8")
    counts = verdict_counts(document["findings"])
    print(f"Wrote {report_path}")
    print(
        f"confirmed {counts['confirmed']}, uncertain {counts['uncertain']}, "
        f"false positives {counts['false-positive']}, pending {counts['pending']}"
    )
    return 0


def looks_security(finding: dict[str, Any]) -> bool:
    audit = finding.get("audit", {})
    text = " ".join(
        [
            str(finding.get("category", "")),
            str(finding.get("content", "")),
            str(audit.get("evidence", "")),
            str(audit.get("notes", "")),
        ]
    ).lower()
    return "security" in str(finding.get("category", "")).lower() or any(
        pattern.search(text) for pattern in SECURITY_PATTERNS
    )


def affected_area(path: str) -> str:
    normalized = path.lower()
    rules = (
        ("astrbot/core/pipeline", "Pipeline / EventBus"),
        ("astrbot/core/agent", "Providers / agent runners"),
        ("astrbot/core/provider", "Providers / agent runners"),
        ("astrbot/core/platform", "Platform adapters"),
        ("astrbot/dashboard", "Dashboard / OpenAPI"),
        ("openspec/", "Dashboard / OpenAPI"),
        ("astrbot/core/knowledge_base", "Knowledge base"),
        ("astrbot/core/star", "Plugins / Stars"),
        ("astrbot/builtin_stars", "Plugins / Stars"),
        ("astrbot/core/backup", "Backup / restore"),
        ("docs/", "Docs"),
        (".github/", "CI / toolchain"),
        ("scripts/", "CI / toolchain"),
        ("makefile", "CI / toolchain"),
    )
    for prefix, area in rules:
        if normalized.startswith(prefix):
            return area
    return "Other"


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def redact_secrets(text: str) -> str:
    redacted = str(text)
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def issue_title(finding: dict[str, Any]) -> str:
    text = " ".join(finding.get("content", "").split())
    text = text.rstrip(".")
    if not text:
        text = f"Defect at {location(finding)}"
    if len(text) > 80:
        text = text[:77].rstrip() + "..."
    return f"[bug] {text}"


def strip_intent_note(body: str) -> str:
    markers = ("\n## Human note", "\n## Agent note")
    changed = True
    while changed:
        changed = False
        for marker in markers:
            index = body.rfind(marker)
            if index != -1:
                body = body[:index]
                changed = True
    return body.rstrip()


def issue_body(
    finding: dict[str, Any],
    commit: str,
    superseded: list[dict[str, Any]] | None = None,
) -> str:
    audit = finding.get("audit", {})
    severity = audit.get("severity") or finding["severity"]
    checks = audit.get("checks") or []
    lines = [
        "### Preflight",
        "",
        "- [x] I searched open and closed Issues and PRs.",
        "- [x] I tested the current `master` branch or the exact commit.",
        "- [x] This report contains no secrets, tokens, or private data.",
        "- [x] This is not a security vulnerability (those use a private advisory).",
        "- [x] I filled exactly one of Human note or Agent note, matching who wrote this Issue.",
        "",
        "### Affected area",
        "",
        affected_area(finding["path"]),
        "",
        "### What happened",
        "",
        f"`{location(finding)}` — {finding['content']}",
        "",
        f"- Audited severity: `{severity}`",
        f"- Category: `{finding['category']}`",
        f"- OCR ID: `{finding['id']}`",
    ]
    if audit.get("evidence"):
        lines.append(f"- Evidence: {audit['evidence']}")
    if checks:
        lines.append("- Checks: " + ", ".join(str(check) for check in checks))
    if audit.get("notes"):
        lines.append(f"- Audit notes: {audit['notes']}")
    if finding.get("suggestion_code"):
        lines.extend(
            [
                "",
                "**Suggested fix:**",
                "",
                fence(str(finding["suggestion_code"])),
            ]
        )
    lines.extend(
        [
            "",
            "### Commit or version",
            "",
            f"`{commit}`",
            "",
            "### Environment",
            "",
            f"Source checkout, Python {sys.version.split()[0]}, commit `{commit}`.",
            "",
            "### Author",
            "",
            "Agent",
        ]
    )
    if superseded:
        lines.extend(["", "## Superseded issue", ""])
        for issue in superseded:
            lines.extend(
                [
                    f"This report consolidates #{issue['number']} "
                    f"({issue['url']}). The original issue is closed in favor of "
                    "this merged report.",
                    "",
                    f"**Original title:** {issue['title']}",
                    "",
                    "<details>",
                    "<summary>Original report (intent note omitted)</summary>",
                    "",
                    strip_intent_note(str(issue.get("body", "")) or "(empty)"),
                    "",
                    "</details>",
                    "",
                ]
            )
    lines.extend(
        [
            "## Agent note",
            "",
            "This issue came from an Open Code Review (OCR) whole-repository scan. "
            "The coding agent independently re-read the referenced code and "
            "recorded it as confirmed before drafting this report.",
            "",
            f"- Paths: `{finding['path']}`",
            f"- Checks: {', '.join(str(check) for check in checks) or 'source review'}",
            "- Residual risk: see the evidence above; this is not a claim of "
            "complete coverage of the module.",
            "- AI tools: OCR candidate generation; coding-agent verification.",
        ]
    )
    if superseded:
        refs = ", ".join(f"#{issue['number']}" for issue in superseded)
        lines.append(
            f"- Consolidation: this issue replaces {refs} with the original "
            "context plus the new audited evidence."
        )
    return "\n".join(lines).rstrip() + "\n"


def issue_candidates(gh: str, title: str) -> list[dict[str, Any]]:
    query = re.sub(r"^\[[^\]]+\]\s*", "", title).strip() or title
    result = run_process(
        [
            gh,
            "issue",
            "list",
            "--repo",
            ISSUE_REPO,
            "--state",
            "all",
            "--search",
            query,
            "--json",
            "number,title,url,state",
            "--limit",
            "20",
        ]
    )
    if result.returncode != 0:
        print_process_output(result, "")
        fail("could not check existing issues; refusing to create a duplicate")
    try:
        issues = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        fail(f"could not parse gh issue list output: {exc}")
    return issues if isinstance(issues, list) else []


def exact_issue(issues: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
    wanted = title.strip().lower()
    for issue in issues:
        if str(issue.get("title", "")).strip().lower() == wanted:
            return issue
    return None


def fetch_issue(gh: str, number: int) -> dict[str, Any]:
    result = run_process(
        [
            gh,
            "issue",
            "view",
            str(number),
            "--repo",
            ISSUE_REPO,
            "--json",
            "number,title,body,url,state",
        ]
    )
    if result.returncode != 0:
        print_process_output(result, "")
        fail(f"could not read issue #{number} from {ISSUE_REPO}")
    try:
        issue = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"could not parse gh issue view output: {exc}")
    if not isinstance(issue, dict):
        fail(f"gh issue view returned an unexpected payload for #{number}")
    return issue


def close_superseded(gh: str, issue: dict[str, Any], new_url: str) -> None:
    number = issue["number"]
    comment = (
        f"Consolidated into {new_url} with additional OCR-audited evidence. "
        "Closing this issue in favor of the merged report."
    )
    if str(issue.get("state", "")).upper() == "OPEN":
        result = run_process(
            [
                gh,
                "issue",
                "close",
                str(number),
                "--repo",
                ISSUE_REPO,
                "--comment",
                comment,
            ]
        )
    else:
        result = run_process(
            [
                gh,
                "issue",
                "comment",
                str(number),
                "--repo",
                ISSUE_REPO,
                "--body",
                comment,
            ]
        )
    if result.returncode != 0:
        print_process_output(result, "")
        fail(
            f"created the consolidated issue at {new_url}, but could not close "
            f"or comment on #{number}; finish it manually"
        )
    action = "closed" if str(issue.get("state", "")).upper() == "OPEN" else "linked"
    print(f"Linked and {action} #{number} in favor of {new_url}")


def cmd_issues(args: argparse.Namespace) -> int:
    repo = repo_root(args.repo)
    findings_path, document = read_findings(repo, args.out_dir)
    out = findings_path.parent
    failed_shards = (document.get("coverage") or {}).get("failed") or []
    if failed_shards and not args.allow_partial:
        fail(
            "coverage is partial; failed shard(s): "
            + ", ".join(str(item) for item in failed_shards)
            + ". Rerun the failed modules or pass --allow-partial."
        )
    pending = [
        finding["id"]
        for finding in document["findings"]
        if finding["audit"]["verdict"] == "pending"
    ]
    if pending:
        fail("complete the audit first; still pending: " + ", ".join(pending))
    confirmed = [
        finding
        for finding in document["findings"]
        if finding["audit"]["verdict"] == "confirmed"
    ]
    if not confirmed:
        print("No confirmed findings; no issue drafts written.")
        return 0

    supersede_map: dict[str, list[int]] = {}
    for raw in args.supersede:
        left, sep, right = raw.partition(":")
        if not sep or not left.strip().isdigit() or not right.strip():
            fail("--supersede must use ISSUE_NUMBER:DRAFT_ID, for example 123:OCR-001")
        draft_id = right.strip()
        number = int(left.strip())
        mapped = supersede_map.setdefault(draft_id, [])
        if number not in mapped:
            mapped.append(number)

    commit_result = run_process(["git", "-C", str(repo), "rev-parse", "HEAD"])
    commit = (
        commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"
    )
    issues_dir = out / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    for old in issues_dir.glob("ISSUE-*.md"):
        old.unlink()

    security: list[dict[str, Any]] = []
    drafts: list[tuple[dict[str, Any], str, Path]] = []
    seen_titles: set[str] = set()
    for finding in confirmed:
        if looks_security(finding):
            security.append(finding)
            continue
        title = issue_title(finding)
        if title in seen_titles:
            continue
        seen_titles.add(title)
        body = issue_body(finding, commit)
        if contains_secret(body):
            fail(
                f"{finding['id']} draft contains a possible secret; redact the "
                "finding before drafting or filing an issue"
            )
        draft = issues_dir / f"ISSUE-{finding['id']}.md"
        draft.write_text(
            f"<!-- title: {title} -->\n<!-- labels: bug -->\n\n" + body,
            encoding="utf-8",
        )
        drafts.append((finding, title, draft))

    unknown = set(supersede_map) - {finding["id"] for finding, _, _ in drafts}
    if unknown:
        fail(
            "--supersede references findings that have no public draft: "
            + ", ".join(sorted(unknown))
        )

    superseded_by_draft: dict[str, list[dict[str, Any]]] = {}
    gh = shutil.which("gh")
    if supersede_map and not gh:
        fail("gh is required to read the Issues being superseded")
    for finding, title, draft in drafts:
        numbers = supersede_map.get(finding["id"])
        if not numbers:
            continue
        assert gh is not None
        originals = [fetch_issue(gh, number) for number in numbers]
        body = issue_body(finding, commit, originals)
        if contains_secret(body):
            fail(
                f"{finding['id']} consolidated draft contains a possible secret; "
                "redact the original Issue or finding first"
            )
        draft.write_text(
            f"<!-- title: {title} -->\n<!-- labels: bug -->\n\n" + body,
            encoding="utf-8",
        )
        superseded_by_draft[finding["id"]] = originals

    index = ["# Issue drafts", ""]
    for finding, title, draft in drafts:
        index.append(f"- `{finding['id']}` — {title} → `{draft.name}`")
    if security:
        index.extend(["", "## Security findings (not for public issues)", ""])
        for finding in security:
            index.append(
                f"- `{finding['id']}` — `{location(finding)}`: "
                f"{redact_secrets(finding['content'])}"
            )
        index.extend(
            [
                "",
                "Use https://github.com/Xero-Team/AstrBot/security/advisories/new "
                "per `SECURITY.md`; do not open a public issue.",
            ]
        )
    if not drafts and not security:
        index.append("No drafts were produced.")
    (issues_dir / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    if security:
        security_path = out / "security-findings.md"
        lines = [
            "# Security findings",
            "",
            "Do not open a public Issue for these findings. Follow `SECURITY.md` "
            "and the private advisory channel:",
            "",
            "https://github.com/Xero-Team/AstrBot/security/advisories/new",
            "",
            "This file can contain sensitive evidence. It is gitignored; do not "
            "commit it or paste it into a public channel.",
            "",
        ]
        for finding in security:
            lines.extend(
                [
                    f"## {finding['id']} — `{location(finding)}`",
                    "",
                    redact_secrets(finding["content"]),
                    "",
                    f"- Severity: {finding['audit'].get('severity') or finding['severity']}",
                    f"- Evidence: {redact_secrets(finding['audit'].get('evidence', ''))}",
                    "",
                ]
            )
        security_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Security findings written to {security_path} (never file publicly).")

    print(f"Wrote {len(drafts)} issue draft(s) under {issues_dir}")
    for _, title, draft in drafts:
        print(f"- {draft} — {title}")
    if security:
        print(
            f"Skipped {len(security)} security finding(s) from public issue creation."
        )

    if not args.create:
        print("Review the drafts. Re-run with --create only when the user asked.")
        return 0
    if not drafts:
        return 0

    if not gh:
        fail("gh is required to create issues")
    auth = run_process([gh, "auth", "status", "--hostname", "github.com"])
    if auth.returncode != 0:
        print_process_output(auth, "")
        fail("gh is not authenticated for github.com")
    created: list[str] = []
    for finding, title, draft in drafts:
        candidates = issue_candidates(gh, title)
        existing = exact_issue(candidates, title)
        if existing:
            print(f"Skipping {finding['id']}: existing issue {existing['url']}")
            continue

        superseded = superseded_by_draft.get(finding["id"], [])
        related = [
            issue
            for issue in candidates
            if str(issue.get("title", "")).strip().lower() != title.strip().lower()
        ]
        if related and not superseded and not args.allow_related:
            print(
                f"Skipping {finding['id']}: related issue(s) found. Review them, "
                "then use --supersede ISSUE:DRAFT to consolidate or "
                "--allow-related if they are unrelated."
            )
            for issue in related:
                print(
                    f"  #{issue.get('number')} [{issue.get('state')}] "
                    f"{issue.get('title')} {issue.get('url')}"
                )
            continue

        result = run_process(
            [
                gh,
                "issue",
                "create",
                "--repo",
                ISSUE_REPO,
                "--title",
                title,
                "--body-file",
                str(draft),
                "--label",
                "bug",
            ]
        )
        if result.returncode != 0:
            print_process_output(result, "")
            print("Created before the failure: " + ", ".join(created or ["none"]))
            fail(f"failed to create issue for {finding['id']}")
        url = next(
            (
                line.strip()
                for line in (result.stdout or "").splitlines()
                if line.strip().startswith("https://github.com/")
            ),
            "",
        )
        expected = f"https://github.com/{ISSUE_REPO}/issues/"
        if not url.startswith(expected):
            fail(f"gh returned an unexpected issue URL: {url or '<empty>'}")
        created.append(url)
        print(f"Opened {finding['id']}: {url}")
        for issue in superseded:
            close_superseded(gh, issue, url)
    print(f"Opened {len(created)} issue(s) on {ISSUE_REPO}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install and configure Open Code Review (ocr), run a whole-project "
            "scan, and audit its findings."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    print_key = subparsers.add_parser("print-key", help=argparse.SUPPRESS)
    print_key.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    print_key.set_defaults(func=cmd_print_key)

    install = subparsers.add_parser(
        "install", help="Install ocr and sync .env credentials into its config"
    )
    install.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    install.add_argument("--upgrade", action="store_true", help="Reinstall ocr@latest")
    install.add_argument(
        "--no-install", action="store_true", help="Do not run npm install"
    )
    install.add_argument("--no-test", action="store_true", help="Skip ocr llm test")
    install.add_argument(
        "--check-only", action="store_true", help="Validate settings only"
    )
    install.set_defaults(func=cmd_install)

    doctor = subparsers.add_parser("doctor", help="Check local prerequisites")
    doctor.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    doctor.add_argument("--repo")
    doctor.add_argument("--out-dir")
    doctor.set_defaults(func=cmd_doctor)

    preview = subparsers.add_parser("preview", help="Show which files ocr would scan")
    preview.add_argument("--repo")
    preview.add_argument("--out-dir")
    preview.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    preview.add_argument("--path", action="append", default=[])
    preview.add_argument("--exclude", action="append", default=[])
    preview.add_argument("--no-default-excludes", action="store_true")
    preview.set_defaults(func=cmd_preview)

    run = subparsers.add_parser("run", help="Run a whole-repository ocr scan")
    run.add_argument("--repo")
    run.add_argument("--out-dir")
    run.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    run.add_argument("--path", action="append", default=[])
    run.add_argument("--exclude", action="append", default=[])
    run.add_argument("--no-default-excludes", action="store_true")
    run.add_argument("--background")
    run.add_argument("--background-file")
    run.add_argument("--concurrency", type=int)
    run.add_argument("--timeout", type=int)
    run.add_argument("--max-tokens-budget", type=int)
    run.add_argument("--batch")
    run.add_argument(
        "--jobs",
        type=int,
        default=1,
        help=f"Split reviewable files into at most {MAX_SHARD_JOBS} balanced shards and run that many OCR processes",
    )
    run.add_argument(
        "--shard-file",
        help="JSON file with explicit shard path groups (list of lists or {shards: [...]})",
    )
    run.add_argument("--resume")
    run.set_defaults(func=cmd_run)

    listing = subparsers.add_parser("list", help="List normalized findings")
    listing.add_argument("--repo")
    listing.add_argument("--out-dir")
    listing.add_argument("--pending", action="store_true")
    listing.add_argument("--verdict", choices=VERDICTS)
    listing.set_defaults(func=cmd_list)

    apply_audit = subparsers.add_parser(
        "apply-audit", help="Record independent verification verdicts"
    )
    apply_audit.add_argument("audit_file", help="JSON file, or - for stdin")
    apply_audit.add_argument("--repo")
    apply_audit.add_argument("--out-dir")
    apply_audit.add_argument("--require-all", action="store_true")
    apply_audit.set_defaults(func=cmd_apply_audit)

    finalize = subparsers.add_parser("finalize", help="Render the audited final report")
    finalize.add_argument("--repo")
    finalize.add_argument("--out-dir")
    finalize.add_argument("--allow-pending", action="store_true")
    finalize.add_argument(
        "--allow-partial",
        action="store_true",
        help="Render even when one or more shards failed",
    )
    finalize.set_defaults(func=cmd_finalize)

    issues = subparsers.add_parser(
        "issues", help="Draft or open GitHub issues from confirmed findings"
    )
    issues.add_argument("--repo")
    issues.add_argument("--out-dir")
    issues.add_argument(
        "--create",
        action="store_true",
        help=f"Open issues on {ISSUE_REPO} after duplicate checks",
    )
    issues.add_argument(
        "--supersede",
        action="append",
        default=[],
        metavar="ISSUE:DRAFT",
        help="Close an existing issue in favor of a consolidated draft, e.g. 123:OCR-001",
    )
    issues.add_argument(
        "--allow-related",
        action="store_true",
        help="Create even when related issues exist, after manually confirming no overlap",
    )
    issues.add_argument(
        "--allow-partial",
        action="store_true",
        help="Draft or create Issues from a partially covered run",
    )
    issues.set_defaults(func=cmd_issues)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SkillError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
