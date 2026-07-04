# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.6.0] - 2026-07-05

### Fixed (security)
- **Security**: `pluck install` ran a repo's detected install method (`install.sh`, `pip install -e`, `npm install`, `cargo build`, or `make`) immediately, with no confirmation step at all — `--force`/`--yes` were parsed but never actually wired into the install path, so they had no effect. Installing now always asks for confirmation first, showing exactly what will run, unless `--force`/`--yes` is passed on purpose. Refuses safely on a non-interactive run, `sys.stdin` being `None`, Ctrl-C, or Ctrl-D, instead of hanging or crashing.
- **Security**: `_sanitize_repo_name` now also rejects Windows-style drive-letter paths (e.g. `C:\Windows\System32`), matching the backslash handling `_safe_tar_members` already used elsewhere in this file.

### Fixed
- Installing multiple repos with `--jobs > 1` now requires `--force`/`--yes` up front, since prompting for confirmation across threads at once isn't safe.
- The `--jobs` error message now correctly mentions both `--force` and `--yes`.

### Removed
- Deleted `seeds/`, `schemas/`, and `migrations/` — three vestigial directories from an earlier scaffold, each containing nothing but a stray backup file.

### Docs
- Clarified in the README that `gitlab.com/mabodu/pluck` is an intentional mirror (GitLab hosts canonical development + CI), not a stale link.
- Fixed `opencode.md` reporting a stale test count.

### Added (tests)
- `test_confirm_install_refuses_when_noninteractive`, `test_install_cancelled_without_force_noninteractive`, `test_install_proceeds_with_force`, `test_install_proceeds_when_user_types_y`, `test_install_cancelled_when_user_types_n`, `test_parallel_install_without_force_exits` — cover the new confirmation gate.
- `test_confirm_install_refuses_when_stdin_is_none`, `test_confirm_install_eof_at_prompt_is_treated_as_no`, `test_confirm_install_ctrl_c_exits_cleanly`, `test_parallel_install_with_force_succeeds` — cover the crash fixes and the parallel-with-force path.
- `test_rejects_windows_drive_path_backslash`, `test_rejects_windows_drive_path_forward_slash`, `test_allows_name_with_colon_but_no_drive_pattern` — cover the sanitizer hardening.
- Total: 145 tests passing (up from 132).

## [0.5.0] - 2026-06-30

### Fixed (code review follow-ups)
- **Security**: Backslash-based path traversal bypass in `_safe_tar_members` and zip extraction — on Unix, backslashes are valid filename characters, so `foo\..\..\bar` would bypass the `..` check that uses `Path.parts`. Backslashes are now normalized to forward slashes before checking, and the member name is updated in place.
- **Bug**: `install_python` symlink logic could still raise `IsADirectoryError` if a directory existed at `install_dir/bin/<name>` (e.g. user-created). Now checks `is_file()`/`is_symlink()` before unlinking and warns + skips if the target is a directory.
- **Bug**: Protocol handler hard-depended on `python3` after the URL-parsing rewrite. Now probes for `python3` then `python` then falls back to a shell-based best-effort parser that truncates at the first `&`.
- **Bug**: `save_registry` leaked the `.tmp` file when `os.replace` failed and the direct-write fallback was used. The temp file is now cleaned up in the error path.
- **Concurrency**: `uninstall_app`, `pin_app`, `unpin_app`, `clean_registry`, `import_registry`, and `update_app` now all acquire the registry advisory lock for their read-modify-write sequences (previously only `register_app` was locked). This closes the race condition that `--jobs > 1` parallel operations could still trigger via these functions.

### Added (tests)
- `test_safe_tar_members_rejects_backslash_traversal` — regression for the backslash bypass.
- `test_install_python_skips_symlink_when_target_is_directory` — regression for the symlink-dir guard.
- `test_uninstall_app_acquires_lock` — verifies `uninstall_app` holds the registry lock.
- `test_pin_unpin_acquires_lock` — verifies `pin_app`/`unpin_app` hold the registry lock.
- Total: 132 tests passing (up from 128).

