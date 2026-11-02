"""Command-line interface for todorot."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import List, Optional

from . import __version__
from .gitinfo import blame, is_git_repo
from .scanner import DEFAULT_TAGS, Marker, find_markers, iter_files

DAY = 86400


def format_age(days: int) -> str:
    if days < 1:
        return "today"
    if days < 90:
        return f"{days}d"
    if days < 730:
        return f"{days // 30}mo"
    return f"{days / 365:.1f}y"


class Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def red(self, t: str) -> str: return self._wrap("31", t)
    def yellow(self, t: str) -> str: return self._wrap("33", t)
    def green(self, t: str) -> str: return self._wrap("32", t)
    def dim(self, t: str) -> str: return self._wrap("2", t)
    def bold(self, t: str) -> str: return self._wrap("1", t)


def collect(root: Path, tags: List[str], ignore: List[str], use_git: bool) -> List[Marker]:
    git_ok = use_git and is_git_repo(root)
    now = time.time()
    markers: List[Marker] = []
    for path in iter_files(root, ignore):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits = find_markers(text, tags)
        if not hits:
            continue
        rel = path.relative_to(root).as_posix()
        blame_map = blame(root, rel) if git_ok else None
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = now
        for lineno, tag, assignee, message in hits:
            if blame_map and lineno in blame_map:
                stamp, author = blame_map[lineno]
            else:
                stamp, author = mtime, None
            markers.append(Marker(
                file=rel, line=lineno, tag=tag, text=message,
                assignee=assignee, author=author,
                age_days=max(0, int((now - stamp) // DAY)),
            ))
    return markers


def render_text(markers: List[Marker], root: Path, max_age: Optional[int], style: Style) -> str:
    out: List[str] = []
    files = len({m.file for m in markers})
    out.append(style.bold(f"todorot {__version__}") + style.dim(f"  {root}"))
    if not markers:
        out.append("")
        out.append(style.green("✔ No TODO/FIXME markers found. Suspiciously clean."))
        return "\n".join(out)
    out.append(style.dim(f"{len(markers)} marker(s) in {files} file(s)"))
    out.append("")

    loc_width = max(len(f"{m.file}:{m.line}") for m in markers)
    tag_width = max(len(m.tag) for m in markers)
    who_width = max(len(m.assignee or m.author or "-") for m in markers)
    out.append(style.dim(
        f"{'AGE':>6}  {'TAG':<{tag_width}}  {'LOCATION':<{loc_width}}  {'WHO':<{who_width}}  TEXT"
    ))
    for m in markers:
        age = f"{format_age(m.age_days):>6}"
        over = max_age is not None and m.age_days > max_age
        age = style.red(age) if over else age
        loc = f"{m.file}:{m.line}".ljust(loc_width)
        who = (m.assignee or m.author or "-").ljust(who_width)
        out.append(f"{age}  {m.tag.ljust(tag_width)}  {loc}  {style.dim(who)}  {m.text}")

    out.append("")
    counts = Counter(m.tag for m in markers)
    out.append("By tag: " + ", ".join(f"{t} {n}" for t, n in counts.most_common()))
    oldest = max(markers, key=lambda m: m.age_days)
    out.append(f"Oldest: {format_age(oldest.age_days)} ({oldest.file}:{oldest.line})")
    if max_age is not None:
        offenders = [m for m in markers if m.age_days > max_age]
        if offenders:
            out.append(style.red(f"{len(offenders)} marker(s) older than {max_age} days."))
        else:
            out.append(style.green(f"All markers are younger than {max_age} days."))
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="todorot",
        description="Find TODO/FIXME comments and see how long they have been rotting "
                    "(age comes from git blame).",
    )
    p.add_argument("--version", action="version", version=f"todorot {__version__}")
    p.add_argument("path", nargs="?", default=".", help="project directory (default: .)")
    p.add_argument("--max-age", type=int, metavar="DAYS",
                   help="exit 1 if any marker is older than DAYS days (for CI)")
    p.add_argument("--tags", default=",".join(DEFAULT_TAGS),
                   help="comma-separated markers to look for (default: %(default)s)")
    p.add_argument("--sort", choices=["age", "file"], default="age")
    p.add_argument("--top", type=int, metavar="N", help="only show the N oldest markers")
    p.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                   help="glob of paths to skip, e.g. 'tests/*' (repeatable)")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--no-git", action="store_true", help="use file mtime instead of git blame")
    p.add_argument("--no-color", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"todorot: not a directory: {args.path}", file=sys.stderr)
        return 2

    tags = [t.strip().upper() for t in args.tags.split(",") if t.strip()]
    markers = collect(root, tags, args.ignore, use_git=not args.no_git)
    if args.sort == "age":
        markers.sort(key=lambda m: (-m.age_days, m.file, m.line))
    else:
        markers.sort(key=lambda m: (m.file, m.line))
    if args.top:
        markers = sorted(markers, key=lambda m: -m.age_days)[: args.top]

    if args.format == "json":
        offenders = [m for m in markers if args.max_age is not None and m.age_days > args.max_age]
        print(json.dumps({
            "root": str(root),
            "count": len(markers),
            "over_max_age": len(offenders),
            "markers": [m.to_dict() for m in markers],
        }, indent=2))
    else:
        color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ
        print(render_text(markers, root, args.max_age, Style(color)))

    if args.max_age is not None and any(m.age_days > args.max_age for m in markers):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
