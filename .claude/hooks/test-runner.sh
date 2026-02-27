#!/usr/bin/env bash
# PostToolUse hook: Test reminder after code edits
# Checks if edited file has corresponding test file

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Skip test files themselves, config files, docs
case "$FILE_PATH" in
  *.test.*|*.spec.*|*__tests__*|*.config.*|*.md|*.json|*.yml|*.yaml)
    exit 0
    ;;
esac

EXTENSION="${FILE_PATH##*.}"
BASENAME=$(basename "$FILE_PATH" ".$EXTENSION")
DIR=$(dirname "$FILE_PATH")

# Check for common test file patterns
TEST_FILES=()
for pattern in \
  "$DIR/$BASENAME.test.$EXTENSION" \
  "$DIR/$BASENAME.spec.$EXTENSION" \
  "$DIR/__tests__/$BASENAME.test.$EXTENSION" \
  "$DIR/../__tests__/$BASENAME.test.$EXTENSION" \
  "${DIR}_test/${BASENAME}_test.$EXTENSION" \
  "$DIR/test_$BASENAME.$EXTENSION"; do
  if [ -f "$pattern" ]; then
    TEST_FILES+=("$pattern")
  fi
done

if [ ${#TEST_FILES[@]} -gt 0 ]; then
  echo "Related test files found: ${TEST_FILES[*]}. Consider running tests to verify changes."
fi

exit 0
