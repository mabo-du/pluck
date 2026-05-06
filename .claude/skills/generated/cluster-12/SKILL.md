---
name: cluster-12
description: "Skill for the Cluster_12 area of gh-install. 8 symbols across 1 files."
---

# Cluster_12

8 symbols | 1 files | Cohesion: 46%

## When to Use

- Working with code in `src/`
- Understanding how print_usage, print_header, print_warning work
- Modifying cluster_12-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/gh_install.py` | print_usage, _completion_script, print_header, print_warning, search_github (+3) |

## Entry Points

Start here when exploring this area:

- **`print_usage`** (Function) — `src/gh_install.py:70`
- **`print_header`** (Function) — `src/gh_install.py:274`
- **`print_warning`** (Function) — `src/gh_install.py:284`
- **`search_github`** (Function) — `src/gh_install.py:889`
- **`clean_registry`** (Function) — `src/gh_install.py:995`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `print_usage` | Function | `src/gh_install.py` | 70 |
| `print_header` | Function | `src/gh_install.py` | 274 |
| `print_warning` | Function | `src/gh_install.py` | 284 |
| `search_github` | Function | `src/gh_install.py` | 889 |
| `clean_registry` | Function | `src/gh_install.py` | 995 |
| `list_installed` | Function | `src/gh_install.py` | 1056 |
| `main` | Function | `src/gh_install.py` | 1205 |
| `_completion_script` | Function | `src/gh_install.py` | 131 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → _enable_colors` | cross_community | 3 |
| `Register_app → Print_warning` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 16 calls |

## How to Explore

1. `gitnexus_context({name: "print_usage"})` — see callers and callees
2. `gitnexus_query({query: "cluster_12"})` — find related execution flows
3. Read key files listed above for implementation details
