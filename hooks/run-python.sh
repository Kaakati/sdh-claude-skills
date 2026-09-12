#!/usr/bin/env bash
# Cross-platform Python 3 launcher for Claude Code hooks.
#
#   bash run-python.sh [--fail-closed] <hook.py> [args...]
#
# A REAL Python 3, found once:
#   * Windows (Git Bash / MSYS / Cygwin): python, then `py -3`, then python3. python3 there is
#     usually the WindowsApps App Execution Alias (several times slower to start) or a Microsoft
#     Store stub that runs nothing, and a python.org install often leaves only `py` on PATH.
#   * macOS / Linux: python3, then python.
#   The winner's real executable (sys.executable) is cached in $CLAUDE_PLUGIN_DATA, so later hooks
#   start ONE interpreter instead of a validation run plus the hook. The cache is used only when
#   it is owned by this user and still points at an executable; without $CLAUDE_PLUGIN_DATA every
#   run validates first, as before.
#
# --fail-closed (security-scan, dangerous-command-blocker, terraform-command-gate only):
#   PreToolUse blocks on exit 2 or a deny decision; any other exit is a non-blocking error and the
#   tool RUNS. A gate that could not start (no Python) or died before deciding (a broken _hooklib
#   import) therefore failed OPEN. With the flag, both exit 2 with the reason on stderr.
#   No launcher closes one gap: a gate still running at its hooks.json `timeout` (10 s; 30 s for
#   security-scan) is cancelled and the tool runs through the normal permission flow, so the
#   permission floor (the Bash(...) and PowerShell(...) denies) is what still holds. A cold Windows
#   interpreter probe (python, py -3, python3) is the realistic stall; the cache above keeps it rare.
#   Every other hook keeps exit 1 — a non-blocking "hook error" notice the user sees — because a
#   launcher exit 2 means something else per event: on PostToolUse and PostToolUseFailure it feeds
#   this stderr to Claude after every call, on Stop it keeps Claude working, on TaskCreated it rolls
#   the task back, on TeammateIdle and TaskCompleted it keeps the teammate working or the task open,
#   and on UserPromptSubmit it blocks and erases the prompt. (The team gates' own exit 2 is deliberate.)
#
# Debug: CLAUDE_HOOKS_DEBUG=1 bash hooks/run-python.sh hooks/security-scan.py

set -euo pipefail

# Force UTF-8 for stdin/stdout/stderr regardless of the host locale.
# Claude Code reads hook output as UTF-8, but Python on Windows defaults to the
# legacy codepage (e.g. cp1252), which mangles non-ASCII output into U+FFFD.
# PYTHONUTF8=1 (PEP 540) makes every hook emit valid UTF-8 on all platforms.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

FAIL_CLOSED=0
if [ "${1:-}" = "--fail-closed" ]; then
  FAIL_CLOSED=1
  shift
fi
HOOK="${1:-}"
HOOK_NAME="${HOOK##*/}"
CACHE=""
if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
  CACHE="${CLAUDE_PLUGIN_DATA}/sdh-python-interpreter"
fi
PY=()

is_windows() {
  case "${OSTYPE:-}" in msys*|cygwin*|win32*) return 0 ;; esac
  [ -n "${MSYSTEM:-}" ] || [ "${OS:-}" = "Windows_NT" ]
}

# The cached interpreter, when the cache is ours and still points at an executable.
from_cache() {
  local cached=""
  [ -n "$CACHE" ] && [ -f "$CACHE" ] && [ -O "$CACHE" ] || return 1
  IFS= read -r cached < "$CACHE" || true
  [ -n "$cached" ] && [ -x "$cached" ] || return 1
  PY=("$cached")
}

# Accept a candidate (an argv, e.g. `py -3`) only if it really runs Python 3; keep the real
# executable it reports, so the cache skips aliases and launchers next time.
probe() {
  local exe=""
  command -v "$1" >/dev/null 2>&1 || return 1
  exe="$("$@" -c 'import sys; assert sys.version_info >= (3, 0); sys.stdout.write(sys.executable.replace(chr(92), "/"))' 2>/dev/null)" || return 1
  if [ -n "$exe" ] && [ -x "$exe" ]; then
    PY=("$exe")
  else
    PY=("$@")
  fi
}

remember() {
  [ -n "$CACHE" ] && [ "${#PY[@]}" -eq 1 ] || return 0
  case "${PY[0]}" in /*|[A-Za-z]:/*) ;; *) return 0 ;; esac
  { [ -d "${CACHE%/*}" ] || mkdir -p "${CACHE%/*}"; } 2>/dev/null || return 0
  printf '%s\n' "${PY[0]}" > "$CACHE" 2>/dev/null || true
}

if is_windows; then
  TRIED="python, py -3, python3"
else
  TRIED="python3, python"
fi

if ! from_cache; then
  if is_windows; then
    probe python || probe py -3 || probe python3 || true
  else
    probe python3 || probe python || true
  fi
  remember
fi

if [ "${#PY[@]}" -eq 0 ]; then
  if [ "$FAIL_CLOSED" = "1" ]; then
    echo "BLOCKED: sdh fail-closed gate ${HOOK_NAME} could not start: no working Python 3 on PATH (tried ${TRIED}), so this action was not evaluated. Install Python 3 so one of those is on PATH, or run the action manually outside Claude Code." >&2
    exit 2
  fi
  echo "ERROR: No working Python 3 found on PATH (tried ${TRIED}); sdh hook ${HOOK_NAME} did not run." >&2
  exit 1
fi

if [ "${CLAUDE_HOOKS_DEBUG:-}" = "1" ]; then
  echo "[run-python] Using: ${PY[*]} ($("${PY[@]}" --version 2>&1)); cache: ${CACHE:-none}" >&2
fi

if [ "$FAIL_CLOSED" = "1" ]; then
  rc=0
  "${PY[@]}" "$@" || rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then
    echo "BLOCKED: sdh fail-closed gate ${HOOK_NAME} exited ${rc} before it could decide, so this action was not evaluated. Run the hook by hand to see why (docs/hook-development.md), or run the action manually outside Claude Code. Interpreter: ${PY[*]}; cache: ${CACHE:-none} (delete it if that interpreter is broken)." >&2
    exit 2
  fi
  exit "$rc"
fi

exec "${PY[@]}" "$@"
