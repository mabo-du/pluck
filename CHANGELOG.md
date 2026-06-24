# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2026-06-24

### Changed
- **Renamed project from `gh-install` to `pluck` everywhere**: source file, test file, module names, pyproject.toml entry points (with backward-compat shim) — `src/gh_install.py` → `src/pluck.py`, `tests/test_gh_install.py` → `tests/test_pluck.py`

### Added
- `_safe_urlopen()` — URL scheme validation helper that blocks `file://` / custom scheme abuse (resolves 8 CodeFactor security issues)
- `_check_install_method()` — extracted method-detection checks for reduced complexity
- `_clone_repo()` — extracted clone logic with retry/timeout handling
- `_safe_dir_size()` — robust directory size calculation with per-file error handling
- `_bitbucket_repo_url()` — safe Bitbucket URL extraction helper
- API endpoint constants (`_API_GITHUB_SEARCH`, `_API_GITLAB_SEARCH`, `_API_CODEBERG_SEARCH`, `_API_BITBUCKET_SEARCH`, `_API_GITLAB_RELEASES`)
- `opencode.md` — project context file for AI tooling with verification commands and off-limits paths

### Fixed
- **Security**: 8 CodeFactor URL scheme audit issues — all `urllib.request.urlopen()` calls now use `_safe_urlopen()` which restricts to `https://` / `http://` only
- **Code quality**: 4 complex method refactorings — `detect_install_method()`, `download_and_install()`, `_parse_args()`, `main()` all broken into smaller functions with dispatch tables
- **Code quality**: 1 complex method in `pforge-mcp/server.mjs` — extracted 4 handler functions from the `CallToolRequestSchema` handler
- **Code quality**: Extracted `createExpressApp()` REST route handlers
- **Code quality**: Reduced `_clone_repo` parameter count from 8 to 7 (removed unused `install_dir`)
- **Security**: Changed test chmod from `0o755` to `0o700` (less permissive)
- **Security**: Replaced hardcoded `/tmp/test` paths with `tempfile`-based paths in tests
- **22 aislop auto-fixes**: removed unused imports, narrative comments, and formatting issues
- **4 bare except-with-pass**: added proper error messages or restructured to avoid silent swallows
- **3 chained dict `.get()` calls**: normalized with explicit helper functions

### Infrastructure
- **Cross-platform release workflow**: PyInstaller binaries for Linux, macOS, and Windows
- **CI/CD**: All 11 GitHub Actions pinned to immutable SHAs for supply-chain security
- **Gitignore**: Added patterns for `.env*`, `.charter/`, `.claude/local/`, `.cursor/cache/`, `.hk/`, `docs/plans/`
- **Quality gates**: Added `aislop scan` and `charter doctor` compliance improvements

## [0.3.2] - 2026-06-12

### Fixed
- **Security**: Fixed shared path checks during uninstallation to properly resolve symlinks, preventing accidental deletion of directories like `~/bin`.
- **Bug**: Fixed `python` install method breaking packages by copying source to the app directory before running `pip install -e`.
- **Bug**: Prevented temporary directory resource leaks in `/tmp` by ensuring cleanup on installation errors.
- **Bug**: Removed duplicate printing of tool checks in `pluck doctor` output.
- Post-install hook path double-nesting (`~/.config/pluck/pluck/hooks/` → `~/.config/pluck/hooks/`)
- PyPI license metadata now shows correctly (inline table format)

## [0.2.0] - 2026-05-08

### Changed
- **Published to PyPI as `pluck-cli`** — `pip install pluck-cli`

