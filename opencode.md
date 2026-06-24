# pluck — project guidelines

pluck installs any git repo from any forge. Auto-detects project type, auto-installs, done.

## Quick start

```bash
pip install -e .
pluck install https://github.com/user/repo
```

## Commands

install, update, info, list, uninstall, verify, clean, stats, doctor, config, search, export, import, completion, pin, unpin, self-update, cache, version, help

## Tests

```bash
python -m pytest tests/ -v
```

## Key files

- `src/pluck.py` — main application
- `tests/test_pluck.py` — test suite
- `pyproject.toml` — build config, entry points, lint settings
