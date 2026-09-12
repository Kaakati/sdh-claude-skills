# Hook Development & Debugging

How to write, test, and debug the `sdh` plugin's hooks. Based on *The Governed Agent* Ch. 9 (the
development workflow), Ch. 22 (the fixture harness as a standing audit), and Ch. 25 (debugging).
The output contract per event, the launcher, and the per-hook stance live in
[`hooks/README.md`](../hooks/README.md). This page is the loop.

---

## The development loop

**Hooks written blind and tested in a live session are how you get defects.** Do this instead:

### 1. Capture a real event — don't guess at the schema

```jsonc
// temporarily, in your project's .claude/settings.json
{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
  {"type": "command", "command": "bash hooks/run-python.sh hooks/capture-event.py"}]}]}}
```

Trigger the tool once and a real fixture lands in `hooks/tests/fixtures/`.
- **Encoding:** the event is saved byte for byte.
- **No overwrites:** a second capture in the same second gets a `-N` suffix.
- **Credentials:** a fixture holds whatever the tool was about to write, so it can contain a real
  credential. The directory is gitignored and files are owner-only on POSIX; still read one before
  you share it.

The research behind v4.0.0 found that the event fields people *remember* differ from the ones on the
wire. TeammateIdle carries `teammate_name` and `team_name`, not `teammate_id` or a task. TaskCreated
and TaskCompleted carry `task_id`, `task_subject`, and optionally `task_description`,
`teammate_name`, `team_name`. SubagentStart carries `agent_id` and `agent_type`, and its context goes
out as `hookSpecificOutput.additionalContext`; a team config names members by `agentId`. Capture
first.

### 2. Develop against the fixture, not the session

```bash
python hooks/my-gate.py < hooks/tests/fixtures/PreToolUse-Bash-1784092811.json; echo "exit: $?"
```

This loop takes under a second. The alternative (edit, start a session, trigger the tool, squint
at the output) takes a minute, and you will run it fifty times.

A hand-built fixture has no `hook_event_name`. `_hooklib` treats such an event as a test: the gate
writes no audit record, and the dispatcher does not wait for auto-format. Keep `hook_event_name` in
captured fixtures when you want to exercise those paths.

### 3. Decide the fail stance *consciously*

Before writing the logic, answer one question: **when this hook crashes, what should happen?** See
the stance table in [`hooks/README.md`](../hooks/README.md). Security gates fail **closed**: register
them with `run-python.sh --fail-closed` and run them with `fail_closed=True`. Advisory hooks fail
**open**, but never *silently* (see below).

### 4. Write it against `_hooklib`

```python
import _hooklib as hooklib

def check(event):
    if not hooklib.is_shell_tool(event):          # Bash, PowerShell or Monitor
        return
    command = hooklib.shell_command(event)
    ...
    hooklib.deny("BLOCKED: X is not allowed. Do Y instead.")   # ALWAYS name the remedy

if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="my-gate")
```

- **Advisory checkers** use `check(event) -> list[str]` plus `hooklib.run_post_checker(check)`.
  `post-edit-dispatch.py` runs them in-process: add the filename to its `CHECKERS` list, where 15
  checkers are registered today. Keep `orthogonality-checker.py` last: it reads the architecture
  index under its own 1.5 s budget.
- **Output.** A checker *returns* lines and never prints them. The dispatcher sends them through
  `hooklib.emit()` as `hookSpecificOutput.additionalContext`, because PostToolUse stdout on exit 0
  goes to the debug log and not to the model. Calling `notice_once` from inside a dispatched
  checker would print a second JSON object and corrupt the reply; use `first_in_session` and return
  the line.
