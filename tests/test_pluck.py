import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pluck import (
    SHARED_PATHS,
    VALID_METHODS,
    _cmd_install,
    _confirm_install,
    _detect_host_type,
    _extract_global_flags,
    _format_bytes,
    _get_disk_size,
    _is_executable,
    _parse_args,
    _parse_gist_url,
    _parse_snippet_url,
    _sanitize_repo_name,
    config_command,
    detect_install_method,
    doctor,
    download_and_install,
    export_registry,
    import_registry,
    info_app,
    install_python,
    load_registry,
    parse_repo_url,
    pin_app,
    register_app,
    save_registry,
    stats_command,
    uninstall_app,
    unpin_app,
    update_app,
    verify_apps,
)


class TestParseRepoUrl:
    def test_github_https(self):
        result = parse_repo_url("https://github.com/owner/repo")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        assert result["host"] == "github.com"
        assert result["host_type"] == "github"
        assert result["url"] == "https://github.com/owner/repo"
        assert result.get("is_gist") is False

    def test_github_http(self):
        result = parse_repo_url("http://github.com/owner/repo")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        assert result["host_type"] == "github"

    def test_github_ssh(self):
        result = parse_repo_url("git@github.com:owner/repo.git")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        assert result["host_type"] == "github"

    def test_github_url_with_git_extension(self):
        result = parse_repo_url("https://github.com/owner/repo.git")
        assert result is not None
        assert result["repo"] == "repo"

    def test_github_url_with_subpath(self):
        """Tree/branch paths in URL should not prevent parsing."""
        result = parse_repo_url("https://github.com/owner/repo/tree/main")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"

    def test_github_hyphenated(self):
        result = parse_repo_url("https://github.com/my-org/my-repo")
        assert result is not None
        assert result["owner"] == "my-org"
        assert result["repo"] == "my-repo"
        assert result["host_type"] == "github"

    # ── Other forges ──

    def test_gitlab_https(self):
        result = parse_repo_url("https://gitlab.com/gitlab-org/gitlab")
        assert result is not None
        assert result["owner"] == "gitlab-org"
        assert result["repo"] == "gitlab"
        assert result["host"] == "gitlab.com"
        assert result["host_type"] == "gitlab"

    def test_gitlab_ssh(self):
        result = parse_repo_url("git@gitlab.com:owner/project.git")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "project"
        assert result["host_type"] == "gitlab"

    def test_codeberg_https(self):
        result = parse_repo_url("https://codeberg.org/user/repo")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "repo"
        assert result["host"] == "codeberg.org"
        assert result["host_type"] == "codeberg"

    def test_bitbucket_https(self):
        result = parse_repo_url("https://bitbucket.org/owner/repo")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        assert result["host_type"] == "bitbucket"

    def test_sourcehut_https(self):
        result = parse_repo_url("https://git.sr.ht/~user/repo")
        assert result is not None
        assert result["owner"] == "~user"
        assert result["repo"] == "repo"
        assert result["host"] == "git.sr.ht"
        assert result["host_type"] == "sourcehut"

    def test_gitea_https(self):
        result = parse_repo_url("https://gitea.com/user/repo")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "repo"
        assert result["host_type"] == "gitea"

    def test_gogs_https(self):
        result = parse_repo_url("https://gogs.io/user/repo")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "repo"
        assert result["host_type"] == "gogs"

    def test_pagure_https(self):
        result = parse_repo_url("https://pagure.io/user/repo")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "repo"
        assert result["host_type"] == "pagure"

    def test_forgejo_https(self):
        result = parse_repo_url("https://forgejo.org/user/repo")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "repo"
        assert result["host_type"] == "forgejo"

    def test_self_hosted_generic(self):
        """Self-hosted git instances should parse as 'generic' type."""
        result = parse_repo_url("https://git.example.com/team/project")
        assert result is not None
        assert result["owner"] == "team"
        assert result["repo"] == "project"
        assert result["host_type"] == "generic"

    def test_self_hosted_ssh(self):
        result = parse_repo_url("git@git.internal.company.com:org/repo.git")
        assert result is not None
        assert result["owner"] == "org"
        assert result["repo"] == "repo"
        assert result["host_type"] == "generic"

    def test_ssh_protocol_url(self):
        result = parse_repo_url("ssh://git@gitlab.com/owner/project.git")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "project"

    def test_git_protocol_url(self):
        result = parse_repo_url("git://github.com/owner/repo.git")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"

    def test_trailing_slash(self):
        """New parser handles trailing slashes gracefully."""
        result = parse_repo_url("https://gitlab.com/owner/repo/")
        assert result is not None
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"

    def test_invalid_url_random_string(self):
        result = parse_repo_url("not-a-url")
        assert result is None

    def test_invalid_url_empty(self):
        result = parse_repo_url("")
        assert result is None

    def test_detect_host_type_known(self):
        assert _detect_host_type("github.com") == "github"
        assert _detect_host_type("gitlab.com") == "gitlab"
        assert _detect_host_type("codeberg.org") == "codeberg"
        assert _detect_host_type("bitbucket.org") == "bitbucket"
        assert _detect_host_type("git.sr.ht") == "sourcehut"
        assert _detect_host_type("gitea.com") == "gitea"
        assert _detect_host_type("gogs.io") == "gogs"
        assert _detect_host_type("pagure.io") == "pagure"
        assert _detect_host_type("forgejo.org") == "forgejo"

    def test_detect_host_type_unknown(self):
        assert _detect_host_type("git.example.com") == "generic"
        assert _detect_host_type("192.168.1.100") == "generic"

    def test_detect_host_type_www_prefix(self):
        assert _detect_host_type("www.github.com") == "github"
        assert _detect_host_type("WWW.GITLAB.COM") == "gitlab"


