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
if [[ "$input" == pluck://* ]]; then
    target_url=$(python3 - "$input" <<'PY'
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
