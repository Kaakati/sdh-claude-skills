# Claude Code Hooks

Deterministic quality gates that run on every Claude Code action. Every entry in `hooks.json` is a
**command hook** — there are no prompt or agent hooks — and every command goes through the
`run-python.sh` launcher.

## System Requirements

- **Python 3.6+**: all hook logic is standard-library Python. Every file parses under the 3.6
  grammar, but only current 3.x interpreters are actually exercised.
- **Bash**: `hooks.json` runs `bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh" …`. On Windows that
  means Git Bash.

There are no other dependencies. `auto-format.py` uses whichever formatters the project or PATH
provides (`rubocop`, `prettier`, `htmlbeautifier`, `ruff`, `terraform`). When one is missing it
says so once per session and blocks nothing.

The orthogonality engine keeps its index in the standard library's `sqlite3`, and falls back to a
JSON file on a Python build without it. The boundary and clone tools it can use (packwerk,
import-linter, tach, dependency-cruiser, jscpd, squawk) run only when the project already has them,
and never through `npx`, `pnpm dlx`, `yarn dlx`, `bunx`, `uvx`, `uv run` or `pipx run`.

## The launcher (`run-python.sh`)

```
bash run-python.sh [--fail-closed] <hook.py> [args...]
```

| | Windows (Git Bash, MSYS, Cygwin, `OS=Windows_NT`) | macOS / Linux |
|---|---|---|
| Interpreter order | `python`, `py -3`, `python3` | `python3`, `python` |
| Why that order | `python3` is usually the WindowsApps alias (several times slower to start) or a Microsoft Store stub that runs nothing, and a python.org install may put only `py` on PATH | platform default |
| Accepted when | the candidate runs `assert sys.version_info >= (3, 0)` and reports its real `sys.executable` | same |
| Cache | That executable is written to `$CLAUDE_PLUGIN_DATA/sdh-python-interpreter`. It is reused only while this user owns the file and the path is still executable. Later hooks then start one interpreter instead of a probe plus the hook. | same |
| Encoding | `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` are exported, because otherwise output leaves in cp1252 and Claude Code shows `�` | same |

**When a hook cannot run:**

| Registration | No Python 3 found | The hook exits with a code other than 0 or 2 (e.g. an import breaks) | The hook runs past its `timeout` |
|---|---|---|---|
| `--fail-closed` (`security-scan`, `dangerous-command-blocker`, `terraform-command-gate`) | exit 2 with `BLOCKED: … could not start` on stderr. The tool does **not** run. | exit 2 with `BLOCKED: … exited N before it could decide`, naming the interpreter and the cache path | the tool **runs**. Claude Code cancels a timed-out command hook and discards its output, which on PreToolUse is no decision, and no launcher can turn that into exit 2 |
| every other hook | exit 1 with `ERROR: No working Python 3 found …`: a visible hook error that blocks nothing | the hook's own exit code (1 is visible and non-blocking) | cancelled, with its output discarded. The `async` index hook is the exception: once it runs in the background, no timeout is enforced on it |

- **A stalled gate is not a gate.** The hooks reference: "A timed-out `command`, `http`, or
  `mcp_tool` hook doesn't block the tool call." The timeouts are 10 s for
  `dangerous-command-blocker` and `terraform-command-gate` and 30 s for `security-scan`. The
  realistic stall is a cold start on Windows, where the launcher probes `python`, `py -3` and
  `python3`; the `$CLAUDE_PLUGIN_DATA` interpreter cache keeps every later start to one
  interpreter. After a stall, what still holds is the permission floor: its `Bash(...)` rules and
  their `PowerShell(...)` mirrors.
- **Why the launcher exits 2 only for the three fail-closed gates.** Exit 2 does something different
  on each event (hooks reference, *Exit code 2 behavior per event*). On PreToolUse it blocks the
  tool. On PostToolUse and PostToolUseFailure it only shows stderr to Claude, so a launcher exit 2
  would hand Claude its "no Python" text after every edit. On Stop it keeps Claude working, on
  TaskCreated it rolls the task back, on TeammateIdle and TaskCompleted it keeps the teammate
  working or the task open, on UserPromptSubmit it blocks and erases the prompt, and on
  SessionStart and SubagentStart it only shows stderr to the user. The team gates below exit 2 on
  purpose, from their own code; the launcher never does it for them.
- **A cached interpreter that breaks.** If the cached path is still executable but no longer runs,
  the fail-closed gates block until the cache file is deleted. The message names that file.
- **Windows without Git Bash.** Claude Code enables the PowerShell tool and registers no Bash tool,
  and `bash` is either missing or resolves to WSL. Every hook then fails with a non-blocking error,
  and no launcher change can fix that. What still protects the session is the copied permission
  floor's `PowerShell(...)` denies, because a `Bash(...)` rule never matches the PowerShell tool.
- **Shell form, not exec form.** The command is a shell string with the plugin root in double
  quotes. Exec form (`"command": "bash"` plus `args`) resolves `bash` through PATH rather than
  Claude Code's own Git Bash lookup; on Windows that is often missing or WSL, so every hook would
  stop without a word. A plugin root containing a space works. One containing `$`, a backtick, `"`,
  or a UNC `\\` prefix does not.

### Line endings

`run-python.sh` **must** keep LF line endings. With CRLF, bash fails with
`bad interpreter: /usr/bin/env bash^M`. The repo's `.gitattributes` pins `*.sh` (and all text) to
`eol=lf`, so every clone gets LF whatever `core.autocrlf` says. Do not re-save the launcher with
CRLF.

## Output contract per event

On exit 0, plain stdout goes to the **debug log** for every event except UserPromptSubmit,
UserPromptExpansion, SessionStart and PostModelSwitch. A checker that `print`s its warning reaches
nobody. Each hook below uses the channel the hooks reference defines for its event. Claude Code caps
each output string at 10,000 characters.