- **Reading the event.** Use `get_file_path` / `get_content`. They already cover `notebook_path`,
  `new_source`, MultiEdit `edits[]`, MCP `path` / `newText`, and the `files[]` a GitHub
  `push_files` commits (`get_file_entries` gives each entry's path and content). To ask whether an
  MCP tool is a file writer, call `is_mcp_file_write(name)`, never `startswith("mcp__")`, so the
  answer matches the registered matcher, `_hooklib.MCP_FILE_WRITE_MATCHER`.
- **Matching paths.** Use `under()` for canonical dirs, which is project-relative, and
  `match_path()` for protected-name comparisons, which folds case only where the filesystem does.
- **Shell commands.** Register a shell gate on `Bash|PowerShell|Monitor`, never `Bash` alone. On
  Windows without Git Bash, Claude Code registers no Bash tool, and "a hook that matches only
  `Bash` never fires there" (hooks reference, *PowerShell*); Monitor runs its command under the
  Bash permission rules. Read the command with `hooklib.shell_command(event)`, and import `_shell`
  (and `_gitpush` for pushes) rather than writing a regex over the raw string, passing
  `hooklib.shell_dialect(event)` so a PowerShell command is lexed as PowerShell. A regex denies a
  commit message that *mentions* `DROP TABLE` and misses `rm -fr /`. A fail-closed gate imports
  the lexer inside its guarded import, so a broken lexer denies. A fail-open gate imports it at
  the top, so a broken lexer is a visible hook error (exit 1), not an allow.
- **Frontend checkers.** Ask `_vendored.is_vendored_ui(path)` before issuing a size, style, label,
  copy, or test-coverage warning on a shadcn/ui primitive the CLI owns. A warning about a class that
  compiles to nothing still applies there.
- **Name a skill.** Every warning-emitting hook names a skill in the form "the `<skill>` skill",
  and that skill's `paths:` must cover the file the warning is about.

### 5. Test it — hooks are code

Add cases to `hooks/tests/run-all.py`, and add a row to the **trigger-precision matrix**: a crafted
event that must fire, and the nearest correct work that must stay quiet. Then run:

```bash
bash hooks/run-python.sh hooks/tests/run-all.py
```

A guarantee nobody tests decays. The harness is also a **standing audit**: it enforces that fail-open
paths stay visible, that every deny reason names a remedy, and that the sentinel detects a stale
floor.

Test a fail-open gate's `check()` **in-process** as well as through a subprocess. The fail-open
wrapper turns an exception into an allow, so a subprocess test of a crashing gate passes for the
wrong reason. That is how a migration-validator bug stayed hidden until v4.0.0.

---

## Background hooks (`async` and `asyncRewake`)

Two hooks run in the background, and both belong to the orthogonality engine. Reach for either flag
only when work must not hold up a tool call or a session start. Every rule below exists because
nobody is watching a background hook while it runs.

| | `orthogonality-index.py` | `orthogonality-watch.py` |
|---|---|---|
| Registration | SessionStart `startup\|resume\|fork`, `async: true`, timeout 30 | PostToolUse `Edit\|Write\|MultiEdit\|Bash\|PowerShell` and the MCP file writers, plus PostToolUseFailure `Bash\|PowerShell`; `asyncRewake: true`, timeout 150 |
| How it speaks | it does not: a failure becomes a row in the index `status` table, which `orthogonality-checker` reports once per session | exit 2 with at most 5 lines on **stderr** wakes Claude |
| Every other outcome | exit 0, no output | exit 0, no output, a crash included |
| Its own budget | 120 s, then a partial commit | 25 s for the refresh, after waiting up to 15 s for a lock another refresh holds, inside the 150 s timeout |

- **Never exit 2 from an `asyncRewake` hook for an error.** Exit 2 wakes Claude with whatever is on
  stderr, so a crash would reach Claude as a traceback dressed as a finding.
- **Deduplicate.** A background hook starts on every matching tool call. Without a per-session
  "already shown" record, ten edits wake Claude ten times.
- **Budget inside the script, and commit as you go.** A pass that is stopped or killed then loses
  nothing, and the next one continues.
- **Exit early.** The watcher filters shell programs and file extensions before it imports the
  engine, because it starts on every Bash or PowerShell call and every edit.
- **The harness.** Synchronous handlers declare a 1–30 s timeout; `async` and `asyncRewake` handlers
  1–180 s, and the set of background handlers is pinned. Matrix rows judge an `asyncRewake` hook on
  exit 2 plus stderr, with stdout empty.

**What the hooks reference documents** (hooks reference, *Run hooks in the background*, re-read
2026-09-12):
- "When an async hook fires, Claude Code starts the hook process and immediately continues without
  waiting for it to finish."
- "Once an async hook is running in the background, Claude Code doesn't enforce `timeout` on it.
  Claude Code still enforces `timeout` on a hook you run with `asyncRewake`." So the index hook's
  30 s is not a limit on its run, and the watcher's 150 s is.
- "In non-interactive mode with the `-p` flag, Claude Code kills any async hook still running at
  teardown and finalizes it with outcome `cancelled`." An index refresh cut short there resumes
  from its last commit in the next session.
- After an async hook exits, Claude Code delivers its `additionalContext` and `systemMessage` to
  Claude on the next turn, and shows neither to the user. An `asyncRewake` hook that exits 2 "wakes
  Claude immediately even when the session is idle", with its stderr (or stdout when stderr is
  empty) as a system reminder.
- "Each execution creates a separate background process. There is no deduplication across multiple
  firings of the same async hook."

