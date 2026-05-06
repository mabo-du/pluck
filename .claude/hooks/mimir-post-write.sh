#!/usr/bin/env bash
# PostToolUse hook: triggers incremental reindex after file writes or git commits
# Always async (fire-and-forget) — never blocks Claude

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

should_reindex=false
changed_file=""

case "$TOOL" in
  Write|Edit|MultiEdit)
    # File was written — get the path
    changed_file=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')
    if [ -n "$changed_file" ]; then
      should_reindex=true
    fi
    ;;
  Bash)
    # Check if it was a git commit
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    if echo "$CMD" | grep -qE 'git\s+(commit|merge|rebase|cherry-pick)'; then
      should_reindex=true
    fi
    ;;
esac

if [ "$should_reindex" = true ]; then
  # Fire async incremental reindex — doesn't block Claude
  # Pass changed file hint for faster patch planning
  if [ -n "$changed_file" ]; then
    nohup mimir analyze --incremental --hint "$changed_file" \
      --repo "$REPO_DIR" \
      > /tmp/mimir-reindex.log 2>&1 &
  else
    nohup mimir analyze --incremental \
      --repo "$REPO_DIR" \
      > /tmp/mimir-reindex.log 2>&1 &
  fi
fi

exit 0