| Event | Hooks | What the model receives | What the user sees | Blocking |
|---|---|---|---|---|
| PreToolUse | the 7 gates | `permissionDecisionReason` from a `deny`. An `ask` reason is shown to the user but not to Claude (hooks reference, *PreToolUse decision control*), so a remedy written into an ask never reaches Claude | the `ask` prompt with its reason; a `systemMessage` if the audit trail could not record the decision | Gates decide with `permissionDecision` JSON and exit 0. Exit 2 also blocks; only the launcher uses it, for the fail-closed gates |
| PostToolUse | `auto-format`, `post-edit-dispatch`, `audit-logger` | `hookSpecificOutput.additionalContext`, sent through `hooklib.emit`. Capped at 20 lines / 4,000 characters, followed by a `+N more` line. `HOOK ERROR` lines are always kept. `SDH_HOOK_MAX_WARNINGS=0` removes the cap. | a `systemMessage` for an audit gap | never: they exit 0. An exit 2 would not block either; it would show stderr to Claude, since the tool already ran |
| PostToolUse and PostToolUseFailure (`asyncRewake`) | `orthogonality-watch` | the stderr text on exit 2: at most 5 lines, only for findings not yet shown this session. It wakes Claude even when the session is idle. stdout stays empty | nothing directly | never: exit 2 only wakes Claude, and a crash exits 0 |
| PostToolUseFailure | `audit-logger` | `additionalContext` for an audit gap | `systemMessage` for an audit gap | never |
| PermissionDenied | `audit-logger` | nothing (the event has no context field) | `systemMessage` for an audit gap | never |
| SessionStart | `session-start-check` | `additionalContext`: git state, detected area, its scoped skills, and a floor note for missing rules that are not a gap (the build-artifact `Read` denies, or a `Read(**/*secret*)` a managed floor leaves to projects) | `systemMessage`: **GOVERNANCE GAP** | never (exit 2 would only show stderr to the user) |
| SessionStart (`async`) | `orthogonality-index` | nothing. A refresh failure goes to the index `status` table and reaches the model through `orthogonality-checker`'s once-per-session note. Only a broken engine import prints a `HOOK ERROR` line, as `additionalContext`, which Claude Code hands to Claude on the next turn, as it does for any async hook | nothing: an async hook's `additionalContext` and `systemMessage` are not shown to the user | never |
| UserPromptSubmit | `vague-request-detector` | `additionalContext` alongside the prompt (no transcript entry) | nothing | never (exit 2 would block and erase the prompt) |
| Stop | `session-stop-summary` | nothing, because `additionalContext` and `decision: "block"` both keep the conversation going | `systemMessage`: the working-tree summary, only when it changed | never |
| SubagentStart | `subagent-context` | `additionalContext` placed at the start of the subagent's context | nothing | this event cannot block |
| TeammateIdle | `teammate-idle-checker` | the stderr text on exit 2; the teammate keeps working with it as feedback | `systemMessage` once the gate gives up after 3 identical rejections | exit 2 |
| TaskCreated | `task-completed-checker` | nothing (it only snapshots a baseline) | nothing | never (always exit 0) |
| TaskCompleted | `task-completed-checker`, `team-task-validator` | the stderr text on exit 2; the task stays open and the reason goes to the model | `systemMessage` after 3 identical rejections | exit 2 |

`task-completed-checker.py` is also registered on **TaskCreated**. There it snapshots the task's
baseline and always exits 0. That baseline is how a change outside a linked worktree gets attributed
to a task. Changes made before the task was created are not attributed, and the team gates stay quiet
about them.

## Architecture

### Shared library (`_hooklib.py`)

Every hook imports `_hooklib`, which holds event parsing, file reading, path matching, the audit
trail, the run loops and framework detection. That keeps each hook small and consistent. Existing
public signatures are kept backward compatible.

| Helper | Purpose |
|--------|---------|
| `load_event()` | Parse the hook JSON from stdin; `{}` on any parse error (fail-open at the parse boundary) |
| `load_event_strict()` | `(event, error)`: tells empty stdin, unparseable text, a non-object event, and a non-object `tool_input` apart |
| `tool_name(event)` / `tool_input(event)` | Tolerate non-dict events |
| `get_file_path(event)` | `file_path`, NotebookEdit's `notebook_path`, and `path` (or a move's `destination`) for `mcp__*` tools only (Grep and Glob also take a `path`) |
| `get_content(event)` | Everything the tool writes, joined: `content`, `new_string`, `new_source`, every `edits[].new_string` / `edits[].newText`, and every `files[]` entry's content |
| `get_file_entries(event)` | `(path, content)` for each file an MCP call commits as a list (GitHub `push_files` sends `files`); `[]` for every other tool |
| `SHELL_TOOLS` / `is_shell_tool(event)` / `shell_command(event)` / `shell_dialect(event)` | The shell tools (`Bash`, `PowerShell`, `Monitor`), the command one runs (`""` for a Monitor WebSocket watch), and the lexer dialect: `powershell` for PowerShell, `bash` for Bash and Monitor |
| `MCP_FILE_WRITE_MATCHER` / `is_mcp_file_write(name)` | The one list of MCP file-writing tools, `^mcp__[^_].*__(write_file\|edit_file\|create_directory\|move_file\|create_or_update_file\|push_files)$`. `hooks.json` registers the PreToolUse file gates on exactly this string, and `security-scan` and `mcp-install-gate` test tool names with it |
| `match_path(path)` | Normalized path, lowercased only where the filesystem folds case (always on Windows; tested on disk elsewhere) |
| `read_file(path)` | UTF-8 with `errors="replace"`, `""` on error. An empty read of a non-empty file is retried once, because a formatter truncates before it writes. |
| `under(path, "app/models")` / `under_any` / `replace_first_segment` | Match canonical structure under **any** wrapper dir. An absolute path is matched relative to its project root. |
| `project_root(path)` / `rel_to_root(path)` | The root that matching is relative to: the nearest dir holding `Gemfile`, `package.json`, `pyproject.toml` or `manage.py`, stopping at `.git`; failing that, `CLAUDE_PROJECT_DIR` or the event's cwd |
| `detect_framework(path)` | `rails` / `nextjs` / `vite` / `react-native` / `django` / `fastapi` / `None`, from markers |
| `emit(lines, event_name=, system_message=)` | The single output channel: `additionalContext` for the model (capped on PostToolUse), plus an optional `systemMessage` for the user |
| `hook_error(label, exc)` | The fail-open `HOOK ERROR` line |
| `first_in_session` / `seen_this_session` / `notice_once` | Once-per-session markers; they fail toward speaking |
| `formatter_marker(event)` | The marker file auto-format and the dispatcher share for one tool call |
| `redact(text)` / `audit_dir(event)` / `append_audit(event, record)` | The audit trail (see below) |
| `run_post_checker(check)` | Run loop for advisory checkers (`check(event) -> list[str]`) |
| `run_pre_blocker(check, fail_closed=, gate_label=)` | Run loop for PreToolUse gates. `deny()` / `ask()` are also written to the audit trail. |

