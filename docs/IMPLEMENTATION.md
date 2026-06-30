# Implementation Document

## Architecture Overview

`pluck` is a single-file Python 3 CLI application (~2400 lines) with zero external dependencies. It provides a simple interface for installing repositories from any git hosting platform (GitHub, GitLab, Codeberg, Bitbucket, SourceHut, etc.) by auto-detecting the project type and applying the appropriate installation strategy.

### Entry Point

```
src/pluck.py
```

Executed via `python src/pluck.py <command> [args]` or `pluck` after pip install.

A backward-compat shim at `src/gh_install.py` (`from pluck import *`) preserves the legacy `gh-install` entry point.

### Core Modules (by function group)

| Group | Functions | Purpose |
|-------|-----------|---------|
| **CLI** | `main()`, `print_usage()`, `_parse_args()` | Command routing for 19 commands |
| **URL Parsing** | `parse_repo_url()`, `_parse_snippet_url()`, `_detect_host_type()` | Extract owner/repo from any git repo URL; detect forge type; handle gists and GitLab snippets |
| **Detection** | `detect_install_method()`, `_check_install_method()` | Scans repo for project files with configurable method priority |
| **Installers** | `install_script()`, `install_python()`, `install_node()`, `install_go()`, `install_rust()`, `install_binary()`, `install_make()` | Project-type-specific installation logic |
| **Release assets** | `install_release_asset()`, `_github_release_url()`, `_gitlab_release_url()`, `_safe_tar_members()` | Download prebuilt release assets; safe tar/zip extraction |
| **Orchestration** | `download_and_install()`, `_clone_repo()`, `_try_release_install()`, `_install_local_path()` | Clones to temp (with shallow/ref support), detects method, dispatches installer, registers, cleans up, shows summary |
| **Registry** | `register_app()`, `load_registry()`, `save_registry()`, `_with_registry_lock()`, `list_installed()`, `uninstall_app()`, `pin_app()`, `unpin_app()` | JSON-based app tracking at `~/.pluck-registry.json` with atomic writes + advisory file locking |
| **Config** | `_load_user_config()`, `_save_user_config()`, `config_command()`, `_migrate_old_registry()` | User config at `$XDG_CONFIG_HOME/pluck/config.json`; one-time migration from old `gh-install` paths |
| **Info** | `info_app()`, `_get_disk_size()`, `_safe_dir_size()`, `_format_bytes()` | Detailed app info with disk size calculation |
| **Doctor** | `doctor()` | Checks availability of git, python3, npm, go, cargo, make |
| **Search** | `search_github()`, `search_gitlab()`, `search_codeberg()`, `search_bitbucket()`, `search_all_forges()` | Multi-forge repo search via `urllib` (with `_safe_urlopen` scheme guard) |
| **Migration** | `export_registry()`, `import_registry()` | Export/import registry for machine migration |
| **Cache** | `cache_command()` | Prune or locate the download cache at `~/.cache/pluck` |
| **Self-update** | `self_update()` | Pip-upgrade `pluck-cli` in place |
| **UI** | `Colors`, `print_header()`, `print_success()`, `print_warning()`, `print_error()` | Terminal color output with TTY auto-detection |
| **Completion** | `_completion_script()`, `_get_app_names()` | Bash and Zsh shell completion generation |
| **Security** | `_safe_urlopen()`, `_sanitize_repo_name()`, `_safe_tar_members()`, `SHARED_PATHS` | Scheme allowlist, path-traversal guard, safe archive extraction, shared-dir delete protection |

### Data Flow

```
User input (URL)
  → parse_repo_url() (detects forge type, supports gists)
  → git clone (temp dir, optional --depth 1, optional --branch)
  → detect_install_method() (respects method_priority config)
  → dispatch to appropriate install_*()
  → register_app() → ~/.pluck-registry.json (atomic write + lock)
  → post-install summary (name, method, location, size)
  → cleanup temp dir
```

If `--method release` is used, `download_and_install` calls `_try_release_install` first, and falls back to a clone+install if no release assets are available.

## Infrastructure Status

| Item | Status |
|------|--------|
| Test suite | 111 tests passing across 24 test classes |
| Package configuration | `pyproject.toml` with setuptools, ruff, pytest, semantic-release |
| Linting/formatting config | `pyproject.toml` with ruff config |
| CI/CD pipeline | GitHub Actions release workflow (PyInstaller binaries for Linux/macOS/Windows + wheel + PyPI publish + GitHub Release) |
| LICENSE file | MIT License |
| CHANGELOG | `CHANGELOG.md` with Keep a Changelog format |
| Contributing guide | `CONTRIBUTING.md` with dev workflow docs |
| Pre-commit hooks | `.pre-commit-config.yaml` with ruff |
| PyPI publishing | `.github/workflows/release.yml` |
| Shell completion | Bash and Zsh completion scripts via `completion` command |
| README badges | CI, License, Python version |
| .gitignore | Comprehensive Python/build/IDE/OS patterns |

## Dependencies

| Dependency | Source | Purpose |
|------------|--------|---------|
| Python 3 standard library | Built-in | All functionality |
| pytest | Dev dependency | Test suite |
| Git | External (required) | Cloning repositories |
| npm | External (optional) | Node.js project installs |
| Go | External (optional) | Go project installs |
| Cargo/Rust | External (optional) | Rust project installs |
| make | External (optional) | Makefile-based installs |

## Registry Schema

**File**: `~/.pluck-registry.json`

