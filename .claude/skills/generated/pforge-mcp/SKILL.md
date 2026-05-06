---
name: pforge-mcp
description: "Skill for the Pforge-mcp area of gh-install. 5 symbols across 1 files."
---

# Pforge-mcp

5 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `pforge-mcp/`
- Understanding how runPforge, findProjectRoot, executeTool work
- Modifying pforge-mcp-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pforge-mcp/server.mjs` | runPforge, findProjectRoot, executeTool, createExpressApp, main |

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `runPforge` | Function | `pforge-mcp/server.mjs` | 44 |
| `findProjectRoot` | Function | `pforge-mcp/server.mjs` | 64 |
| `executeTool` | Function | `pforge-mcp/server.mjs` | 225 |
| `createExpressApp` | Function | `pforge-mcp/server.mjs` | 389 |
| `main` | Function | `pforge-mcp/server.mjs` | 505 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → RunPforge` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "runPforge"})` — see callers and callees
2. `gitnexus_query({query: "pforge-mcp"})` — find related execution flows
3. Read key files listed above for implementation details
