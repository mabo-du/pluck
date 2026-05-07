import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gh_install import (
    SHARED_PATHS,
    VALID_METHODS,
    _detect_host_type,
    _extract_global_flags,
    _format_bytes,
    _get_disk_size,
    _is_executable,
    _parse_args,
    _parse_gist_url,
    _sanitize_repo_name,
    config_command,
    detect_install_method,
    doctor,
    download_and_install,
    export_registry,
    import_registry,
    info_app,
    load_registry,
    parse_repo_url,
    register_app,
    save_registry,
    stats_command,
    uninstall_app,
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
        assert len(VALID_METHODS) == 8

    def test_all_expected_methods_present(self):
        expected = {"script", "binary", "python", "node", "go", "rust", "make", "download"}
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


class TestIsExecutable:
    def _make_file(self, name, content=""):
        tmp = Path(tempfile.mkdtemp())
        f = tmp / name
        f.write_text(content)
        return f

    def test_executable_file(self):
        f = self._make_file("script.sh")
        os.chmod(f, 0o755)
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
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["https://github.com/a/b"])
        assert install_dir is None
        assert dry_run is False
        assert force is False
        assert shallow is False
        assert ref is None
        assert method is None
        assert urls == ["https://github.com/a/b"]

    def test_dir_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--dir", "/tmp/test", "https://github.com/a/b"])
        assert install_dir == Path("/tmp/test")
        assert urls == ["https://github.com/a/b"]

    def test_dry_run_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--dry-run", "https://github.com/a/b"])
        assert dry_run is True

    def test_force_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--force", "https://github.com/a/b"])
        assert force is True

    def test_yes_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--yes", "https://github.com/a/b"])
        assert force is True

    def test_shallow_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--shallow", "https://github.com/a/b"])
        assert shallow is True

    def test_ref_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--ref", "v2.0", "https://github.com/a/b"])
        assert ref == "v2.0"

    def test_method_flag(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args(["--method", "python", "https://github.com/a/b"])
        assert method == "python"

    def test_combined_flags(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args([
            "--dir", "/custom", "--dry-run", "--shallow",
            "--ref", "main", "--method", "python",
            "https://github.com/a/b",
        ])
        assert install_dir == Path("/custom")
        assert dry_run is True
        assert shallow is True
        assert ref == "main"
        assert method == "python"

    def test_flags_between_urls(self):
        (
            install_dir, dry_run, force, shallow, ref,
            method, json_output, timeout, retries, urls,
        ) = _parse_args([
            "https://github.com/a/b", "--dir", "/opt", "https://github.com/c/d",
        ])
        assert install_dir == Path("/opt")
        assert len(urls) == 2


class TestDryRun:
    @patch("gh_install.parse_repo_url")
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

        result = download_and_install(
            "https://github.com/test/myrepo", install_dir=install_dir, dry_run=True
        )

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
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file

        register_app("testrepo", "https://github.com/a/b", Path("/tmp/test"), "python")

        registry = load_registry()
        assert "testrepo" in registry["apps"]
        assert registry["apps"]["testrepo"]["url"] == "https://github.com/a/b"
        assert registry["apps"]["testrepo"]["method"] == "python"

        gh_install.APP_REGISTRY_FILE = original

    def test_uninstall_nonexistent_app(self):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        result = uninstall_app("nonexistent")
        assert result is False

        gh_install.APP_REGISTRY_FILE = original


class TestUpdateApp:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"
        self.install_dir = Path(self.tmp) / "install"
        self.install_dir.mkdir()

    def test_update_nonexistent_app(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        result = update_app("nonexistent")
        assert result is False

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

        gh_install.APP_REGISTRY_FILE = original

    def test_update_dry_run(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
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

        gh_install.APP_REGISTRY_FILE = original


class TestInfoApp:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"
        self.install_dir = Path(self.tmp) / "install"
        self.install_dir.mkdir()
        (self.install_dir / "myapp").mkdir()
        (self.install_dir / "myapp" / "file.txt").write_text("hello")

    def test_info_existing_app(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
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

        gh_install.APP_REGISTRY_FILE = original

    def test_info_nonexistent_app(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({"apps": {}})

        result = info_app("nonexistent")
        assert result is False

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

        gh_install.APP_REGISTRY_FILE = original


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
        import gh_install

        original = gh_install.CONFIG_FILE
        gh_install.CONFIG_FILE = self.config_file

        config_command()

        captured = capsys.readouterr()
        assert "No configuration set" in captured.out

        gh_install.CONFIG_FILE = original

    def test_config_set_and_get(self, capsys):
        import gh_install

        original = gh_install.CONFIG_FILE
        gh_install.CONFIG_FILE = self.config_file

        config_command("install_dir", "/opt/apps")
        captured = capsys.readouterr()
        assert "Set install_dir" in captured.out

        config_command("install_dir")
        captured = capsys.readouterr()
        assert "/opt/apps" in captured.out

        gh_install.CONFIG_FILE = original


class TestExportImport:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.registry_file = Path(self.tmp) / "test-registry.json"
        self.export_file = Path(self.tmp) / "export.json"

    def test_export_registry(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
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

        gh_install.APP_REGISTRY_FILE = original

    def test_import_registry(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
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

        gh_install.APP_REGISTRY_FILE = original

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
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({
            "apps": {
                "existing-app": {
                    "url": "https://github.com/a/existing-app",
                    "path": str(self.install_dir / "existing-app"),
                    "method": "python",
                    "installed_at": "2026-01-01",
                }
            }
        })

        result = verify_apps()
        assert result is True

        captured = capsys.readouterr()
        assert "All" in captured.out
        assert "valid" in captured.out.lower()

        gh_install.APP_REGISTRY_FILE = original

    def test_verify_with_missing_app(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({
            "apps": {
                "missing-app": {
                    "url": "https://github.com/a/missing-app",
                    "path": str(self.tmp / "nonexistent"),
                    "method": "python",
                    "installed_at": "2026-01-01",
                }
            }
        })

        result = verify_apps()
        assert result is False

        captured = capsys.readouterr()
        assert "missing" in captured.out.lower()

        gh_install.APP_REGISTRY_FILE = original

    def test_verify_json_output(self, capsys):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({
            "apps": {
                "existing-app": {
                    "url": "https://github.com/a/existing-app",
                    "path": str(self.install_dir / "existing-app"),
                    "method": "python",
                    "installed_at": "2026-01-01",
                }
            }
        })

        result = verify_apps(json_output=True)
        assert result is True

        gh_install.APP_REGISTRY_FILE = original


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
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({
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
        })

        stats_command()
        captured = capsys.readouterr()
        assert "Total apps" in captured.out
        assert "2" in captured.out
        assert "python" in captured.out
        assert "node" in captured.out

        gh_install.APP_REGISTRY_FILE = original

    def test_stats_json_output(self):
        import gh_install

        original = gh_install.APP_REGISTRY_FILE
        gh_install.APP_REGISTRY_FILE = self.registry_file
        save_registry({
            "apps": {
                "app1": {
                    "url": "https://github.com/a/app1",
                    "path": str(self.install_dir / "app1"),
                    "method": "python",
                    "installed_at": "2026-01-01",
                }
            }
        })

        stats_command(json_output=True)
        gh_install.APP_REGISTRY_FILE = original


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
        args, json_output = _extract_global_flags(["app-name"])
        assert args == ["app-name"]
        assert json_output is False

    def test_json_flag(self):
        args, json_output = _extract_global_flags(["--json", "app-name"])
        assert args == ["app-name"]
        assert json_output is True

    def test_no_color_flag(self):
        args, json_output = _extract_global_flags(["--no-color", "app-name"])
        assert args == ["app-name"]
        assert json_output is False

    def test_combined_flags_with_positional(self):
        args, json_output = _extract_global_flags(["--json", "--no-color", "app-name"])
        assert args == ["app-name"]
        assert json_output is True

    def test_no_positional_args(self):
        args, json_output = _extract_global_flags(["--json"])
        assert args == []
        assert json_output is True


class TestDownloadAndInstallMocked:
    def setup_method(self):
        # Pre-create real temp directories before any patches are active
        self.tmp_clone = Path(tempfile.mkdtemp())
        self.tmp_install = Path(tempfile.mkdtemp())

    @patch("gh_install.subprocess.run")
    @patch("gh_install.tempfile.mkdtemp")
    @patch("gh_install.parse_repo_url")
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

    @patch("gh_install.subprocess.run")
    @patch("gh_install.tempfile.mkdtemp")
    @patch("gh_install.parse_repo_url")
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

    @patch("gh_install.subprocess.run")
    @patch("gh_install.tempfile.mkdtemp")
    @patch("gh_install.parse_repo_url")
    def test_download_and_install_invalid_url(self, mock_parse, mock_mkdtemp, mock_run):
        """Test that invalid URL returns None."""
        mock_parse.return_value = None

        result = download_and_install("not-a-valid-url")
        assert result is None

    @patch("gh_install.subprocess.run")
    @patch("gh_install.tempfile.mkdtemp")
    @patch("gh_install.parse_repo_url")
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