### Fixed
- **Bug**: `install_python` symlink logic attempted to `unlink()` the non-empty `app_dir` directory when an entry-point script matched the repo name, causing `IsADirectoryError`. Symlinks are now created at `install_dir/bin/<name>` instead.
- **Bug**: `_try_release_install` claimed to "fall back to clone" but actually returned `None`, causing `pluck install --method release` to silently fail when no release assets were available. The fallback is now real.
- **Bug**: `install_make` could raise an uncaught `CalledProcessError` when the fallback `make` invocation failed. It now returns `None` like the other installers.
- **Bug**: `scripts/pluck-protocol-handler.sh` used a naive `sed` to extract the `url` query param, which appended trailing `&key=value` parameters to the target URL. Rewritten to use Python's `urllib.parse` for correct query-string handling.
- **Bug**: `Dockerfile` only copied `src/gh_install.py` (a `from pluck import *` shim), so the Docker build failed because `pluck.py` was missing. Now copies both files.
- **Bug**: `_parse_args` silently treated flags missing their value (e.g. `pluck install --dir` with no value) as URLs, producing confusing "Invalid repository URL: --dir" errors. Now raises a friendly `ValueError`.
- **Bug**: `_extract_global_flags` documented a 3-tuple return but only returned 2 values (`no_color` was computed but discarded). Now actually returns `(cleaned_args, json_output, no_color)`.
- **Bug**: `search_gitlab` used `collector=` parameter name, inconsistent with the `results=` convention used by the other searchers. Renamed to `results=`.
- **Bug**: `search_codeberg` had a redundant `ok` flag check (the second branch was dead code). Consolidated.
- **Bug**: `cache_command` used an awkward `CACHE_DIR.rmdir() if CACHE_DIR.exists() else None` ternary that could crash on a non-empty directory. Now uses a try/except.
- **Bug**: `install_release_asset` would attempt to fetch releases for gists/snippets (which have `host_type=github/gitlab` but no releases API). Now explicitly skips them.
- **Security**: `tarfile.extractall()` was called without `filter='data'`, allowing path-traversal in malicious tarballs (CVE-2007-4559 family). Now uses `filter='data'` on Python 3.12+ and a custom `_safe_tar_members()` filter on older versions. Zip extraction is also sanitized.
- **Security**: `save_registry` was non-atomic; a crash mid-write could corrupt `~/.pluck-registry.json`. Now writes to a temp file and renames into place.
- **Security**: `register_app` performed an unsynchronized read-modify-write, allowing `--jobs > 1` parallel installs to lose each other's entries. Now holds an `fcntl.flock` advisory lock for the full read-modify-write.
- **Robustness**: `load_registry` would crash on a corrupt registry file. Now logs a warning and returns a fresh empty registry.

### Changed
- `requires-python` bumped from `>=3.6` to `>=3.8` to match the documented Python requirement (3.6 is EOL).
- `pyproject.toml` classifiers updated to drop Python 3.6/3.7.

### Removed
- `pforge-mcp/` directory — belonged to the unrelated "Plan Forge" project (https://github.com/srnichols/plan-forge) and referenced files that don't exist in this repo (`./orchestrator.mjs`, `./hub.mjs`).
- `docs/COPILOT-VSCODE-GUIDE.md` — also from "Plan Forge", not relevant to pluck.
- `charter.yaml` — referenced `use-charter.dev` schema, unrelated to pluck.

### Added
- `_safe_tar_members()` helper for path-traversal-safe tar extraction on Python < 3.12.
- `_with_registry_lock()` context manager for advisory-file-lock-based serialization.
- `ARCHITECTURE.md` — filled in the previous stub with overview, layout, data flow, concurrency model, and security posture.
- 17 new regression tests in `tests/test_pluck.py`:
  - `TestParseArgsMissingFlagValue` (6 tests)
  - `TestRegistryAtomicWrite` (3 tests)
  - `TestInstallPythonSymlink` (1 test)
  - `TestSafeTarMembers` (1 test)
  - `TestProtocolHandlerUrlParsing` (4 tests)
  - `TestReleaseInstallFallback` (1 test)
  - `TestInstallMakeFallback` (1 test)

### Documentation
- `README.md`: corrected test count (111→128), removed references to nonexistent `ci.yml`/`publish-pypi.yml` workflows, removed "coming soon" note for the browser extension (it already exists), updated line count (2200→2400).
- `docs/IMPLEMENTATION.md`: rewrote to reflect current state (2400 lines, 19 commands, 128 tests, 30 test classes, registry locking, security notes).
- `CONTRIBUTING.md`: updated file references (`test_gh_install.py` → `test_pluck.py`, `gh_install` → `pluck`).
- `man/pluck.1`: updated version (0.2.0 → 0.4.0), added missing `pin`/`unpin`/`self-update`/`cache` commands and `--jobs`/`--release`/`--verbose` flags.
- `HomebrewFormula/pluck-cli.rb`: updated URL version (0.2.0 → 0.4.0).
- `assets/browser-extension/README.md`: removed "icon not yet provided" note (icon.png exists).
- `scripts/install-protocol-handler.sh`: removed "coming soon" note for the browser extension.

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
