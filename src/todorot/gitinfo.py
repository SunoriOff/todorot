"""Line ages and authors from ``git blame``."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

HEADER = re.compile(r"^[0-9a-f]{40} \d+ (\d+)")


def _git(root: Path, *args: str) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None


def is_git_repo(root: Path) -> bool:
    result = _git(root, "rev-parse", "--is-inside-work-tree")
    return bool(result and result.returncode == 0 and result.stdout.strip() == "true")


def parse_blame(output: str) -> Dict[int, Tuple[int, str]]:
    """Parse ``git blame --line-porcelain`` output into ``{line: (epoch, author)}``."""
    result: Dict[int, Tuple[int, str]] = {}
    current: Optional[int] = None
    author: Optional[str] = None
    stamp: Optional[int] = None
    for line in output.splitlines():
        if line.startswith("\t"):
            if current is not None and stamp is not None:
                result[current] = (stamp, author or "unknown")
            current, author, stamp = None, None, None
            continue
        header = HEADER.match(line)
        if header:
            current = int(header.group(1))
        elif line.startswith("author "):
            author = line[len("author "):]
        elif line.startswith("author-time "):
            try:
                stamp = int(line[len("author-time "):])
            except ValueError:
                stamp = None
    return result


def blame(root: Path, relpath: str) -> Optional[Dict[int, Tuple[int, str]]]:
    """Return per-line ``(epoch, author)`` for a tracked file, or ``None``."""
    result = _git(root, "blame", "--line-porcelain", "-w", "--", relpath)
    if not result or result.returncode != 0:
        return None
    return parse_blame(result.stdout)