The reference describes no foreground mode for either flag. Before you depend on timing, capture
one SessionStart `async` run and one `asyncRewake` run, interactive and under `claude -p`, as in
step 1.

---

## The orthogonality engine

`hooks/_arch*.py` is one engine behind `orthogonality-checker.py`, `orthogonality-index.py`,
`orthogonality-watch.py` and the `orthogonality` skill's six scripts, each of which is a thin
wrapper. The module map, the index location and the fail stance are in
[`hooks/README.md`](../hooks/README.md) → *Orthogonality engine*. For development:

- **Adding a detector.** Write `detect_<id>(view, delta, config)` in the matching
  `_archdetect_*.py` (`delta` is `None` in a scan), and register the ID in `_archrules`' catalog and
  family. Add a fire row and a quiet row to the trigger-precision matrix. Only IDs in
  `_archrules.EDIT_TIME` reach the edit-time checker; every other ID is scan-only.
- **Naming the owner.** A finding names its owner as "the `<skill>` skill", plus the `orthogonality`
  skill. `test_hook_messages_point_somewhere_real` fails when an `owner_skill` in `_archrules` or
  `_mechanisms.json` is not a real skill.
- **Changing a house choice.** Change `_mechanisms.json` and the standards' Library preferences
  together: `test_mechanism_registry_matches_the_standards` fails when they disagree.
- **The limits are a contract.** The checker's 3 lines and 1.5 s, the watcher's 5 lines, `brief`'s
  15 lines, and a finding's 320 characters are compared with the skill's references. Change both
  together.
- **Standard library only, 3.6 grammar.** `sqlite3` is optional (a JSON store takes over), TOML goes
  through `_archtoml.py`, and YAML is read by restricted line parsers.
- **Bump `_archstore.SCHEMA_VERSION` whenever a parser or a stored fact changes.** It is the parser
  generation, and each generation gets its own index key (`-v<SCHEMA_VERSION>`), so two plugin
  versions on one machine never rewrite each other's index.

**Run it by hand.** Point `SDH_ORTHOGONALITY_DIR` at a scratch directory first, so a hand run neither
reads nor disturbs a real session's index. Delete that directory to start over.

```bash
bash hooks/run-python.sh skills/orthogonality/scripts/arch_index.py --project <project> --rebuild
bash hooks/run-python.sh skills/orthogonality/scripts/arch_index.py --project <project> --status
bash hooks/run-python.sh skills/orthogonality/scripts/arch_scan.py --project <project> --new-only --format markdown
echo '{"tool_name":"Bash","tool_input":{"command":"npm install ky"},"cwd":"<project>"}' \
  | bash hooks/run-python.sh hooks/orthogonality-watch.py; echo "exit: $?"
```

**Test it.** `bash hooks/run-python.sh hooks/tests/run-all.py --only orthogonality` runs the engine,
script, store, performance and matrix tests. The performance guards read each generated file once
before timing them, because a Windows runner pays a first-open scan on freshly written files; their
budgets are tripled on Windows.

---

## The first move when something is wrong: observe, don't guess

> Most "the agent ignored my rule" reports are really "my rule never loaded" or "my hook never ran"
> — different bugs, different fixes than the ones people reach for.

1. **Check what's registered.** `/hooks` shows the configuration that actually loaded. Configuration
   you wrote but haven't confirmed loaded is configuration you're *imagining*. Half of hook
   debugging ends here: the hook is registered under the wrong event, or a JSON syntax error dropped
   it silently.
2. **Run the hook by hand.** This is the single most useful diagnostic:
   ```bash
   echo '{"tool_name":"Bash","tool_input":{"command":"terraform destroy"}}' \
     | bash hooks/run-python.sh hooks/terraform-command-gate.py; echo "exit: $?"
   ```
   If the decision is right by hand, the bug is in **registration or matching**. If it is wrong,
   the bug is in the **script**.
3. **Read the agent definition, not your memory of it.** *"The tool list you remember writing and
   the tool list on disk diverge more often than pride admits."*

---