### Added
- `--timeout <secs>` flag — set timeout for git clone operations
- `--retries <n>` flag — auto-retry failed git clones with 2s backoff
- `clean` command — remove orphaned registry entries (apps whose paths no longer exist)
- `verify` command — check if installed apps are still valid (files exist, not corrupted)
- `stats` command — show installation statistics (total apps, disk usage, method breakdown)
- `remove` alias for uninstall command
- `--json` flag — machine-readable output for scripting
- `--no-color` flag — disable colored output
- ANSI color auto-detection — colors disabled automatically when piping or on non-TTY
- Post-install hooks — run custom scripts after each install via `~/.config/gh-install/hooks/post-install.sh`
- Dockerfile for containerized testing and deployment
- Man page (`man/gh-install.1`)
- Type hints throughout codebase (`from __future__ import annotations`)
- `_format_bytes()` helper for human-readable size formatting
- `_run_post_install_hook()` with `GH_INSTALL_APP`, `GH_INSTALL_PATH`, `GH_INSTALL_METHOD` env vars
- `clean_registry()` with dry-run and force support
- `verify_apps()` with valid/invalid count
- `stats_command()` with total, valid, orphaned, size, and method breakdown
- `GIST_PATTERN` regex for gist URL detection
- `VALID_METHODS` constant for method validation
- Test suite expanded to 73 tests across 14 test classes
- `--shallow` flag — use `git clone --depth 1` for much faster downloads
- `--ref <ref>` flag — clone a specific branch or tag instead of default
- `--method <method>` flag — force a specific install method instead of auto-detect
- `--yes` flag — non-interactive mode (alias for `--force`)
- Gist support — `gist.github.com` URLs are detected and installed as `gist-<id>`
- Post-install summary — shows name, method, location, and disk size after install
- Disk size calculation — `_get_disk_size()` with human-readable output (B/KB/MB/GB)
- Method priority config — users can configure preferred method order via config file
- User config file support — `$XDG_CONFIG_HOME/gh-install/config.json`
- `.gitignore` — comprehensive patterns for Python, build, IDE, and OS files
- `python-semantic-release` config in `pyproject.toml`
- License format updated to SPDX string (removes deprecation warnings)
- `list` command now shows disk size and existence check for each app
- Shell completion updated for all new commands and flags
- `VALID_METHODS` constant for install method validation
- `GIST_PATTERN` regex for gist URL detection

### Changed
- `detect_install_method()` now accepts optional `method_priority` parameter
- `download_and_install()` now accepts `shallow`, `ref`, and `method_override` parameters
- `_parse_args()` now returns 7 values: `install_dir, dry_run, force, shallow, ref, method, urls`
- `parse_github_url()` now returns `is_gist` flag in result dict
- `list_installed()` shows disk size and existence status per app
- Shell completion scripts updated with all 17 commands and new flags
- `print_usage()` updated with all commands, options, and formatting

### Fixed
- Duplicate `_load_user_config()` function removed
- License deprecation warnings in `pyproject.toml`

## [0.1.0] - Initial Release

### Added
- Basic CLI with `install`, `list`, `uninstall`, and `help` commands
- Auto-detection of install methods (script, binary, Python, Node, Go, Rust, Makefile, download)
- JSON-based app registry for tracking installations
- Batch installation support
- Terminal color output
- `update` command to re-install an app from its original GitHub URL
- `--dir <path>` flag to override the default install directory
- `--dry-run` flag to preview installation without making changes
- `--force` flag to skip confirmation prompts
- Error handling in all installer functions
- `_sanitize_repo_name()` to reject path traversal attempts
- `_is_executable()` helper for improved binary detection
- `SHARED_PATHS` guard to prevent destructive uninstalls
- Platform-aware default install directory
- `update_app()` with registry rollback on failure
- `_parse_args()` for unified CLI flag parsing
- MIT License
- `pyproject.toml` with setuptools, ruff, pytest, and coverage config
- Test suite with 47 unit tests across 9 test classes
- GitHub Actions CI workflow (Ubuntu + macOS, Python 3.8–3.13, ruff lint, coverage)
- PyPI publishing workflow
- Shell completion (Bash and Zsh)
- `--version` flag
- CHANGELOG.md
- CONTRIBUTING.md
- `.pre-commit-config.yaml`
- README badges (CI, License, Python version)
