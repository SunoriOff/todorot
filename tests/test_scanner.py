from todorot.scanner import find_markers, iter_files


def test_detects_markers_in_comments():
    code = (
        "x = 1  # TODO: refactor this\n"
        "// FIXME handle errors\n"
        "/* HACK: temporary */\n"
        "<!-- XXX remove me -->\n"
    )
    found = find_markers(code)
    assert [(ln, tag) for ln, tag, _, _ in found] == [
        (1, "TODO"), (2, "FIXME"), (3, "HACK"), (4, "XXX"),
    ]
    assert found[0][3] == "refactor this"
    assert found[2][3] == "temporary"
    assert found[3][3] == "remove me"


def test_ignores_markers_outside_comments():
    code = 'print("TODO list")\nTODO_LIST = []\nnote = "FIXME"\n'
    assert find_markers(code) == []


def test_assignee_is_extracted():
    found = find_markers("# TODO(alice): write tests\n")
    assert found[0][2] == "alice"
    assert found[0][3] == "write tests"


def test_custom_tags():
    assert find_markers("# NOTE: hi\n# TODO: x\n", tags=["NOTE"])[0][1] == "NOTE"
    assert len(find_markers("# NOTE: hi\n# TODO: x\n", tags=["NOTE"])) == 1


def test_word_boundaries():
    assert find_markers("# TODOS are bad\n") == []


def test_iter_files_skips_vendor_dirs_and_ignored_globs(tmp_path):
    (tmp_path / "a.py").write_text("# TODO a\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.js").write_text("// TODO b\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "c.py").write_text("# TODO c\n")
    (tmp_path / "notes.txt").write_text("TODO d\n")
    names = [p.name for p in iter_files(tmp_path, ignore=["tests/*"])]
    assert names == ["a.py"]