## Symptom → cause

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **Hook never fires** | Not registered, wrong event, or the `matcher` doesn't match the tool. In this plugin, hooks live in `hooks/hooks.json`, **not** `.claude/settings.json`. Edit-type matchers are `Edit\|Write\|MultiEdit` (plus `NotebookEdit` for security-scan), and MCP file tools need their own group: an anchored `^mcp__[^_].*__(…)$` list that equals `_hooklib.MCP_FILE_WRITE_MATCHER`. An MCP tool whose name is not on that list reaches no gate, by design. Shell gates match `Bash\|PowerShell\|Monitor`: a gate on `Bash` alone never sees a PowerShell command, and on Windows without Git Bash there is no Bash tool at all. | Run `/hooks` to confirm it loaded. Check the matcher, and confirm the command uses `${CLAUDE_PLUGIN_ROOT}`. |
| **Hook fires but never blocks** | **The most serious symptom, because the system *looks* protected.** A PreToolUse gate must emit `permissionDecision: deny` JSON (or exit 2). **Exit 1 is a non-blocking error, so the tool runs.** A gate that crashes before deciding, or never starts because Python is missing, therefore fails open unless the launcher runs it with `--fail-closed`. A gate that runs past its `timeout` is cancelled and the tool runs, with or without that flag. | Run it by hand and inspect stdout. Confirm it routes through `hooklib.deny()`, and that its `hooks.json` entry passes `--fail-closed` if it is a security gate. Check the harness's `assert_blocked` cases. |
| **A team gate blocks with no explanation** | A TeammateIdle or TaskCompleted gate printed its reason to **stdout** and then exited 2. On exit 2 only **stderr** reaches the teammate or model. | Write the reason to stderr. The three team gates also stop after 3 identical rejections, telling the developer via `systemMessage`. |
| **Gate blocks everything** | The inverse emergency: a **fail-closed** gate crashing on every event (a schema change, a missing binary, a broken import, or a stale interpreter cache). Because it fails closed *correctly*, everything is denied. | Run it by hand against a *normal* event. The deny names the gate and the exception (`the … hook errored and is failing closed`), or, from the launcher, the exit code, interpreter and cache path. Delete `$CLAUDE_PLUGIN_DATA/sdh-python-interpreter` if that interpreter is broken. A broken or missing `_shell.py`, `_shellcore.py` or `_shellpwsh.py` denies every shell command at the two fail-closed shell gates (a broken `_dangerpwsh.py` does too, at the blocker), and is a visible hook error (exit 1) at the three fail-open ones. |
| **A checker enforces nothing, but everything looks green** | A dead gate passing for a green one. Or the checker **printed** instead of returning lines, so its output went to the debug log. Or it read the file mid-format and saw `""`. | Grep the session output for `HOOK ERROR`. Never reintroduce a bare `except: pass` or a `print()` in a checker. Keep the dispatcher's formatter wait. |
| **Warnings are cut off** | The PostToolUse cap: 20 lines / 4,000 characters per reply, and 5 lines per checker in the dispatcher. | Run the checker standalone with `SDH_HOOK_MAX_WARNINGS=0`. |
| **A shadcn/ui primitive gets no warnings** | By design, `_vendored.is_vendored_ui()` exempts files under `components.json` `aliases.ui` from the size, style, label, and coverage checks. | Put house compositions outside `aliases.ui`, where everything is checked. If the alias in `components.json` points somewhere too broad, fix the alias. |
| **An ORTHOGONALITY finding you expected never appears** | The index is not built yet: a once-per-session note says so, and only the file-local checks (DK4, MF3, MF5, CM1) ran. Or the finding predates the baseline (frozen at the first complete index, so hooks stay quiet and scans list it), was already shown this session, or is scan-only (DK6, TF1, TF2). Or the file is out of scope (a vendored shadcn/ui primitive, a config `ignore` glob), or `SDH_ORTHOGONALITY=off`. | Check completeness with `arch_index.py --status`, then run `arch_scan.py --paths <file>`, which lists frozen findings too. A new session builds the index. |
| **The watcher never wakes Claude** | It wakes Claude only for new findings after a Bash or PowerShell install, a generator, or a tree-rewriting `git` command, a failed one included. A file edit adds no watcher lines, because the checker already reported that file. Each finding wakes Claude once per session, and a crash exits 0 silently. | Replay the Bash event by hand (*The orthogonality engine*) and read the exit code and stderr. A crash surfaces as the checker's failed-background-refresh note. |
| **The model argues with a denial / retries variations** | The reason names *what* is forbidden but not *what to do instead*. **"Denied" invites retries; "denied because X, do Y instead" invites Y.** | Rewrite the reason to name the remedy. The `[deny reasons must name a remedy]` test guards this. |
| **An agent edited what it shouldn't** | The **read-only lie**: the agent has `Bash`, which *is* edit access (`sed -i`, `echo >`). A "review-only" agent with Bash is theater. | Remove `Bash` from the tool list, or constrain it with permission rules. `permissionMode` is **silently ignored** for plugin-shipped agents; the tool list is the real control. |
| **A deny that should fire doesn't** | The **permission layer was never copied**. A plugin cannot ship `permissions`, so the floor may be absent or **stale**. Or the command came from the PowerShell tool, which a `Bash(...)` rule never matches: the floor needs its `PowerShell(...)` mirrors. | The SessionStart sentinel names the exact missing rules, the PowerShell mirrors included, as a `systemMessage` the developer sees. It reads project, local, user, and file-based managed settings. Re-copy the `permissions` block from the plugin's `.claude/settings.json`. |
| **Skill won't load / loads for everything** | Its `paths:` glob is wrong, too narrow, or too broad. Detection here is wrapper-agnostic: globs match canonical structure (`**/app/**/*.rb`), not a folder name. | Check the skill's frontmatter `paths:`. CI's tier-discipline job catches unindexed rules and broken references. |
| **Sessions feel slow** | Per-call hook cost. The 15 advisory checkers run in **one** process via `post-edit-dispatch.py`, and `auto-format` is separate because formatters are slow. `audit-logger` runs on **every** tool call, Read and Grep included. The orthogonality index and watcher run in the background, and under `claude -p` a background hook still running at teardown is killed (*Background hooks*). | Don't re-split the dispatcher. Make sure `CLAUDE_PLUGIN_DATA` reaches the hooks, so the interpreter cache saves a probe per launch (`CLAUDE_HOOKS_DEBUG=1` prints `cache: none` otherwise). Check whether a checker reads large files. The dispatcher skips the rest after 20 s and names them. `SDH_ORTHOGONALITY=off` turns the orthogonality hooks off for a run where they cost too much. |

