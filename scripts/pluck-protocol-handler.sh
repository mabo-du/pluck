#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# pluck protocol handler — receives URLs via the pluck:// protocol
# and passes them to pluck install.
#
# Usage (direct):
#   pluck-protocol-handler.sh "pluck://install?url=https://github.com/user/repo"
#
# Usage (via xdg-open / browser):
#   Click a pluck:// link in your browser, and this handler is called.
#
# Browser integration steps (see install-protocol-handler.sh):
#   1. Register the protocol handler on your OS
#   2. Use a bookmarklet to send URLs to pluck://

set -euo pipefail

# Parse the pluck:// URL
# Expected format: pluck://install?url=<encoded-git-url>
input="${1:-}"

if [[ -z "$input" ]]; then
    echo "Usage: $0 pluck://install?url=<encoded-url>"
    echo "       $0 <direct-git-url>"  # also accepts a plain git URL
    exit 1
fi

# If input is a pluck:// URL, extract the actual git URL using Python's
# urllib.parse for correct query-string handling. A naive sed substitution
# would include trailing &key=value params in the URL (see CVE-style bug).
# Fall back to shell-based parsing if no Python interpreter is available
# (the shell-based version is best-effort and may include trailing params).
if [[ "$input" == pluck://* ]]; then
    if command -v python3 &>/dev/null; then
        PY_BIN=python3
    elif command -v python &>/dev/null; then
        PY_BIN=python
    else
        PY_BIN=""
    fi

    if [[ -n "$PY_BIN" ]]; then
        target_url=$("$PY_BIN" - "$input" <<'PY'
import sys
import urllib.parse

url = sys.argv[1]
parsed = urllib.parse.urlparse(url)
# pluck://install?url=... — query is in parsed.query
qs = urllib.parse.parse_qs(parsed.query)
urls = qs.get("url")
if not urls:
    sys.stderr.write("Error: no 'url' parameter in pluck:// URL\n")
    sys.exit(1)
print(urls[0])
PY
        )
    else
        # No Python interpreter — fall back to shell-based parsing.
        # Best-effort: strips the prefix, URL-decodes, and truncates at
        # the first & to drop extra query params.
        raw_url="${input#pluck://install?url=}"
        # URL-decode %XX sequences using printf
        decoded_url=$(printf '%b' "${raw_url//%/\\x}" 2>/dev/null || echo "$raw_url")
        # Truncate at first & to drop extra query params
        target_url="${decoded_url%%&*}"
        if [[ -z "$target_url" ]]; then
            echo "Error: no 'url' parameter in pluck:// URL" >&2
            exit 1
        fi
        echo "Warning: python3 not found, using shell-based URL parsing (best-effort)" >&2
    fi
else
    # Plain git URL — use directly (handy for quick use)
    target_url="$input"
fi

echo " pluck → Installing from: $target_url"
echo ""

# Dispatch to pluck
if command -v pluck &>/dev/null; then
    pluck install "$target_url"
elif command -v gh-install &>/dev/null; then
    gh-install install "$target_url"            # legacy compat alias
elif [[ -f "$(dirname "$0")/../src/pluck.py" ]]; then
    python3 "$(dirname "$0")/../src/pluck.py" install "$target_url"
elif [[ -f "$(dirname "$0")/../src/gh_install.py" ]]; then
    python3 "$(dirname "$0")/../src/gh_install.py" install "$target_url"  # legacy compat
else
    echo "Error: pluck not found. Install it first: pip install pluck" >&2
    exit 1
fi
