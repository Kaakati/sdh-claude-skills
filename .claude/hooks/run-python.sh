#!/usr/bin/env bash
# Cross-platform Python 3 launcher for Claude Code hooks.
# Tries python3 (Linux/macOS), falls back to python (Windows/conda).
# Debug: CLAUDE_HOOKS_DEBUG=1 bash .claude/hooks/run-python.sh script.py

set -euo pipefail

# Force UTF-8 for stdin/stdout/stderr regardless of the host locale.
# Claude Code reads hook output as UTF-8, but Python on Windows defaults to the
# legacy codepage (e.g. cp1252), which mangles non-ASCII output into U+FFFD.
# PYTHONUTF8=1 (PEP 540) makes every hook emit valid UTF-8 on all platforms.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

PY=""
for candidate in python3 python; do
  if command -v "$candidate" &>/dev/null; then
    # Validate the interpreter is real Python 3 (catches Windows Microsoft Store stub)
    if "$candidate" -c "import sys; assert sys.version_info >= (3, 0)" 2>/dev/null; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "ERROR: No working Python 3 found on PATH (tried python3, python)" >&2
  exit 1
fi

if [ "${CLAUDE_HOOKS_DEBUG:-}" = "1" ]; then
  echo "[run-python] Using: $PY ($($PY --version 2>&1))" >&2
fi

exec "$PY" "$@"