---

## Gotchas specific to this plugin

- **`${CLAUDE_PLUGIN_ROOT}`**: hook commands in `hooks/hooks.json` must use it. A bare `hooks/…`
  path works only when the cwd happens to be the plugin root. CI enforces this.
- **Shell form, not exec form.** Keep `"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh\" …"`.
  Exec form resolves `bash` through PATH, which on Windows is often missing or WSL.
- **A matcher with regex characters is unanchored.** Claude Code tests such a matcher against the
  tool name as an unanchored JavaScript regular expression, so `mcp__.*__write_file` also selects a
  longer name that merely contains it. Wrap MCP matchers in `^…$`, as both MCP groups in
  `hooks.json` do, and keep the PreToolUse one identical to `_hooklib.MCP_FILE_WRITE_MATCHER`: the
  harness's parity probe fails when `hooks.json`, `_hooklib`, `security-scan`, and
  `mcp-install-gate` disagree.
- **Windows.** The launcher prefers `python`, then `py -3`, then `python3` (usually the slow
  WindowsApps alias or a Store stub that runs nothing), and caches the winner. It forces
  `PYTHONUTF8=1`, because Python otherwise emits cp1252 and Claude Code shows `�`. It **must** keep
  LF line endings: `.gitattributes` pins them, and CRLF gives `bad interpreter: …^M`. Without Git
  Bash, every hook fails with a non-blocking error. The PowerShell tool is on by default on Windows
  (for claude.ai and Console accounts even with Git Bash installed), so a shell gate that matches
  only `Bash` misses the commands that run there.
- **Exit codes by event.** Exit 2 does something different on each event (hooks reference, *Exit
  code 2 behavior per event*). It blocks the tool on PreToolUse. On PostToolUse and
  PostToolUseFailure it only shows stderr to Claude; on Stop it keeps Claude working; on
  TaskCreated it rolls the task back; on TeammateIdle and TaskCompleted it keeps the teammate
  working or the task open; on UserPromptSubmit it blocks and erases the prompt; and on
  SessionStart and SubagentStart it only shows stderr to the user. So the launcher exits 2 only for
  the three fail-closed PreToolUse gates, and every other hook exits 1 when it cannot start. The
  team gates' own exit 2 is deliberate.
- **MSYS paths.** Git Bash `/tmp/...` paths cannot be resolved by Windows-native Python. When you
  write fixtures by hand, use Windows-form paths (`E:/...`), or the tests will silently read empty
  files and pass for the wrong reason.
- **Project-relative matching.** `under()` on an absolute path matches relative to the nearest
  package root. A fixture path with no `Gemfile`, `package.json`, `pyproject.toml`, or `manage.py`
  above it falls back to `CLAUDE_PROJECT_DIR` or the event cwd. Build fixture trees with the marker
  they need.
- **`json.load(sys.stdin)` outside a try** is the classic crash. Use `hooklib.load_event()`, or
  `hooklib.load_event_strict()` when the hook must refuse or report an event it could not parse.
