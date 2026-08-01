#!/usr/bin/env python3
"""Audit a skill directory for concrete structural and safety hazards.

The scanner is intentionally heuristic. It reports finding codes and locations,
never the matching source text, so suspected secret values are not echoed.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_TEXT_BYTES = 1_000_000
MAX_SKILL_LINES = 500
TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
SENSITIVE_NAMES = {
    ".env",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}
SELF_RELATIVE_PATH = Path("scripts/audit_skill.py")


@dataclass(frozen=True)
class Rule:
    code: str
    pattern: re.Pattern[str]


@dataclass(frozen=True, order=True)
class Finding:
    relative_path: str
    line: int
    code: str


RULES = (
    Rule(
        "SECRET_PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
    ),
    Rule(
        "SECRET_GITHUB_TOKEN",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    Rule(
        "SECRET_OPENAI_KEY",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    Rule(
        "SECRET_AWS_ACCESS_KEY",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    Rule(
        "SECRET_TELEGRAM_TOKEN",
        re.compile(r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b"),
    ),
    Rule(
        "SECRET_GENERIC_ASSIGNMENT",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|private[_-]?key|secret)\b"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:-]{12,}"
        ),
    ),
    Rule(
        "PROMPT_AUTHORITY_OVERRIDE",
        re.compile(
            r"(?i)\b(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior|system|developer)\s+instructions?\b"
        ),
    ),
    Rule(
        "PROMPT_FORCED_EXECUTION",
        re.compile(r"(?i)\b(?:execute|run)\s+(?:it\s+)?immediately\b"),
    ),
    Rule(
        "PROMPT_BYPASS_APPROVAL",
        re.compile(
            r"(?i)\b(?:without|do\s+not\s+(?:ask|wait)\s+for)\s+"
            r"(?:the\s+)?(?:user(?:'s)?\s+)?(?:approval|permission|confirmation)\b"
        ),
    ),
    Rule(
        "INSTALL_PIPE_TO_SHELL",
        re.compile(r"(?i)\b(?:curl|wget)\b[^\n]{0,240}\|\s*(?:ba|z|fi)?sh\b"),
    ),
    Rule(
        "DESTRUCTIVE_SHELL",
        re.compile(r"(?i)(?:\brm\s+-[^\n]*r[^\n]*f\b|\bgit\s+reset\s+--hard\b)"),
    ),
    Rule(
        "ELEVATED_COMMAND",
        re.compile(r"(?i)(?<![A-Za-z0-9_-])sudo(?![A-Za-z0-9_-])"),
    ),
    Rule(
        "GLOBAL_AGENT_WRITE",
        re.compile(
            r"(?i)\b(?:cp|mv|install|write|append)\b[^\n]{0,180}"
            r"(?:\.codex|\.claude)/(?:skills|rules|commands)\b"
        ),
    ),
)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _walk(root: Path) -> tuple[list[Path], list[Finding]]:
    files: list[Path] = []
    findings: list[Finding] = []

    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in dirnames:
            path = current_path / dirname
            if dirname in SKIP_DIRS:
                continue
            if path.is_symlink():
                findings.append(Finding(_relative(path, root), 0, "SYMLINK"))
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            path = current_path / filename
            relative = _relative(path, root)
            if path.is_symlink():
                findings.append(Finding(relative, 0, "SYMLINK"))
                continue
            files.append(path)

    return files, findings


def _validate_frontmatter(root: Path, findings: list[Finding]) -> None:
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        findings.append(Finding("SKILL.md", 0, "MISSING_SKILL_MD"))
        return

    text = skill_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > MAX_SKILL_LINES:
        findings.append(Finding("SKILL.md", 0, "SKILL_TOO_LONG"))

    if not lines or lines[0] != "---":
        findings.append(Finding("SKILL.md", 1, "INVALID_FRONTMATTER"))
        return

    try:
        closing = lines.index("---", 1)
    except ValueError:
        findings.append(Finding("SKILL.md", 1, "INVALID_FRONTMATTER"))
        return

    fields: dict[str, str] = {}
    for number, line in enumerate(lines[1:closing], start=2):
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            findings.append(Finding("SKILL.md", number, "INVALID_FRONTMATTER"))
            continue
        fields[match.group(1)] = match.group(2).strip()

    if set(fields) != {"name", "description"}:
        findings.append(Finding("SKILL.md", 1, "FRONTMATTER_FIELDS"))
    if fields.get("name") != root.name:
        findings.append(Finding("SKILL.md", 2, "NAME_MISMATCH"))
    description = fields.get("description", "")
    if len(description) < 40 or "TODO" in description:
        findings.append(Finding("SKILL.md", 3, "DESCRIPTION_INCOMPLETE"))

    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).split("#", 1)[0]
        if not target or "://" in target or target.startswith("#"):
            continue
        candidate = (root / target).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            findings.append(
                Finding("SKILL.md", _line_number(text, match.start()), "OUTSIDE_REFERENCE")
            )
            continue
        if not candidate.exists():
            findings.append(
                Finding("SKILL.md", _line_number(text, match.start()), "BROKEN_REFERENCE")
            )

    lineage = root / "references" / "lineage.md"
    if not lineage.is_file():
        findings.append(Finding("references/lineage.md", 0, "MISSING_LINEAGE"))


def audit(root: Path) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    files, walk_findings = _walk(root)
    findings.extend(walk_findings)
    _validate_frontmatter(root, findings)

    scanned = 0
    for path in files:
        relative_path = Path(_relative(path, root))
        lowered_name = path.name.lower()
        if (
            lowered_name in SENSITIVE_NAMES
            or lowered_name.startswith(".env.")
            or path.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}
        ):
            findings.append(Finding(relative_path.as_posix(), 0, "SENSITIVE_FILE"))

        if relative_path == SELF_RELATIVE_PATH:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != "SKILL.md":
            continue
        try:
            size = path.stat().st_size
        except OSError:
            findings.append(Finding(relative_path.as_posix(), 0, "UNREADABLE_FILE"))
            continue
        if size > MAX_TEXT_BYTES:
            findings.append(Finding(relative_path.as_posix(), 0, "TEXT_FILE_TOO_LARGE"))
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        scanned += 1
        for rule in RULES:
            for match in rule.pattern.finditer(text):
                findings.append(
                    Finding(
                        relative_path.as_posix(),
                        _line_number(text, match.start()),
                        rule.code,
                    )
                )

    return sorted(set(findings)), scanned


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a skill directory without modifying it."
    )
    parser.add_argument("skill_dir", type=Path, help="Directory containing SKILL.md")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    root = args.skill_dir.expanduser()
    if not root.is_dir():
        print("ERROR: target is not a directory", file=sys.stderr)
        return 2
    root = root.resolve()

    findings, scanned = audit(root)
    if findings:
        print(f"FAIL: {len(findings)} finding(s) across {scanned} scanned text file(s)")
        for finding in findings:
            location = finding.relative_path
            if finding.line:
                location = f"{location}:{finding.line}"
            print(f"{location} {finding.code}")
        return 1

    print(f"PASS: 0 findings across {scanned} scanned text file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
