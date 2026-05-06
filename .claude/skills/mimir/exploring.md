---
name: mimir-exploring
description: >
  Navigate unfamiliar code using the Mimir knowledge graph.
  Use when asked to explore a codebase, find where something is implemented,
  understand how a feature works, or trace a data flow.
---

## Prerequisite

**Ensure the MCP daemon is running** before using these tools:
```bash
mimir daemon start
```

## When to use mimir tools for exploration

1. Start with resources: read `mimir://repo/{name}/context` for codebase overview
2. Use `query()` tool for natural language search: "authentication flow", "database connection"
3. Use `context()` tool for 360-degree view of any symbol
4. Use `cypher()` tool for custom graph traversal if needed

## Exploration pattern

```
query("entry points for user authentication")
→ find relevant processes
→ context("handleLogin") for full call chain
→ follow outgoing calls to understand the flow
```
