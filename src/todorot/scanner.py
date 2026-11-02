"""Find TODO-style markers inside code comments."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence

DEFAULT_TAGS = ("TODO", "FIXME", "HACK", "XXX", "BUG")

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rb", ".php",
    ".rs", ".java", ".kt", ".kts", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs",
    ".swift", ".sh", ".bash", ".zsh", ".yml", ".yaml", ".toml", ".sql",
    ".lua", ".vue", ".svelte", ".css", ".scss", ".html", ".dart", ".scala",
    ".ex", ".exs", ".r", ".pl", ".tf",
}

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist",
    "build", "target", ".tox", ".mypy_cache", ".pytest_cache", ".next",
    ".nuxt", "vendor", ".idea", ".vscode", "coverage", ".gradle",
}

MAX_FILE_SIZE = 1_000_000

# A marker only counts when a comment opener appears before it on the line.
COMMENT_OPENER = re.compile(r"(#|//|/\*|\*|--|<!--|;|%)")


def build_pattern(tags: Sequence[str]) -> "re.Pattern[str]":
    alternation = "|".join(re.escape(t) for t in tags)
    return re.compile(rf"\b({alternation})\b(?:\(([^)]*)\))?\s*:?\s*(.*)")


@dataclass
class Marker:
    file: str
    line: int
    tag: str
    text: str
    assignee: Optional[str] = None
    author: Optional[str] = None
    age_days: int = 0

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "tag": self.tag,
            "text": self.text,
            "assignee": self.assignee,
            "author": self.author,
            "age_days": self.age_days,
        }


def find_markers(text: str, tags: Sequence[str] = DEFAULT_TAGS) -> List[tuple]:
    """Return ``[(line_number, tag, assignee, text), ...]`` for *text*."""
    pattern = build_pattern(tags)
    found = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = pattern.search(line)
        if not match:
            continue
        if not COMMENT_OPENER.search(line[: match.start()]):
            continue
        message = match.group(3).strip()
        for closer in ("*/", "-->"):
            if message.endswith(closer):
                message = message[: -len(closer)].rstrip()
        found.append((lineno, match.group(1), match.group(2), message))
    return found


def iter_files(root: Path, ignore: Iterable[str] = ()) -> Iterator[Path]:
    ignore = list(ignore)
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if not path.is_file() or path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        rel_posix = rel.as_posix()
        if any(fnmatch.fnmatch(rel_posix, pat) for pat in ignore):
            continue
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        yield path
