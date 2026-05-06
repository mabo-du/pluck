#!/usr/bin/env bash
# PreToolUse hook: intercepts grep/glob/bash tool calls
# Injects graph context for the search term into Claude's environment
# Exit 0 = allow tool to proceed (we only augment, never block)

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
QUERY=""

case "$TOOL" in
  Bash)
    # Extract search term from grep/rg/find commands
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    if echo "$CMD" | grep -qE '(grep|rg|ripgrep|find|fd)\s'; then
      # Parse first non-flag argument as the search query
      QUERY=$(echo "$CMD" | grep -oP '(?<=(grep|rg)\s+(-\w+\s+)*)"\K[^"]+|(?<=(grep|rg)\s+(-\w+\s+)*)\S+' | head -1)
    fi
    ;;
  Glob)
    QUERY=$(echo "$INPUT" | jq -r '.tool_input.pattern // empty')
    ;;
esac

# If we extracted a query, call mimir for context and append to stdout
# Claude Code merges hook stdout into tool context
if [ -n "$QUERY" ] && [ ${#QUERY} -gt 2 ]; then
  CONTEXT=$(mimir query --json --quiet "$QUERY" 2>/dev/null)
  if [ -n "$CONTEXT" ] && [ "$CONTEXT" != "null" ]; then
    # Output as hookSpecificOutput — Claude Code surfaces this as context
    jq -n \
      --arg ctx "$CONTEXT" \
      '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          additionalContext: ("Graph context for search:\n" + $ctx)
        }
      }'
  fi
fi

exit 0
