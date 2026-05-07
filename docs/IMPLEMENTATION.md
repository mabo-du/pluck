# Implementation Document

## Architecture Overview

`pluck` is a single-file Python 3 CLI application (~1500 lines) with zero external dependencies. It provides a simple interface for installing repositories from any git hosting platform (GitHub, GitLab, Codeberg, Bitbucket, SourceHut, etc.) by auto-detecting project type and applying the appropriate installation strategy.

### Entry Point

```
src/gh_install.py
```

Executed via `python src/gh_install.py <command> [args]` or `gh-install` after pip install.

### Core Modules (by function group)

| Group | Functions | Purpose |
|-------|-----------|---------|
| **CLI** | `main()`, `print_usage()` | Command routing for 17 commands |
| **URL Parsing** | `parse_repo_url()`, `_parse_gist_url()`, `_detect_host_type()` | Extract owner/repo from any git repo URL; detect forge type |
| **Detection** | `detect_install_method()` | Scans repo for project files with configurable method priority |
| **Installers** | `install_script()`, `install_python()`, `install_node()`, `install_go()`, `install_rust()`, `install_binary()`, `install_make()` | Project-type-specific installation logic |
| **Orchestration** | `download_and_install()` | Clones to temp (with shallow/ref support), detects method, dispatches installer, registers, cleans up, shows summary |
| **Registry** | `register_app()`, `load_registry()`, `save_registry()`, `list_installed()`, `uninstall_app()` | JSON-based app tracking at `~/.gh-install-registry.json` |
| **Config** | `_load_user_config()`, `_save_user_config()`, `config_command()` | User config at `$XDG_CONFIG_HOME/gh-install/config.json` |
| **Info** | `info_app()`, `_get_disk_size()` | Detailed app info with disk size calculation |
| **Doctor** | `doctor()` | Checks availability of git, python3, npm, go, cargo, make |
| **Search** | `search_github()` | GitHub API repository search via `urllib` |
| **Migration** | `export_registry()`, `import_registry()` | Export/import registry for machine migration |
| **UI** | `Colors`, `print_header()`, `print_success()`, `print_warning()`, `print_error()` | Terminal color output |
| **Completion** | `_completion_script()`, `_get_app_names()` | Bash and Zsh shell completion generation |

### Data Flow

```
User input (URL)
  → parse_repo_url() (detects forge type, supports gists)
  → git clone (temp dir, optional --depth 1, optional --branch)
  → detect_install_method() (respects method_priority config)
  → dispatch to appropriate install_*()
  → register_app() → ~/.pluck-registry.json
  → post-install summary (name, method, location, size)
  → cleanup temp dir
```

## Bugs and Issues

### Resolved (18 total)

1. ~~**`install_python` venv path collision**~~ — **FIXED**
2. ~~**`uninstall_app` destructive for shared directories**~~ — **FIXED**
3. ~~**No error handling for git clone failures**~~ — **FIXED**
4. ~~**`register_app` uses platform-dependent `date` command**~~ — **FIXED**
5. ~~**Hardcoded macOS-specific install directory**~~ — **FIXED**
6. ~~**`install_go` ignores `install_dir` parameter**~~ — **FIXED**
7. ~~**`install_node` copies entire repo including `node_modules`**~~ — **FIXED**
8. ~~**`install_make` defined after reference**~~ — **FIXED**
9. ~~**No progress output during `git clone`**~~ — **FIXED**
10. ~~**`install_binary` executable detection is unreliable**~~ — **FIXED**
11. ~~**No input validation for path traversal**~~ — **FIXED**
12. ~~**Duplicate help text**~~ — **FIXED**
13. ~~**Hardcoded NVIDIA API key in .aider.conf.yml**~~ — **FIXED**: Replaced with env var comment
14. ~~**Duplicate code in download_and_install()**~~ — **FIXED**: Removed 55-line duplicate block that caused double clone + temp dir leak
15. ~~**verify_apps() never defined**~~ — **FIXED**: Implemented function (was causing NameError)
16. ~~**stats_command() never defined**~~ — **FIXED**: Implemented function (was causing NameError)
17. ~~**json_output uninitialized in main()**~~ — **FIXED**: Initialized at top of main() + added `_extract_global_flags()` helper
18. ~~**python3 hardcoded in doctor()**~~ — **FIXED**: Falls back to `python` if `python3` not found

## Infrastructure Status

| Item | Status |
|------|--------|
| Test suite | 92 tests passing |
| Package configuration | `pyproject.toml` with setuptools, ruff, pytest, semantic-release |
| Linting/formatting config | `pyproject.toml` with ruff config |
| CI/CD pipeline | GitHub Actions (Ubuntu + macOS, Python 3.8–3.13, ruff lint, coverage) |
| LICENSE file | MIT License |
| CHANGELOG | `CHANGELOG.md` with Keep a Changelog format |
| Contributing guide | `CONTRIBUTING.md` with dev workflow docs |
| Pre-commit hooks | `.pre-commit-config.yaml` with ruff |
| PyPI publishing | `.github/workflows/publish-pypi.yml` |
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
      "installed_at": "<timestamp>"
    }
  }
}
```

**Install methods**: `script`, `binary`, `python`, `node`, `go`, `rust`, `make`, `download`

## User Config Schema

**File**: `$XDG_CONFIG_HOME/pluck/config.json` (default: `~/.config/pluck/config.json`)

```json
{
  "install_dir": "/custom/path",
  "method_priority": ["script", "python", "node", "go", "rust", "make", "binary", "download"]
}
```

## Test Suite

**Location**: `tests/test_gh_install.py`

**Coverage**: 108 tests across 23 test classes:
- `TestParseRepoUrl` (22 tests) — URL parsing for GitHub, GitLab, Codeberg, Bitbucket, SourceHut, Gitea, Gogs, Pagure, Forgejo, self-hosted, generic
- `TestGistUrl` (4 tests) — gist URL parsing
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

## Commands (17 total)

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
| `search <query>` | Search GitHub repositories via API |
| `export <file>` | Export registry to JSON file |
| `import <file>` | Import registry from JSON file |
| `completion <shell>` | Generate shell completion (bash/zsh) |
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
