---
name: mimir-debugging
description: >
  Trace bugs through call chains using Mimir.
  Use when debugging an error, tracing unexpected behavior,
  or finding what calls a broken function.
---

## Prerequisite

**Ensure the MCP daemon is running** before using these tools:
```bash
mimir daemon start
```

## Debugging with graph context

1. `context(brokenFunction)` → see all callers
2. `impact(brokenFunction, "upstream")` → full blast radius
3. `query(errorMessage)` → find related code by semantic search
4. `detect_changes()` → check if recent changes caused the bug
