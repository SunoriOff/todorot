# Contributing to todorot

Thanks for helping! The project is small on purpose: zero runtime dependencies, fast, easy to read.

## Setup

```bash
git clone https://github.com/SunoriOff/todorot
cd todorot
pip install -e ".[dev]"
pytest
```

## Where to change things

To support more comment styles, edit `COMMENT_OPENER` and `CODE_EXTENSIONS` in `src/todorot/scanner.py` and add a test in `tests/test_scanner.py`.

## Pull requests

- Keep PRs focused, one change each.
- Add or update tests; CI must pass on Python 3.9 to 3.13.
- Don't add runtime dependencies.

## Reporting bugs

Open an issue with a minimal input and the output you expected. Those reports are very valuable.
