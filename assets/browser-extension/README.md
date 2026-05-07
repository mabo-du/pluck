# pluck Browser Extension

Adds a right-click context menu item to install git repos with pluck.

## Prerequisites

The [pluck protocol handler](../scripts/install-protocol-handler.sh) must be
registered on your system first:

```bash
bash scripts/install-protocol-handler.sh
```

This tells your OS to handle `pluck://` URLs by running the `pluck install` command.

## Installation

### Chrome / Brave / Edge / Chromium

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `assets/browser-extension/` folder
5. The extension is now active

### Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on**
3. Select `assets/browser-extension/manifest.json`
4. The extension is now active (for this session)

### Permanent Firefox installation

Pack the extension as a `.xpi` and sign it via Mozilla Add-ons,
or use `xpinstall.signatures.required = false` in `about:config`.

## Usage

1. Right-click any git repo link on any forge (GitHub, GitLab, Codeberg, etc.)
2. Select **Install with pluck**
3. The protocol handler launches `pluck install <url>` in your terminal

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Extension manifest (Chrome/Chromium MV3) |
| `background.js` | Context menu handler |
| `icon.png` | Extension icon (not yet provided) |
