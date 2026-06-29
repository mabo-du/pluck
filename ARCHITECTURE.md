# pluck Architecture

## Overview

`pluck` is a zero-dependency Python 3 CLI that installs git repositories from
any git hosting platform (GitHub, GitLab, Codeberg, Bitbucket, SourceHut,
Gitea, Gogs, Pagure, Forgejo, self-hosted, or any URL that parses as
`host/owner/repo`). It clones to a temp directory, auto-detects the project
type, dispatches to the appropriate installer, registers the result in a
JSON registry, and cleans up.

The codebase is intentionally a single file (`src/pluck.py`, ~2400 lines)
with a small backward-compat shim (`src/gh_install.py`) for the legacy
`gh-install` entry point. There is no plugin system, no runtime dependency
on third-party packages, and no daemon.

## Layout

| Path | Responsibility |
|------|----------------|
| `src/pluck.py` | All application logic (CLI, URL parsing, installers, registry, search, release assets) |
| `src/gh_install.py` | One-line `from pluck import *` shim for backward compat with the old `gh-install` name |
| `tests/test_pluck.py` | 111 unit tests across 24 test classes |
| `scripts/pluck-protocol-handler.sh` | Receives `pluck://install?url=...` URLs from the browser and dispatches to `pluck install` |
| `scripts/install-protocol-handler.sh` | Registers the `pluck://` protocol handler on macOS (launchd) and Linux (xdg) |
| `assets/browser-extension/` | Chrome/Chromium MV3 extension adding a right-click "Install with pluck" menu item |
| `man/pluck.1` | Man page for the `pluck` command |
| `man/gh-install.1` | Legacy man page kept for backward compat |
| `Dockerfile` | Container image definition |
| `pyproject.toml` | Build config, entry points, ruff/pytest/semantic-release settings |
| `.github/workflows/release.yml` | Build wheel + PyInstaller binaries for Linux/macOS/Windows, publish to PyPI and GitHub Releases |
| `HomebrewFormula/pluck-cli.rb` | Homebrew formula (installs from PyPI source) |

## Data Flow

```
User input (URL or local path)
  → parse_repo_url() (detects forge type, supports gists + GitLab snippets)
  → _clone_repo() (temp dir, optional --depth 1 / --branch, retry on transient failures)
  → detect_install_method() (respects method_priority config)
  → dispatch to install_script / install_python / install_node / install_go /
            install_rust / install_make / install_binary
  → register_app() → ~/.pluck-registry.json (atomic write + advisory lock)
  → _run_post_install_hook() (optional user script at ~/.config/pluck/hooks/post-install.sh)
  → _print_summary() (name, method, location, size)
  → cleanup temp dir
```

If `--method release` is requested, `download_and_install()` calls
`_try_release_install()` first to download prebuilt release assets from the
forge's releases API; on failure it falls back to a normal clone+install so
the user does not need to re-run.

## Concurrency Model

`register_app()` performs a read-modify-write on `~/.pluck-registry.json`.
To support `--jobs > 1` parallel installs without losing entries, the entire
read-modify-write is wrapped in an `fcntl.flock` advisory lock on
`~/.pluck-registry.lock`. `save_registry()` additionally writes to a temp
file and renames into place, so a crash mid-write cannot leave a
half-written registry. On Windows (no `fcntl`), the lock is a no-op and
only the atomic-rename protection applies.

## Security Posture

| Threat | Mitigation |
|--------|------------|
| URL scheme abuse (`file://`, `ftp://`) | `_safe_urlopen()` allows only `http`/`https` |
| Path traversal via repo name | `_sanitize_repo_name()` rejects `..` and leading slashes |
| Tarball path traversal (CVE-2007-4559) | `tarfile.extractall(..., filter='data')` on Python 3.12+, `_safe_tar_members()` fallback on older versions |
| Zip-slip | Manual sanitization of zip member paths before extraction |
| Deleting shared system directories during uninstall | `SHARED_PATHS` + `$HOME` are protected |
| Registry corruption on crash | Atomic temp-file + rename in `save_registry()` |
| Registry race under `--jobs` | `fcntl.flock` advisory lock in `register_app()` |

## Extending

To add a new install method:

1. Add detection logic to `_check_install_method()` and the method name to `VALID_METHODS`.
2. Implement `install_<method>(repo_path, install_dir)` returning the installed path or `None`.
3. Register it in `_INSTALL_FUNCS` (and the local copy in `_install_local_path`).
4. Add tests for detection and the installer in `tests/test_pluck.py`.

To add a new forge for release-asset installs:

1. Add host detection to `_detect_host_type()` if not already covered.
2. Implement `_<forge>_release_url(repo_info, install_dir)`.
3. Wire it into `install_release_asset()`.
