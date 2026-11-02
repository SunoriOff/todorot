# todorot

[![CI](https://github.com/SunoriOff/todorot/actions/workflows/ci.yml/badge.svg)](https://github.com/SunoriOff/todorot/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/todorot.svg)](https://pypi.org/project/todorot/)
[![Python](https://img.shields.io/pypi/pyversions/todorot.svg)](https://pypi.org/project/todorot/)
[![License: WTFPL](https://img.shields.io/badge/license-WTFPL-brightgreen.svg)](LICENSE)
![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen)

**A `TODO` is a promise. `todorot` shows you which ones you broke.**

Every codebase has them: `# TODO: handle unicode`, `// FIXME: passwords are compared in plain text`. Grep finds them, but it can't tell you that one has been sitting there for **3.7 years**. `todorot` reads `git blame` to date every marker, sorts the oldest first, and can fail your CI when TODOs go stale.

```text
$ todorot --max-age 365

todorot 0.1.0  /home/me/my-app
4 marker(s) in 3 file(s)

   AGE  TAG    LOCATION        WHO    TEXT
  3.7y  FIXME  src/auth.py:2   alice  passwords are compared in plain text
  20mo  TODO   src/api.js:2    bob    add pagination
  20mo  HACK   src/api.js:5    bob    retry until the flaky backend answers
   43d  TODO   src/utils.py:2  chloe  handle unicode

By tag: TODO 2, FIXME 1, HACK 1
Oldest: 3.7y (src/auth.py:2)
3 marker(s) older than 365 days.
```

Zero dependencies, pure Python, works on any language that has comments.

## Install

```bash
pip install todorot
# or without installing:
pipx run todorot
```

Requires Python 3.9+ and `git` (optional: without git it falls back to file modification time).

## Usage

```bash
todorot                         # scan the current directory, oldest first
todorot path/to/project
todorot --max-age 180           # exit 1 if any marker is older than 180 days
todorot --top 10                # only the 10 oldest
todorot --tags TODO,FIXME       # choose which markers to look for
todorot --ignore 'tests/*' --ignore 'docs/*'
todorot --sort file             # group by file instead of age
todorot --format json           # machine-readable
todorot --no-git                # use file mtime instead of git blame
```

Exit codes: `0` ok, `1` markers older than `--max-age`, `2` bad usage.

### What counts as a marker

A word from the tag list (`TODO`, `FIXME`, `HACK`, `XXX`, `BUG` by default) that appears **inside a comment** (`#`, `//`, `/* */`, `--`, `<!-- -->`, `;`, `%`). Strings like `"TODO list"` or a variable named `TODO_LIST` are ignored.

You can attach an owner, and it is shown in the **WHO** column: `# TODO(alice): write tests`. Otherwise `todorot` shows the git author of the line.

Handled languages include Python, JS/TS, Go, Ruby, PHP, Rust, Java/Kotlin, C/C++/C#, Swift, shell, SQL, YAML, TOML, HTML/CSS, Vue/Svelte and more. `node_modules`, `.venv`, `dist`, `build` and other vendor folders are skipped.

## Use it in CI

Fail the build when a TODO gets older than 6 months:

```yaml
name: todo-rot
on: [push, pull_request]
jobs:
  todorot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # required: git blame needs the full history
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install todorot
      - run: todorot --max-age 180
```

> `fetch-depth: 0` matters. With the default shallow clone every line looks as old as the last commit, and ages will be wrong.

## How it works

1. Walk the tree and find markers inside comments.
2. Run `git blame --line-porcelain` once per file that has markers, to get the date and author of each line.
3. Compute the age, sort, print.

## Development

```bash
git clone https://github.com/SunoriOff/todorot
cd todorot
pip install -e ".[dev]"
pytest
```

## Roadmap

- [ ] Config file (`.todorot.toml`) for tags, ignores and default max age
- [ ] `--since` filter to only show markers added in a date range
- [ ] SARIF output for GitHub code scanning
- [ ] Link each marker to its commit

## License

[WTFPL](LICENSE): do what the fuck you want to.