```json
{
  "apps": {
    "<repo-name>": {
      "url": "<github-url>",
      "path": "<install-path>",
      "method": "<install-method>",
      "pinned": false,
      "installed_at": "<timestamp>"
    }
  }
}
```

**Install methods**: `script`, `binary`, `python`, `node`, `go`, `rust`, `make`, `download`, `release`

**Concurrency**: Writes are atomic (temp file + rename). `register_app()` holds an advisory `fcntl.flock` on `~/.pluck-registry.lock` for the full read-modify-write so `--jobs > 1` parallel installs cannot lose each other's entries.

## User Config Schema

**File**: `$XDG_CONFIG_HOME/pluck/config.json` (default: `~/.config/pluck/config.json`)

```json
{
  "install_dir": "/custom/path",
  "method_priority": ["script", "python", "node", "go", "rust", "make", "binary", "download"]
}
```

## Test Suite

**Location**: `tests/test_pluck.py`

**Coverage**: 111 tests across 24 test classes:
- `TestParseRepoUrl` (22 tests) — URL parsing for GitHub, GitLab, Codeberg, Bitbucket, SourceHut, Gitea, Gogs, Pagure, Forgejo, self-hosted, generic
- `TestGistUrl` (7 tests) — gist URL parsing (GitHub gists + GitLab snippets)
- `TestDetectInstallMethod` (17 tests) — Project type detection with method priority
- `TestSharedPaths` (2 tests) — Safety guard validation
- `TestValidMethods` (2 tests) — VALID_METHODS constant
- `TestSanitizeRepoName` (4 tests) — Path traversal protection
- `TestIsExecutable` (6 tests) — Binary detection heuristics
- `TestGetDiskSize` (3 tests) — Disk size calculation
- `TestParseArgs` (10 tests) — CLI flag parsing (all flags)
- `TestDryRun` (1 test) — Dry run mode integration
- `TestRegistryOperations` (3 tests) — Registry save/load/register/uninstall
- `TestUpdateApp` (2 tests) — Update command logic
- `TestInfoApp` (2 tests) — Info command
- `TestDoctor` (2 tests) — Doctor command
- `TestConfigCommand` (2 tests) — Config command
- `TestExportImport` (4 tests) — Export/import commands
- `TestVerifyApps` (3 tests) — verify_apps() with valid/missing/json
- `TestStatsCommand` (2 tests) — stats_command() output and JSON
- `TestFormatBytes` (5 tests) — _format_bytes() size formatting
- `TestExtractGlobalFlags` (5 tests) — _extract_global_flags() edge cases
- `TestDownloadAndInstallMocked` (4 tests) — Clone/retry/error flows with mocks

**Run tests**: `python -m pytest tests/ -v`

## Commands (19 total)

| Command | Description |
|---------|-------------|
| `install <url> [options]` | Install from any git repo URL |
| `update <name> [--force]` | Update an installed app |
| `info <name>` | Show detailed app info (URL, method, path, size, exists) |
| `list` | List all installed apps with size and existence check |
| `uninstall <name> [--force]` | Uninstall an app |
| `remove <name> [--force]` | Alias for uninstall |
| `verify` | Check if installed apps are still valid |
| `clean [--force] [--dry-run]` | Remove orphaned registry entries |
| `stats` | Show installation statistics |
| `doctor` | Check tool availability (git, python3, npm, go, cargo, make) |
| `config [key] [value]` | View or set configuration values |
| `search <query> [--forge <name>] [--all] [--output <file>]` | Search repos across forges |
| `export <file>` | Export registry to JSON file |
| `import <file>` | Import registry from JSON file |
| `completion <shell>` | Generate shell completion (bash/zsh) |
| `pin <name>` | Pin an app to prevent updates |
| `unpin <name>` | Unpin an app |
| `self-update` | Update pluck via PyPI |
| `cache <prune\|path>` | Manage download cache |
| `version` | Show version |
| `help` | Show usage |

## Install Options

| Flag | Description |
|------|-------------|
| `--dir <path>` | Install to a custom directory |
| `--dry-run` | Preview without making changes |
| `--force` | Skip confirmation prompts |
| `--shallow` | Use `git clone --depth 1` for faster downloads |
| `--ref <ref>` | Clone a specific branch or tag |
| `--method <method>` | Force a specific install method |
| `--yes` | Non-interactive mode (alias for `--force`) |
| `--json` | Machine-readable output (for select commands) |
| `--no-color` | Disable colored output |
| `--timeout <secs>` | Timeout for git clone in seconds |
| `--retries <n>` | Auto-retry failed git clones with 2s backoff |
| `--jobs <n>` | Number of parallel installs (default: 1) |
| `--release` | Install from pre-built release assets instead of cloning |
| `--verbose` | Show detailed git clone output |

## Security Notes

- **URL scheme allowlist**: `_safe_urlopen()` blocks `file://`, `ftp://`, and other non-http(s) schemes to prevent CVE-2023-24329-style abuse.
- **Path traversal**: `_sanitize_repo_name()` rejects names containing `..` or leading slashes; safe archive extraction prevents tar/zip-slip.
- **Shared directory protection**: `SHARED_PATHS` and `$HOME` are never deleted during uninstall/update.
- **Atomic registry writes**: `save_registry()` writes to a temp file and renames, so a crash mid-write cannot corrupt `~/.pluck-registry.json`.
- **Advisory locking**: `register_app()` holds an `fcntl.flock` so parallel installs (via `--jobs`) cannot lose each other's entries.
