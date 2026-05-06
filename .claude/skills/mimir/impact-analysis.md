---
name: mimir-impact
description: >
  Analyse blast radius before making any code change.
  Use before editing any function, class, or interface.
  Always run impact analysis before refactoring shared utilities.
---

## Prerequisite

**Ensure the MCP daemon is running** before using these tools:
```bash
mimir daemon start
```

## Pre-edit impact check pattern

BEFORE editing any symbol:
1. `impact(symbolName, "upstream", minConfidence: 0.7)`
2. Review depth-1 callers (WILL BREAK)
3. Review depth-2 (LIKELY AFFECTED)
4. Inform user of risk level before proceeding
