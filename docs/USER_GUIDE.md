# Pluck User Guide

Welcome to the Pluck User Guide! Pluck is a zero-dependency CLI tool that automatically detects, clones, and installs applications from any Git forge (GitHub, GitLab, Codeberg, Bitbucket, self-hosted, etc.).

## Quick Start

You can install any repository by simply passing its URL to pluck:

```bash
pluck install https://github.com/user/repo
```

## How It Works

When you run `pluck install`, the tool:
1. **Clones** the repository to a temporary directory.
2. **Detects** the type of project (Script, Python, Node.js, Go, Rust, Makefile, Binary).
3. **Installs** it based on the detected method.
4. **Registers** the installation so you can update or uninstall it later.

### Install Methods

Pluck automatically uses the first applicable method:
- **Script**: Runs `bash install.sh --yes`
- **Python**: Creates a virtual environment and runs `pip install`
- **Node.js**: Runs `npm install`
- **Go**: Runs `go build`
- **Rust**: Runs `cargo build --release`
- **Makefile**: Runs `make install`
- **Binary**: Copies pre-built binaries (e.g. from GitHub Releases)
- **Download**: Simply copies the directory if no other method is found

## Commands

- `install <url>`: Install an app from a git repository.
- `update <name>`: Update an installed app to the latest version.
- `info <name>`: Show details about an installed app.
- `list`: List all installed apps and their sizes.
- `uninstall <name>` (or `remove`): Uninstall an app.
- `verify`: Check if all installed apps are still valid and present on disk.
- `clean`: Remove orphaned registry entries (apps that were manually deleted).
- `stats`: Show installation statistics.
- `pin <name>` / `unpin <name>`: Prevent or allow an app to be updated.
- `search <query>`: Search for repositories across forges.
- `export <file>` / `import <file>`: Backup and restore your installed apps.

## Configuration

You can customize Pluck by setting configurations:

```bash
pluck config install_dir ~/MyApps
```

### Post-Install Hooks

Create an executable script at `~/.config/pluck/hooks/post-install.sh`. It will run after every successful installation, with these environment variables available:
- `$PLUCK_APP`: The name of the application.
- `$PLUCK_PATH`: Where it was installed.
- `$PLUCK_METHOD`: The install method used.

## Browser Integration

Install the `pluck://` protocol handler to install apps directly from your browser:
```bash
bash scripts/install-protocol-handler.sh
```
Load the browser extension from `assets/browser-extension/` to get a right-click context menu "Install with pluck".
