#!/usr/bin/env python3
"""Copy the shared goldfish prompts into every adapter file.

Each adapter file marks where a shared prompt goes:

    <!-- eg:shared shared/prompts/reviewer.md -->
    ...generated, do not edit by hand...
    <!-- eg:end -->

The text between the markers is replaced with the named file (path relative to
the repo root). Edit the source file, never the generated copy.

Usage:
    python3 scripts/sync_shared.py          # rewrite adapter files
    python3 scripts/sync_shared.py --check  # exit 1 if any file is out of date (for CI)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTER_GLOBS = ["claude/commands/*.md", "codex/skills/*/SKILL.md", "gemini/commands/*.md"]
BLOCK = re.compile(r"(<!-- eg:shared ([\w./-]+) -->\n)(.*?)(<!-- eg:end -->)", re.S)


def render(text: str, path: Path) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(2)
        source = (ROOT / name).resolve()
        if ROOT not in source.parents or not source.is_file():
            sys.exit(f"{path.relative_to(ROOT)}: shared file not found: {name}")
        body = source.read_text()
        if not body.endswith("\n"):
            body += "\n"
        return match.group(1) + body + match.group(4)

    return BLOCK.sub(replace, text)


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for pattern in ADAPTER_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            old = path.read_text()
            new = render(old, path)
            if new != old:
                stale.append(path.relative_to(ROOT))
                if not check:
                    path.write_text(new)
    if check and stale:
        print("Shared prompts are out of date in:")
        for p in stale:
            print(f"  {p}")
        print("Run: python3 scripts/sync_shared.py")
        return 1
    print("updated:" if stale else "all adapter files match shared/prompts", *stale, sep="\n  " if stale else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
