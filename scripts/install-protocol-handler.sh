#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# install-protocol-handler.sh — Register the pluck:// URL protocol handler
#
# After running this, clicking a pluck:// link in your browser will
# open pluck and install the repo.
#
# For the browser right-click integration:
#   1. Run this script to register the protocol handler
#   2. Follow the README section to set up the bookmarklet
#
# Browser support:
#   - Firefox: native pluck:// support after install
#   - Chrome/Chromium: native pluck:// support after install
#   - Other browsers: depends on OS-level protocol handling

set -euo pipefail

HANDLER_NAME="pluck"
HANDLER_SCRIPT="$(cd "$(dirname "$0")" && pwd)/pluck-protocol-handler.sh"

# --- Determine install locations ---
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS — use launchd plist
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_PATH="$PLIST_DIR/sh.pluck.protocol-handler.plist"

    mkdir -p "$PLIST_DIR"
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>sh.pluck.protocol-handler</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HANDLER_SCRIPT</string>
    </array>
    <key>URLProtocols</key>
    <array>
        <string>pluck</string>
    </array>
</dict>
</plist>
EOF

    # Register the protocol with the system
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
        -f "$PLIST_PATH" 2>/dev/null || true

    echo "✓ Registered pluck:// protocol handler for macOS"
    echo "  Plist: $PLIST_PATH"

else
    # Linux — use desktop entry (works with xdg-open, GNOME, KDE, etc.)
    DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    DESKTOP_PATH="$DESKTOP_DIR/pluck-handler.desktop"

    mkdir -p "$DESKTOP_DIR"
    cat > "$DESKTOP_PATH" << EOF
[Desktop Entry]
Type=Application
Name=pluck Installer
Exec=$HANDLER_SCRIPT %u
StartupNotify=false
MimeType=x-scheme-handler/pluck;
NoDisplay=true
EOF

    # Register with xdg
    if command -v xdg-mime &>/dev/null; then
        xdg-mime default pluck-handler.desktop x-scheme-handler/pluck
    fi
    if command -v xdg-open &>/dev/null; then
        xdg-open "pluck://install?url=https://github.com/user/repo" 2>/dev/null || true
    fi
    # Update desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    echo "✓ Registered pluck:// protocol handler for Linux"
    echo "  Desktop entry: $DESKTOP_PATH"
fi

chmod +x "$HANDLER_SCRIPT"

echo ""
echo " Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Restart your browser"
echo "   2. Create a bookmark with this URL as the target:"
echo ""
echo "      javascript:location.href='pluck://install?url='+encodeURIComponent(location.href)"
echo ""
echo "   3. When you're on a git repo page, click the bookmark to install it"
echo ""
echo " Or for even easier access, install the 'pluck' browser extension:"
echo "   https://gitlab.com/mabodu/pluck/-/tree/main/assets/browser-extension"
echo " (coming soon)"
