#!/usr/bin/env python3
"""
GitHub App Installer - Paste URL, Auto-Install, Done!
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

__version__ = "0.1.0"

# Configuration
DEFAULT_INSTALL_DIR_MACOS = Path.home() / "Applications"
DEFAULT_INSTALL_DIR_LINUX = Path.home() / ".local" / "opt"
if sys.platform == "darwin":
    DEFAULT_INSTALL_DIR = DEFAULT_INSTALL_DIR_MACOS
else:
    DEFAULT_INSTALL_DIR = DEFAULT_INSTALL_DIR_LINUX
APP_REGISTRY_FILE = Path.home() / ".pluck-registry.json"
_CONFIG_OLD_REGISTRY = Path.home() / ".gh-install-registry.json"
CONFIG_FILE = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pluck" / "config.json"
)
_CONFIG_OLD_DIR = Path.home() / ".config" / "gh-install"
SHARED_PATHS = {
    Path.home() / "go" / "bin",
    Path.home() / "Applications",
    Path.home() / ".local" / "opt",
    Path.home() / "bin",
}
VALID_METHODS = {"script", "binary", "python", "node", "go", "rust", "make", "download"}
GIST_PATTERN = r"gist\.github\.com[:/]([^/]+)/([a-f0-9]+)"

# Color auto-detection
_COLORS_ENABLED = sys.stdout.isatty()


def _enable_colors(enabled: bool) -> None:
    global _COLORS_ENABLED
    _COLORS_ENABLED = enabled


def _load_user_config():
    """Load user config file if it exists."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_user_config(config):
    """Save user config file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def print_usage():
    commands = [
        ("install <url> [opts]", "Install from any git repo URL"),
        ("update <name> [--force]", "Update an installed app"),
        ("info <name>", "Show app details"),
        ("list", "List installed apps"),
        ("uninstall <name> [--force]", "Uninstall an app"),
        ("remove <name> [--force]", "Alias for uninstall"),
        ("verify", "Check installed apps validity"),
        ("clean [--force]", "Remove orphaned registry entries"),
        ("stats", "Show installation statistics"),
        ("doctor", "Check tool availability"),
        ("config [key] [value]", "View/set config"),
        ("search <query>", "Search GitHub repos (other forges coming)"),
        ("export <file>", "Export registry"),
        ("import <file>", "Import registry"),
        ("completion <shell>", "Generate shell completion"),
        ("version", "Show version"),
        ("help", "Show this help"),
    ]
    opts = [
        ("--dir <path>", "Install to a custom directory"),
        ("--dry-run", "Show what would be done without making changes"),
        ("--force", "Skip confirmation prompts"),
        ("--shallow", "Use shallow clone (--depth 1)"),
        ("--ref <ref>", "Clone a specific branch or tag"),
        ("--method <method>", "Force install method"),
        ("--yes", "Non-interactive mode (alias for --force)"),
        ("--json", "Output in JSON format (for scripting)"),
        ("--no-color", "Disable colored output"),
        ("--timeout <secs>", "Timeout for git clone in seconds"),
        ("--retries <n>", "Number of retries for failed git clone"),
    ]

    print("Usage:")
    print("  pluck <command> [args] [options]")
    print()
    print("Commands:")
    max_cmd = max(len(c[0]) for c in commands)
    for cmd, desc in commands:
        print(f"  {cmd:<{max_cmd}}  {desc}")
    print()
    print("Options:")
    max_opt = max(len(o[0]) for o in opts)
    for opt, desc in opts:
        print(f"  {opt:<{max_opt}}  {desc}")


def _parse_gist_url(url):
    """Extract gist info from a gist URL (currently GitHub Gists only)."""
    match = re.search(GIST_PATTERN, url)
    if match:
        return {
            "host": "gist.github.com",
            "host_type": "github",
            "owner": match.group(1),
            "repo": f"gist-{match.group(2)}",
            "url": f"https://gist.github.com/{match.group(1)}/{match.group(2)}.git",
            "is_gist": True,
        }
    return None


def _completion_script(shell):
    """Return shell completion script for bash or zsh."""
    if shell == "bash":
        return """_pluck_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local commands="install update info list uninstall doctor config search export import completion version help"

    case "${COMP_WORDS[1]}" in
        install)
            if [[ "$prev" == "--dir" ]]; then
                _filedir -d
            else
                opts="--dir --dry-run --force --shallow --ref --method --yes"
                COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
            fi
            return
            ;;
        update|uninstall|info)
            local apps
            apps=$(python3 -c "
import json, os
p = os.path.expanduser('~/.pluck-registry.json')
if os.path.exists(p):
    data = json.load(open(p))
    print(' '.join(data.get('apps', {}).keys()))
" 2>/dev/null)
            COMPREPLY=( $(compgen -W "$apps --force --dry-run" -- "$cur") )
            return
            ;;
        list|version|help|doctor)
            return
            ;;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh" -- "$cur") )
            return
            ;;
        config)
            COMPREPLY=( $(compgen -W "install_dir method_priority" -- "$cur") )
            return
            ;;
        *)
            COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
            return
            ;;
    esac
}
complete -F _pluck_completion pluck
"""
    elif shell == "zsh":
        return """#compdef pluck