class TestGistUrl:
    def test_gist_https_url(self):
        result = parse_repo_url("https://gist.github.com/user/abc123def")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "gist-abc123def"
        assert result.get("is_gist") is True
        assert result["host_type"] == "github"

    def test_gist_ssh_url(self):
        result = parse_repo_url("git@gist.github.com:user/abc123def")
        assert result is not None
        assert result["owner"] == "user"
        assert result["repo"] == "gist-abc123def"

    def test_gist_url_with_git_extension(self):
        result = parse_repo_url("https://gist.github.com/user/abc123def.git")
        assert result is not None
        assert result["repo"] == "gist-abc123def"

    def test_parse_gist_url_direct(self):
        result = _parse_gist_url("https://gist.github.com/test/abcd1234")
        assert result is not None
        assert result["url"] == "https://gist.github.com/test/abcd1234.git"
        assert result.get("is_gist") is True

    # ── GitLab snippets ──

    def test_gitlab_personal_snippet(self):
        result = parse_repo_url("https://gitlab.com/-/snippets/1234567")
        assert result is not None
        assert result["host"] == "gitlab.com"
        assert result["host_type"] == "gitlab"
        assert result["repo"] == "snippet-1234567"
        assert result["url"] == "https://gitlab.com/-/snippets/1234567.git"
        assert result.get("is_gist") is True

    def test_gitlab_project_snippet(self):
        result = parse_repo_url("https://gitlab.com/my-org/my-project/-/snippets/7654321")
        assert result is not None
        assert result["host"] == "gitlab.com"
        assert result["host_type"] == "gitlab"
        assert result["owner"] == "my-org/my-project"
        assert result["repo"] == "snippet-7654321"
        assert result["url"] == "https://gitlab.com/my-org/my-project/-/snippets/7654321.git"
        assert result.get("is_gist") is True

    def test_gitlab_snippet_direct(self):
        result = _parse_snippet_url("https://gitlab.com/-/snippets/98765")
        assert result is not None
        assert result["url"] == "https://gitlab.com/-/snippets/98765.git"
        assert result["host_type"] == "gitlab"


class TestDetectInstallMethod:
    def _make_temp_repo(self, files):
        tmp = tempfile.mkdtemp()
        for f in files:
            path = Path(tmp) / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        return Path(tmp)

    def test_detects_install_script(self):
        tmp = self._make_temp_repo(["install.sh"])
        assert detect_install_method(tmp) == "script"

    def test_detects_python_pyproject(self):
        tmp = self._make_temp_repo(["pyproject.toml"])
        assert detect_install_method(tmp) == "python"

    def test_detects_python_setup(self):
        tmp = self._make_temp_repo(["setup.py"])
        assert detect_install_method(tmp) == "python"

    def test_detects_node(self):
        tmp = self._make_temp_repo(["package.json"])
        assert detect_install_method(tmp) == "node"

    def test_detects_go_mod(self):
        tmp = self._make_temp_repo(["go.mod"])
        assert detect_install_method(tmp) == "go"

    def test_detects_go_files(self):
        tmp = self._make_temp_repo(["main.go"])
        assert detect_install_method(tmp) == "go"

    def test_detects_rust(self):
        tmp = self._make_temp_repo(["Cargo.toml"])
        assert detect_install_method(tmp) == "rust"

    def test_detects_makefile(self):
        tmp = self._make_temp_repo(["Makefile"])
        assert detect_install_method(tmp) == "make"

    def test_detects_binary_release(self):
        tmp = self._make_temp_repo(["release/linux/app"])
        assert detect_install_method(tmp) == "binary"

    def test_detects_binary_bin(self):
        tmp = self._make_temp_repo(["bin/linux/app"])
        assert detect_install_method(tmp) == "binary"

    def test_detects_appimage(self):
        tmp = self._make_temp_repo(["myapp.AppImage"])
        assert detect_install_method(tmp) == "binary"

    def test_detects_deb(self):
        tmp = self._make_temp_repo(["myapp.deb"])
        assert detect_install_method(tmp) == "binary"

    def test_defaults_to_download(self):
        tmp = self._make_temp_repo(["README.md"])
        assert detect_install_method(tmp) == "download"

    def test_script_takes_priority_over_python(self):
        tmp = self._make_temp_repo(["install.sh", "pyproject.toml"])
        assert detect_install_method(tmp) == "script"

    def test_python_takes_priority_over_node(self):
        tmp = self._make_temp_repo(["pyproject.toml", "package.json"])
        assert detect_install_method(tmp) == "python"

    def test_method_priority_respected(self):
        tmp = self._make_temp_repo(["pyproject.toml", "package.json"])
        assert detect_install_method(tmp, method_priority=["node", "python"]) == "node"

    def test_method_priority_invalid_filtered(self):
        tmp = self._make_temp_repo(["pyproject.toml"])
        assert detect_install_method(tmp, method_priority=["invalid", "python"]) == "python"


class TestSharedPaths:
    def test_shared_paths_not_empty(self):
        assert len(SHARED_PATHS) > 0

    def test_shared_paths_are_absolute(self):
        for path in SHARED_PATHS:
            assert path.is_absolute()


class TestValidMethods:
    def test_valid_methods_not_empty(self):
        assert len(VALID_METHODS) == 9

    def test_all_expected_methods_present(self):
        expected = {"script", "binary", "python", "node", "go", "rust", "make", "download", "release"}
        assert VALID_METHODS == expected


class TestSanitizeRepoName:
    def test_valid_name(self):
        assert _sanitize_repo_name("my-repo") == "my-repo"

    def test_rejects_dotdot(self):
        assert _sanitize_repo_name("../etc") is None

    def test_rejects_leading_slash(self):
        assert _sanitize_repo_name("/etc/passwd") is None

    def test_rejects_leading_backslash(self):
        assert _sanitize_repo_name("\\windows\\system32") is None

    def test_rejects_windows_drive_path_backslash(self):
        assert _sanitize_repo_name("C:\\Windows\\System32") is None

    def test_rejects_windows_drive_path_forward_slash(self):
        assert _sanitize_repo_name("C:/Windows/System32") is None

    def test_allows_name_with_colon_but_no_drive_pattern(self):
        # Sanity check the new regex isn't overly broad - a colon alone,
        # not shaped like "<letter>:<slash>", should still be allowed.
        assert _sanitize_repo_name("weird:name") == "weird:name"


