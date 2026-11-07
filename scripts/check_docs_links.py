#!/usr/bin/env python3
"""Lightweight documentation link checker.

Default scope: current guidance, model, reference, validation, stage indexes,
and Stage 12 reports. Historical report bodies in stages 3–11 are excluded
unless --all is passed. Code fences and inline code are ignored.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

ROOT_FILES = [
    "AGENTS.md",
    "README.md",
    "RULES.md",
    "STYLE.md",
    "KNOWN_ISSUES.md",
    "CHANGELOG.md",
]

CURRENT_GLOBS = [
    "docs/README.md",
    "docs/DECISIONS.md",
    "docs/LEGACY_IO_POLICY.md",
    "docs/model/*.md",
    "docs/references/*.md",
    "docs/validation/*.md",
    "docs/archive/README.md",
    "docs/wiki/INDEX.md",
    "docs/wiki/README.md",
    "docs/wiki/topics/*.md",
    "docs/wiki/stages/*/README.md",
    "docs/wiki/stages/stage12/*.md",
    "data/validation/observations/**/README.md",
    "data/validation/observations/**/provenance.md",
]

HISTORICAL_GLOBS = [
    "docs/wiki/stages/**/*.md",
    "data/validation/observations/**/*.md",
]

LOCAL_ONLY_PREFIXES = (
    "data/input/",
    "data/runs/",
    "data/output/",
    "docs/wiki/ERA5_INTEGRATION_TODO.md",
    "docs/references/work_references.bib",
    "data/validation/observations/stage10.18d/raw/",
)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_RE = re.compile(r'(?:href|src)="([^"]+)"')
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def strip_code(text: str) -> str:
    return INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))


def candidate_paths(target: str, source: Path) -> list[Path]:
    t = unquote(target).split("#", 1)[0]
    if not t:
        return []
    if t.startswith("/"):
        return [(ROOT / t.lstrip("/")).resolve()]
    return [(source.parent / t).resolve(), (ROOT / t).resolve()]


def is_local_only(target: str) -> bool:
    t = unquote(target).split("#", 1)[0].lstrip("./")
    return any(t.startswith(p) for p in LOCAL_ONLY_PREFIXES)


def case_mismatch(target: str, source: Path) -> str | None:
    t = unquote(target).split("#", 1)[0]
    if not t:
        return None
    for base in (source.parent, ROOT):
        p = (base / t)
        parts = p.parts
        current = Path(parts[0])
        for part in parts[1:]:
            if not current.is_dir():
                break
            names = {x.name.lower(): x.name for x in current.iterdir()}
            actual = names.get(part.lower())
            if actual is None:
                break
            if actual != part:
                return str(current / actual)
            current = current / part
    return None


def slugify(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s]+", "-", s).strip("-")
    return s


def anchors(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    result = set()
    for line in text.splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            result.add(slugify(heading))
    return result


def collect_files(all_docs: bool) -> list[Path]:
    files: set[Path] = set()
    for name in ROOT_FILES:
        p = ROOT / name
        if p.is_file():
            files.add(p)
    globs = CURRENT_GLOBS + (HISTORICAL_GLOBS if all_docs else [])
    for pattern in globs:
        files.update(p for p in ROOT.glob(pattern) if p.is_file())
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="include historical report bodies")
    parser.add_argument("--anchors", action="store_true", help="check Markdown heading anchors")
    args = parser.parse_args()

    files = collect_files(args.all)
    checked = 0
    broken: list[str] = []
    excluded: list[str] = []
    warnings: list[str] = []

    for source in files:
        text = strip_code(source.read_text(encoding="utf-8", errors="replace"))
        targets = LINK_RE.findall(text) + HTML_RE.findall(text)
        for raw in targets:
            target = raw.strip().split()[0].strip("<>\"'")
            if not target or target.startswith(("#", "http://", "https://", "mailto:", "tel:", "data:")):
                continue
            checked += 1
            resolved = next((p for p in candidate_paths(target, source) if p.exists()), None)
            if resolved is None:
                if is_local_only(target):
                    excluded.append(f"{source.relative_to(ROOT)} -> {target}")
                else:
                    mismatch = case_mismatch(target, source)
                    if mismatch:
                        broken.append(f"{source.relative_to(ROOT)} -> {target} (case mismatch: {mismatch})")
                    else:
                        broken.append(f"{source.relative_to(ROOT)} -> {target}")
                continue
            if args.anchors and "#" in target and resolved.suffix == ".md":
                anchor = target.split("#", 1)[1]
                if anchor and anchor not in anchors(resolved):
                    warnings.append(f"{source.relative_to(ROOT)} -> {target} (missing heading anchor)")

    print(f"checked files: {len(files)}")
    print(f"checked local links: {checked}")
    print(f"broken links: {len(broken)}")
    print(f"local-only/excluded references: {len(excluded)}")
    print(f"anchor warnings: {len(warnings)}")

    for label, rows in (("BROKEN", broken), ("EXCLUDED", excluded), ("WARN", warnings)):
        if rows:
            print(f"\n{label}:")
            for row in rows:
                print(f"  {row}")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
