#!/usr/bin/env bash
# PostToolUse hook: Auto-format files after edits
# Reads JSON from stdin, extracts file_path, runs appropriate formatter

set -euo pipefail

# Read tool output from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

EXTENSION="${FILE_PATH##*.}"

case "$EXTENSION" in
  rb|rake)
    if command -v rubocop &>/dev/null; then
      rubocop --autocorrect-all --fail-level=error "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  js|jsx|ts|tsx|css|scss|json|yaml|yml)
    if command -v prettier &>/dev/null; then
      prettier --write "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  erb)
    if command -v htmlbeautifier &>/dev/null; then
      htmlbeautifier "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  py)
    if command -v black &>/dev/null; then
      black --quiet "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  tf|tfvars)
    if command -v terraform &>/dev/null; then
      terraform fmt "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
esac

exit 0
