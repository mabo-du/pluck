<p align="center">
  <h1 align="center">📦 GitHub App Installer</h1>
  <p align="center"><strong>Paste GitHub URL → Auto-install → Done!</strong></p>
</p>

<p align="center">
  <a href="https://github.com/mark/gh-install/actions/workflows/ci.yml"><img src="https://github.com/mark/gh-install/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/mark/gh-install/actions/workflows/publish-pypi.yml"><img src="https://github.com/mark/gh-install/actions/workflows/publish-pypi.yml/badge.svg" alt="Publish"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/Code%20style-ruff-EF5552" alt="Code style: ruff"></a>
  <img src="https://img.shields.io/badge/Dependencies-Zero-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/Tests-92%20passing-brightgreen" alt="92 passing tests">
  <img src="https://img.shields.io/badge/Commands-17-blue" alt="17 commands">
  <img src="https://img.shields.io/badge/Flags-11-purple" alt="11 flags">
</p>

---

A CLI tool that simplifies installing GitHub repositories and gists for users who lack technical knowledge. The tool automatically detects the project type and installs it appropriately.

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
# Install any GitHub repository
gh-install install https://github.com/user/repo

# That's it. The tool detects the project type and installs it.
```

## 🔄 How It Works

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   GitHub URL    │────▶│  Clone to    │────▶│  Detect Method  │────▶│  Install     │
│   or Gist       │     │  Temp Dir    │     │  (Auto-detect)  │     │  (8 methods) │
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
- 🔗 **GitHub & Gist URLs** — Install from any GitHub repository or gist
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
- 🔍 **Search** — Search GitHub repositories via API
- 📤 **Export/Import** — Migrate registry between machines

### Configuration
- 📁 **Custom directory** — `--dir` to override default install location
- ⚙️ **User config** — Persistent settings via config file
- 🎨 **JSON output** — `--json` for machine-readable output
- 🚫 **No colors** — `--no-color` for clean terminal output
- 🔇 **Non-interactive** — `--yes` for scripting
- 🐳 **Docker support** — Containerized installation
- 📖 **Man page** — `man gh-install` for offline docs
- 🔧 **Post-install hooks** — Custom scripts after each install

## 📖 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `install <url>` | Install from GitHub | `gh-install install https://github.com/user/repo` |
| `update <name>` | Update an installed app | `gh-install update myapp` |
| `info <name>` | Show app details | `gh-install info myapp` |
| `list` | List installed apps | `gh-install list` |
| `uninstall <name>` | Uninstall an app | `gh-install uninstall myapp` |
| `remove <name>` | Alias for uninstall | `gh-install remove myapp` |
| `verify` | Check apps validity | `gh-install verify` |
| `clean` | Remove orphaned entries | `gh-install clean --force` |
| `stats` | Show statistics | `gh-install stats` |
| `doctor` | Check tool availability | `gh-install doctor` |
| `config [key] [val]` | View/set config | `gh-install config install_dir ~/Apps` |
| `search <query>` | Search GitHub repos | `gh-install search python installer` |
| `export <file>` | Export registry | `gh-install export ~/backup.json` |
| `import <file>` | Import registry | `gh-install import ~/backup.json` |
| `completion <shell>` | Generate shell completion | `gh-install completion bash` |
| `version` | Show version | `gh-install version` |
| `help` | Show help | `gh-install help` |

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
git clone https://github.com/mark/gh-install.git
cd gh-install

# Make the script executable
chmod +x src/gh_install.py

# Optional: add to your PATH
ln -s $(pwd)/src/gh_install.py /usr/local/bin/gh-install
```

### Via pip (not yet on PyPI)

> **Note**: gh-install is not yet published to PyPI. Track [issue #NNN](https://github.com/mark/gh-install/issues) for the first PyPI release. The Docker image is published to GHCR.

To install from source instead (see [From Source](#from-source)).

```bash
# Once published:
pip install gh-install
```

### Via Docker

```bash
docker build -t gh-install .
docker run gh-install install https://github.com/user/repo
```

## ⚙️ Configuration

### Default Paths

| Constant | macOS | Linux | Description |
|----------|-------|-------|-------------|
| `DEFAULT_INSTALL_DIR` | `~/Applications` | `~/.local/opt` | Where apps are installed |
| `APP_REGISTRY_FILE` | `~/.gh-install-registry.json` | `~/.gh-install-registry.json` | App registry |
| `CONFIG_FILE` | `~/.config/gh-install/config.json` | `~/.config/gh-install/config.json` | User config |

### User Config File

```json
{
  "install_dir": "/custom/path",
  "method_priority": ["script", "python", "node", "go", "rust", "make", "binary", "download"]
}
```

Manage via CLI:

```bash
gh-install config install_dir ~/Apps
gh-install config method_priority '["python","node","binary","download"]'
```

### Post-Install Hooks

Create `~/.config/gh-install/hooks/post-install.sh` to run custom scripts after each install.

Available environment variables:
- `$GH_INSTALL_APP` — Repository name
- `$GH_INSTALL_PATH` — Installation path
- `$GH_INSTALL_METHOD` — Install method used

## 📁 Project Structure

```
gh-install/
├── src/
│   └── gh_install.py          # Main application (~1300 lines)
├── tests/
│   └── test_gh_install.py     # Test suite (73 tests)
├── docs/
│   └── IMPLEMENTATION.md      # Implementation details
├── man/
│   └── gh-install.1           # Man page
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
92 tests passing across 20 test classes:
├── TestParseGithubUrl (9 tests)
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
