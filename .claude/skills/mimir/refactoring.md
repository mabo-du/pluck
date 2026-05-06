---
name: mimir-refactoring
description: >
  Plan safe refactors using dependency mapping.
  Use for renames, interface changes, module splits, or any
  structural change that affects multiple files.
---

## Prerequisite

**Ensure the MCP daemon is running** before using these tools:
```bash
mimir daemon start
```

## Safe refactor pattern

1. `impact(target, "both")` — understand full scope
2. `rename(old, new, dry_run: true)` — preview all affected files
3. Check `text_search_edits` (dynamic references, not in graph)
4. Execute in order: deepest dependents first, then the symbol itself