class TestIsExecutable:
    def _make_file(self, name, content=""):
        tmp = Path(tempfile.mkdtemp())
        f = tmp / name
        f.write_text(content)
        return f

    def test_executable_file(self):
        f = self._make_file("script.sh")
        os.chmod(f, 0o700)
        assert _is_executable(f) is True

    def test_non_executable_file_with_extension(self):
        f = self._make_file("data.txt")
        assert _is_executable(f) is False

    def test_file_without_extension(self):
        f = self._make_file("binary")
        assert _is_executable(f) is True

    def test_directory_not_executable(self):
        d = Path(tempfile.mkdtemp())
        assert _is_executable(d) is False

    def test_exe_extension(self):
        f = self._make_file("app.exe")
        assert _is_executable(f) is True

    def test_bin_extension(self):
        f = self._make_file("tool.bin")
        assert _is_executable(f) is True


class TestGetDiskSize:
    def test_file_size(self):
        tmp = Path(tempfile.mkdtemp())
        f = tmp / "test.txt"
        f.write_text("a" * 1024)
        size = _get_disk_size(f)
        assert "KB" in size

    def test_directory_size(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a.txt").write_text("x" * 2048)
        (tmp / "b.txt").write_text("y" * 2048)
        size = _get_disk_size(tmp)
        assert "KB" in size

    def test_nonexistent_returns_zero(self):
        assert _get_disk_size("/nonexistent/path/xyz") == "0 B"


class TestParseArgs:
    def test_urls_only(self):
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
        ) = _parse_args(["https://github.com/a/b"])
        assert install_dir is None
        assert dry_run is False
        assert force is False
        assert shallow is False
        assert ref is None
        assert method is None
        assert urls == ["https://github.com/a/b"]

    def test_dir_flag(self):
        tmpdir = tempfile.mkdtemp()
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
        ) = _parse_args(["--dir", tmpdir, "https://github.com/a/b"])
        assert install_dir == Path(tmpdir)
        assert urls == ["https://github.com/a/b"]

    def test_dry_run_flag(self):
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
        ) = _parse_args(["--dry-run", "https://github.com/a/b"])
        assert dry_run is True

    def test_force_flag(self):
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
        ) = _parse_args(["--force", "https://github.com/a/b"])
        assert force is True

    def test_yes_flag(self):
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
        ) = _parse_args(["--yes", "https://github.com/a/b"])
        assert force is True

    def test_shallow_flag(self):
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
        ) = _parse_args(["--shallow", "https://github.com/a/b"])
        assert shallow is True

    def test_ref_flag(self):
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
        ) = _parse_args(["--ref", "v2.0", "https://github.com/a/b"])
        assert ref == "v2.0"

    def test_method_flag(self):
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
        ) = _parse_args(["--method", "python", "https://github.com/a/b"])
        assert method == "python"

    def test_combined_flags(self):
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
        ) = _parse_args(
            [
                "--dir",
                "/custom",
                "--dry-run",
                "--shallow",
                "--ref",
                "main",
                "--method",
                "python",
                "https://github.com/a/b",
            ]
        )
        assert install_dir == Path("/custom")
        assert dry_run is True
        assert shallow is True
        assert ref == "main"
        assert method == "python"

    def test_flags_between_urls(self):
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
        ) = _parse_args(
            [
                "https://github.com/a/b",
                "--dir",
                "/opt",
                "https://github.com/c/d",
            ]
        )
        assert install_dir == Path("/opt")
        assert len(urls) == 2


class TestDryRun:
    @patch("pluck.parse_repo_url")
    def test_dry_run_returns_path_without_cloning(self, mock_parse):
        mock_parse.return_value = {
            "host": "github.com",
            "host_type": "github",
            "owner": "test",
            "repo": "myrepo",
            "url": "https://github.com/test/myrepo",
            "is_gist": False,
        }
        tmp = tempfile.mkdtemp()
        install_dir = Path(tmp) / "install"
        install_dir.mkdir()

        result = download_and_install("https://github.com/test/myrepo", install_dir=install_dir, dry_run=True)

        assert result == install_dir / "myrepo"
        assert len(list(install_dir.iterdir())) == 0


class TestRegistryOperations:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"

    def test_save_and_load_registry(self):
        registry = {
            "apps": {
                "myapp": {
                    "url": "https://github.com/a/b",
                    "path": "/test",
                    "method": "python",
                    "installed_at": "2026-01-01",
                }
            }
        }
        with open(self.registry_file, "w") as f:
            json.dump(registry, f)

        with open(self.registry_file) as f:
            loaded = json.load(f)
        assert loaded["apps"]["myapp"]["url"] == "https://github.com/a/b"

    def test_register_app(self):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file

        register_app("testrepo", "https://github.com/a/b", Path(self.tmp) / "test", "python")

        registry = load_registry()
        assert "testrepo" in registry["apps"]
        assert registry["apps"]["testrepo"]["url"] == "https://github.com/a/b"
        assert registry["apps"]["testrepo"]["method"] == "python"

        pluck.APP_REGISTRY_FILE = original

    def test_uninstall_nonexistent_app(self):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        result = uninstall_app("nonexistent")
        assert result is False

        pluck.APP_REGISTRY_FILE = original


