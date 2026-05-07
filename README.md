<p align="center">
  <h1 align="center">🪶 pluck</h1>
  <p align="center"><strong>Paste any git repo URL → Auto-install → Done!</strong></p>
</p>

<p align="center">
  <a href="https://github.com/mark/pluck/actions/workflows/ci.yml"><img src="https://github.com/mark/pluck/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/mark/pluck/actions/workflows/publish-pypi.yml"><img src="https://github.com/mark/pluck/actions/workflows/publish-pypi.yml/badge.svg" alt="Publish"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/Code%20style-ruff-EF5552" alt="Code style: ruff"></a>
  <img src="https://img.shields.io/badge/Dependencies-Zero-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/Tests-108%20passing-brightgreen" alt="108 passing tests">
  <img src="https://img.shields.io/badge/Commands-17-blue" alt="17 commands">
  <img src="https://img.shields.io/badge/Flags-11-purple" alt="11 flags">
</p>

---

A CLI tool that simplifies installing repositories from any git hosting platform — GitHub, GitLab, Codeberg, Bitbucket, SourceHut, Gitea, Gogs, Pagure, Forgejo, self-hosted, or any other git forge. Just paste a URL and pluck detects the project type and installs it.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [How It Works](#-how-it-works)
- [Features](#-features)
- [Commands](#-commands)
- [Flags](#-flags)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [Why This Exists](#-why-this-exists)

## 🚀 Quick Start

```bash
# Install from any git hosting platform
pluck install https://github.com/user/repo
pluck install https://gitlab.com/user/project
pluck install https://codeberg.org/user/repo

# That's it. The tool detects the project type and installs it.
```

## 🔄 How It Works

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Any git URL    │────▶│  Clone to    │────▶│  Detect Method  │────▶│  Install     │
│  (any forge)    │     │  Temp Dir    │     │  (Auto-detect)  │     │  (8 methods) │
└─────────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                                                                         │
┌─────────────────┐     ┌──────────────┐                                │
│   Post-Install  │◀────│  Register    │◀───────────────────────────────┘
│   Hook (opt)    │     │  App         │
└─────────────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│  Summary +      │
│  Cleanup        │
└─────────────────┘
```

### Install Methods

| Method | Detection | Action |
|--------|-----------|--------|
| 🔧 **Script** | `install.sh` | Runs `bash install.sh --yes` |
| 🐍 **Python** | `pyproject.toml`, `setup.py` | Creates venv, pip installs |
| 🟢 **Node.js** | `package.json` | Copies source, runs `npm install` |
| 🔵 **Go** | `go.mod`, `*.go` | Runs `go build -o` to install dir |
| 🦀 **Rust** | `Cargo.toml` | Runs `cargo build --release`, copies binary |
| 📋 **Makefile** | `Makefile` | Runs `make install PREFIX=...` |
| 📦 **Binary** | `release/`, `bin/`, `*.AppImage`, `*.deb` | Copies to install dir |
| 📥 **Download** | Fallback | Copies entire directory |

## ✨ Features

### Installation
- 🔗 **Any git forge** — Install from GitHub, GitLab, Codeberg, Bitbucket, SourceHut, Gitea, Gogs, Pagure, Forgejo, self-hosted, or any git URL
- 🔍 **Auto-detection** — Automatically detects project type and install method
- 📦 **Batch install** — Install multiple repositories in one command
- ⚡ **Shallow clone** — `--shallow` for faster downloads
- 🏷️ **Branch/tag support** — `--ref` to install specific versions
- 🎯 **Force method** — `--method` to override auto-detection
- ⏱️ **Timeout & retry** — `--timeout` and `--retries` for flaky connections

### Management
- 📋 **List apps** — See all installed applications with disk size
- 🔄 **Update apps** — Re-install from original URL
- 🗑️ **Uninstall** — Remove apps with safety guards
- ✅ **Verify** — Check installed apps integrity
- 🧹 **Clean** — Remove orphaned registry entries
- 📊 **Stats** — Installation statistics and method breakdown
- 🔍 **Search** — Search GitHub repositories via API (other forges coming)
- 📤 **Export/Import** — Migrate registry between machines

### Configuration
- 📁 **Custom directory** — `--dir` to override default install location
- ⚙️ **User config** — Persistent settings via config file
- 🎨 **JSON output** — `--json` for machine-readable output
- 🚫 **No colors** — `--no-color` for clean terminal output
- 🔇 **Non-interactive** — `--yes` for scripting
- 🐳 **Docker support** — Containerized installation
- 📖 **Man page** — `man pluck` for offline docs
- 🔧 **Post-install hooks** — Custom scripts after each install

## 📖 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `install <url>` | Install from any git repo URL | `pluck install https://gitlab.com/user/project` |
| `update <name>` | Update an installed app | `pluck update myapp` |
| `info <name>` | Show app details | `pluck info myapp` |
| `list` | List installed apps | `pluck list` |
| `uninstall <name>` | Uninstall an app | `pluck uninstall myapp` |
| `remove <name>` | Alias for uninstall | `pluck remove myapp` |
| `verify` | Check apps validity | `pluck verify` |
| `clean` | Remove orphaned entries | `pluck clean --force` |
| `stats` | Show statistics | `pluck stats` |
| `doctor` | Check tool availability | `pluck doctor` |
| `config [key] [val]` | View/set config | `pluck config install_dir ~/Apps` |
| `search <query>` | Search GitHub repos (other forges coming) | `pluck search python installer` |
| `export <file>` | Export registry | `pluck export ~/backup.json` |
| `import <file>` | Import registry | `pluck import ~/backup.json` |
| `completion <shell>` | Generate shell completion | `pluck completion bash` |
| `version` | Show version | `pluck version` |
| `help` | Show help | `pluck help` |

## 🏷️ Flags

| Flag | Description |
|------|-------------|
| `--dir <path>` | Install to a custom directory |
| `--dry-run` | Preview without making changes |
| `--force` | Skip confirmation prompts |
| `--shallow` | Use shallow clone (`--depth 1`) |
| `--ref <ref>` | Clone a specific branch or tag |
| `--method <method>` | Force install method |
| `--yes` | Non-interactive mode (alias for `--force`) |
| `--json` | Output in JSON format (for scripting) |
| `--no-color` | Disable colored output |
| `--timeout <secs>` | Timeout for git clone in seconds |
| `--retries <n>` | Number of retries for failed git clone |

## 📥 Installation

### From Source

```bash
# Clone the repository
git clone https://gitlab.com/mabodu/gh-install.git
cd gh-install

# Install via pip
pip install -e .

# Or run directly
./src/gh_install.py install https://github.com/user/repo
```

### Via pip (not yet on PyPI)

```bash
# Once published to PyPI:
pip install pluck
```

> **Note**: pluck is not yet published to PyPI. Install from source above, or use the Docker image.

### Via Docker

```bash
docker build -t pluck .
docker run pluck install https://gitlab.com/user/project
```

## ⚙️ Configuration

### Default Paths

| Constant | macOS | Linux | Description |
|----------|-------|-------|-------------|
| `DEFAULT_INSTALL_DIR` | `~/Applications` | `~/.local/opt` | Where apps are installed |
| `APP_REGISTRY_FILE` | `~/.pluck-registry.json` | `~/.pluck-registry.json` | App registry |
| `CONFIG_FILE` | `~/.config/pluck/config.json` | `~/.config/pluck/config.json` | User config |

### User Config File

```json
{
  "install_dir": "/custom/path",
  "method_priority": ["script", "python", "node", "go", "rust", "make", "binary", "download"]
}
```

Manage via CLI:

```bash
pluck config install_dir ~/Apps
pluck config method_priority '["python","node","binary","download"]'
```

### Post-Install Hooks

Create `~/.config/pluck/hooks/post-install.sh` to run custom scripts after each install.

Available environment variables:
- `$GH_INSTALL_APP` — Repository name
- `$GH_INSTALL_PATH` — Installation path
- `$GH_INSTALL_METHOD` — Install method used

## 📁 Project Structure

```
pluck/
├── src/
│   └── gh_install.py          # Main application (~1500 lines)
├── tests/
│   └── test_gh_install.py     # Test suite (108 tests)
├── docs/
│   └── IMPLEMENTATION.md      # Implementation details
├── man/
│   ├── pluck.1                # Man page
│   └── gh-install.1           # Legacy man page
├── .github/
│   └── workflows/
│       ├── ci.yml             # CI: test + lint
│       └── publish-pypi.yml   # PyPI publish
├── README.md                  # This file
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # Developer guide
├── LICENSE                    # MIT License
├── Dockerfile                 # Container image
├── pyproject.toml             # Package config
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .gitignore                 # Git ignore patterns
└── .dockerignore              # Docker ignore patterns
```

## 🛠️ Development

```bash
# Install dev dependencies
pip install pytest ruff

# Run tests
python -m pytest tests/ -v

# Run linter
ruff check src/ tests/

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Test Coverage

```
108 tests passing across 23 test classes:
├── TestParseRepoUrl (22 tests)
├── TestGistUrl (4 tests)
├── TestDetectInstallMethod (17 tests)
├── TestSharedPaths (2 tests)
├── TestValidMethods (2 tests)
├── TestSanitizeRepoName (4 tests)
├── TestIsExecutable (6 tests)
├── TestGetDiskSize (3 tests)
├── TestParseArgs (10 tests)
├── TestDryRun (1 test)
├── TestRegistryOperations (3 tests)
├── TestUpdateApp (2 tests)
├── TestInfoApp (2 tests)
├── TestDoctor (2 tests)
├── TestConfigCommand (2 tests)
├── TestExportImport (4 tests)
├── TestVerifyApps (3 tests)
├── TestStatsCommand (2 tests)
├── TestFormatBytes (5 tests)
├── TestExtractGlobalFlags (5 tests)
└── TestDownloadAndInstallMocked (4 tests)
```


## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

---

<p align="center">
  Made with ❤️ for non-technical users everywhere
</p>