`_hooklib` re-exports two modules, so hooks keep calling `hooklib.<name>` with unchanged signatures:
`_hookpaths.py` (project-relative matching and framework detection) and `_hookaudit.py` (the audit
trail).

The shell lexer lives in `_shell.py`, the API the five shell gates call. It has two dialects that
yield one segment shape:
- `_shellcore.py`, the POSIX lexer for the Bash and Monitor tools: quotes, pipes, redirects,
  here-documents, subshells and brace groups, `if`/`for`/`while` and `function` bodies, `!`,
  `$(...)` and backticks (bare or double-quoted), `bash <<<`, and `$'...'`;
- `_shellpwsh.py`, the PowerShell lexer for the PowerShell tool: backtick escapes, `''`,
  here-strings, `(...)`/`$(...)`/`{...}` groups, and comments.

Both follow the scripts another program will run (`bash -c`, `eval`, `ssh host "…"`, `| sh`,
`pwsh -Command`, `Invoke-Expression`, `cmd /c`, `wsl`), each read in its own dialect, and match
program names without regard to case or a `.exe` suffix. `_dangerpwsh.py` holds
`dangerous-command-blocker`'s PowerShell rules. The git push parser that `pre-commit-check` and
`deployment-gate` share lives in `_gitpush.py`. For a push that names no destination, it asks the
repository in the event's `cwd` (`@{push}`, else the current branch). It never does so without that
`cwd`, or after a `cd`, `ssh`, `wsl` or `git checkout`/`switch`/`worktree` earlier in the command.

What a broken module costs:
- A broken or missing `_shell.py`, `_shellcore.py` or `_shellpwsh.py` denies every shell command at
  the fail-closed `dangerous-command-blocker` and `terraform-command-gate`, and a broken
  `_dangerpwsh.py` does the same at the blocker.
- At `deployment-gate`, `mcp-install-gate` and `pre-commit-check`, it is a visible hook error
  (exit 1) naming the module, not a silent allow. A missing `_teamgate.py`, which the two push
  gates use for git state, is the same exit 1.

### Advisory dispatcher (`post-edit-dispatch.py`)

The **15** advisory PostToolUse checkers run **in one process** through the dispatcher. It reads the
event once and calls each checker's `check(event)`, which saves 15 Python cold starts per edit.

- **Event errors.** An empty, unparseable, non-object, or bad-`tool_input` event produces one
  `HOOK ERROR` line, and no checker runs.
- **Waiting for the formatter.** Matching PostToolUse hooks run in parallel, so before the first
  checker reads the file the dispatcher waits for auto-format's `done` marker. It stops expecting
  a formatter after 0.5 s with no marker, and gives up after 8 s with a note.
- **Output cap.** Each checker shows at most 5 lines plus `...and N more from <checker>`.
- **Time budget.** After 20 s (`hooks.json` allows 30), the remaining checkers are skipped and
  named in a `HOOK ERROR` line.
- **Crashes.** A checker that crashes is **reported**, never swallowed.
- **The orthogonality checker runs last.** It enforces its own 1.5 s budget on the index lookup, so
  a cold or large index cannot delay the checkers before it.

`auto-format.py` stays a separate entry because it rewrites files and runs slow formatters.

### Wrapper-directory-agnostic detection

Checkers detect frameworks by **canonical internal structure** (`app/models`, `src/pages`,
`src/screens`) and **on-disk markers** (`Gemfile`, `next.config.*`, `vite.config.*`,
`metro.config.js`, `react-native` in `package.json`, `manage.py`, `pyproject.toml`), never by a
fixed top-level folder name. Rails works under `backend/`, `api/`, or the repo root. Matching is
relative to the project, so a checkout under `/app` (a Docker `WORKDIR`) is not mistaken for Rails
`app/`. See the root `README.md` → *Project Directory Convention*.

### Vendored shadcn/ui primitives (`_vendored.py`)

`shadcn add` copies registry source into the directory `components.json` names in `aliases.ui`. That
source belongs to the CLI: a later `add --diff` compares against it, so a size or style warning on
`ui/sidebar.tsx` asks the model to rewrite upstream code. One Write of a stock sidebar used to draw
ten warnings.

**How the directory is found.** `is_vendored_ui(file_path)` finds the nearest `components.json`,
stopping at `.git`, and resolves `aliases.ui`, or `<aliases.components>/ui` when `ui` is absent.
Resolution tries, in order:
1. `tsconfig.json` / `tsconfig.app.json` / `jsconfig.json` `paths`, following one `extends` hop;
2. `package.json` `imports`;
3. `@/` as `<pkg>/src` if that exists, else `<pkg>`;
4. a bare relative alias.

**When it says "not vendored".** It never raises. A malformed config reads as not vendored, so every
check still runs. An alias that resolves to the package root or its `src/`, equals
`aliases.components`, or holds `molecules/`, `organisms/` or `templates/` is refused, so house
components are never exempted.

| Hook | On files under `aliases.ui` |
|---|---|
| `code-quality-checker`, `test-coverage-checker`, `i18n-checker`, `atomic-design-checker` | skipped entirely |
| `accessibility-checker` | skips the alt, label, and focus-style checks; **still** reports a clickable `<div>`/`<span>` and an interactive element hidden with `aria-hidden` |
| `design-token-checker` | skips the style checks; **still** reports a color utility on an unregistered token (a class that compiles to nothing is a bug, not a style) |
| `auto-format` | not reformatted, so `shadcn add --diff` stays readable |
| `teammate-idle-checker` | no "add a test" demand |
| everything else | unchanged |

Blocks installed **outside** `aliases.ui` are fully checked. The rules the skipped checks enforced
for vendored files (label props filled from `t()`, focus-ring contrast, the reduced-motion backstop)
are now held only by the `std-shadcn-ui` skill.