_pluck() {
    local -a commands
    commands=(
        'install:Install from any git repo URL'
        'update:Update an installed app'
        'info:Show app details'
        'list:List installed apps'
        'uninstall:Uninstall an app'
        'doctor:Check tool availability'
        'config:View/set config'
        'search:Search GitHub repos'
        'export:Export registry'
        'import:Import registry'
        'completion:Generate shell completion'
        'version:Show version'
        'help:Show help'
    )

    _arguments -C \\
        '1: :->command' \\
        '*: :->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[1] in
                install)
                    _arguments \\
                        '--dir[Install to custom directory]:directory:_directories' \\
                        '--dry-run[Preview without changes]' \\
                        '--force[Skip confirmation]' \\
                        '--shallow[Use shallow clone]' \\
                        '--ref[Clone specific branch/tag]:ref:' \\
                        '--method[Force install method]:(script python node go rust' \
                        'make binary download)' \
                        '--yes[Non-interactive mode]'
                    ;;
                update|uninstall|info)
                    local apps
                    apps=($(python3 -c "
import json, os
p = os.path.expanduser('~/.pluck-registry.json')
if os.path.exists(p):
    data = json.load(open(p))
    print(' '.join(data.get('apps', {}).keys()))
" 2>/dev/null))
                    _arguments \\
                        '--force[Skip confirmation]' \\
                        '--dry-run[Preview without changes]' \\
                        "1:app:($apps)"
                    ;;
                completion)
                    _arguments '1:shell:(bash zsh)'
                    ;;
            esac
            ;;
    esac
}
_pluck
"""
    else:
        return None


def _get_app_names():
    """Return list of installed app names for completion."""
    try:
        if APP_REGISTRY_FILE.exists():
            with open(APP_REGISTRY_FILE) as f:
                data = json.load(f)
            return list(data.get("apps", {}).keys())
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _sanitize_repo_name(name):
    """Reject repo names that could cause path traversal."""
    if ".." in name or name.startswith("/") or name.startswith("\\"):
        return None
    return name


class Colors:
    GREEN = "\033[92m" if _COLORS_ENABLED else ""
    YELLOW = "\033[93m" if _COLORS_ENABLED else ""
    RED = "\033[91m" if _COLORS_ENABLED else ""
    BLUE = "\033[94m" if _COLORS_ENABLED else ""
    CYAN = "\033[96m" if _COLORS_ENABLED else ""
    END = "\033[0m" if _COLORS_ENABLED else ""


def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.GREEN}  {text}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def _detect_host_type(host):
    """Identify the forge type from a git hosting domain."""
    host_lower = host.lower().removeprefix("www.")
    forge_map = {
        "github.com": "github",
        "gitlab.com": "gitlab",
        "codeberg.org": "codeberg",
        "bitbucket.org": "bitbucket",
        "git.sr.ht": "sourcehut",
        "gitea.com": "gitea",
        "gogs.io": "gogs",
        "pagure.io": "pagure",
        "forgejo.org": "forgejo",
    }
    return forge_map.get(host_lower, "generic")


def parse_repo_url(url):
    """Extract owner/repo from any git hosting URL.

    Supports GitHub, GitLab, Codeberg, Bitbucket, SourceHut, Gitea,
    self-hosted instances, and any other standard git hosting.
    """
    # Try gist detection first
    gist_info = _parse_gist_url(url)
    if gist_info:
        return gist_info

    # Normalize: strip trailing slash
    url = url.rstrip("/")

    patterns = [
        # HTTPS: https://host/owner/repo[.git][/extra/path]
        r"https?://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
        # SSH git@host:owner/repo[.git]
        r"git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?$",
        # SSH ssh://git@host/owner/repo[.git]
        r"ssh://git@([^/]+)/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
        # git protocol: git://host/owner/repo[.git]
        r"git://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            host = match.group(1)
            owner = match.group(2)
            repo = match.group(3)
            host_type = _detect_host_type(host)
            normalized_url = f"https://{host}/{owner}/{repo}"
            return {
                "host": host,
                "host_type": host_type,
                "owner": owner,
                "repo": repo,
                "url": normalized_url,
                "is_gist": False,
            }

    return None


# Backward-compat alias — remove in a future release
parse_github_url = parse_repo_url


def detect_install_method(repo_path, method_priority=None):
    """Detect the best installation method for a repository"""
    if method_priority:
        methods = [m for m in method_priority if m in VALID_METHODS]
    else:
        methods = ["script", "binary", "python", "node", "go", "rust", "make", "download"]

    for method in methods:
        if method == "script" and (repo_path / "install.sh").exists():
            return "script"
        if method == "binary" and (
            (repo_path / "release" / "linux").exists()
            or (repo_path / "bin" / "linux").exists()
            or list(repo_path.glob("*.AppImage"))
            or list(repo_path.glob("*.deb"))
        ):
            return "binary"
        if method == "python" and (
            (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists()
        ):
            return "python"
        if method == "node" and (repo_path / "package.json").exists():
            return "node"
        if method == "go" and ((repo_path / "go.mod").exists() or list(repo_path.glob("*.go"))):
            return "go"
        if method == "rust" and (repo_path / "Cargo.toml").exists():
            return "rust"
        if method == "make" and (repo_path / "Makefile").exists():
            return "make"

    return "download"


def install_script(repo_path, install_dir):
    """Install using install.sh script"""
    print("  Running install.sh script...")

    try:
        subprocess.run(["bash", "install.sh", "--yes"], cwd=repo_path, check=True)
        print_success("Installation script completed")
        return install_dir
    except subprocess.CalledProcessError:
        print_warning("Install script failed, copying directory instead")
        return install_binary(repo_path, install_dir)


def install_python(repo_path, install_dir):
    """Install Python project"""
    print("  Installing Python project...")

    try:
        app_dir = install_dir / repo_path.name
        venv_path = app_dir / ".venv"
        venv_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

        pip_path = venv_path / "bin" / "pip"
        subprocess.run([str(pip_path), "install", "-e", str(repo_path)], check=True)

        print_success(f"Installed to {app_dir}")

        if (venv_path / "bin" / repo_path.name).exists():
            bin_file = venv_path / "bin" / repo_path.name
            link_path = install_dir / repo_path.name
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
            link_path.symlink_to(bin_file)
            print_success(f"Created symlink: {link_path}")
            return app_dir

        return app_dir
    except subprocess.CalledProcessError as e:
        print_error(f"Python installation failed: {e}")
        return None


def install_node(repo_path, install_dir):
    """Install Node.js project"""
    print("  Installing Node.js project...")

    try:
        dest = install_dir / repo_path.name
        ignore = shutil.ignore_patterns("node_modules", ".git")
        shutil.copytree(repo_path, dest, dirs_exist_ok=True, ignore=ignore)

        subprocess.run(["npm", "install"], cwd=dest, check=True)

        print_success(f"Installed to {dest}")
        return dest
    except subprocess.CalledProcessError as e:
        print_error(f"Node.js installation failed: {e}")
        return None


def install_go(repo_path, install_dir):
    """Install Go project"""
    print("  Installing Go project...")

    try:
        subprocess.run(
            ["go", "build", "-o", str(install_dir / repo_path.name), "."],
            cwd=repo_path,
            check=True,
        )

        binary_path = install_dir / repo_path.name
        if binary_path.exists():
            print_success(f"Installed to {binary_path}")
            return binary_path

        return install_dir
    except subprocess.CalledProcessError as e:
        print_error(f"Go installation failed: {e}")
        return None


def install_rust(repo_path, install_dir):
    """Install Rust project"""
    print("  Installing Rust project...")

    try:
        subprocess.run(["cargo", "build", "--release"], cwd=repo_path, check=True)

        target_dir = repo_path / "target" / "release"
        binaries = list(target_dir.glob("*"))
        binaries = [b for b in binaries if b.is_file() and not b.suffix]

        if binaries:
            for binary in binaries:
                dest = install_dir / binary.name
                shutil.copy2(binary, dest)
                print_success(f"Installed {binary.name} to {dest}")

            return install_dir

        return None
    except subprocess.CalledProcessError as e:
        print_error(f"Rust installation failed: {e}")
        return None


def _is_executable(item):
    """Check if a file is likely an executable binary or script."""
    if not item.is_file():
        return False
    if os.access(item, os.X_OK):
        return True
    executable_extensions = {".exe", ".bin", ".sh", ".py", ".pl", ".rb", ".app"}
    if item.suffix.lower() in executable_extensions:
        return True
    if "." not in item.name:
        return True
    return False


def install_binary(repo_path, install_dir):
    """Install pre-built binary"""
    print("  Installing pre-built binary...")

    binary_dirs = ["release", "bin", "dist"]

    for dir_name in binary_dirs:
        binary_dir = repo_path / dir_name
        if binary_dir.exists():
            for item in binary_dir.iterdir():
                if _is_executable(item):
                    dest = install_dir / item.name
                    shutil.copy2(item, dest)
                    print_success(f"Installed {item.name} to {dest}")

            return install_dir

    # Fallback: copy entire directory
    dest = install_dir / repo_path.name
    shutil.copytree(repo_path, dest, dirs_exist_ok=True)
    print_success(f"Installed to {dest}")
    return dest


def install_make(repo_path, install_dir):
    """Install using Makefile"""
    print("  Installing using Makefile...")

    try:
        subprocess.run(["make", "install", f"PREFIX={install_dir}"], cwd=repo_path, check=True)
        print_success(f"Installed to {install_dir}")
        return install_dir
    except subprocess.CalledProcessError:
        subprocess.run(["make"], cwd=repo_path, check=True)
        return install_binary(repo_path, install_dir)


def _get_disk_size(path):
    """Get disk size of a path in human-readable format."""
    try:
        total = 0
        p = Path(path)
        if p.is_file():
            total = p.stat().st_size
        elif p.is_dir():
            for dirpath, _, filenames in os.walk(p):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
        if total >= 1024 * 1024 * 1024:
            return f"{total / (1024 * 1024 * 1024):.1f} GB"
        elif total >= 1024 * 1024:
            return f"{total / (1024 * 1024):.1f} MB"
        elif total >= 1024:
            return f"{total / 1024:.1f} KB"
        return f"{total} B"
    except OSError:
        return "unknown"


def download_and_install(
    repo_url,
    install_dir=None,
    dry_run=False,
    shallow=False,
    ref=None,
    method_override=None,
    timeout=None,
    retries=0,
):
    """Download and install a repository from any git hosting URL"""

    if install_dir is None:
        user_config = _load_user_config()
        config_dir = user_config.get("install_dir")
        if config_dir:
            install_dir = Path(config_dir).expanduser()
        else:
            install_dir = DEFAULT_INSTALL_DIR

    # Parse repository URL
    repo_info = parse_repo_url(repo_url)
    if not repo_info:
        print_error(f"Invalid repository URL: {repo_url}")
        return None

    repo_type = "Gist" if repo_info.get("is_gist") else "Repository"
    host_label = repo_info.get("host", "unknown")
    print(f"  {repo_type}: {repo_info['owner']}/{repo_info['repo']} ({host_label})")

    # Validate repo name to prevent path traversal
    safe_name = _sanitize_repo_name(repo_info["repo"])
    if not safe_name:
        print_error(f"Invalid repository name: {repo_info['repo']}")
        return None

    # Dry-run check before doing any I/O
    if dry_run:
        print(f"  [DRY RUN] Would install to: {install_dir / safe_name}")
        print(f"  [DRY RUN] Would use method: {method_override or '(auto-detected after clone)'}")
        return install_dir / safe_name

    # Create install directory if it doesn't exist
    install_dir.mkdir(parents=True, exist_ok=True)

    # Clone to temp directory
    temp_dir = Path(tempfile.mkdtemp())
    repo_path = temp_dir / safe_name

    clone_cmd = ["git", "clone"]
    if shallow:
        clone_cmd.extend(["--depth", "1"])
    if ref:
        clone_cmd.extend(["--branch", ref])
    clone_cmd.extend([repo_info["url"], str(repo_path)])

    attempts = retries + 1
    for attempt in range(attempts):
        if attempts > 1:
            print(f"  Downloading... (attempt {attempt + 1}/{attempts})")
        else:
            print("  Downloading...")

        try:
            subprocess.run(clone_cmd, check=True, timeout=timeout)
            break
        except subprocess.TimeoutExpired:
            print_error(f"Clone timed out after {timeout}s")
            if attempt < attempts - 1:
                time.sleep(2)
                continue
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        except subprocess.CalledProcessError as e:
            if attempt < attempts - 1:
                print_warning("Clone failed, retrying...")
                time.sleep(2)
                continue
            print_error(f"Failed to clone repository: {repo_info['url']}")
            if e.stderr:
                print_error(e.stderr.strip())
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    # Detect install method
    user_config = _load_user_config()
    method_priority = user_config.get("method_priority")
    install_method = method_override or detect_install_method(repo_path, method_priority)
    print(f"  Detected install method: {install_method}")

    # Install based on method
    install_funcs = {
        "python": install_python,
        "node": install_node,
        "go": install_go,
        "rust": install_rust,
        "binary": install_binary,
        "make": install_make,
        "script": install_script,
        "download": install_binary,
    }

    install_func = install_funcs.get(install_method, install_binary)
    installed_path = install_func(repo_path, install_dir)

    # Clean up temp directory
    shutil.rmtree(temp_dir)

    # Register the installation
    if installed_path:
        register_app(repo_info["repo"], repo_url, installed_path, install_method)
        # Post-install summary
        print()
        print(f"  {Colors.CYAN}Summary:{Colors.END}")
        print(f"    Name:     {repo_info['repo']}")
        print(f"    Method:   {install_method}")
        print(f"    Location: {installed_path}")
        print(f"    Size:     {_get_disk_size(installed_path)}")
        return installed_path

    return None


def update_app(
    repo_name,
    install_dir=None,
    dry_run=False,
    force=False,
    shallow=False,
    ref=None,
    timeout=None,
    retries=0,
):
    """Update an installed application"""
    registry = load_registry()

    if repo_name not in registry["apps"]:
        print_error(f"{repo_name} is not installed")
        return False

    app_info = registry["apps"][repo_name]
    url = app_info["url"]
    old_path = Path(app_info["path"])

    print_header(f"Updating {repo_name}")
    print(f"  Current: {app_info['installed_at']}")
    print(f"  URL: {url}")

    if dry_run:
        print(f"  [DRY RUN] Would re-install from: {url}")
        print(f"  [DRY RUN] Would update: {old_path}")
        return True

    # Remove old installation
    if old_path.exists() and old_path.resolve() not in SHARED_PATHS:
        if old_path.is_file():
            old_path.unlink()
        else:
            shutil.rmtree(old_path, ignore_errors=True)

    # Remove from registry before re-installing
    del registry["apps"][repo_name]
    save_registry(registry)

    # Re-install
    target_dir = old_path.parent if old_path.parent.exists() else install_dir
    result = download_and_install(
        url,
        install_dir=target_dir,
        shallow=shallow,
        ref=ref,
        timeout=timeout,
        retries=retries,
    )

    if result:
        print_success(f"Updated {repo_name}")
        return True
    else:
        print_error(f"Failed to update {repo_name}")
        # Restore old registry entry
        registry["apps"][repo_name] = app_info
        save_registry(registry)
        return False


def info_app(repo_name, json_output=False):
    """Show detailed info about an installed app"""
    registry = load_registry()

    if repo_name not in registry["apps"]:
        if json_output:
            print(json.dumps({"error": f"{repo_name} is not installed"}))
        else:
            print_error(f"{repo_name} is not installed")
        return False

    app_info = registry["apps"][repo_name]
    install_path = Path(app_info["path"])

    if json_output:
        data = {
            "name": repo_name,
            "url": app_info["url"],
            "method": app_info["method"],
            "path": app_info["path"],
            "installed_at": app_info["installed_at"],
            "size": _get_disk_size(install_path),
            "exists": install_path.exists(),
        }
        print(json.dumps(data, indent=2))
        return True

    print_header(f"App Info: {repo_name}")
    labels = ["URL", "Method", "Path", "Installed", "Size", "Exists"]
    values = [
        app_info["url"],
        app_info["method"],
        app_info["path"],
        app_info["installed_at"],
        _get_disk_size(install_path),
        "Yes" if install_path.exists() else "No (files may have been moved)",
    ]
    max_label = max(len(label) for label in labels)
    for label, value in zip(labels, values):
        print(f"  {Colors.CYAN}{label}:{Colors.END}{' ' * (max_label - len(label) + 1)}{value}")

    return True


def doctor(json_output=False):
    """Check if all required and optional tools are available"""
    tools = {
        "git": ("Required", "Cloning repositories"),
        "python3": ("Required", "Running this tool"),
        "npm": ("Optional", "Node.js project installs"),
        "go": ("Optional", "Go project installs"),
        "cargo": ("Optional", "Rust project installs"),
        "make": ("Optional", "Makefile-based installs"),
    }

    all_ok = True
    results = []
    for tool, (req, purpose) in tools.items():
        # Check the canonical name, but fall back for python3 → python
        exe = tool
        found = bool(shutil.which(exe))
        if not found and exe == "python3":
            found = bool(shutil.which("python"))
        results.append({"tool": tool, "required": req, "found": found, "purpose": purpose})
        results.append({"tool": tool, "required": req, "found": found, "purpose": purpose})
        if not found and req == "Required":
            all_ok = False

    if json_output:
        print(json.dumps({"tools": results, "all_ok": all_ok}, indent=2))
        return all_ok

    print_header("Doctor — Tool Availability Check")

    for r in results:
        status = f"{Colors.GREEN}✓{Colors.END}" if r["found"] else f"{Colors.RED}✗{Colors.END}"
        label = f"{Colors.YELLOW}[{r['required']}]{Colors.END}"
        print(f"  {status} {r['tool']:<10} {label:<12} {r['purpose']}")

    print()
    if all_ok:
        print_success("All required tools are available")
    else:
        print_error("Some required tools are missing")

    return all_ok


def config_command(key=None, value=None):
    """View or set configuration values"""
    config = _load_user_config()

    if key is None:
        # Show all config
        print_header("Configuration")
        if not config:
            print_warning("No configuration set")
            print(f"\n  Config file: {CONFIG_FILE}")
            print(f"  Install dir (default): {DEFAULT_INSTALL_DIR}")
        else:
            for k, v in config.items():
                print(f"  {k}: {v}")
            print(f"\n  Config file: {CONFIG_FILE}")
        return

    if value is None:
        # Show specific key
        if key in config:
            print(f"  {key}: {config[key]}")
        else:
            print_warning(f"Config key '{key}' is not set")
        return

    # Set value
    config[key] = value
    _save_user_config(config)
    print_success(f"Set {key} = {value}")


def search_github(query, limit=10):
    """Search repositories using the GitHub API (GitHub-only; other forges coming)."""
    print(f"  Searching GitHub for '{query}'...")

    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={limit}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_error(f"Search failed: {e}")
        return

    items = data.get("items", [])
    if not items:
        print_warning("No results found")
        return

    print_header(f"Search Results for '{query}' ({len(items)} found)")
    for i, repo in enumerate(items, 1):
        name = repo["full_name"]
        stars = repo["stargazers_count"]
        desc = repo.get("description") or "No description"
        lang = repo.get("language") or "Unknown"
        print(f"  {i}. {Colors.GREEN}{name}{Colors.END}")
        print(f"     {desc}")
        print(f"     {Colors.CYAN}★{Colors.END} {stars:,}  |  Language: {lang}")
        print(f"     URL: {repo['html_url']}")
        print()


def export_registry(filepath):
    """Export the app registry to a file"""
    registry = load_registry()
    path = Path(filepath).expanduser()
    with open(path, "w") as f:
        json.dump(registry, f, indent=2)
    print_success(f"Exported {len(registry['apps'])} apps to {path}")


def import_registry(filepath):
    """Import the app registry from a file"""
    path = Path(filepath).expanduser()
    if not path.exists():
        print_error(f"File not found: {path}")
        return False

    with open(path) as f:
        data = json.load(f)

    if "apps" not in data:
        print_error("Invalid registry file format")
        return False

    registry = load_registry()
    imported = 0
    for name, info in data["apps"].items():
        if name not in registry["apps"]:
            registry["apps"][name] = info
            imported += 1
        else:
            print_warning(f"Skipping {name} (already installed)")

    save_registry(registry)
    print_success(f"Imported {imported} new apps")
    return True


def register_app(repo_name, repo_url, install_path, install_method, skip_hook=False):
    """Register an installed application"""

    registry = load_registry()

    registry["apps"][repo_name] = {
        "url": repo_url,
        "path": str(install_path),
        "method": install_method,
        "installed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_registry(registry)
    print_success(f"Registered {repo_name}")

    if not skip_hook:
        _run_post_install_hook(repo_name, str(install_path), install_method)


def _run_post_install_hook(repo_name, install_path, method):
    """Run user-defined post-install hook if configured."""
    hook_dir = CONFIG_FILE.parent / "pluck" / "hooks"
    hook_file = hook_dir / "post-install.sh"

    if hook_file.exists():
        env = os.environ.copy()
        env["GH_INSTALL_APP"] = repo_name
        env["GH_INSTALL_PATH"] = install_path
        env["GH_INSTALL_METHOD"] = method

        try:
            subprocess.run(["bash", str(hook_file)], env=env, check=True)
        except subprocess.CalledProcessError as e:
            print_warning(f"Post-install hook failed with exit code {e.returncode}")
        except FileNotFoundError:
            print_warning("Post-install hook requires bash")


def clean_registry(dry_run=False, force=False, json_output=False):
    """Remove orphaned registry entries (apps whose paths no longer exist)"""
    registry = load_registry()
    orphaned = []

    for name, info in registry["apps"].items():
        install_path = Path(info["path"])
        if not install_path.exists():
            orphaned.append({"name": name, "path": info["path"]})

    if not orphaned:
        if json_output:
            print(json.dumps({"orphaned": []}))
        else:
            print_success("No orphaned entries found")
        return 0

    if json_output:
        data = {"orphaned": orphaned, "count": len(orphaned)}
        if dry_run:
            data["dry_run"] = True
        print(json.dumps(data, indent=2))
        return len(orphaned)

    print_header(f"Found {len(orphaned)} orphaned entries")
    for entry in orphaned:
        print(f"  {Colors.RED}{entry['name']}{Colors.END} — {entry['path']} (missing)")

    if dry_run:
        print(f"\n  {Colors.YELLOW}[DRY RUN] Would remove {len(orphaned)} entries{Colors.END}")
        return len(orphaned)

    if not force:
        confirm = input(f"\nRemove {len(orphaned)} orphaned entries? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled")
            return 0

    for entry in orphaned:
        del registry["apps"][entry["name"]]

    save_registry(registry)
    print_success(f"Removed {len(orphaned)} orphaned entries")
    return len(orphaned)


def load_registry():
    """Load the app registry"""
    if APP_REGISTRY_FILE.exists():
        with open(APP_REGISTRY_FILE) as f:
            return json.load(f)

    return {"apps": {}}


def save_registry(registry):
    """Save the app registry"""
    with open(APP_REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


def list_installed(json_output=False):
    """List all installed applications"""
    registry = load_registry()

    if not registry["apps"]:
        if json_output:
            print(json.dumps({"apps": []}))
        else:
            print_warning("No applications installed yet")
        return

    if json_output:
        apps = []
        for name, info in registry["apps"].items():
            install_path = Path(info["path"])
            apps.append(
                {
                    "name": name,
                    "url": info["url"],
                    "method": info["method"],
                    "path": info["path"],
                    "size": _get_disk_size(install_path),
                    "exists": install_path.exists(),
                    "installed_at": info["installed_at"],
                }
            )
        print(json.dumps({"apps": apps}, indent=2))
        return

    print_header(f"Installed Applications ({len(registry['apps'])})")

    for name, info in registry["apps"].items():
        install_path = Path(info["path"])
        size = _get_disk_size(install_path)
        exists = "✓" if install_path.exists() else "✗"
        print(f"\n{Colors.GREEN}{name}{Colors.END}  [{exists}]")
        print(f"  URL: {info['url']}")
        print(f"  Method: {info['method']}")
        print(f"  Path: {info['path']}")
        print(f"  Size: {size}")
        print(f"  Installed: {info['installed_at']}")


def uninstall_app(repo_name, force=False):
    """Uninstall an application"""
    registry = load_registry()

    if repo_name not in registry["apps"]:
        print_error(f"{repo_name} is not installed")
        return False

    app_info = registry["apps"][repo_name]

    # Ask for confirmation
    if not force:
        confirm = input(f"Uninstall {repo_name}? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled")
            return False

    # Remove installed files — but never delete shared system directories
    install_path = Path(app_info["path"])
    if install_path.resolve() in SHARED_PATHS or install_path.resolve() == Path.home():
        print_error(f"Refusing to uninstall: {install_path} is a shared directory")
        print_warning("Remove files from this directory manually instead")
        return False

    if install_path.exists():
        if install_path.is_file():
            install_path.unlink()
        else:
            shutil.rmtree(install_path, ignore_errors=True)

    # Remove from registry
    del registry["apps"][repo_name]
    save_registry(registry)

    print_success(f"Uninstalled {repo_name}")
    return True


def _parse_args(args):
    """Parse all CLI flags from a list of arguments."""
    install_dir = None
    dry_run = False
    force = False
    yes = False
    shallow = False
    ref = None
    method = None
    json_output = False
    no_color = False
    timeout = None
    retries = 0
    urls = []

    i = 0
    while i < len(args):
        if args[i] == "--dir" and i + 1 < len(args):
            install_dir = Path(args[i + 1]).expanduser()
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        elif args[i] == "--force":
            force = True
            i += 1
        elif args[i] == "--yes":
            yes = True
            i += 1
        elif args[i] == "--shallow":
            shallow = True
            i += 1
        elif args[i] == "--ref" and i + 1 < len(args):
            ref = args[i + 1]
            i += 2
        elif args[i] == "--method" and i + 1 < len(args):
            method = args[i + 1]
            i += 2
        elif args[i] == "--json":
            json_output = True
            i += 1
        elif args[i] == "--no-color":
            no_color = True
            i += 1
        elif args[i] == "--timeout" and i + 1 < len(args):
            try:
                timeout = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--retries" and i + 1 < len(args):
            try:
                retries = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            urls.append(args[i])
            i += 1

    if yes:
        force = True
    if no_color:
        _enable_colors(False)

    return install_dir, dry_run, force, shallow, ref, method, json_output, timeout, retries, urls


def verify_apps(json_output=False):
    """Check if installed apps are still valid (files exist, not corrupted)."""
    registry = load_registry()
    results = []

    for name, info in registry["apps"].items():
        install_path = Path(info["path"])
        exists = install_path.exists()
        size = _get_disk_size(install_path) if exists else "N/A"
        results.append({
            "name": name,
            "url": info["url"],
            "path": info["path"],
            "exists": exists,
            "size": size,
            "installed_at": info["installed_at"],
        })

    valid_count = sum(1 for r in results if r["exists"])
    invalid_count = len(results) - valid_count

    if json_output:
        print(json.dumps({
            "total": len(results),
            "valid": valid_count,
            "invalid": invalid_count,
            "apps": results,
        }, indent=2))
        return valid_count == len(results)

    print_header(f"Verification ({len(results)} apps)")
    for r in results:
        status = f"{Colors.GREEN}✓{Colors.END}" if r["exists"] else f"{Colors.RED}✗{Colors.END}"
        print(f"  {status} {Colors.CYAN}{r['name']}{Colors.END} — {r['path']} ({r['size']})")

    print()
    if invalid_count == 0:
        print_success(f"All {valid_count} apps are valid")
    else:
        print_warning(f"{valid_count} valid, {invalid_count} missing")

    return valid_count == len(results)


def stats_command(json_output=False):
    """Show installation statistics."""
    registry = load_registry()
    apps = registry["apps"]

    total = len(apps)
    valid = 0
    orphaned = 0
    total_size = 0
    method_counts = {}

    for name, info in apps.items():
        install_path = Path(info["path"])
        method = info.get("method", "unknown")
        method_counts[method] = method_counts.get(method, 0) + 1

        if install_path.exists():
            valid += 1
            try:
                if install_path.is_file():
                    total_size += install_path.stat().st_size
                elif install_path.is_dir():
                    for dirpath, _, filenames in os.walk(install_path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if not os.path.islink(fp):
                                total_size += os.path.getsize(fp)
            except OSError:
                pass
        else:
            orphaned += 1

    if json_output:
        print(json.dumps({
            "total_apps": total,
            "valid": valid,
            "orphaned": orphaned,
            "total_size_bytes": total_size,
            "total_size_human": _format_bytes(total_size),
            "by_method": method_counts,
        }, indent=2))
        return

    print_header("Installation Statistics")
    print(f"  Total apps:  {total}")
    print(f"  Valid:       {valid}")
    print(f"  Orphaned:    {orphaned}")
    print(f"  Total size:  {_format_bytes(total_size)}")
    print()
    print(f"  {Colors.CYAN}By Method:{Colors.END}")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"    {method:<10} {count}")


def _format_bytes(size):
    """Format byte count into human-readable string."""
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
    elif size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    elif size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _extract_global_flags(args):
    """Extract global flags (--json, --no-color) from an arg list, returning (cleaned_args, json_output, no_color)."""
    json_output = False
    no_color = False
    cleaned = []
    i = 0
    while i < len(args):
        if args[i] == "--json":
            json_output = True
        elif args[i] == "--no-color":
            no_color = True
        else:
            cleaned.append(args[i])
        i += 1
    if no_color:
        _enable_colors(False)
    return cleaned, json_output


def _migrate_old_registry():
    """Migrate from old .gh-install-registry.json to .pluck-registry.json."""
    if _CONFIG_OLD_REGISTRY.exists() and not APP_REGISTRY_FILE.exists():
        try:
            data = _CONFIG_OLD_REGISTRY.read_text()
            APP_REGISTRY_FILE.write_text(data)
            _CONFIG_OLD_REGISTRY.unlink()
            print_warning("Migrated registry from .gh-install-registry.json to .pluck-registry.json")
        except OSError:
            pass
    if _CONFIG_OLD_DIR.exists() and not CONFIG_FILE.exists():
        try:
            config_data = _CONFIG_OLD_DIR / "config.json"
            if config_data.exists():
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                config_data.rename(CONFIG_FILE)
                _CONFIG_OLD_DIR.rmdir()
                print_warning("Migrated config from ~/.config/gh-install/ to ~/.config/pluck/")
        except OSError:
            pass


def main():
    """Main entry point"""
    # Auto-migrate from old gh-install paths
    _migrate_old_registry()

    # Initialize flags shared across command branches
    json_output = False
    force = False
    dry_run = False

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    # Handle global --version flag before command dispatch
    if sys.argv[1] in ("--version", "-v"):
        print(f"pluck v{__version__}")
        sys.exit(0)

    command = sys.argv[1]

    if command == "install":
        install_dir, dry_run, force, shallow, ref, method, json_output, timeout, retries, urls = (
            _parse_args(sys.argv[2:])
        )

        if not urls:
            print_error("Please provide a repository URL")
            sys.exit(1)

        if method and method not in VALID_METHODS:
            print_error(f"Invalid method: {method}. Valid: {', '.join(sorted(VALID_METHODS))}")
            sys.exit(1)

        if dry_run:
            print_header("Dry Run — No changes will be made")

        for url in urls:
            print(f"\nInstalling: {url}")
            download_and_install(
                url,
                install_dir=install_dir,
                dry_run=dry_run,
                shallow=shallow,
                ref=ref,
                method_override=method,
                timeout=timeout,
                retries=retries,
            )

    elif command == "update":
        install_dir, dry_run, force, shallow, ref, method, json_output, timeout, retries, rest = (
            _parse_args(sys.argv[2:])
        )
        if not rest:
            print_error("Please provide an app name")
            sys.exit(1)

        if dry_run:
            print_header("Dry Run — No changes will be made")

        for name in rest:
            update_app(
                name,
                install_dir=install_dir,
                dry_run=dry_run,
                force=force,
                shallow=shallow,
                ref=ref,
                timeout=timeout,
                retries=retries,
            )

    elif command == "info":
        rest, json_output = _extract_global_flags(sys.argv[2:])
        if not rest:
            print_error("Please provide an app name")
            sys.exit(1)
        info_app(rest[0], json_output=json_output)

    elif command == "list":
        _, json_output = _extract_global_flags(sys.argv[2:])
        list_installed(json_output=json_output)

    elif command in ("uninstall", "remove"):
        install_dir, dry_run, force, shallow, ref, method, json_output, timeout, retries, rest = (
            _parse_args(sys.argv[2:])
        )
        if not rest:
            print_error("Please provide an app name")
            sys.exit(1)

        for name in rest:
            uninstall_app(name, force=force)

    elif command == "verify":
        _, json_output = _extract_global_flags(sys.argv[2:])
        verify_apps(json_output=json_output)

    elif command == "clean":
        install_dir, dry_run, force, shallow, ref, method, json_output, timeout, retries, rest = (
            _parse_args(sys.argv[2:])
        )
        clean_registry(dry_run=dry_run, force=force, json_output=json_output)

    elif command == "stats":
        _, json_output = _extract_global_flags(sys.argv[2:])
        stats_command(json_output=json_output)

    elif command == "doctor":
        _, json_output = _extract_global_flags(sys.argv[2:])
        doctor(json_output=json_output)

    elif command == "config":
        key = sys.argv[2] if len(sys.argv) > 2 else None
        value = sys.argv[3] if len(sys.argv) > 3 else None
        config_command(key, value)

    elif command == "search":
        if len(sys.argv) < 3:
            print_error("Please provide a search query")
            sys.exit(1)
        query = " ".join(sys.argv[2:])
        search_github(query)

    elif command == "export":
        if len(sys.argv) < 3:
            print_error("Please provide an output file path")
            sys.exit(1)
        export_registry(sys.argv[2])

    elif command == "import":
        if len(sys.argv) < 3:
            print_error("Please provide an input file path")
            sys.exit(1)
        import_registry(sys.argv[2])

    elif command == "completion":
        if len(sys.argv) < 3:
            print_error("Please specify a shell: bash or zsh")
            sys.exit(1)
        shell = sys.argv[2]
        script = _completion_script(shell)
        if script:
            print(script)
        else:
            print_error(f"Unsupported shell: {shell}")
            print("Supported shells: bash, zsh")
            sys.exit(1)

    elif command == "version":
        print(f"pluck v{__version__}")

    elif command == "help":
        print_usage()

    else:
        print_error(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
