# pluck

pluck installs any git repo from any forge. Auto-detects project type, auto-installs, done.

## Quick start

```bash
pip install -e .
pluck install https://github.com/user/repo
```

## Commands

install, update, info, list, uninstall, verify, clean, stats, doctor, config, search, export, import, completion, pin, unpin, self-update, cache, version, help

## Verification

```bash
python -m pytest tests/ -v           # run all tests
ruff check src/ tests/               # lint
python -m build                      # verify package builds
```

## Off-limits for agents

Do not modify without explicit human approval:

- `.github/workflows/` — CI/CD pipeline definitions
- `pyproject.toml` — build configuration and entry points
- `src/gh_install.py` — backward-compat shim (managed by rename process)
- `docs/IMPLEMENTATION.md` — architecture documentation
- `CHANGELOG.md` — version history (managed by semantic-release)

## Key files

- `src/pluck.py` — main application
- `tests/test_pluck.py` — test suite (111+ tests)
- `pyproject.toml` — build config, entry points, lint settings
