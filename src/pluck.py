#!/usr/bin/env python3
"""
GitHub App Installer - Paste URL, Auto-Install, Done!
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

__version__ = "0.5.0"


def _safe_urlopen(req, timeout=None):
    """Open a URL with scheme validation.

    Only https:// and http:// schemes are allowed to prevent file:/
    or custom scheme abuse (e.g.  CVE-2023-24329 style attacks).
    """
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"Blocked URL with disallowed scheme '{parsed.scheme}': {url}")
    return urllib.request.urlopen(req, timeout=timeout)


# Configuration
DEFAULT_INSTALL_DIR_MACOS = Path.home() / "Applications"
DEFAULT_INSTALL_DIR_LINUX = Path.home() / ".local" / "opt"
if sys.platform == "darwin":
    DEFAULT_INSTALL_DIR = DEFAULT_INSTALL_DIR_MACOS
else:
    DEFAULT_INSTALL_DIR = DEFAULT_INSTALL_DIR_LINUX
APP_REGISTRY_FILE = Path.home() / ".pluck-registry.json"
_CONFIG_OLD_REGISTRY = Path.home() / ".gh-install-registry.json"
CONFIG_FILE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pluck" / "config.json"
_CONFIG_OLD_DIR = Path.home() / ".config" / "gh-install"
CACHE_DIR = Path.home() / ".cache" / "pluck"
SHARED_PATHS = {
    Path.home() / "go" / "bin",
    Path.home() / "Applications",
    Path.home() / ".local" / "opt",
    Path.home() / "bin",
}
VALID_METHODS = {"script", "binary", "python", "node", "go", "rust", "make", "download", "release"}
GIST_PATTERN = r"gist\.github\.com[:/]([^/]+)/([a-f0-9]+)"
# API endpoint constants
_API_GITHUB_SEARCH = "https://api.github.com/search/repositories"
_API_GITLAB_SEARCH = "https://gitlab.com/api/v4/projects"
_API_CODEBERG_SEARCH = "https://codeberg.org/api/v1/repos/search"
_API_BITBUCKET_SEARCH = "https://api.bitbucket.org/2.0/repositories"
_API_GITLAB_RELEASES = "https://gitlab.com/api/v4/projects"
# GitLab personal snippet: gitlab.com/-/snippets/12345
# GitLab project snippet: gitlab.com/owner/repo/-/snippets/12345
SNIPPET_PATTERNS = [
    r"gitlab\.com/-/snippets/(\d+)",
    r"gitlab\.com/([^/]+)/([^/]+)/-/snippets/(\d+)",
]

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
        (
            "search <query> [--forge <name>] [--all] [--output <file>]",
            "Search repos (github|gitlab|codeberg|bitbucket)",
        ),
        ("export <file>", "Export registry"),
        ("import <file>", "Import registry"),
        ("completion <shell>", "Generate shell completion"),
        ("pin <name>", "Pin an app to prevent updates"),
        ("unpin <name>", "Unpin an app"),
        ("self-update", "Update pluck itself"),
        ("cache <prune|path>", "Manage download cache"),
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
        ("--jobs <n>", "Number of parallel installs (default: 1)"),
        ("--verbose", "Show detailed git clone output"),
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


def _parse_snippet_url(url):
    """Extract snippet/gist info from gist or code snippet URLs.

    Supports:
    - GitHub Gists: gist.github.com/user/id
    - GitLab personal snippets: gitlab.com/-/snippets/id
    - GitLab project snippets: gitlab.com/owner/repo/-/snippets/id
    """
    # GitHub Gist
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

    # GitLab personal snippet
    match = re.search(SNIPPET_PATTERNS[0], url)
    if match:
        snippet_id = match.group(1)
        return {
            "host": "gitlab.com",
            "host_type": "gitlab",
            "owner": "-",
            "repo": f"snippet-{snippet_id}",
            "url": f"https://gitlab.com/-/snippets/{snippet_id}.git",
            "is_gist": True,
        }

    # GitLab project snippet
    match = re.search(SNIPPET_PATTERNS[1], url)
    if match:
        owner = match.group(1)
        project = match.group(2)
        snippet_id = match.group(3)
        return {
            "host": "gitlab.com",
            "host_type": "gitlab",
            "owner": f"{owner}/{project}",
            "repo": f"snippet-{snippet_id}",
            "url": f"https://gitlab.com/{owner}/{project}/-/snippets/{snippet_id}.git",
            "is_gist": True,
        }

    return None


# Backward compat alias
_parse_gist_url = _parse_snippet_url


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
    host_lower = host.lower()
    if host_lower.startswith("www."):
        host_lower = host_lower[4:]
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
    gist_info = _parse_snippet_url(url)
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


def _check_install_method(repo_path, method):
    """Check if a given install method applies to repo_path."""
    checks = {
        "script": lambda: (repo_path / "install.sh").exists(),
        "binary": lambda: (
            (repo_path / "release" / "linux").exists()
            or (repo_path / "bin" / "linux").exists()
            or list(repo_path.glob("*.AppImage"))
            or list(repo_path.glob("*.deb"))
        ),
        "python": lambda: (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists(),
        "node": lambda: (repo_path / "package.json").exists(),
        "go": lambda: (repo_path / "go.mod").exists() or list(repo_path.glob("*.go")),
        "rust": lambda: (repo_path / "Cargo.toml").exists(),
        "make": lambda: (repo_path / "Makefile").exists(),
    }
    checker = checks.get(method)
    return checker() if checker else False


def detect_install_method(repo_path, method_priority=None):
    """Detect the best installation method for a repository"""
    if method_priority:
        methods = [m for m in method_priority if m in VALID_METHODS]
    else:
        methods = ["script", "binary", "python", "node", "go", "rust", "make", "download"]

    for method in methods:
        if method == "download":
            continue
        if _check_install_method(repo_path, method):
            return method

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
        ignore = shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv")
        shutil.copytree(repo_path, app_dir, dirs_exist_ok=True, ignore=ignore)

        venv_path = app_dir / ".venv"
        venv_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

        pip_path = venv_path / "bin" / "pip"
        subprocess.run([str(pip_path), "install", "-e", str(app_dir)], check=True)

        print_success(f"Installed to {app_dir}")

        # If the package installed a console-script entry point with the same
        # name as the repo, expose it as a sibling symlink in install_dir/bin/.
        # (Previously this tried to unlink app_dir itself, which is a non-empty
        # directory — causing IsADirectoryError whenever an entry point existed.)
        entry_point = venv_path / "bin" / repo_path.name
        if entry_point.exists():
            bin_dir = install_dir / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            link_path = bin_dir / repo_path.name
            # Only unlink files and symlinks — never directories. A directory
            # at this path is almost certainly user-created and we should not
            # blow it away silently.
            if link_path.is_symlink() or (link_path.exists() and link_path.is_file()):
                link_path.unlink()
            elif link_path.is_dir():
                print_warning(
                    f"Skipping symlink creation: {link_path} is a directory "
                    f"(not overwriting)"
                )
                return app_dir
            link_path.symlink_to(entry_point)
            print_success(f"Created symlink: {link_path} → {entry_point}")

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
        # 'make install' failed — try a plain 'make' build, then copy binaries.
        try:
            subprocess.run(["make"], cwd=repo_path, check=True)
        except subprocess.CalledProcessError as e:
            print_error(f"Make build failed: {e}")
            return None
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


def _clone_repo(repo_info, safe_name, shallow, ref, verbose, timeout, retries):
    """Clone a repository to a temp directory. Returns (temp_dir, repo_path) or None on failure."""
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
            subprocess.run(
                clone_cmd,
                check=True,
                timeout=timeout,
                stdout=None if verbose else subprocess.DEVNULL,
                stderr=None if verbose else subprocess.DEVNULL,
            )
            return temp_dir, repo_path
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

    return None


def _print_summary(name, method, path):
    """Print a formatted installation summary."""
    print()
    print(f"  {Colors.CYAN}Summary:{Colors.END}")
    print(f"    Name:     {name}")
    print(f"    Method:   {method}")
    print(f"    Location: {path}")
    print(f"    Size:     {_get_disk_size(path)}")


_INSTALL_FUNCS = {
    "python": install_python,
    "node": install_node,
    "go": install_go,
    "rust": install_rust,
    "binary": install_binary,
    "make": install_make,
    "script": install_script,
    "download": install_binary,
}

# What each install method actually executes, in plain language — shown to
# the user before we run anything from a repo they haven't reviewed.
_METHOD_DESCRIPTIONS = {
    "script": "run install.sh from the cloned repo",
    "python": "create a virtualenv and run 'pip install -e .' (executes the package's build/setup code)",
    "node": "run 'npm install' (executes any postinstall scripts the package defines)",
    "go": "run 'go build' to compile the project",
    "rust": "run 'cargo build --release' (executes any build.rs build script the crate defines)",
    "make": "run 'make install' (falling back to 'make') from the cloned repo",
    "binary": "copy pre-built files from the repo — no code is executed",
    "download": "copy pre-built files from the repo — no code is executed",
}


def _confirm_install(repo_info, method):
    """Ask the user to confirm before running code from a freshly-cloned,
    unreviewed repository. Returns True if it's safe to proceed.

    Refuses (rather than hanging or crashing) when stdin isn't an
    interactive terminal — a non-interactive run must pass --yes/--force
    to skip this on purpose.
    """
    description = _METHOD_DESCRIPTIONS.get(method, f"run the '{method}' install method")
    print()
    print_warning(f"About to install from {repo_info.get('url', 'this repository')}")
    print(f"  Detected method: {Colors.CYAN}{method}{Colors.END} — this will {description}.")
    if not sys.stdin.isatty():
        print_error("Refusing to run an unreviewed install non-interactively without --yes.")
        print("  Re-run with --yes (or --force) if you're sure.")
        return False
    confirm = input("  Continue? [y/N]: ")
    return confirm.lower() == "y"


def download_and_install(
    repo_url,
    install_dir=None,
    dry_run=False,
    shallow=False,
    ref=None,
    method_override=None,
    verbose=False,
    timeout=None,
    retries=0,
    force=False,
):
    """Download and install a repository from any git hosting URL"""

    if install_dir is None:
        user_config = _load_user_config()
        config_dir = user_config.get("install_dir")
        if config_dir:
            install_dir = Path(config_dir).expanduser()
        else:
            install_dir = DEFAULT_INSTALL_DIR

    # Check if this is a local path instead of a URL
    local_candidate = Path(repo_url).expanduser()
    if local_candidate.exists():
        return _install_local_path(
            repo_url,
            install_dir,
            dry_run=dry_run,
            method_override=method_override,
        )

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

    # If release method requested, skip cloning and try release assets
    if method_override == "release":
        release_result = _try_release_install(repo_info, repo_url, install_dir, safe_name, dry_run)
        if release_result is not None:
            return release_result
        # Release asset install failed — fall back to a normal clone+install
        # so the user doesn't have to re-run without --release.
        print_warning("Falling back to clone+install...")
        method_override = None

    # Dry-run check before doing any I/O
    if dry_run:
        print(f"  [DRY RUN] Would install to: {install_dir / safe_name}")
        print(f"  [DRY RUN] Would use method: {method_override or '(auto-detected after clone)'}")
        return install_dir / safe_name

    # Create install directory if it doesn't exist
    install_dir.mkdir(parents=True, exist_ok=True)

    # Clone to temp directory
    clone_result = _clone_repo(repo_info, safe_name, shallow, ref, verbose, timeout, retries)
    if clone_result is None:
        return None
    temp_dir, repo_path = clone_result

    # Detect install method
    user_config = _load_user_config()
    method_priority = user_config.get("method_priority")
    install_method = method_override or detect_install_method(repo_path, method_priority)
    print(f"  Detected install method: {install_method}")

    if not force and not _confirm_install(repo_info, install_method):
        print_warning("Installation cancelled.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    # Install based on method
    install_func = _INSTALL_FUNCS.get(install_method, install_binary)
    try:
        installed_path = install_func(repo_path, install_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Register the installation
    if installed_path:
        register_app(repo_info["repo"], repo_url, installed_path, install_method)
        _print_summary(repo_info["repo"], install_method, installed_path)
        return installed_path

    return None


def _try_release_install(repo_info, repo_url, install_dir, safe_name, dry_run):
    """Try installing from release assets (called when method_override == 'release').

    Returns the installed path on success, or None on failure (caller is
    expected to fall back to a normal clone+install).
    """
    if dry_run:
        print(f"  [DRY RUN] Would install release assets for: {repo_info['owner']}/{repo_info['repo']}")
        return install_dir / safe_name
    install_dir.mkdir(parents=True, exist_ok=True)
    print("  Attempting release asset install...")
    installed_path = install_release_asset(repo_info, install_dir)
    if installed_path:
        register_app(repo_info["repo"], repo_url, installed_path, "release")
        _print_summary(repo_info["repo"], "release", installed_path)
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
    # Read the current entry under the lock so we get a consistent snapshot.
    with _with_registry_lock():
        registry = load_registry()
        if repo_name not in registry["apps"]:
            print_error(f"{repo_name} is not installed")
            return False
        app_info = registry["apps"][repo_name].copy()

    url = app_info["url"]
    old_path = Path(app_info["path"])

    # Check if app is pinned
    if app_info.get("pinned", False):
        print_warning(f"{repo_name} is pinned — skipping update")
        print("  Use 'pluck unpin' first, or --force to override")
        return True

    print_header(f"Updating {repo_name}")
    print(f"  Current: {app_info['installed_at']}")
    print(f"  URL: {url}")

    if dry_run:
        print(f"  [DRY RUN] Would re-install from: {url}")
        print(f"  [DRY RUN] Would update: {old_path}")
        return True

    resolved_shared_paths = {p.resolve() for p in SHARED_PATHS}
    if (
        old_path.exists()
        and old_path.resolve() not in resolved_shared_paths
        and old_path.resolve() != Path.home().resolve()
    ):
        if old_path.is_file():
            old_path.unlink()
        else:
            shutil.rmtree(old_path, ignore_errors=True)

    # Remove the old registry entry under the lock so concurrent operations
    # don't see a half-deleted state. The re-install itself runs unlocked
    # (download_and_install acquires its own lock when calling register_app).
    with _with_registry_lock():
        registry = load_registry()
        if repo_name in registry["apps"]:
            del registry["apps"][repo_name]
            save_registry(registry)

    # Re-install (unlocked — register_app will lock when it writes the new entry)
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
        # Restore old registry entry under the lock
        with _with_registry_lock():
            registry = load_registry()
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

    pinned = app_info.get("pinned", False)
    if json_output:
        data = {
            "name": repo_name,
            "url": app_info["url"],
            "method": app_info["method"],
            "pinned": pinned,
            "path": app_info["path"],
            "installed_at": app_info["installed_at"],
            "size": _get_disk_size(install_path),
            "exists": install_path.exists(),
        }
        print(json.dumps(data, indent=2))
        return True

    print_header(f"App Info: {repo_name}")
    labels = ["URL", "Method", "Path", "Pinned", "Installed", "Size", "Exists"]
    values = [
        app_info["url"],
        app_info["method"],
        app_info["path"],
        "Yes" if pinned else "No",
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
        exe = tool
        found = bool(shutil.which(exe))
        if not found and exe == "python3":
            found = bool(shutil.which("python"))
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


def _search_print_result(index, name, desc, stars, lang, url, star_char="★"):
    """Print a formatted search result."""
    print(f"  {index}. {Colors.GREEN}{name}{Colors.END}")
    print(f"     {desc}")
    print(f"     {Colors.CYAN}{star_char}{Colors.END} {stars:,}  |  Language: {lang}")
    print(f"     URL: {url}")
    print()


def search_github(query, limit=10, results=None):
    """Search repositories using the GitHub API.
    If results (list) is provided, appends result dicts instead of printing.
    """
    print(f"  Searching GitHub for '{query}'...")
    url = f"{_API_GITHUB_SEARCH}?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={limit}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
        with _safe_urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_error(f"Search failed: {e}")
        return

    items = data.get("items", [])
    if not items:
        print_warning("No results found")
        return

    if results is not None:
        for i, repo in enumerate(items, 1):
            results.append(
                {
                    "index": i,
                    "name": repo["full_name"],
                    "description": repo.get("description") or "No description",
                    "stars": repo["stargazers_count"],
                    "language": repo.get("language") or "Unknown",
                    "url": repo["html_url"],
                }
            )
    else:
        print_header(f"GitHub Results — '{query}' ({len(items)} found)")
        for i, repo in enumerate(items, 1):
            _search_print_result(
                i,
                repo["full_name"],
                repo.get("description") or "No description",
                repo["stargazers_count"],
                repo.get("language") or "Unknown",
                repo["html_url"],
            )


def search_gitlab(query, limit=10, results=None):
    """Search repositories using the GitLab API."""
    print(f"  Searching GitLab for '{query}'...")
    url = f"{_API_GITLAB_SEARCH}?search={urllib.parse.quote(query)}&per_page={limit}&order_by=stars&sort=desc"
    # Note: GitLab search is unauthenticated but rate-limited (600 req/h per IP)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with _safe_urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_error(f"Search failed: {e}")
        return

    if not data:
        print_warning("No results found")
        return

    parsed = []
    for project in data:
        # GitLab returns projects ordered by last_activity by default;
        # sort with our own star sort since we requested order_by=stars
        parsed.append(
            {
                "name": project.get("path_with_namespace", project["path"]),
                "description": project.get("description") or "No description",
                "stars": project.get("star_count", 0),
                "language": project.get("programming_language") or project.get("language") or "Unknown",
                "url": project.get("web_url", project.get("http_url_to_repo", "")),
            }
        )

    parsed.sort(key=lambda r: r["stars"], reverse=True)

    if results is not None:
        for i, r in enumerate(parsed[:limit], 1):
            results.append(
                {
                    "index": i,
                    "name": r["name"],
                    "description": r["description"],
                    "stars": r["stars"],
                    "language": r["language"],
                    "url": r["url"],
                }
            )
    else:
        print_header(f"GitLab Results — '{query}' ({len(parsed)} found)")
        for i, r in enumerate(parsed[:limit], 1):
            _search_print_result(
                i, r["name"], r["description"], r["stars"], r["language"], r["url"], star_char="\u2605"
            )


def search_codeberg(query, limit=10, results=None):
    """Search repositories using the Codeberg (Gitea/Forgejo) API."""
    print(f"  Searching Codeberg for '{query}'...")
    url = f"{_API_CODEBERG_SEARCH}?q={urllib.parse.quote(query)}&limit={limit}&sort=stars"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with _safe_urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_error(f"Search failed: {e}")
        return

    # Codeberg returns either a list (legacy) or {"data": [...], "ok": true}.
    items = data.get("data", []) if isinstance(data, dict) else data
    ok_flag = data.get("ok", True) if isinstance(data, dict) else True
    if not ok_flag or not items:
        print_warning("No results found")
        return

    if results is not None:
        for i, repo in enumerate(items, 1):
            results.append(
                {
                    "index": i,
                    "name": repo.get("full_name", "unknown"),
                    "description": repo.get("description") or "No description",
                    "stars": repo.get("stars_count", 0),
                    "language": repo.get("language") or "Unknown",
                    "url": repo.get("html_url", ""),
                }
            )
    else:
        print_header(f"Codeberg Results — '{query}' ({len(items)} found)")
        for i, repo in enumerate(items, 1):
            _search_print_result(
                i,
                repo.get("full_name", "unknown"),
                repo.get("description") or "No description",
                repo.get("stars_count", 0),
                repo.get("language") or "Unknown",
                repo.get("html_url", ""),
            )


def _bitbucket_repo_url(repo):
    """Extract the HTML URL from a Bitbucket API repo object."""
    links = repo.get("links") if isinstance(repo, dict) else None
    html = links.get("html") if isinstance(links, dict) else None
    href = html.get("href") if isinstance(html, dict) else None
    return href or ""


def search_bitbucket(query, limit=10, results=None):
    """Search repositories using the Bitbucket Cloud API."""
    print(f"  Searching Bitbucket for '{query}'...")
    url = f'{_API_BITBUCKET_SEARCH}?q=name~"{urllib.parse.quote(query)}"&sort=-updated_on'
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with _safe_urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_error(f"Search failed: {e}")
        return

    items = data.get("values", [])
    if not items:
        print_warning("No results found")
        return

    if results is not None:
        for i, repo in enumerate(items, 1):
            results.append(
                {
                    "index": i,
                    "name": repo.get("full_name", "unknown"),
                    "description": repo.get("description") or "No description",
                    "stars": 0,
                    "language": repo.get("language") or "Unknown",
                    "url": _bitbucket_repo_url(repo),
                }
            )
    else:
        print_header(f"Bitbucket Results — '{query}' ({len(items)} found)")
        for i, repo in enumerate(items, 1):
            full_name = repo.get("full_name", "unknown")
            desc = repo.get("description") or "No description"
            lang = repo.get("language") or "Unknown"
            url = _bitbucket_repo_url(repo)
            _search_print_result(i, full_name, desc, 0, lang, url, star_char="\u2022")


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

    with _with_registry_lock():
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
    """Register an installed application.

    Holds the registry lock for the full read-modify-write so parallel
    installs (via --jobs) can't lose each other's entries.
    """
    new_entry = {
        "url": repo_url,
        "path": str(install_path),
        "method": install_method,
        "pinned": False,
        "installed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with _with_registry_lock():
        registry = load_registry()
        registry["apps"][repo_name] = new_entry
        save_registry(registry)

    print_success(f"Registered {repo_name}")

    if not skip_hook:
        _run_post_install_hook(repo_name, str(install_path), install_method)


def _run_post_install_hook(repo_name, install_path, method):
    """Run user-defined post-install hook if configured."""
    hook_dir = CONFIG_FILE.parent / "hooks"
    hook_file = hook_dir / "post-install.sh"

    if hook_file.exists():
        env = os.environ.copy()
        env["PLUCK_APP"] = repo_name
        env["PLUCK_PATH"] = install_path
        env["PLUCK_METHOD"] = method
        # Legacy aliases — remove in a future release
        # Legacy aliases kept for backward compat — remove in a future release
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
    with _with_registry_lock():
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
        try:
            with open(APP_REGISTRY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable registry — start fresh rather than crash.
            print_warning(f"Registry at {APP_REGISTRY_FILE} was unreadable, starting fresh")
            return {"apps": {}}

    return {"apps": {}}


def save_registry(registry):
    """Save the app registry atomically.

    Writes to a sibling temp file and renames into place so a crash mid-write
    can't leave a half-written registry. Concurrent read-modify-write
    sequences should be wrapped in `_with_registry_lock()` to avoid losing
    entries when multiple writers race.
    """
    APP_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = APP_REGISTRY_FILE.with_suffix(".tmp")
    try:
        with open(tmp_file, "w") as f:
            json.dump(registry, f, indent=2)
        try:
            os.replace(tmp_file, APP_REGISTRY_FILE)
        except OSError:
            # Atomic rename failed (e.g. cross-device). Fall back to a direct
            # write and clean up the temp file so it doesn't accumulate.
            APP_REGISTRY_FILE.write_text(json.dumps(registry, indent=2))
            try:
                tmp_file.unlink()
            except OSError:
                pass
    except OSError:
        # Couldn't even create the temp file — last-resort direct write.
        APP_REGISTRY_FILE.write_text(json.dumps(registry, indent=2))


def _with_registry_lock():
    """Context manager that acquires the registry advisory lock for the
    duration of a read-modify-write sequence. Yields nothing useful.

    Falls back to a no-op on platforms without fcntl (e.g. Windows).
    """
    import contextlib

    try:
        import fcntl
    except ImportError:
        # No fcntl (Windows) — return a no-op context manager.
        return contextlib.nullcontext()

    APP_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_file = APP_REGISTRY_FILE.with_suffix(".lock")

    @contextlib.contextmanager
    def _cm():
        with open(lock_file, "w") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    return _cm()


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
        pinned = info.get("pinned", False)
        pin_tag = f" {Colors.YELLOW}[PINNED]{Colors.END}" if pinned else ""
        print(f"\n{Colors.GREEN}{name}{Colors.END}{pin_tag}  [{exists}]")
        print(f"  URL: {info['url']}")
        print(f"  Method: {info['method']}")
        print(f"  Path: {info['path']}")
        print(f"  Size: {size}")
        print(f"  Installed: {info['installed_at']}")


def uninstall_app(repo_name, force=False):
    """Uninstall an application"""
    with _with_registry_lock():
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
        resolved_shared_paths = {p.resolve() for p in SHARED_PATHS}
        if install_path.resolve() in resolved_shared_paths or install_path.resolve() == Path.home().resolve():
            print_error(f"Refusing to uninstall: {install_path} is a shared directory")
            print_warning("Remove files from this directory manually instead")
            return False

        if install_path.exists():
            if install_path.is_file():
                install_path.unlink()
            else:
                shutil.rmtree(install_path, ignore_errors=True)

        del registry["apps"][repo_name]
        save_registry(registry)

    print_success(f"Uninstalled {repo_name}")
    return True


class _ParseContext:
    """Mutable container for _parse_args state."""

    def __init__(self):
        self.install_dir = None
        self.dry_run = False
        self.force = False
        self.yes = False
        self.shallow = False
        self.ref = None
        self.method = None
        self.json_output = False
        self.no_color = False
        self.verbose = False
        self.timeout = None
        self.retries = 0
        self.jobs = 1
        self.urls = []


def _parse_flag(flag, ctx, args, i):
    """Handle a single CLI flag. Returns the updated index.

    Raises ValueError if a flag that requires a value (e.g. --dir) is at the
    end of the arg list with no value following it.
    """
    handlers = {
        "--dir": lambda: setattr(ctx, "install_dir", Path(args[i + 1]).expanduser()) or i + 2,
        "--dry-run": lambda: setattr(ctx, "dry_run", True) or i + 1,
        "--force": lambda: setattr(ctx, "force", True) or i + 1,
        "--yes": lambda: setattr(ctx, "yes", True) or i + 1,
        "--shallow": lambda: setattr(ctx, "shallow", True) or i + 1,
        "--ref": lambda: setattr(ctx, "ref", args[i + 1]) or i + 2,
        "--method": lambda: setattr(ctx, "method", args[i + 1]) or i + 2,
        "--json": lambda: setattr(ctx, "json_output", True) or i + 1,
        "--verbose": lambda: setattr(ctx, "verbose", True) or i + 1,
        "--no-color": lambda: setattr(ctx, "no_color", True) or i + 1,
        "--timeout": lambda: _try_int(ctx, "timeout", args[i + 1]) or i + 2,
        "--retries": lambda: _try_int(ctx, "retries", args[i + 1]) or i + 2,
        "--jobs": lambda: setattr(ctx, "jobs", max(1, _try_int_val(args[i + 1], 1))) or i + 2,
    }
    handler = handlers.get(flag)
    if handler:
        if i + _flag_arg_count(flag) >= len(args):
            raise ValueError(f"Flag {flag} requires a value but none was provided")
        return handler()
    ctx.urls.append(args[i])
    return i + 1


def _flag_arg_count(flag):
    """Number of extra args a flag consumes."""
    return 1 if flag in ("--dir", "--ref", "--method", "--timeout", "--retries", "--jobs") else 0


def _try_int(ctx, attr, val):
    """Try to set an int attribute; silently ignore on ValueError."""
    try:
        setattr(ctx, attr, int(val))
    except ValueError:
        return  # non-integer flag value — leave default


def _try_int_val(val, default):
    """Try to parse an int, returning default on failure."""
    try:
        return int(val)
    except ValueError:
        return default


def _parse_args(args):
    """Parse all CLI flags from a list of arguments.

    Raises ValueError if a flag requiring a value is missing its value.
    """
    ctx = _ParseContext()
    i = 0
    while i < len(args):
        i = _parse_flag(args[i], ctx, args, i)

    if ctx.yes:
        ctx.force = True
    if ctx.no_color:
        _enable_colors(False)

    return (
        ctx.install_dir,
        ctx.dry_run,
        ctx.force,
        ctx.shallow,
        ctx.ref,
        ctx.method,
        ctx.json_output,
        ctx.verbose,
        ctx.no_color,
        ctx.timeout,
        ctx.retries,
        ctx.jobs,
        ctx.urls,
    )


def verify_apps(json_output=False):
    """Check if installed apps are still valid (files exist, not corrupted)."""
    registry = load_registry()
    results = []

    for name, info in registry["apps"].items():
        install_path = Path(info["path"])
        exists = install_path.exists()
        size = _get_disk_size(install_path) if exists else "N/A"
        results.append(
            {
                "name": name,
                "url": info["url"],
                "path": info["path"],
                "exists": exists,
                "size": size,
                "installed_at": info["installed_at"],
            }
        )

    valid_count = sum(1 for r in results if r["exists"])
    invalid_count = len(results) - valid_count

    if json_output:
        print(
            json.dumps(
                {
                    "total": len(results),
                    "valid": valid_count,
                    "invalid": invalid_count,
                    "apps": results,
                },
                indent=2,
            )
        )
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
            total_size += _safe_dir_size(install_path)
        else:
            orphaned += 1

    if json_output:
        print(
            json.dumps(
                {
                    "total_apps": total,
                    "valid": valid,
                    "orphaned": orphaned,
                    "total_size_bytes": total_size,
                    "total_size_human": _format_bytes(total_size),
                    "by_method": method_counts,
                },
                indent=2,
            )
        )
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


def _safe_dir_size(path):
    """Calculate disk size of path, returning 0 on inaccessible paths."""
    try:
        if path.is_file():
            return path.stat().st_size
        if path.is_dir():
            total = 0
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        try:
                            total += os.path.getsize(fp)
                        except OSError:
                            continue  # skip inaccessible files
            return total
        return 0
    except OSError:
        return 0


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
    """Extract global flags (--json, --no-color) from an arg list.

    Returns a tuple of (cleaned_args, json_output, no_color). The no_color
    side effect (_enable_colors(False)) is applied inside this function so
    callers don't need to do anything extra.
    """
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
    return cleaned, json_output, no_color


def _migrate_old_registry():
    """Migrate from old .gh-install-registry.json to .pluck-registry.json."""
    if _CONFIG_OLD_REGISTRY.exists() and not APP_REGISTRY_FILE.exists():
        try:
            data = _CONFIG_OLD_REGISTRY.read_text()
            APP_REGISTRY_FILE.write_text(data)
            _CONFIG_OLD_REGISTRY.unlink()
            print_warning("Migrated registry from .gh-install-registry.json to .pluck-registry.json")
        except OSError:
            print_warning("Could not migrate old .gh-install-registry.json (may already be gone)")
    if _CONFIG_OLD_DIR.exists() and not CONFIG_FILE.exists():
        try:
            config_data = _CONFIG_OLD_DIR / "config.json"
            if config_data.exists():
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                config_data.rename(CONFIG_FILE)
                _CONFIG_OLD_DIR.rmdir()
                print_warning("Migrated config from ~/.config/gh-install/ to ~/.config/pluck/")
        except OSError:
            print_warning("Could not migrate old ~/.config/gh-install directory (may already be gone)")


# ── Pin / Unpin ──


def pin_app(repo_name):
    """Pin an app to prevent updates."""
    with _with_registry_lock():
        registry = load_registry()
        if repo_name not in registry["apps"]:
            print_error(f"{repo_name} is not installed")
            return False
        registry["apps"][repo_name]["pinned"] = True
        save_registry(registry)
    print_success(f"Pinned {repo_name}")
    return True


def unpin_app(repo_name):
    """Unpin an app."""
    with _with_registry_lock():
        registry = load_registry()
        if repo_name not in registry["apps"]:
            print_error(f"{repo_name} is not installed")
            return False
        registry["apps"][repo_name]["pinned"] = False
        save_registry(registry)
    print_success(f"Unpinned {repo_name}")
    return True


# ── Cache Management ──


def cache_command(action):
    """Manage the download cache."""
    if action == "prune":
        if not CACHE_DIR.exists():
            print_success("Cache is already empty")
            return True
        total = 0
        for entry in CACHE_DIR.iterdir():
            if entry.is_file():
                total += entry.stat().st_size
                entry.unlink()
            elif entry.is_dir():
                total += sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
                shutil.rmtree(entry, ignore_errors=True)
        # Remove the now-empty cache directory itself (best-effort).
        try:
            CACHE_DIR.rmdir()
        except OSError:
            # Directory not empty (race) or already gone — non-fatal.
            pass
        print_success(f"Cleared cache ({_format_bytes(total)})")
        return True
    elif action == "path":
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print(CACHE_DIR)
        return True
    else:
        print_error(f"Unknown cache action: {action} (try: prune, path)")
        return False


# ── Install from Local Path ──


def _install_local_path(repo_url, install_dir, dry_run=False, method_override=None):
    """Install a project from a local directory path."""
    local_path = Path(repo_url).expanduser().resolve()
    safe_name = _sanitize_repo_name(local_path.name)
    if not safe_name:
        print_error(f"Invalid local path name: {local_path.name}")
        return None

    if dry_run:
        print(f"  [DRY RUN] Would install from local path: {local_path}")
        print(f"  [DRY RUN] Would use method: {method_override or '(auto-detected)'}")
        return install_dir / safe_name

    install_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Installing from local path: {local_path}")

    install_method = method_override or detect_install_method(local_path)
    print(f"  Detected install method: {install_method}")

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
    installed_path = install_func(local_path, install_dir)

    if installed_path:
        register_app(safe_name, str(local_path), installed_path, install_method)
        print()
        print(f"  {Colors.CYAN}Summary:{Colors.END}")
        print(f"    Name:     {safe_name}")
        print(f"    Method:   {install_method}")
        print(f"    Location: {installed_path}")
        print(f"    Size:     {_get_disk_size(installed_path)}")
        return installed_path
    return None


# ── Self-Update ──


def self_update():
    """Update pluck itself via PyPI."""
    print_header("Updating pluck")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pluck-cli"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print_success("pluck updated to latest version")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Update failed: {e}")
        return False


# ── Search All Forges + Export ──


def _search_with_results(query, limit, searcher_func):
    """Run a searcher and return results as a list of dicts."""
    results = []
    searcher_func(query, limit=limit, results=results)
    return results


def search_all_forges(query, limit=5, output_file=None):
    """Search all supported forges and optionally export results."""
    all_results = []
    forges = [
        ("GitHub", search_github),
        ("GitLab", search_gitlab),
        ("Codeberg", search_codeberg),
        ("Bitbucket", search_bitbucket),
    ]

    for name, searcher in forges:
        print(f"  Searching {name} for '{query}'...")
        results = _search_with_results(query, limit, searcher)
        all_results.append((name, results))

    print_header(f"Aggregated Search Results — '{query}'")
    for forge_name, results in all_results:
        if results:
            print(f"\n{Colors.CYAN}── {forge_name} ({len(results)} results) ──{Colors.END}")
            for r in results:
                print(f"  {r['index']}. {Colors.GREEN}{r['name']}{Colors.END}")
                print(f"     {r['description']}")
                print(f"     \u2605 {r['stars']:,}  |  Language: {r['language']}")
                print(f"     URL: {r['url']}")
                print()

    # Export to file if requested
    if output_file:
        out_path = Path(output_file).expanduser()
        lines = [f"Search Results: '{query}' ({datetime.now():%Y-%m-%d %H:%M})", "=" * 60, ""]
        for forge_name, results in all_results:
            if results:
                lines.append(f"── {forge_name} ──")
                for r in results:
                    lines.append(f"{r['name']}  |  \u2605 {r['stars']:,}  |  {r['language']}")
                    lines.append(f"  {r['url']}")
                    lines.append(f"  {r['description']}")
                    lines.append("")
            else:
                lines.append(f"── {forge_name} ── (no results)")
                lines.append("")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines) + "\n")
        print_success(f"Exported results to {out_path}")


# ── Release Asset Install ──


def _safe_tar_members(tar):
    """Yield tar members that are safe to extract (no path traversal, no absolute paths).

    Used as a fallback on Python < 3.12 where tarfile.extractall(filter=...) is
    not available. Mirrors the protections of filter='data' for the path-traversal
    case (CVE-2007-4559).

    Backslashes in member names are normalized to forward slashes before
    checking, because on Unix a backslash is a valid filename character — so
    `foo\\..\\..\\bar` would bypass a naive `Path(..).parts` check that
    only looks for `..` segments split by the OS path separator.
    """
    for member in tar.getmembers():
        # Normalize backslashes so the path-traversal check works on Unix
        # (where backslashes are literal filename characters, not separators).
        sanitized_name = member.name.replace("\\", "/")
        member_path = Path(sanitized_name)
        if member_path.is_absolute() or ".." in member_path.parts:
            print_warning(f"Skipping unsafe tar entry: {member.name}")
            continue
        member.name = sanitized_name
        # Reject symlinks/hardlinks that point outside the extract dir
        if member.issym() or member.islnk():
            sanitized_linkname = member.linkname.replace("\\", "/")
            link_path = Path(sanitized_linkname)
            if link_path.is_absolute() or ".." in link_path.parts:
                print_warning(f"Skipping unsafe tar link: {member.name} -> {member.linkname}")
                continue
            member.linkname = sanitized_linkname
        yield member


def _github_release_url(repo_info, install_dir):
    """Try to download a pre-built release asset from GitHub."""
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "pluck"}
        req = urllib.request.Request(api_url, headers=headers)
        with _safe_urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_warning(f"Could not fetch GitHub release: {e}")
        return None

    assets = data.get("assets", [])
    if not assets:
        print_warning("No release assets found")
        return None

    # Pick a matching asset: prefer the one matching the current platform
    arch_hints = []
    if sys.platform == "linux":
        arch_hints = ["linux", "Linux", "x86_64", "amd64"]
    elif sys.platform == "darwin":
        arch_hints = ["macos", "darwin", "Darwin", "macOS", "x86_64", "amd64", "arm64"]

    best = None
    for asset in assets:
        name = asset["name"]
        if all(hint in name for hint in arch_hints):
            best = asset
            break

    if not best and assets:
        # Fallback to first asset
        best = assets[0]

    if not best:
        print_warning("No suitable asset found")
        return None

    # Download the asset
    print(f"  Downloading release asset: {best['name']}")
    dl_url = best["browser_download_url"]
    dest = CACHE_DIR / best["name"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        req = urllib.request.Request(dl_url, headers={"User-Agent": "pluck"})
        with _safe_urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
    except Exception as e:
        print_error(f"Download failed: {e}")
        return None

    print_success(f"Downloaded to {dest}")

    # If it's an archive, extract it
    if best["name"].endswith(".tar.gz") or best["name"].endswith(".tgz"):
        import tarfile

        extract_dir = install_dir / repo
        extract_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(dest) as tar:
            # Use filter='data' on Python 3.12+ to prevent path traversal
            # (CVE-2007-4559). On older Pythons, fall back to a sanitizing filter.
            try:
                tar.extractall(extract_dir, filter="data")
            except TypeError:
                # Python < 3.12 — no filter= argument. Apply a manual sanitizing
                # filter that strips absolute paths and parent-dir traversals.
                tar.extractall(extract_dir, members=_safe_tar_members(tar))
        print_success(f"Extracted to {extract_dir}")
        return extract_dir
    elif best["name"].endswith(".zip"):
        import zipfile

        extract_dir = install_dir / repo
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest) as zf:
            # Sanitize member paths to prevent path traversal (zip-slip).
            # Backslashes are normalized to forward slashes before checking
            # because on Unix a backslash is a literal filename character —
            # `foo\..\..\bar` would otherwise bypass the `..` check.
            for member in zf.infolist():
                sanitized_filename = member.filename.replace("\\", "/")
                member_path = Path(sanitized_filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    print_warning(f"Skipping unsafe zip entry: {member.filename}")
                    continue
                member.filename = sanitized_filename
                zf.extract(member, extract_dir)
        print_success(f"Extracted to {extract_dir}")
        return extract_dir
    else:
        # Single binary
        dest.chmod(0o755)
        bin_dir = install_dir / repo
        bin_dir.mkdir(parents=True, exist_ok=True)
        final = bin_dir / best["name"]
        shutil.move(str(dest), str(final))
        print_success(f"Installed binary to {final}")
        return bin_dir


def _gitlab_release_url(repo_info, install_dir):
    """Try to download a pre-built release asset from GitLab."""
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    # GitLab generic packages API
    encoded = urllib.parse.quote(owner + "/" + repo, safe="")
    api_url = f"{_API_GITLAB_RELEASES}/{encoded}/releases/permalink/latest"
    try:
        req = urllib.request.Request(api_url, headers={"Accept": "application/json", "User-Agent": "pluck"})
        with _safe_urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print_warning(f"Could not fetch GitLab release: {e}")
        return None

    assets = data.get("assets") or {}
    links = assets.get("links") or []
    if not links:
        print_warning("No release assets found")
        return None

    # Pick first binary link
    for link in links:
        url = link.get("direct_asset_url") or link.get("url", "")
        if url:
            name = link.get("name", "asset")
            dest = CACHE_DIR / name
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            print(f"  Downloading release asset: {name}")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "pluck"})
                with _safe_urlopen(req, timeout=60) as resp:
                    dest.write_bytes(resp.read())
            except Exception as e:
                print_warning(f"Download failed: {e}")
                continue

            bin_dir = install_dir / repo
            bin_dir.mkdir(parents=True, exist_ok=True)
            final = bin_dir / name
            dest.chmod(0o755)
            shutil.move(str(dest), str(final))
            print_success(f"Installed release asset to {final}")
            return bin_dir

    print_warning("Could not download any release asset")
    return None


def install_release_asset(repo_info, install_dir):
    """Install from pre-built release assets instead of cloning."""
    # Gists and snippets carry host_type=github/gitlab but have no releases API
    # — skip silently and let the caller fall back to a clone.
    if repo_info.get("is_gist"):
        print_warning("Release assets are not available for gists/snippets")
        return None
    host_type = repo_info.get("host_type", "")
    if host_type == "github":
        return _github_release_url(repo_info, install_dir)
    elif host_type == "gitlab":
        return _gitlab_release_url(repo_info, install_dir)
    else:
        print_warning(f"Release asset install not yet supported for {host_type}")
        return None


def _cmd_install():
    """Handle 'install' command."""
    (
        install_dir,
        dry_run,
        force,
        shallow,
        ref,
        method,
        json_output,
        verbose,
        no_color,
        timeout,
        retries,
        jobs,
        urls,
    ) = _parse_args(sys.argv[2:])

    if not urls:
        print_error("Please provide a repository URL")
        sys.exit(1)

    if method and method not in VALID_METHODS:
        print_error(f"Invalid method: {method}. Valid: {', '.join(sorted(VALID_METHODS))}")
        sys.exit(1)

    if dry_run:
        print_header("Dry Run — No changes will be made")

    if jobs > 1 and len(urls) > 1:
        if not force:
            print_error("Installing multiple repos with --jobs requires --yes.")
            print("  Can't safely prompt for confirmation on multiple repos at once.")
            sys.exit(1)
        print_header(f"Installing {len(urls)} repos with {jobs} workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(
                    download_and_install,
                    url,
                    install_dir=install_dir,
                    dry_run=dry_run,
                    shallow=shallow,
                    ref=ref,
                    method_override=method,
                    verbose=verbose,
                    timeout=timeout,
                    retries=retries,
                    force=force,
                ): url
                for url in urls
            }
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print_error(f"Failed to install {url}: {e}")
    else:
        for url in urls:
            print(f"\nInstalling: {url}")
            download_and_install(
                url,
                install_dir=install_dir,
                dry_run=dry_run,
                shallow=shallow,
                ref=ref,
                method_override=method,
                verbose=verbose,
                timeout=timeout,
                retries=retries,
                force=force,
            )


def _cmd_update():
    """Handle 'update' command."""
    (
        install_dir,
        dry_run,
        force,
        shallow,
        ref,
        method,
        json_output,
        verbose,
        no_color,
        timeout,
        retries,
        jobs,
        rest,
    ) = _parse_args(sys.argv[2:])
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


def _cmd_info():
    """Handle 'info' command."""
    rest, json_output, _no_color = _extract_global_flags(sys.argv[2:])
    if not rest:
        print_error("Please provide an app name")
        sys.exit(1)
    info_app(rest[0], json_output=json_output)


def _cmd_list():
    """Handle 'list' command."""
    _, json_output, _no_color = _extract_global_flags(sys.argv[2:])
    list_installed(json_output=json_output)


def _cmd_uninstall():
    """Handle 'uninstall' / 'remove' command."""
    (
        install_dir,
        dry_run,
        force,
        shallow,
        ref,
        method,
        json_output,
        verbose,
        no_color,
        timeout,
        retries,
        jobs,
        rest,
    ) = _parse_args(sys.argv[2:])
    if not rest:
        print_error("Please provide an app name")
        sys.exit(1)
    for name in rest:
        uninstall_app(name, force=force)


def _cmd_verify():
    """Handle 'verify' command."""
    _, json_output, _no_color = _extract_global_flags(sys.argv[2:])
    verify_apps(json_output=json_output)


def _cmd_clean():
    """Handle 'clean' command."""
    (
        install_dir,
        dry_run,
        force,
        shallow,
        ref,
        method,
        json_output,
        verbose,
        no_color,
        timeout,
        retries,
        jobs,
        rest,
    ) = _parse_args(sys.argv[2:])
    clean_registry(dry_run=dry_run, force=force, json_output=json_output)


def _cmd_stats():
    """Handle 'stats' command."""
    _, json_output, _no_color = _extract_global_flags(sys.argv[2:])
    stats_command(json_output=json_output)


def _cmd_doctor():
    """Handle 'doctor' command."""
    _, json_output, _no_color = _extract_global_flags(sys.argv[2:])
    doctor(json_output=json_output)


def _cmd_config():
    """Handle 'config' command."""
    key = sys.argv[2] if len(sys.argv) > 2 else None
    value = sys.argv[3] if len(sys.argv) > 3 else None
    config_command(key, value)


def _cmd_search():
    """Handle 'search' command."""
    args = sys.argv[2:]
    if not args:
        print_error("Please provide a search query")
        sys.exit(1)

    output_file = None
    search_all = False
    forge = "github"
    cleaned = []
    i = 0
    while i < len(args):
        if args[i] == "--forge" and i + 1 < len(args):
            forge = args[i + 1].lower()
            i += 2
        elif args[i] == "--all":
            search_all = True
            i += 1
        elif args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        else:
            cleaned.append(args[i])
            i += 1

    query = " ".join(cleaned)
    if not query:
        print_error("Please provide a search query")
        sys.exit(1)

    if search_all:
        search_all_forges(query, output_file=output_file)
    else:
        forge_searchers = {
            "github": search_github,
            "gitlab": search_gitlab,
            "codeberg": search_codeberg,
            "bitbucket": search_bitbucket,
        }
        searcher = forge_searchers.get(forge)
        if searcher:
            searcher(query)
        else:
            print_error(f"Unknown forge: {forge}. Supported: {', '.join(sorted(forge_searchers))}")
            sys.exit(1)


def _cmd_export():
    """Handle 'export' command."""
    if len(sys.argv) < 3:
        print_error("Please provide an output file path")
        sys.exit(1)
    export_registry(sys.argv[2])


def _cmd_import():
    """Handle 'import' command."""
    if len(sys.argv) < 3:
        print_error("Please provide an input file path")
        sys.exit(1)
    import_registry(sys.argv[2])


def _cmd_completion():
    """Handle 'completion' command."""
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


def _cmd_pin():
    """Handle 'pin' command."""
    if len(sys.argv) < 3:
        print_error("Please provide an app name")
        sys.exit(1)
    pin_app(sys.argv[2])


def _cmd_unpin():
    """Handle 'unpin' command."""
    if len(sys.argv) < 3:
        print_error("Please provide an app name")
        sys.exit(1)
    unpin_app(sys.argv[2])


# Command dispatch table
_COMMANDS = {
    "install": _cmd_install,
    "update": _cmd_update,
    "info": _cmd_info,
    "list": _cmd_list,
    "uninstall": _cmd_uninstall,
    "remove": _cmd_uninstall,
    "verify": _cmd_verify,
    "clean": _cmd_clean,
    "stats": _cmd_stats,
    "doctor": _cmd_doctor,
    "config": _cmd_config,
    "search": _cmd_search,
    "export": _cmd_export,
    "import": _cmd_import,
    "completion": _cmd_completion,
    "pin": _cmd_pin,
    "unpin": _cmd_unpin,
    "self-update": lambda: sys.exit(1) if not self_update() else None,
    "cache": lambda: cache_command(sys.argv[2] if len(sys.argv) > 2 else "path"),
    "version": lambda: print(f"pluck v{__version__}"),
    "help": print_usage,
}


def main():
    """Main entry point"""
    _migrate_old_registry()

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    if sys.argv[1] in ("--version", "-v"):
        print(f"pluck v{__version__}")
        sys.exit(0)

    command = sys.argv[1]
    handler = _COMMANDS.get(command)
    if handler:
        try:
            handler()
        except ValueError as e:
            # Catch ValueError from _parse_args (flag missing its value).
            print_error(str(e))
            sys.exit(1)
    else:
        print_error(f"Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