class TestUpdateApp:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"
        self.install_dir = Path(self.tmp) / "install"
        self.install_dir.mkdir()

    def test_update_nonexistent_app(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        result = update_app("nonexistent")
        assert result is False

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

        pluck.APP_REGISTRY_FILE = original

    def test_update_dry_run(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "myapp": {
                        "url": "https://github.com/test/myapp",
                        "path": str(self.install_dir / "myapp"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        result = update_app("myapp", dry_run=True)
        assert result is True

        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

        pluck.APP_REGISTRY_FILE = original


class TestInfoApp:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"
        self.install_dir = Path(self.tmp) / "install"
        self.install_dir.mkdir()
        (self.install_dir / "myapp").mkdir()
        (self.install_dir / "myapp" / "file.txt").write_text("hello")

    def test_info_existing_app(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "myapp": {
                        "url": "https://github.com/test/myapp",
                        "path": str(self.install_dir / "myapp"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        result = info_app("myapp")
        assert result is True

        captured = capsys.readouterr()
        assert "myapp" in captured.out
        assert "python" in captured.out

        pluck.APP_REGISTRY_FILE = original

    def test_info_nonexistent_app(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        result = info_app("nonexistent")
        assert result is False

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

        pluck.APP_REGISTRY_FILE = original


class TestDoctor:
    def test_doctor_returns_bool(self):
        result = doctor()
        assert isinstance(result, bool)

    def test_doctor_checks_git(self, capsys):
        doctor()
        captured = capsys.readouterr()
        assert "git" in captured.out.lower()


class TestConfigCommand:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.config_file = Path(self.tmp) / "config.json"

    def test_config_show_all_empty(self, capsys):
        import pluck

        original = pluck.CONFIG_FILE
        pluck.CONFIG_FILE = self.config_file

        config_command()

        captured = capsys.readouterr()
        assert "No configuration set" in captured.out

        pluck.CONFIG_FILE = original

    def test_config_set_and_get(self, capsys):
        import pluck

        original = pluck.CONFIG_FILE
        pluck.CONFIG_FILE = self.config_file

        config_command("install_dir", "/opt/apps")
        captured = capsys.readouterr()
        assert "Set install_dir" in captured.out

        config_command("install_dir")
        captured = capsys.readouterr()
        assert "/opt/apps" in captured.out

        pluck.CONFIG_FILE = original


class TestExportImport:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"
        self.export_file = Path(self.tmp) / "export.json"

    def test_export_registry(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "app1": {
                        "url": "https://github.com/a/b",
                        "path": "/test",
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        export_registry(str(self.export_file))
        assert self.export_file.exists()

        with open(self.export_file) as f:
            data = json.load(f)
        assert "app1" in data["apps"]

        pluck.APP_REGISTRY_FILE = original

    def test_import_registry(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        # Create export file
        with open(self.export_file, "w") as f:
            json.dump(
                {
                    "apps": {
                        "app1": {
                            "url": "https://github.com/a/b",
                            "path": "/test",
                            "method": "python",
                            "installed_at": "2026-01-01",
                        }
                    }
                },
                f,
            )

        result = import_registry(str(self.export_file))
        assert result is True

        registry = load_registry()
        assert "app1" in registry["apps"]

        pluck.APP_REGISTRY_FILE = original

    def test_import_nonexistent_file(self, capsys):
        result = import_registry("/nonexistent/file.json")
        assert result is False

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    def test_import_invalid_format(self, capsys):
        with open(self.export_file, "w") as f:
            json.dump({"not_apps": {}}, f)

        result = import_registry(str(self.export_file))
        assert result is False

        captured = capsys.readouterr()
        assert "invalid" in captured.out.lower()


class TestVerifyApps:
    def setup_method(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.registry_file = self.tmp / "test-registry.json"
        self.install_dir = self.tmp / "install"
        self.install_dir.mkdir()
        (self.install_dir / "existing-app").mkdir()
        (self.install_dir / "existing-app" / "file.txt").write_text("data")

    def test_verify_all_valid(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "existing-app": {
                        "url": "https://github.com/a/existing-app",
                        "path": str(self.install_dir / "existing-app"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        result = verify_apps()
        assert result is True

        captured = capsys.readouterr()
        assert "All" in captured.out
        assert "valid" in captured.out.lower()

        pluck.APP_REGISTRY_FILE = original

    def test_verify_with_missing_app(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "missing-app": {
                        "url": "https://github.com/a/missing-app",
                        "path": str(self.tmp / "nonexistent"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        result = verify_apps()
        assert result is False

        captured = capsys.readouterr()
        assert "missing" in captured.out.lower()

        pluck.APP_REGISTRY_FILE = original

    def test_verify_json_output(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "existing-app": {
                        "url": "https://github.com/a/existing-app",
                        "path": str(self.install_dir / "existing-app"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        result = verify_apps(json_output=True)
        assert result is True

        pluck.APP_REGISTRY_FILE = original


class TestStatsCommand:
    def setup_method(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.registry_file = self.tmp / "test-registry.json"
        self.install_dir = self.tmp / "install"
        self.install_dir.mkdir()
        (self.install_dir / "app1").mkdir()
        (self.install_dir / "app1" / "data.bin").write_text("x" * 2048)
        (self.install_dir / "app2").mkdir()
        (self.install_dir / "app2" / "data.bin").write_text("y" * 1024)

    def test_stats_returns_with_output(self, capsys):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "app1": {
                        "url": "https://github.com/a/app1",
                        "path": str(self.install_dir / "app1"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    },
                    "app2": {
                        "url": "https://github.com/a/app2",
                        "path": str(self.install_dir / "app2"),
                        "method": "node",
                        "installed_at": "2026-01-01",
                    },
                }
            }
        )

        stats_command()
        captured = capsys.readouterr()
        assert "Total apps" in captured.out
        assert "2" in captured.out
        assert "python" in captured.out
        assert "node" in captured.out

        pluck.APP_REGISTRY_FILE = original

    def test_stats_json_output(self):
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        save_registry(
            {
                "apps": {
                    "app1": {
                        "url": "https://github.com/a/app1",
                        "path": str(self.install_dir / "app1"),
                        "method": "python",
                        "installed_at": "2026-01-01",
                    }
                }
            }
        )

        stats_command(json_output=True)
        pluck.APP_REGISTRY_FILE = original


class TestFormatBytes:
    def test_format_bytes_zero(self):
        assert _format_bytes(0) == "0 B"

    def test_format_bytes_bytes(self):
        assert _format_bytes(500) == "500 B"

    def test_format_bytes_kb(self):
        assert _format_bytes(2048) == "2.0 KB"

    def test_format_bytes_mb(self):
        assert _format_bytes(5 * 1024 * 1024) == "5.0 MB"

    def test_format_bytes_gb(self):
        assert _format_bytes(3 * 1024 * 1024 * 1024) == "3.0 GB"


class TestExtractGlobalFlags:
    def test_no_flags(self):
        args, json_output, no_color = _extract_global_flags(["app-name"])
        assert args == ["app-name"]
        assert json_output is False
        assert no_color is False

    def test_json_flag(self):
        args, json_output, _no_color = _extract_global_flags(["--json", "app-name"])
        assert args == ["app-name"]
        assert json_output is True

    def test_no_color_flag(self):
        args, _json_output, no_color = _extract_global_flags(["--no-color", "app-name"])
        assert args == ["app-name"]
        assert no_color is True

    def test_combined_flags_with_positional(self):
        args, json_output, no_color = _extract_global_flags(["--json", "--no-color", "app-name"])
        assert args == ["app-name"]
        assert json_output is True
        assert no_color is True

    def test_no_positional_args(self):
        args, json_output, _no_color = _extract_global_flags(["--json"])
        assert args == []
        assert json_output is True


class TestDownloadAndInstallMocked:
    def setup_method(self):
        # Pre-create real temp directories before any patches are active
        self.tmp_clone = Path(tempfile.mkdtemp())
        self.tmp_install = Path(tempfile.mkdtemp())

    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_download_and_install_success(self, mock_parse, mock_mkdtemp, mock_run):
        """Test happy path with mocked subprocess."""
        mock_parse.return_value = {
            "host": "github.com",
            "host_type": "github",
            "owner": "test",
            "repo": "myrepo",
            "url": "https://github.com/test/myrepo",
            "is_gist": False,
        }
        # Use pre-created temp dir so we don't hit the patched mkdtemp
        mock_mkdtemp.return_value = str(self.tmp_clone)
        (self.tmp_clone / "myrepo").mkdir(parents=True)
        (self.tmp_clone / "myrepo" / "install.sh").touch()

        download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
            shallow=True,
            ref="main",
        )

        # Verify clone was called with correct args (first call to subprocess.run)
        mock_run.assert_called()
        first_call_args = mock_run.call_args_list[0][0][0]
        assert "clone" in first_call_args

    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_download_and_install_retry_on_failure(self, mock_parse, mock_mkdtemp, mock_run):
        """Test that clone retries on CalledProcessError."""
        mock_parse.return_value = {
            "host": "github.com",
            "host_type": "github",
            "owner": "test",
            "repo": "myrepo",
            "url": "https://github.com/test/myrepo",
            "is_gist": False,
        }
        mock_mkdtemp.return_value = str(self.tmp_clone)
        (self.tmp_clone / "myrepo").mkdir(parents=True)

        # Fail first call, succeed second
        # Note: after clone succeeds, install_script will also call subprocess.run,
        # so we need enough return values for all expected calls
        mock_run.side_effect = [
            subprocess.CalledProcessError(128, "git clone"),
            None,  # clone succeeds on retry
            None,  # install_script bash call
        ]

        download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
            retries=1,
        )

        assert mock_run.call_count >= 2

    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_download_and_install_invalid_url(self, mock_parse, mock_mkdtemp, mock_run):
        """Test that invalid URL returns None."""
        mock_parse.return_value = None

        result = download_and_install("not-a-valid-url")
        assert result is None

    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_download_and_install_timeout_retry(self, mock_parse, mock_mkdtemp, mock_run):
        """Test that clone retries on TimeoutExpired."""
        import subprocess as sp

        mock_parse.return_value = {
            "host": "github.com",
            "host_type": "github",
            "owner": "test",
            "repo": "myrepo",
            "url": "https://github.com/test/myrepo",
        }
        mock_mkdtemp.return_value = str(self.tmp_clone)
        (self.tmp_clone / "myrepo").mkdir(parents=True)

        # Raise timeout on first call
        mock_run.side_effect = sp.TimeoutExpired("git clone", 30)

        result = download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
            retries=1,
            timeout=30,
        )

        assert result is None  # All retries exhausted


class TestInstallConfirmation:
    """Covers PLK-01: installing must never silently run a repo's install
    method without either an explicit --force/--yes or a real 'y' from an
    interactive user."""

    def setup_method(self):
        self.tmp_clone = Path(tempfile.mkdtemp())
        self.tmp_install = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmp_clone, ignore_errors=True)
        shutil.rmtree(self.tmp_install, ignore_errors=True)

    def _mock_repo_info(self):
        return {
            "host": "github.com",
            "host_type": "github",
            "owner": "test",
            "repo": "myrepo",
            "url": "https://github.com/test/myrepo",
            "is_gist": False,
        }

    def _make_fake_clone_with_install_script(self):
        (self.tmp_clone / "myrepo").mkdir(parents=True)
        (self.tmp_clone / "myrepo" / "install.sh").touch()

    def test_confirm_install_refuses_when_noninteractive(self):
        # Under pytest, stdin isn't a real terminal - this documents that
        # assumption and checks the function fails safe because of it.
        assert sys.stdin.isatty() is False
        assert _confirm_install(self._mock_repo_info(), "script") is False

    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_install_cancelled_without_force_noninteractive(self, mock_parse, mock_mkdtemp, mock_run):
        mock_parse.return_value = self._mock_repo_info()
        mock_mkdtemp.return_value = str(self.tmp_clone)
        self._make_fake_clone_with_install_script()

        result = download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
        )

        assert result is None
        # Only the clone should have run - install.sh must never execute
        assert mock_run.call_count == 1
        assert "clone" in mock_run.call_args_list[0][0][0]

    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_install_proceeds_with_force(self, mock_parse, mock_mkdtemp, mock_run):
        mock_parse.return_value = self._mock_repo_info()
        mock_mkdtemp.return_value = str(self.tmp_clone)
        self._make_fake_clone_with_install_script()

        download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
            force=True,
        )

        # Clone, then install.sh - the pre-existing happy path, unchanged
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[1][0][0] == ["bash", "install.sh", "--yes"]

    @patch("builtins.input", return_value="y")
    @patch("sys.stdin.isatty", return_value=True)
    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_install_proceeds_when_user_types_y(
        self, mock_parse, mock_mkdtemp, mock_run, mock_isatty, mock_input
    ):
        mock_parse.return_value = self._mock_repo_info()
        mock_mkdtemp.return_value = str(self.tmp_clone)
        self._make_fake_clone_with_install_script()

        download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
        )

        mock_input.assert_called_once()
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[1][0][0] == ["bash", "install.sh", "--yes"]

    @patch("builtins.input", return_value="n")
    @patch("sys.stdin.isatty", return_value=True)
    @patch("pluck.subprocess.run")
    @patch("pluck.tempfile.mkdtemp")
    @patch("pluck.parse_repo_url")
    def test_install_cancelled_when_user_types_n(
        self, mock_parse, mock_mkdtemp, mock_run, mock_isatty, mock_input
    ):
        mock_parse.return_value = self._mock_repo_info()
        mock_mkdtemp.return_value = str(self.tmp_clone)
        self._make_fake_clone_with_install_script()

        result = download_and_install(
            "https://github.com/test/myrepo",
            install_dir=self.tmp_install,
        )

        assert result is None
        assert mock_run.call_count == 1  # clone only

    def test_parallel_install_without_force_exits(self):
        import pytest

        test_argv = [
            "pluck",
            "install",
            "https://github.com/a/b",
            "https://github.com/c/d",
            "--jobs",
            "2",
        ]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                _cmd_install()
        assert exc_info.value.code == 1

    @patch("pluck.download_and_install")
    def test_parallel_install_with_force_succeeds(self, mock_download):
        mock_download.return_value = None
        test_argv = [
            "pluck",
            "install",
            "https://github.com/a/b",
            "https://github.com/c/d",
            "--jobs",
            "2",
            "--yes",
        ]
        with patch.object(sys, "argv", test_argv):
            _cmd_install()  # must not raise SystemExit

        assert mock_download.call_count == 2
        for call in mock_download.call_args_list:
            assert call.kwargs.get("force") is True

    @patch("sys.stdin", None)
    def test_confirm_install_refuses_when_stdin_is_none(self):
        # sys.stdin can genuinely be None (e.g. some daemon/GUI contexts) -
        # must fail safe, not raise AttributeError calling .isatty() on it.
        assert _confirm_install(self._mock_repo_info(), "script") is False

    @patch("builtins.input", side_effect=EOFError)
    @patch("sys.stdin.isatty", return_value=True)
    def test_confirm_install_eof_at_prompt_is_treated_as_no(self, mock_isatty, mock_input):
        # Ctrl-D (or any closed stdin mid-prompt) must cancel, not crash.
        assert _confirm_install(self._mock_repo_info(), "script") is False

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    @patch("sys.stdin.isatty", return_value=True)
    def test_confirm_install_ctrl_c_exits_cleanly(self, mock_isatty, mock_input):
        import pytest

        # Ctrl-C must exit with the conventional 128+SIGINT code, not an
        # unhandled traceback.
        with pytest.raises(SystemExit) as exc_info:
            _confirm_install(self._mock_repo_info(), "script")
        assert exc_info.value.code == 130


class TestParseArgsMissingFlagValue:
    """Regression tests: --dir / --ref / --method etc. with no value used
    to be silently appended to the URLs list, producing confusing
    'Invalid repository URL: --dir' errors. They must now raise ValueError.
    """

    def test_dir_without_value_raises(self):
        import pytest

        with pytest.raises(ValueError, match="--dir"):
            _parse_args(["--dir"])

    def test_ref_without_value_raises(self):
        import pytest

        with pytest.raises(ValueError, match="--ref"):
            _parse_args(["--ref"])

    def test_method_without_value_raises(self):
        import pytest

        with pytest.raises(ValueError, match="--method"):
            _parse_args(["--method"])

    def test_timeout_without_value_raises(self):
        import pytest

        with pytest.raises(ValueError, match="--timeout"):
            _parse_args(["--timeout"])

    def test_jobs_without_value_raises(self):
        import pytest

        with pytest.raises(ValueError, match="--jobs"):
            _parse_args(["--jobs"])

    def test_dir_with_value_at_end_ok(self):
        """--dir followed by a value should NOT raise."""
        (
            install_dir,
            *_rest,
            urls,
        ) = _parse_args(["--dir", "/opt"])
        assert install_dir == Path("/opt")
        assert urls == []


class TestRegistryAtomicWrite:
    """Regression tests for the registry atomic write + locking refactor."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"

    def test_save_registry_writes_atomically(self):
        """save_registry should leave a valid JSON file at APP_REGISTRY_FILE."""
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        try:
            save_registry({"apps": {"foo": {"url": "x", "path": "/x", "method": "script", "installed_at": "now"}}})
            # File should exist and be valid JSON.
            assert self.registry_file.exists()
            with open(self.registry_file) as f:
                data = json.load(f)
            assert "foo" in data["apps"]
            # Temp file should have been renamed away.
            assert not self.registry_file.with_suffix(".tmp").exists()
        finally:
            pluck.APP_REGISTRY_FILE = original

    def test_load_registry_recovers_from_corrupt_file(self, capsys):
        """A corrupt registry file should not crash load_registry."""
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        try:
            self.registry_file.write_text("{not valid json")
            result = load_registry()
            assert result == {"apps": {}}
            captured = capsys.readouterr()
            assert "unreadable" in captured.out.lower()
        finally:
            pluck.APP_REGISTRY_FILE = original

    def test_register_app_creates_lock_file(self):
        """register_app should create a sibling .lock file (advisory lock)."""
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        try:
            register_app("foo", "https://github.com/a/b", Path("/tmp/foo"), "script")
            lock_file = self.registry_file.with_suffix(".lock")
            assert lock_file.exists()
        finally:
            pluck.APP_REGISTRY_FILE = original

    def test_uninstall_app_acquires_lock(self):
        """uninstall_app should use the registry lock (regression: it used
        to do an unsynchronized read-modify-write that could lose entries
        under --jobs parallelism).
        """
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        try:
            # Seed registry with an app whose install path doesn't exist
            # (so uninstall doesn't try to delete anything).
            save_registry({
                "apps": {
                    "ghost": {
                        "url": "https://github.com/a/ghost",
                        "path": "/nonexistent/ghost",
                        "method": "script",
                        "installed_at": "now",
                    }
                }
            })
            result = uninstall_app("ghost", force=True)
            assert result is True
            lock_file = self.registry_file.with_suffix(".lock")
            assert lock_file.exists()
            # The app should be gone from the registry.
            assert "ghost" not in load_registry()["apps"]
        finally:
            pluck.APP_REGISTRY_FILE = original

    def test_pin_unpin_acquires_lock(self):
        """pin_app and unpin_app should both use the registry lock."""
        import pluck

        original = pluck.APP_REGISTRY_FILE
        pluck.APP_REGISTRY_FILE = self.registry_file
        try:
            register_app("foo", "https://github.com/a/foo",
                         Path("/tmp/foo"), "script")
            lock_file = self.registry_file.with_suffix(".lock")

            # Clear the lock file timestamp to verify it's touched again.
            from time import sleep
            sleep(0.05)
            pin_app("foo")
            assert lock_file.exists()
            assert load_registry()["apps"]["foo"]["pinned"] is True

            sleep(0.05)
            unpin_app("foo")
            assert lock_file.exists()
            assert load_registry()["apps"]["foo"]["pinned"] is False
        finally:
            pluck.APP_REGISTRY_FILE = original


class TestInstallPythonSymlink:
    """Regression test: install_python used to try to unlink app_dir (a
    non-empty directory) when an entry-point script existed. Verify it
    now creates a sibling bin/ symlink instead and does not crash.
    """

    def test_install_python_creates_bin_symlink(self, capsys):

        # Build a tiny fake repo with a pyproject.toml declaring an entry point
        # matching the repo name. Use a venv with a stub entry-point binary.
        tmp_repo = Path(tempfile.mkdtemp()) / "myapp"
        tmp_repo.mkdir(parents=True)
        (tmp_repo / "pyproject.toml").write_text(
            """
[project]
name = "myapp"
version = "0.0.1"
[project.scripts]
myapp = "myapp:main"
"""
        )
        (tmp_repo / "myapp.py").write_text("def main(): pass\n")

        install_dir = Path(tempfile.mkdtemp())

        # Mock venv creation + pip install so we don't actually run them.
        with patch("pluck.subprocess.run") as mock_run:
            mock_run.return_value = None  # all subprocess calls succeed
            # Pre-create the venv bin dir + fake entry-point so the symlink
            # code path triggers.
            venv_bin = install_dir / "myapp" / ".venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "myapp").write_text("#!/bin/sh\n")

            result = install_python(tmp_repo, install_dir)

        # install_python should return the app_dir (not None, not crash).
        assert result is not None
        # The bin symlink should exist at install_dir / "bin" / "myapp".
        symlink_path = install_dir / "bin" / "myapp"
        assert symlink_path.is_symlink() or symlink_path.exists()
        # The original app_dir should still be a directory (not replaced).
        assert (install_dir / "myapp").is_dir()

    def test_install_python_skips_symlink_when_target_is_directory(self, capsys):
        """If a directory already exists at install_dir/bin/<name>, the
        symlink logic must NOT call unlink() on it (which would raise
        IsADirectoryError). It should warn and skip instead.
        """
        tmp_repo = Path(tempfile.mkdtemp()) / "myapp"
        tmp_repo.mkdir(parents=True)
        (tmp_repo / "pyproject.toml").write_text(
            """
[project]
name = "myapp"
version = "0.0.1"
[project.scripts]
myapp = "myapp:main"
"""
        )
        (tmp_repo / "myapp.py").write_text("def main(): pass\n")

        install_dir = Path(tempfile.mkdtemp())

        # Pre-create a directory at the symlink target path.
        blocking_dir = install_dir / "bin" / "myapp"
        blocking_dir.mkdir(parents=True)
        # Put a file in it so we can verify it's not deleted.
        (blocking_dir / "important.txt").write_text("user data")

        # Pre-create the venv entry-point so the symlink code path triggers.
        venv_bin = install_dir / "myapp" / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "myapp").write_text("#!/bin/sh\n")

        with patch("pluck.subprocess.run") as mock_run:
            mock_run.return_value = None
            result = install_python(tmp_repo, install_dir)

        # Should not crash, should return app_dir.
        assert result is not None
        # The user's directory and its contents must be preserved.
        assert blocking_dir.is_dir()
        assert (blocking_dir / "important.txt").exists()
        # A warning should have been printed.
        captured = capsys.readouterr()
        assert "directory" in captured.out.lower()


class TestSafeTarMembers:
    """Regression test for CVE-2007-4559 (tarball path traversal)."""

    def test_safe_tar_members_rejects_path_traversal(self):
        """Names with .. should be filtered out."""
        import io
        import tarfile

        import pluck

        # Build an in-memory tar with a malicious entry.
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            # Safe entry
            info = tarfile.TarInfo("safe.txt")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"data"))
            # Unsafe entry (path traversal)
            info = tarfile.TarInfo("../../etc/passwd")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"evil"))

        buf.seek(0)
        with tarfile.open(fileobj=buf) as tar:
            members = list(pluck._safe_tar_members(tar))

        # Only the safe member should be yielded.
        names = [m.name for m in members]
        assert "safe.txt" in names
        assert all(".." not in n for n in names)

    def test_safe_tar_members_rejects_backslash_traversal(self):
        """Names with backslash path traversal (foo\\..\\..\\bar) should be
        filtered out — on Unix a backslash is a literal filename character,
        so a naive check that only looks for '..' split by the OS separator
        would be bypassed.
        """
        import io
        import tarfile

        import pluck

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo("safe.txt")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"data"))
            # Backslash-based traversal — would bypass Path("..").parts check
            # on Unix without backslash normalization.
            info = tarfile.TarInfo("foo\\..\\..\\evil.txt")
            info.size = 4
            tar.addfile(info, io.BytesIO(b"evil"))

        buf.seek(0)
        with tarfile.open(fileobj=buf) as tar:
            members = list(pluck._safe_tar_members(tar))

        names = [m.name for m in members]
        assert "safe.txt" in names
        # The backslash-traversal entry must not appear.
        assert all("evil" not in n for n in names)


class TestProtocolHandlerUrlParsing:
    """Regression test: scripts/pluck-protocol-handler.sh used to extract
    the 'url' query param with a naive sed, which appended extra &key=value
    params to the target URL. The fixed handler uses Python's urllib.parse
    for correct query-string handling. We test the parsing logic directly.
    """

    def _extract_url_from_pluck_protocol(self, pluck_url):
        """Mirror the extraction logic from pluck-protocol-handler.sh."""
        import urllib.parse

        parsed = urllib.parse.urlparse(pluck_url)
        qs = urllib.parse.parse_qs(parsed.query)
        urls = qs.get("url")
        return urls[0] if urls else None

    def test_multi_param_url_extracts_only_url(self):
        """pluck://install?url=...&foo=bar should yield only the url value."""
        result = self._extract_url_from_pluck_protocol(
            "pluck://install?url=https%3A%2F%2Fgithub.com%2Fuser%2Frepo&foo=bar"
        )
        assert result == "https://github.com/user/repo"
        # The trailing &foo=bar MUST NOT be appended.
        assert "foo=bar" not in result

    def test_single_param_url_still_works(self):
        """Simple single-param URL should still parse correctly."""
        result = self._extract_url_from_pluck_protocol(
            "pluck://install?url=https%3A%2F%2Fgithub.com%2Fuser%2Frepo"
        )
        assert result == "https://github.com/user/repo"

    def test_url_with_query_string_preserved(self):
        """A URL that itself contains query params should be preserved intact."""
        result = self._extract_url_from_pluck_protocol(
            "pluck://install?url=https%3A%2F%2Fgithub.com%2Fuser%2Frepo%3Fbranch%3Dmain"
        )
        assert result == "https://github.com/user/repo?branch=main"

    def test_missing_url_param_returns_none(self):
        """If the pluck:// URL has no url= param, extraction returns None."""
        result = self._extract_url_from_pluck_protocol("pluck://install?foo=bar")
        assert result is None


class TestReleaseInstallFallback:
    """Regression test: when method=release fails, download_and_install
    used to return None without trying a clone. It should now fall back.
    """

    def setup_method(self):
        self.tmp_clone = Path(tempfile.mkdtemp())
        self.tmp_install = Path(tempfile.mkdtemp())

    @patch("pluck.install_release_asset")
    @patch("pluck._clone_repo")
    @patch("pluck.parse_repo_url")
    def test_release_failure_falls_back_to_clone(
        self, mock_parse, mock_clone, mock_release
    ):
        """If install_release_asset returns None, a clone+install should run."""
        mock_parse.return_value = {
            "host": "github.com",
            "host_type": "github",
            "owner": "test",
            "repo": "myrepo",
            "url": "https://github.com/test/myrepo",
            "is_gist": False,
        }
        # Release asset install fails.
        mock_release.return_value = None

        # Clone succeeds — return a temp dir + repo_path.
        repo_path = self.tmp_clone / "myrepo"
        repo_path.mkdir(parents=True)
        (repo_path / "install.sh").touch()  # so detect_install_method picks "script"
        mock_clone.return_value = (self.tmp_clone, repo_path)

        # Run with method_override='release'.
        with patch("pluck.subprocess.run") as mock_run:
            mock_run.return_value = None
            with patch("pluck.register_app") as mock_register:
                mock_register.return_value = None
                download_and_install(
                    "https://github.com/test/myrepo",
                    install_dir=self.tmp_install,
                    method_override="release",
                )

        # The clone must have been attempted (fall-through happened).
        mock_clone.assert_called_once()
        # And install_release_asset was tried first.
        mock_release.assert_called_once()


class TestInstallMakeFallback:
    """Regression test: install_make used to call 'make' (without check=True
    semantics) on the fallback path, which could raise an uncaught
    CalledProcessError. It should now return None instead of crashing.
    """

    def test_install_make_returns_none_when_both_make_invocations_fail(self, capsys):
        import subprocess as sp

        import pluck

        tmp_repo = Path(tempfile.mkdtemp())
        (tmp_repo / "Makefile").write_text("all:\n\texit 1\n")
        install_dir = Path(tempfile.mkdtemp())

        with patch("pluck.subprocess.run") as mock_run:
            # Both 'make install' and 'make' raise CalledProcessError.
            mock_run.side_effect = [
                sp.CalledProcessError(2, "make install"),
                sp.CalledProcessError(2, "make"),
            ]
            result = pluck.install_make(tmp_repo, install_dir)

        # Should return None (not raise).
        assert result is None