### Orthogonality engine (`_arch*.py`, `_hooktools.py`, `_mechanisms.json`)

One standard-library engine serves three hooks and the `orthogonality` skill's six scripts. The hook
scripts and `skills/orthogonality/scripts/*.py` are thin wrappers, so no detector logic lives under
`skills/`. What a finding means, how to declare an exception, and every scan flag belong to the
skill: `skills/orthogonality/SKILL.md` and its references.

| Role | Modules |
|---|---|
| Hook entry points | `_archhooks.py`: `checker_lines(event)` for `orthogonality-checker`, `session_refresh(event)` for `orthogonality-index`, `watch(event)` for `orthogonality-watch` |
| Index | `_archstore.py` (SQLite, the index key and `SCHEMA_VERSION`; the JSON fallback lives in `_archstate.py` with the watcher's state), `_archlock.py` (the writer lock and holder liveness), `_archindex.py` (enumeration and caps), `_archrefresh.py` (incremental refresh), `_archview.py` (the read model detectors query) |
| Watcher | `_archwatch.py`: which shell commands rewrite architecture files (looking through `bundle exec`, `uv run`, `poetry run`, `pipenv run`, `pdm run`, `python -m` and `docker compose run\|exec`), the lock wait, and the paths still pending a detector pass |
| Parsers | `_archparse.py` (dispatch), `_archparse_db.py` (Rails schema and migrations), `_archparse_sql.py`, `_archparse_py.py` (Django and SQLAlchemy models), `_archparse_pycode.py`, `_archparse_rb.py`, `_archparse_js.py` (TS/JS and Terraform), `_archparse_manifest.py`, `_archtoml.py` |
| Contexts and graph | `_archconfig.py` (`.claude/orthogonality.json`), `_archcontexts.py` (packwerk, import-linter, tach, Nx tags, the config file, or inferred), `_archgraph.py` (import resolution and cycles; `IMPORT_OF` is shared with `clean-architecture-checker`) |
| Detectors | `_archrules.py` (the finding contract and catalog), `_archdetect_db.py`, `_archdetect_mech.py`, `_archdetect_bound.py`, `_archdetect_clone.py`, with `_archdup.py`, `_archclone.py` and `_archsubjects.py` |
| Scans | `_archscan.py`, `_archreport.py` (json, markdown, brief, sarif-lite), `_archcli.py` (the scripts' command line), `_archtools.py` (installed community tools) |
| Shared helpers | `_hooktools.py` (project-local binaries: `node_modules/.bin`, `.venv`, `bundle exec`, `bin/` binstubs, plus the cmd-shim argument check) and `_mechanisms.json` (the house mechanism per concern and stack, only for concerns the standards name) |

**Where the index lives.**
- `${CLAUDE_PLUGIN_DATA}/orthogonality/<key>/index.sqlite`, beside `refresh.lock` and `watch.state`.
  The key is the first 16 hex digits of the SHA-1 of the project root's real path, the folder name,
  and the parser generation (`-v<SCHEMA_VERSION>`). Projects on one machine never mix, and two
  plugin versions with different parsers keep separate indexes. A linked worktree gets its own key,
  seeded from the main checkout's index.
- With `CLAUDE_PLUGIN_DATA` unset (a plain shell, the harness), it is
  `<tempdir>/sdh-orthogonality/<key>/`. `SDH_ORTHOGONALITY_DIR` overrides both, and a script's
  `--cache-dir` overrides all three; the key is always appended.
- It is a rebuildable cache, never a record: Claude Code deletes the plugin data directory on
  uninstall. A corrupt database is moved aside (`index.sqlite.corrupt`) and rebuilt. An index under
  this key stamped with another schema version is rebuilt by the next full pass; a pass limited to
  a few paths marks it dirty instead.
- **Scope:** `git ls-files --cached --others --exclude-standard` (a directory walk without git).
  Build output, `node_modules`, `.venv`, `__pycache__` and config `ignore` globs are skipped, and the
  walk without git also prunes `site-packages`, `dist-packages`, `AppData`, `Library` and dot
  directories other than `.claude`. At most 50,000 files, and 1 MB per file.
- **No project, no index.** A session started in the home directory, a filesystem root, or a folder
  with no `.git`, package manifest or `.claude/orthogonality.json` builds none, and the checker says
  so once per session.

**Budgets and caps.**

| Hook | Its own budget | `hooks.json` timeout | Output cap |
|---|---|---|---|
| `orthogonality-checker` | 1.5 s for the index lookup, inside the dispatcher's 20 s. A file over the 1 MB cap is never re-parsed; an over-cap schema, migration or manifest is checked from its stored index rows | the dispatcher's 30 s | 3 lines, plus once-per-session notes |
| `orthogonality-index` | 120 s, shared with the baseline, which stamps only the detectors that finished; a stopped pass commits a partial index (`complete: false`) that the next pass continues | 30 s, which a background run is not held to | none |
| `orthogonality-watch` | up to 15 s waiting for a held lock, then 25 s for the index refresh; with `SDH_ORTHOGONALITY_TOOLS=1`, each installed tool within its own budget, 120 s per pass (skipped after a lock wait) | 150 s, enforced | 5 lines on stderr |

**One writer at a time.** The index hook, the watcher and a refreshing scan take `refresh.lock`
(`_archlock.py`), which records the holder's pid, a timestamp and the host.
- **A live holder** touches the lock at every batch commit, so a long pass is never taken for stale.
  A writer that finds the lock held marks the index dirty, and the holder runs one more pass.
- **A dead holder** is detected at once. When the lock was taken on this host and its process no
  longer runs (a closed session, `-p` teardown, a timeout), or its pid now names a later process,
  the lock is broken, and the killed pass resumes from the files it committed. A lock from another
  host, or in the older two-field form, goes stale after 10 minutes.
- **The watcher** waits up to 15 s for the lock, then checks the changed paths against the index as
  it stands and keeps them out of the first baseline, so a later pass still reports them.
- **Readers.** The checker and scans read without locking. During a first build the checker says
  the index is still being built, and `arch_index.py --status` reports that a refresh is in progress
  (exit 0; 1 with `--require-complete`).

**Failing open, visibly.** None of the three hooks is registered `--fail-closed`.
- A checker crash is a `HOOK ERROR` line from the dispatcher, and the other checkers still run.
- The index hook and the watcher exit 0 on any error and write a row to the index's `status` table.
  `orthogonality-checker` reports it once per session.
- The watcher reserves exit 2 for new findings, so a traceback never wakes Claude.

**Switches.**
- `SDH_ORTHOGONALITY=off` (or `0`, `false`, `no`) turns off all three hooks.
- `SDH_ORTHOGONALITY_TOOLS=1` lets the watcher run installed community tools; they are off by
  default.
- `SDH_ORTHOGONALITY_DIR` moves the cache.
- `SDH_ORTHOGONALITY_CLONES=0` makes scans skip DK6 clone detection.

**Running the scans.** Inside a session, use the skill: its commands pass
`--cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality`, so they read the index the hooks keep. From a
checkout of this repo, against any project:

```bash
bash hooks/run-python.sh skills/orthogonality/scripts/arch_index.py --project /path/to/project --status
bash hooks/run-python.sh skills/orthogonality/scripts/arch_scan.py --project /path/to/project --new-only --format markdown
```

- **Which index a shell reads.** A shell without `CLAUDE_PLUGIN_DATA` reads the temp-directory
  index. Pass `--cache-dir` to share the hooks' index.
- **Exit codes:** `0` clean, `1` a finding at or above `--fail-on`, `2` usage or configuration
  error, `3` internal error.
- **What it writes:** into the project, only with `--write-report`
  (`.claude/orthogonality/last-scan.json`, in a directory that ignores itself with a `.gitignore`).
- Every flag, the JSON schema and a CI job are in `skills/orthogonality/references/scans-and-tools.md`.

### Fail-closed or fail-open — decided, not defaulted

Every hook eventually crashes: a schema change, a missing binary, malformed input. What happens
**then** is a security property, chosen consciously for each hook and never inherited by accident.

| Hook | Stance | Why |
|------|--------|-----|
| `security-scan.py` | **fail-closed** | A gate that cannot evaluate must not pass. A crash, an unparseable event, a failed `_hooklib` import, or (through the launcher) a missing Python all deny. |
| `dangerous-command-blocker.py` | **fail-closed** | Same reasoning: an unevaluated destructive command is not a safe one. A broken lexer module (`_shell.py`, `_shellcore.py`, `_shellpwsh.py`) or `_dangerpwsh.py` denies every shell command. |
| `terraform-command-gate.py` | **fail-closed** | "A gate guarding `apply` that crashes must deny." |
| `run-python.sh --fail-closed` | **fail-closed** | Turns "could not start" into exit 2 for the three gates above. It cannot act on a gate that runs past its `timeout`: Claude Code cancels that hook and the tool runs (*When a hook cannot run*). |
| `pre-commit-check.py` | fail-open | A workflow convention, not safety. A bug here must not block every Bash command. |
| `migration-validator.py` | fail-open (`ask`) | A confirmation gate; the write itself is not destructive. |
| `deployment-gate.py` | fail-open (`ask`) | A confirmation gate. |
| `mcp-install-gate.py` | fail-open (`ask`) | A safeguard on a deliberate action. `deniedMcpServers` in managed settings is the real boundary. |
| `teammate-idle-checker.py`, `task-completed-checker.py`, `team-task-validator.py` | fail-open (exit 2 gates) | A crash, or a failure to load the shared helpers, exits 1: a visible hook error, never a block. After 3 identical rejections in a session the gate stops and tells the developer through `systemMessage`. |
| `session-start-check.py`, `session-stop-summary.py`, `subagent-context.py`, `vague-request-detector.py` | fail-open | Informational. They always exit 0 and never block the session, prompt, or subagent. |
| `orthogonality-index.py`, `orthogonality-watch.py` | fail-open (background) | They exit 0 on any error and record it in the index `status` table, which `orthogonality-checker` reports once per session. The watcher reserves exit 2 for new findings, so a crash never wakes Claude with a traceback. |
| all 15 advisory checkers and `auto-format.py` | fail-open | *"The linter's crash should cost you a lint report, not a session."* A fail-closed formatter is an outage generator. |
| `audit-logger.py` | fail-open | Logging must never block a tool, but see below. |

**Fail-closed costs availability.** A bug in a fail-closed gate on `Edit|Write` bricks every edit
until someone fixes it. That is the right trade for the small deny tier, and the wrong one anywhere
else.

### Silent failure is invisible failure

A fail-open hook that swallows its own exception **looks identical to one that passed**, so a dead
gate can pass for a green one for months. Every fail-open path here therefore reports itself:

```
HOOK ERROR: code-quality-checker.py failed to run — ValueError: bad regex.
Its checks did NOT execute, so its rules were not enforced on this edit.
```

- `_hooklib.hook_error(label, exc)` is the only emitter. `run_post_checker` and the dispatcher both
  route through it and name the checker that failed, so the message is actionable.
- `audit-logger.py` is the sharpest case. A silent write failure leaves **invisible holes in the
  audit trail and false confidence that it is complete**, which is strictly worse than having no
  trail. It announces every gap, to the model as `additionalContext` and to the user as
  `systemMessage`.
- A healthy hook stays **silent**, so the signal does not turn into noise.

Fixture tests enforce this (`[fail-open visibility]` in the harness), because a guarantee nobody
tests decays.

### Audit trail (`audit-logger.py` and the gates)

- **What is recorded.**
  - `audit-logger.py` runs on PostToolUse and PostToolUseFailure for every tool (matcher `*`), and
    on PermissionDenied.
  - Each call writes one JSON line: event, tool, `tool_use_id`, outcome (`ok` / `error: …` /
    `denied: …`), target, and redacted details.
  - A hook's own `deny`/`ask` never reaches PostToolUse, so `_hooklib` appends those decisions from
    inside the gate.
  - Only real events are recorded (those carrying `hook_event_name`). Hand-built fixtures and the
    harness therefore write no audit files.
- **Redaction.** It happens before the 500-character truncation, runs in linear time, and covers:
  - any `Authorization` scheme and `Cookie` headers, `NAME=value` secrets, passwords in URLs, and
    PEM keys;
  - `--password`, `--token` and `--api-key` values, `mysql -p<password>`, `sshpass -p` and
    `docker login -p`, `redis-cli -a`, `curl -u user:pass` and `-b` cookies, `aws configure set`
    keys, `gh secret|variable set --body`, and openssl `pass:`;
  - AKIA / `ghp_` / `xox` / `sk-` / `AIza` / JWT formats.

  PowerShell and Monitor commands are recorded and redacted like Bash.
- **Where it is written.**
  - `<project>/.claude/audit/audit.log`, where the project is `CLAUDE_PROJECT_DIR`, then the event
    cwd, then the process cwd.
  - A linked worktree resolves to its main checkout, so a teammate's log is not deleted with its
    worktree.
  - The directory creates its own `.gitignore` containing `*`, and on POSIX the log is owner-only.

### Exit-code / decision convention

| Hook type | Mechanism | "allow" | "block / warn" |
|-----------|-----------|---------|----------------|
| PreToolUse gate | `permissionDecision` JSON on stdout, exit 0 | no JSON | `deny` (block) or `ask` (confirm); the launcher's exit 2 for a fail-closed gate that could not decide |
| PostToolUse checker | `hookSpecificOutput.additionalContext` JSON via `hooklib.emit()`, exit 0 | no output | warning lines (advisory; never exit 2) |
| PostToolUse and PostToolUseFailure background watcher (`asyncRewake`) | exit code + stderr | exit 0, no output | exit 2 with at most 5 lines on **stderr** wakes Claude; it never blocks |
| TeammateIdle / TaskCompleted gate | exit code + stderr | exit 0 | exit 2 with the reason on **stderr** (stdout on exit 2 goes nowhere) |
| SessionStart / UserPromptSubmit / Stop / SubagentStart | one JSON object, exit 0 | no output | `additionalContext` and/or `systemMessage` per the contract table above |
| SessionStart background refresh (`async`) | none, exit 0 | no output | none: a failure is a `status` row that `orthogonality-checker` reports |

## Writing & debugging hooks

See **[docs/hook-development.md](../docs/hook-development.md)**. It covers:
- **The development loop.** Capture a real event with `capture-event.py`, then develop against the
  fixture; each round takes under a second.
- **The first move.** Observe, don't guess.
- **Symptom → cause troubleshooting.** The hook never fires; it fires but never blocks; a gate
  blocks everything; the model argues with a denial; the read-only lie.

## Debug Mode

Set `CLAUDE_HOOKS_DEBUG=1` to see which Python interpreter the launcher selected and which cache it
used:

```bash
CLAUDE_HOOKS_DEBUG=1 bash hooks/run-python.sh hooks/security-scan.py < event.json
# stderr: [run-python] Using: /usr/bin/python3 (Python 3.12.1); cache: /home/me/.claude/plugins/data/sdh/sdh-python-interpreter
```

`cache: none` means `CLAUDE_PLUGIN_DATA` is not set, so every run probes the interpreter first.

## Hook Inventory

35 hook scripts, plus `run-python.sh`, `_mechanisms.json`, and 46 shared modules: `_hooklib.py`,
`_hookpaths.py`, `_hookaudit.py`, `_protected.py`, `_shell.py`, `_shellcore.py`, `_shellpwsh.py`,
`_dangerpwsh.py`, `_gitpush.py`, `_jsx.py`, `_teamgate.py`, `_testpaths.py`, `_vendored.py`,
`_hooktools.py`, and the 32 `_arch*.py` modules of the orthogonality engine.

| Script | Event (matcher) | Purpose |
|--------|-----------------|---------|
| `run-python.sh` | — | Cross-platform Python 3 launcher: interpreter order per OS, interpreter cache, UTF-8, `--fail-closed` |
| `_hooklib.py` | — | Shared library: event parsing, accessors (the shell tools and MCP `files[]` included), emit, run loops. Re-exports `_hookpaths` and `_hookaudit`, so every `hooklib.<name>` call is unchanged |
| `_hookpaths.py` | — | Project-relative path matching (`under`, `rel_to_root`, `project_root`, `replace_first_segment`, `normalize`) and `detect_framework` |
| `_hookaudit.py` | — | The audit trail: `redact`, `audit_dir`, `append_audit` |
| `_protected.py` | — | The protected-file and provider-format key tables `security-scan` reads, and `shell_write_verdict`, which `dangerous-command-blocker` applies to shell redirects, `tee` and here-documents |
| `_shell.py` | — | The shell lexer API the five shell gates read commands through, in the dialect of the tool that sent them |
| `_shellcore.py` | — | The shared segment and word shapes, and the POSIX lexer for Bash and Monitor |
| `_shellpwsh.py` | — | The PowerShell lexer, and the forms that hand a script on (`pwsh -Command`, `Invoke-Expression`, `cmd /c`, `wsl`) or write a file |
| `_dangerpwsh.py` | — | PowerShell's destructive forms, for `dangerous-command-blocker` |
| `_gitpush.py` | — | The one git push parser, shared by `pre-commit-check` and `deployment-gate`; resolves a push that names no destination in the event's repository |
| `_jsx.py` | — | The one JSX tag/token scanner, shared by the accessibility, code-quality, i18n and design-token checkers |
| `_teamgate.py` | — | Git and team-gate helpers for `teammate-idle-checker`, `task-completed-checker` and `team-task-validator` |
| `_testpaths.py` | — | The test-file candidates `test-runner` and `test-coverage-checker` share |
| `_vendored.py` | — | `is_vendored_ui(file_path)`: is this file a shadcn/ui primitive under `components.json` `aliases.ui`? |
| `_hooktools.py` | — | Project-local tool resolution (`node_modules/.bin`, `.venv`, `bundle exec`, `bin/` binstubs) and the cmd-shim argument check, used by the orthogonality tool runner. It never launches `npx`, `pnpm dlx`, `yarn dlx`, `bunx`, `uvx`, `uv run` or `pipx run` |
| `_arch*.py` (32 modules) | — | The orthogonality engine: parsers, the architecture index and its lock, the watcher, detectors and scans (see *Orthogonality engine* above) |
| `_mechanisms.json` | — | The house mechanism registry: for each concern and stack, the house package and its competitors, only for concerns the standards name |
| `capture-event.py` | dev tool | Captures a real event byte for byte into `tests/fixtures/` (gitignored, owner-only on POSIX, never overwritten). A fixture can contain real credentials. |
| `security-scan.py` | PreToolUse (`Edit\|Write\|MultiEdit\|NotebookEdit`, `^mcp__[^_].*__(write_file\|edit_file\|create_directory\|move_file\|create_or_update_file\|push_files)$`) | **Fail-closed.** **Deny:** protected files (`.env*` except templates, `.envrc`, key material, data files in a project's `secrets/`, `credentials/`, `private/`; the tables live in `_protected.py`) and provider-format keys under any variable name. **Ask:** CI workflow edits (with a checklist), credential-shaped literals, Google `AIza` keys. Its MCP pattern is `_hooklib.MCP_FILE_WRITE_MATCHER`, the registered matcher; it reads a move's `destination`, and judges each `files[]` entry a `push_files` commits as a write of its own. |
| `dangerous-command-blocker.py` | PreToolUse (`Bash\|PowerShell\|Monitor`) | **Fail-closed.** Judges the program that actually runs, in the dialect of the tool that sent it. **Deny:** `rm -rf` by target (root, home, wildcard, system dir, bare `$VAR/`; `rm -r` of root or home without `-f`), `mkfs`, `dd` or redirects onto devices and system paths, destructive SQL through a database client (local test/dev databases exempt), remote `redis-cli FLUSHALL`, `sudo rm`, world-writable `chmod`, recursive `chown root`, netcat listeners/exec, `curl` POST or data upload to external URLs. PowerShell (`_dangerpwsh.py`): `Remove-Item -Recurse` on a drive root, home or system directory (a wildcard, `.` or bare-variable target with `-Force` and no filter), `rd /s`/`del /s` through `cmd /c`, `Format-Volume`/`Clear-Disk`/`Remove-Partition`, a download run through `Invoke-Expression`, and `Invoke-WebRequest`/`Invoke-RestMethod` uploads to external URLs. A shell write meets `security-scan`'s file decision (`_protected.shell_write_verdict`): a live key or an environment file written through a redirect or `tee` denies, a `secrets/` data file asks. |
| `terraform-command-gate.py` | PreToolUse (`Bash\|PowerShell\|Monitor`) | **Fail-closed.** **Deny:** `destroy`, `apply -destroy`, `apply -auto-approve`, `state rm\|mv\|push`, `force-unlock` (terraform and tofu). **Ask:** `apply`, with a checklist. **Allow:** the read-only surface. |
| `pre-commit-check.py` | PreToolUse (`Bash\|PowerShell\|Monitor`) | **Deny:** a commit whose subject line is not a Conventional Commit; a force push or deletion of a protected branch, including a force push that names no destination but resolves to one in the event's repository. **Ask:** a direct push to a protected branch (`git push` and `git push origin HEAD` resolved the same way), or a force push with no named destination that does not resolve to one. Reads commands through `_shell.py` and pushes through `_gitpush.py`. |
| `deployment-gate.py` | PreToolUse (`Bash\|PowerShell\|Monitor`) | **Ask:** pushes to protected branches (a push that names no destination resolved in the event's repository), any force push, `aws ecs` deploys, `vercel deploy`/`--prod`, image pushes, fastlane releases, `eas submit`/`update`, `gcloud run\|app\|functions deploy` |
| `mcp-install-gate.py` | PreToolUse (`Bash\|PowerShell\|Monitor`, `Edit\|Write\|MultiEdit`, `^mcp__[^_].*__(write_file\|edit_file\|create_directory\|move_file\|create_or_update_file\|push_files)$`) | **Ask:** `claude mcp add` (reporting the real scope and transport), `shadcn mcp init` through any runner (`npx`, `pnpm dlx`, `bunx`, `yarn dlx`), writes to `.mcp.json` or `.claude.json` servers (shell redirects, PowerShell `Set-Content`/`Out-File`, an MCP move onto `.mcp.json`, a `push_files` entry), and settings writes that approve project servers wholesale (`enableAllProjectMcpServers: true`, a new `enabledMcpjsonServers` name) |
| `migration-validator.py` | PreToolUse (`Edit\|Write\|MultiEdit`) | **Ask:** judges the migration as it will be after the write, for Rails `db/*migrate`, Alembic `alembic/versions` and Django `migrations/`. Checks reversibility, destructive forward operations, and interpolated SQL. |
| `auto-format.py` | PostToolUse (`Edit\|Write\|MultiEdit`, `^mcp__[^_].*__(write_file\|edit_file)$`) | Formats with the project's own binary (table below). Safe corrections only; shadcn `aliases.ui` skipped. |
| `post-edit-dispatch.py` | PostToolUse (same matchers) | Runs the 15 advisory checkers in one process, `orthogonality-checker` last |
| `audit-logger.py` | PostToolUse, PostToolUseFailure, PermissionDenied (`*`) | Redacted JSON-lines audit trail, anchored to the project; Bash, PowerShell and Monitor commands are recorded alike |
| `orthogonality-watch.py` | PostToolUse, `asyncRewake` (`Edit\|Write\|MultiEdit\|Bash\|PowerShell`, `^mcp__[^_].*__(write_file\|edit_file)$`); PostToolUseFailure, `asyncRewake` (`Bash\|PowerShell`) | After a package install, a generator or a tree-rewriting `git` command, read through runner prefixes such as `bundle exec` and `uv run`, updates the architecture index and wakes Claude with at most 5 stderr lines (exit 2), only for findings not yet shown this session. A crash, or a failed call the user interrupted, exits 0 |
| `session-start-check.py` | SessionStart | Git state and framework area for the model; a GOVERNANCE GAP for the user when a secrets, privilege, remote-exec, or infrastructure deny rule, or its `PowerShell(...)` mirror, is missing from every readable settings source (project, local, user, file-based managed). A managed floor carrying the whole catastrophic tier (`managed_tier()`) counts as complete, and a missing `Read(**/*secret*)` is then a note to the model |
| `orthogonality-index.py` | SessionStart, `async` (`startup\|resume\|fork`) | Refreshes the architecture index in the background (120 s budget, partial commits), seeds a linked worktree from the main checkout, and stamps the findings baseline once the index is complete. No output |
| `vague-request-detector.py` | UserPromptSubmit | For an underspecified prompt, suggests `sdh:requirements-consultant`, with a fallback for when AskUserQuestion is unavailable. A prompt with a concrete signal (path, backticks, digit, identifier, stack name, 12+ words) does not fire. |
| `session-stop-summary.py` | Stop | Staged, modified, untracked and ahead counts for the user, only when they changed this session; quiet when `stop_hook_active` is set |
| `subagent-context.py` | SubagentStart | The house stack for every subagent (the chart library per stack, drill-down navigation, and drill-down-ready APIs included); team context only when the subagent is a member of this session's team (matched by the team config's `agentId`), with no paths |
| `teammate-idle-checker.py` | TeammateIdle | Exit 2 while a teammate's own linked worktree has source changes without a test change. Read-only agents are skipped (no edit tool in `agents/<role>.md`). |
| `task-completed-checker.py` | TaskCreated (baseline snapshot, exit 0), TaskCompleted | **Exit 2 when:** a worktree teammate's changes are uncommitted, or a task that promises tests leaves no test-file change (commits count). Its git and team-gate helpers live in `_teamgate.py`. |
| `team-task-validator.py` | TaskCompleted | Exit 2 over debug statements (matched as statements), trailing whitespace, a missing final newline, or mixed indentation, in files the task touched |

**MCP tools reach the gates only through two anchored lists of whole tool names.** A matcher holding
a regex character is an unanchored JavaScript regular expression, so both carry `^…$`:
- **PreToolUse** routes
  `^mcp__[^_].*__(write_file|edit_file|create_directory|move_file|create_or_update_file|push_files)$`
  to `security-scan` and `mcp-install-gate`. The string is `_hooklib.MCP_FILE_WRITE_MATCHER`, and
  both scripts test tool names with `is_mcp_file_write`, never with `startswith("mcp__")`. Both gates
  judge each `files[]` entry of a GitHub `push_files` as a write of its own.
- **PostToolUse** routes `^mcp__[^_].*__(write_file|edit_file)$` to `auto-format`, the
  dispatcher, and `orthogonality-watch`.
- **Left out on purpose.** Gmail `create_draft`, Calendar `create_event`, memory `create_entities`,
  and the claude.ai Google Drive `create_file` (a title, no path) start no gate, because
  `security-scan` denies whenever Python is missing. A third-party file tool with another name (a
  `create_file` that takes a path, `append_file`, `edit_block`) is judged by no gate and no checker;
  only `audit-logger` (matcher `*`) records it.
- **Changing the list.** Edit `hooks.json` and `_hooklib.MCP_FILE_WRITE_MATCHER` in the same change.
  The harness's parity probe fails when `hooks.json`, `_hooklib`, `security-scan`, and
  `mcp-install-gate` disagree.

**Advisory checkers**, in dispatch order (the `CHECKERS` list in `post-edit-dispatch.py`; each is
`check(event) -> list[str]`):
`test-runner.py`, `code-quality-checker.py`, `error-handling-checker.py`,
`test-coverage-checker.py`, `clean-architecture-checker.py`, `i18n-checker.py`,
`accessibility-checker.py`, `api-design-checker.py`, `monitoring-checker.py`,
`atomic-design-checker.py`, `rails-routes-checker.py`, `terraform-checker.py`,
`design-token-checker.py`, `database-design-checker.py`, `orthogonality-checker.py`.

## Optional Formatters

`auto-format.py` runs these when it can resolve them:

| Extension | Command | Binary resolution |
|-----------|---------|-------------------|
| `.rb`, `.rake` | `rubocop --autocorrect --fail-level=error` | `bundle exec` (from the Gemfile's dir) when the nearest `Gemfile.lock` pins it and `bundle` is on PATH, else PATH |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.css`, `.scss`, `.json`, `.yaml`, `.yml` | `prettier --write` | nearest `node_modules/.bin/prettier(.cmd)`, else PATH |
| `.erb` | `htmlbeautifier` | `bundle exec` when pinned, else PATH |
| `.py` | `ruff format --quiet` | nearest `.venv`, else PATH |
| `.tf`, `.tfvars` | `terraform fmt` | PATH |

- **Safe corrections only.** RuboCop runs `--autocorrect`, never `-A`, and ruff runs `format`,
  never `check --fix`. The harness pins this.
- **Windows shims.** On Windows the resolved `.cmd`/`.bat` shim is what runs. A file path containing
  `% ^ & | < > " !` is refused for a shim (with one notice per session), because cmd.exe argument
  parsing cannot be escaped from Python.
- **Notices.** A missing formatter, a 20-second timeout, and exit code 2 or higher each produce one
  notice per session, sent to the model through `emit`.

## Running Tests

```bash
bash hooks/run-python.sh hooks/tests/run-all.py
```

The harness invokes hook scripts with `sys.executable`, so it works whether your system uses
`python` or `python3`. Running it through `run-python.sh` also forces UTF-8. The harness does not
exercise the launcher itself, so launcher cases call `bash hooks/run-python.sh` explicitly.

To run only the orthogonality tests (the engine, the six scripts, the store, the performance guards,
and their trigger-matrix rows):

```bash
bash hooks/run-python.sh hooks/tests/run-all.py --only orthogonality
```

`--only <prefix>` runs every test and matrix row whose name or tag contains the prefix.

The harness is also a **standing audit** (Ch. 22), not just a regression net. Beyond per-hook
behaviour it asserts:
- that fail-open paths stay visible;
- that every `deny` reason names a remedy;
- that the sentinel detects a *stale* permission floor;
- that every file-scoped hook names a loadable skill;
- that documented limits, commit types and required tags equal the numbers and lists the hooks
  enforce.

**The trigger-precision matrix.** For each hook, it holds crafted events that must **fire** next to
near-miss events that must stay **quiet**, for example:
- a commit body mentioning `DROP TABLE`;
- a feature branch named `…-main-nav`;
- `rsync -lrt`;
- `.env.example`;
- a stock shadcn primitive under `aliases.ui`;
- `update!(status: :paid)` in a service.

A precision fix cannot quietly cost recall, and a new rule cannot quietly start firing on correct
work. When you change a hook's decision, add its row to the matrix in the same change.

CI runs the harness on every push and PR, and the `hook-fixtures-windows` job runs
`--only orthogonality` on Windows.
