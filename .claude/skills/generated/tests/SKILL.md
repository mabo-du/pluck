---
name: tests
description: "Skill for the Tests area of gh-install. 101 symbols across 2 files."
---

# Tests

101 symbols | 2 files | Cohesion: 76%

## When to Use

- Working with code in `tests/`
- Understanding how test_detects_install_script, test_detects_python_pyproject, test_detects_python_setup work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/test_gh_install.py` | _make_temp_repo, test_detects_install_script, test_detects_python_pyproject, test_detects_python_setup, test_detects_node (+65) |
| `src/gh_install.py` | detect_install_method, _parse_gist_url, parse_github_url, _enable_colors, _parse_args (+26) |

## Entry Points

Start here when exploring this area:

- **`test_detects_install_script`** (Function) — `tests/test_gh_install.py:122`
- **`test_detects_python_pyproject`** (Function) — `tests/test_gh_install.py:126`
- **`test_detects_python_setup`** (Function) — `tests/test_gh_install.py:130`
- **`test_detects_node`** (Function) — `tests/test_gh_install.py:134`
- **`test_detects_go_mod`** (Function) — `tests/test_gh_install.py:138`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_detects_install_script` | Function | `tests/test_gh_install.py` | 122 |
| `test_detects_python_pyproject` | Function | `tests/test_gh_install.py` | 126 |
| `test_detects_python_setup` | Function | `tests/test_gh_install.py` | 130 |
| `test_detects_node` | Function | `tests/test_gh_install.py` | 134 |
| `test_detects_go_mod` | Function | `tests/test_gh_install.py` | 138 |
| `test_detects_go_files` | Function | `tests/test_gh_install.py` | 142 |
| `test_detects_rust` | Function | `tests/test_gh_install.py` | 146 |
| `test_detects_makefile` | Function | `tests/test_gh_install.py` | 150 |
| `test_detects_binary_release` | Function | `tests/test_gh_install.py` | 154 |
| `test_detects_binary_bin` | Function | `tests/test_gh_install.py` | 158 |
| `test_detects_appimage` | Function | `tests/test_gh_install.py` | 162 |
| `test_detects_deb` | Function | `tests/test_gh_install.py` | 166 |
| `test_defaults_to_download` | Function | `tests/test_gh_install.py` | 170 |
| `test_script_takes_priority_over_python` | Function | `tests/test_gh_install.py` | 174 |
| `test_python_takes_priority_over_node` | Function | `tests/test_gh_install.py` | 178 |
| `test_method_priority_respected` | Function | `tests/test_gh_install.py` | 182 |
| `test_method_priority_invalid_filtered` | Function | `tests/test_gh_install.py` | 186 |
| `detect_install_method` | Function | `src/gh_install.py` | 316 |
| `test_standard_https_url` | Function | `tests/test_gh_install.py` | 40 |
| `test_standard_http_url` | Function | `tests/test_gh_install.py` | 48 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → _enable_colors` | cross_community | 3 |
| `Install_script → _is_executable` | cross_community | 3 |
| `Install_script → Print_success` | intra_community | 3 |
| `Install_make → _is_executable` | cross_community | 3 |
| `Install_make → Print_success` | intra_community | 3 |
| `Download_and_install → _parse_gist_url` | cross_community | 3 |
| `Register_app → Print_warning` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_12 | 10 calls |

## How to Explore

1. `gitnexus_context({name: "test_detects_install_script"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
