<p align="center">
  <img src="assets/images/pluck_logo.png" alt="pluck" width="400"/>
  <br>
  <strong>Pluck git repos from any forge — auto-detect, auto-install, done!</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-333?logo=linux" alt="Platform: Linux | macOS">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License: MIT">
  <img src="https://img.shields.io/badge/Dependencies-Zero-brightgreen" alt="Zero dependencies">
  <img src="https://img.shields.io/badge/Tests-111%20passing-brightgreen" alt="111 passing tests">
  <img src="https://img.shields.io/badge/Forges-11%20supported-blue" alt="11 forges supported">
  <img src="https://img.shields.io/badge/Code%20style-ruff-EF5552" alt="Code style: ruff">
</p>

---

- [Quick Start](#-quick-start)
- [How It Works](#-how-it-works)
- [Features](#-features)
- [Commands](#-commands)
- [Flags](#-flags)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Development](#-development)

## 🚀 Quick Start

<p align="center">
  <img src="assets/images/pluck_chasing.png" alt="pluck chasing repos" width="600"/>
</p>

```bash
# Install from any git forge — one command, zero fuss
pluck install https://github.com/user/repo
pluck install https://gitlab.com/user/project
pluck install https://codeberg.org/user/repo
pluck install https://bitbucket.org/owner/repo

# That's it. Pluck detects the project type and installs it.
```

## 🔄 How It Works

<p align="center">
  <img src="assets/images/pluck_stalking.png" alt="pluck stalking a repo" width="600"/>
</p>

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
- 🌐 **Multi-forge search** — Search GitHub, GitLab, or Codeberg with `--forge`
- 🖱️ **Browser right-click** — Optional extension + protocol handler to install from any page
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

## 🌐 Supported Forges

| Forge | Host | Built-in | Notes |
|-------|------|----------|-------|
| **GitHub** | `github.com` | ✅ | Full support including gists |
| **GitLab** | `gitlab.com` | ✅ | HTTPS & SSH, self-hosted instances auto-detected |
| **Codeberg** | `codeberg.org` | ✅ | Powered by Forgejo |
| **Bitbucket** | `bitbucket.org` | ✅ | Both cloud & self-hosted |
| **SourceHut** | `git.sr.ht` | ✅ | Supports `~user` prefix |
| **Gitea** | `gitea.com` | ✅ | Any Gitea instance works |
| **Gogs** | `gogs.io` | ✅ | Lightweight git service |
| **Pagure** | `pagure.io` | ✅ | Fedora's git hosting |
| **Forgejo** | `forgejo.org` | ✅ | Self-hosted friendly |
| **Any other hosted git** | Any domain | ✅ | Parses as `generic` type |
| **Self-hosted** | Any IP/domain | ✅ | SSH & HTTPS both supported |

Any git hosting platform that follows the standard `host/owner/repo` URL pattern works — no plugin or config needed.

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
git clone https://gitlab.com/mabodu/pluck.git
cd pluck

# Install via pip
pip install -e .

# Or run directly
./src/gh_install.py install https://gitlab.com/user/project
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
- `$PLUCK_APP` — Repository name
- `$PLUCK_PATH` — Installation path
- `$PLUCK_METHOD` — Install method used

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
111 tests passing across 24 test classes:
├── TestParseRepoUrl (22 tests)
├── TestGistUrl (7 tests) — includes GitLab snippets
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
