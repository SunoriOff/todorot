import json
import os
import shutil
import subprocess

import pytest

from todorot.cli import format_age, main
from todorot.gitinfo import parse_blame

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def git(cwd, *args, date=None):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Alice", "GIT_AUTHOR_EMAIL": "a@example.com",
        "GIT_COMMITTER_NAME": "Alice", "GIT_COMMITTER_EMAIL": "a@example.com",
    }
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env, capture_output=True)


def test_format_age():
    assert format_age(0) == "today"
    assert format_age(12) == "12d"
    assert format_age(200) == "6mo"
    assert format_age(1095) == "3.0y"


def test_parse_blame():
    sha = "a" * 40
    output = (
        f"{sha} 1 1 1\nauthor Alice\nauthor-mail <a@x>\nauthor-time 1000\nsummary s\n\tline one\n"
        f"{sha} 2 2\nauthor Bob\nauthor-time 2000\nsummary s\n\tline two\n"
    )
    assert parse_blame(output) == {1: (1000, "Alice"), 2: (2000, "Bob")}


def test_no_git_uses_mtime_and_finds_markers(tmp_path, capsys):
    (tmp_path / "app.py").write_text("# TODO: later\nx = 1\n")
    assert main([str(tmp_path), "--no-git", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "app.py:1" in out
    assert "later" in out


def test_clean_project(tmp_path, capsys):
    (tmp_path / "app.py").write_text("x = 1\n")
    assert main([str(tmp_path), "--no-git", "--no-color"]) == 0
    assert "No TODO/FIXME" in capsys.readouterr().out


def test_bad_path():
    assert main(["/definitely/not/here"]) == 2


@needs_git
def test_old_markers_fail_max_age(tmp_path, capsys):
    git(tmp_path, "init", "-q")
    (tmp_path / "old.py").write_text("# FIXME(bob): ancient bug\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "old", date="2020-01-01T12:00:00")
    assert main([str(tmp_path), "--max-age", "90", "--no-color"]) == 1
    out = capsys.readouterr().out
    assert "ancient bug" in out
    assert "older than 90 days" in out
    assert main([str(tmp_path), "--max-age", "100000"]) == 0


@needs_git
def test_json_output_has_author_and_age(tmp_path, capsys):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.py").write_text("# TODO: x\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "c", date="2021-06-01T12:00:00")
    main([str(tmp_path), "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    marker = data["markers"][0]
    assert marker["author"] == "Alice"
    assert marker["age_days"] > 1000


def test_sort_and_top(tmp_path, capsys):
    (tmp_path / "a.py").write_text("# TODO: one\n# TODO: two\n# TODO: three\n")
    main([str(tmp_path), "--no-git", "--top", "2", "--format", "json"])
    assert json.loads(capsys.readouterr().out)["count"] == 2
