---
name: mimir-antigravity
description: >
  Mimir code intelligence for Antigravity editor.
  Use when working in the Antigravity IDE to explore, debug, or refactor code
  with graph-backed context. Antigravity uses github.copilot.mcpServers config.
---

## Prerequisite

**Ensure the MCP daemon is running** before using these tools:
```bash
mimir daemon start
```

## Antigravity MCP config location

Mimir configures itself at:
`~/Library/Application Support/Antigravity/User/settings.json`

Key: `github.copilot.mcpServers`

## Available tools

- `query()` — semantic + BM25 search across the repo
- `context(symbol)` — 360-degree view: callers, callees, cluster
- `impact(symbol, direction)` — blast radius before editing
- `detect_changes()` — pre-commit risk analysis
- `rename(old, new)` — safe coordinated rename
- `cypher(query)` — raw graph queries
