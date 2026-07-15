#!/usr/bin/env python3
"""
Hook test harness — runs all hook test cases and reports results.

Usage:
  python .claude/hooks/tests/run-all.py

Each test sends simulated tool_input JSON to a hook script via stdin
and asserts on the exit code and stdout output.
"""
import json
import subprocess
import sys
import os

HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASS = 0
FAIL = 0


def run_hook(hook_script, tool_name, tool_input):
    """Run a hook script with simulated input and return (exit_code, stdout)."""
    data = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook_script)],
        input=data,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode, result.stdout.strip()


def run_prompt_hook(hook_script, prompt):
    """Run a UserPromptSubmit hook with simulated prompt and return (exit_code, stdout)."""
    data = json.dumps({"prompt": prompt})
    result = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook_script)],
        input=data,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode, result.stdout.strip()


def assert_allowed(name, hook_script, tool_name, tool_input):
    """Assert the hook allows the action (exit 0, no deny output)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if code == 0 and "deny" not in stdout.lower():
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — exit={code}, output={stdout[:200]}")


def assert_blocked(name, hook_script, tool_name, tool_input):
    """Assert the hook blocks the action (deny in output or exit != 0)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if "deny" in stdout.lower() or code != 0:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected block, got exit={code}, output={stdout[:200]}")


def assert_warns(name, hook_script, tool_name, tool_input):
    """Assert the hook produces a warning (ask in output)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if "ask" in stdout.lower() or "warn" in stdout.lower():
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected warning, got exit={code}, output={stdout[:200]}")


def assert_silent(name, hook_script, tool_name, tool_input):
    """Assert the hook exits 0 with no output (silent skip)."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if code == 0 and stdout == "":
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected silent exit, got exit={code}, output={stdout[:200]}")


def assert_output_contains(name, hook_script, tool_name, tool_input, substring):
    """Assert the hook output contains a specific substring."""
    global PASS, FAIL
    code, stdout = run_hook(hook_script, tool_name, tool_input)
    if code == 0 and substring.lower() in stdout.lower():
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — expected '{substring}' in output, got exit={code}, output={stdout[:200]}")


def test_dangerous_command_blocker():
    print("\n[dangerous-command-blocker.py]")
    assert_blocked("blocks rm -rf /", "dangerous-command-blocker.py", "Bash",
                   {"command": "rm -rf /"})
    assert_blocked("blocks DROP TABLE", "dangerous-command-blocker.py", "Bash",
                   {"command": "psql -c 'DROP TABLE users;'"})
    assert_blocked("blocks sudo rm", "dangerous-command-blocker.py", "Bash",
                   {"command": "sudo rm -rf /var/data"})
    assert_blocked("blocks chmod 777", "dangerous-command-blocker.py", "Bash",
                   {"command": "chmod 777 /etc/passwd"})
    # Redis on this stack is BOTH the Rails cache backend and the Sidekiq queue store, so
    # FLUSHALL against production does not clear a cache — it destroys every enqueued job,
    # irreversibly and without an error. `incident-responder` holds Bash and its own protocol
    # says "Clear stuck queues only as last resort (loses jobs)"; that parenthetical was the
    # only thing standing between a stuck queue and a lost one, and prose is not enforcement.
    assert_blocked("blocks remote redis FLUSHALL", "dangerous-command-blocker.py", "Bash",
                   {"command": "redis-cli -h prod.abc.cache.amazonaws.com FLUSHALL"})
    assert_blocked("blocks remote redis FLUSHDB via -u", "dangerous-command-blocker.py", "Bash",
                   {"command": "redis-cli -u $REDIS_URL FLUSHDB"})
    # ...and must NOT touch ordinary local development, or an incident responder's diagnosis.
    # A gate that flags correct work is a gate people learn to ignore.
    assert_allowed("allows local redis FLUSHALL (dev)", "dangerous-command-blocker.py", "Bash",
                   {"command": "redis-cli FLUSHALL"})
    assert_allowed("allows explicit localhost FLUSHALL", "dangerous-command-blocker.py", "Bash",
                   {"command": "redis-cli -h 127.0.0.1 -p 6379 FLUSHDB"})
    assert_allowed("allows read-only redis against prod", "dangerous-command-blocker.py", "Bash",
                   {"command": "redis-cli -h prod-redis LLEN queue:default"})
    assert_allowed("allows safe git commands", "dangerous-command-blocker.py", "Bash",
                   {"command": "git status"})
    assert_allowed("allows npm commands", "dangerous-command-blocker.py", "Bash",
                   {"command": "npm run test"})
    assert_allowed("skips non-Bash tools", "dangerous-command-blocker.py", "Read",
                   {"file_path": "/etc/passwd"})


def test_migration_validator():
    print("\n[migration-validator.py]")
    assert_warns("warns on up without down", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240101_add_column.rb",
        "content": "class AddColumn < ActiveRecord::Migration\n  def up\n    add_column :users, :age, :integer\n  end\nend"
    })
    assert_warns("warns on remove_column WITHOUT a type (genuinely irreversible)",
                 "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240102_remove_field.rb",
        "content": "class RemoveField < ActiveRecord::Migration[7.1]\n  def change\n    remove_column :users, :legacy_field\n  end\nend"
    })
    # The gate must not fire on the form the db-migration guide recommends. ActiveRecord CAN
    # invert `remove_column` when the type is present, so warning here would flag correct code
    # — and a gate that cries wolf is one people learn to click through.
    assert_allowed("allows remove_column WITH a type (reversible — the recommended form)",
                   "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240102_remove_typed.rb",
        "content": "class RemoveTyped < ActiveRecord::Migration[7.1]\n  def change\n    remove_column :users, :legacy_field, :string\n  end\nend"
    })
    # rename_column is reversible — so it must NOT be called irreversible. It is still risky,
    # for a different reason, and the reason must name the real remedy.
    assert_output_contains("rename_column warns about rolling deploys, not reversibility",
                           "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240105_rename.rb",
        "content": "class Rename < ActiveRecord::Migration[7.1]\n  def change\n    rename_column :users, :name, :full_name\n  end\nend"
    }, "expand/contract")
    assert_allowed("allows drop_table WITH a block (reversible)",
                   "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240106_drop.rb",
        "content": "class Drop < ActiveRecord::Migration[7.1]\n  def change\n    drop_table :legacy do |t|\n      t.string :name\n    end\n  end\nend"
    })
    # Wrapper-agnostic: a repo that does not use `backend/` must still be validated.
    assert_warns("validates migrations under any wrapper (api/db/migrate)",
                 "migration-validator.py", "Write", {
        "file_path": "api/db/migrate/20240107_remove_field.rb",
        "content": "class RemoveField < ActiveRecord::Migration[7.1]\n  def change\n    remove_column :users, :legacy_field\n  end\nend"
    })
    assert_warns("warns on SQL interpolation", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240103_custom.rb",
        "content": 'class Custom < ActiveRecord::Migration\n  def up\n    execute "UPDATE users SET name = \'#{value}\'"\n  end\nend'
    })
    assert_allowed("allows safe migration", "migration-validator.py", "Write", {
        "file_path": "backend/db/migrate/20240104_safe.rb",
        "content": "class Safe < ActiveRecord::Migration\n  def change\n    add_column :users, :nickname, :string\n  end\nend"
    })
    assert_allowed("skips non-migration files", "migration-validator.py", "Write", {
        "file_path": "backend/app/models/user.rb",
        "content": "class User < ApplicationRecord\nend"
    })


def test_deployment_gate():
    print("\n[deployment-gate.py]")
    assert_warns("warns on git push to main", "deployment-gate.py", "Bash",
                 {"command": "git push origin main"})
    assert_warns("warns on force push", "deployment-gate.py", "Bash",
                 {"command": "git push -f origin feature"})
    # Terraform is owned by terraform-command-gate.py, not this hook — two hooks deciding
    # the same command meant a double prompt (approval fatigue) and, on -auto-approve,
    # contradictory decisions (ask vs deny).
    assert_silent("delegates terraform entirely to the three-tier gate", "deployment-gate.py",
                  "Bash", {"command": "terraform apply -auto-approve"})
    assert_warns("warns on vercel deploy", "deployment-gate.py", "Bash",
                 {"command": "vercel deploy --prod"})
    assert_warns("warns on docker push", "deployment-gate.py", "Bash",
                 {"command": "docker push myregistry/myapp:latest"})
    assert_allowed("allows safe commands", "deployment-gate.py", "Bash",
                   {"command": "npm run build"})
    assert_allowed("allows terraform plan", "deployment-gate.py", "Bash",
                   {"command": "terraform plan"})


def test_pre_commit_check():
    print("\n[pre-commit-check.py]")
    # Note: pre-commit-check.py behavior depends on implementation
    assert_allowed("allows non-git commands", "pre-commit-check.py", "Bash",
                   {"command": "npm test"})


def test_accessibility_checker():
    print("\n[accessibility-checker.py]")

    # --- Silent skips for non-matching files ---
    assert_silent("skips markdown files", "accessibility-checker.py", "Edit",
                  {"file_path": "README.md"})
    assert_silent("skips JSON config", "accessibility-checker.py", "Edit",
                  {"file_path": ".claude/settings.json"})
    assert_silent("skips Ruby files", "accessibility-checker.py", "Edit",
                  {"file_path": "backend/app/models/user.rb"})
    assert_silent("skips Python files", "accessibility-checker.py", "Edit",
                  {"file_path": ".claude/hooks/test-runner.py"})
    assert_silent("skips tsx outside web/next/frontend", "accessibility-checker.py", "Edit",
                  {"file_path": "mobile/src/components/Button.tsx"})
    assert_silent("skips empty input", "accessibility-checker.py", "Edit",
                  {"file_path": ""})

    # --- Warnings on matching files ---
    # Create temp test files for detection tests
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    web_dir = os.path.join(tmpdir, "web", "src", "components")
    os.makedirs(web_dir)

    # Test: div onClick detection
    div_click_file = os.path.join(web_dir, "BadButton.tsx")
    with open(div_click_file, "w") as f:
        f.write('<div onClick={() => handleClick()}>Click me</div>')
    assert_output_contains("warns on div onClick", "accessibility-checker.py", "Edit",
                           {"file_path": div_click_file}, "non-semantic")

    # Test: span onClick detection
    span_click_file = os.path.join(web_dir, "BadSpan.tsx")
    with open(span_click_file, "w") as f:
        f.write('<span onClick={toggle} className="link">Toggle</span>')
    assert_output_contains("warns on span onClick", "accessibility-checker.py", "Edit",
                           {"file_path": span_click_file}, "non-semantic")

    # Test: img without alt
    img_file = os.path.join(web_dir, "BadImage.tsx")
    with open(img_file, "w") as f:
        f.write('<img src="/logo.png" width={100} />')
    assert_output_contains("warns on img without alt", "accessibility-checker.py", "Edit",
                           {"file_path": img_file}, "alt text")

    # Test: Image (next/image) without alt
    next_dir = os.path.join(tmpdir, "next", "app", "components")
    os.makedirs(next_dir)
    next_img_file = os.path.join(next_dir, "Hero.tsx")
    with open(next_img_file, "w") as f:
        f.write('<Image src="/hero.jpg" width={800} height={400} />')
    assert_output_contains("warns on next/image without alt", "accessibility-checker.py", "Edit",
                           {"file_path": next_img_file}, "alt text")

    # Test: input without label
    input_file = os.path.join(web_dir, "BadForm.tsx")
    with open(input_file, "w") as f:
        f.write('<input type="text" id="email" placeholder="Email" />')
    assert_output_contains("warns on input without label", "accessibility-checker.py", "Edit",
                           {"file_path": input_file}, "label")

    # Test: outline:none
    outline_file = os.path.join(web_dir, "BadFocus.tsx")
    with open(outline_file, "w") as f:
        f.write('const style = { outline: none };\n<button style={style}>Go</button>')
    assert_output_contains("warns on outline:none", "accessibility-checker.py", "Edit",
                           {"file_path": outline_file}, "focus indicator")

    # Test: aria-hidden with onClick
    aria_file = os.path.join(web_dir, "BadAria.tsx")
    with open(aria_file, "w") as f:
        f.write('<div aria-hidden="true" onClick={close}>X</div>')
    assert_output_contains("warns on aria-hidden with onClick", "accessibility-checker.py", "Edit",
                           {"file_path": aria_file}, "hidden from assistive")

    # Test: clean file passes silently
    clean_file = os.path.join(web_dir, "GoodButton.tsx")
    with open(clean_file, "w") as f:
        f.write('<button onClick={handleClick}>Click me</button>\n<img src="/logo.png" alt="Company logo" />')
    assert_silent("no warnings on clean file", "accessibility-checker.py", "Edit",
                  {"file_path": clean_file})

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_api_design_checker():
    print("\n[api-design-checker.py]")

    # --- Silent skips for non-matching files ---
    assert_silent("skips markdown files", "api-design-checker.py", "Edit",
                  {"file_path": "README.md"})
    assert_silent("skips settings JSON", "api-design-checker.py", "Edit",
                  {"file_path": ".claude/settings.json"})
    assert_silent("skips model files", "api-design-checker.py", "Edit",
                  {"file_path": "backend/app/models/user.rb"})
    assert_silent("skips view files", "api-design-checker.py", "Edit",
                  {"file_path": "web/src/components/Button.tsx"})
    assert_silent("skips empty input", "api-design-checker.py", "Edit",
                  {"file_path": ""})

    # --- Warnings on matching files ---
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    ctrl_dir = os.path.join(tmpdir, "backend", "app", "controllers")
    os.makedirs(ctrl_dir)

    # Test: verb in route path
    verb_file = os.path.join(ctrl_dir, "routes.rb")
    with open(verb_file, "w") as f:
        f.write("get '/api/getUsers', to: 'users#index'\n")
    assert_output_contains("warns on verb in URL path", "api-design-checker.py", "Edit",
                           {"file_path": verb_file}, "verb")

    # Test: unwrapped array response (Rails)
    array_file = os.path.join(ctrl_dir, "users_controller.rb")
    with open(array_file, "w") as f:
        f.write("render json: [user1, user2, user3]\n")
    assert_output_contains("warns on unwrapped array (Rails)", "api-design-checker.py", "Edit",
                           {"file_path": array_file}, "data key")

    # Test: error response missing code/request_id
    error_file = os.path.join(ctrl_dir, "orders_controller.rb")
    with open(error_file, "w") as f:
        f.write('render json: { error: "Not found" }, status: :not_found\n')
    assert_output_contains("warns on error missing code/request_id", "api-design-checker.py", "Edit",
                           {"file_path": error_file}, "error response missing")

    # The envelope is camelCase (`std-api-design/SKILL.md:54` states it; errors-rails.md and
    # errors-typescript.md both write `requestId`). The old check grepped for the SUBSTRING
    # "request_id", so this exactly-correct envelope was flagged "missing request_id" — and the
    # remedy it named would have put a snake_case key in a camelCase API.
    #
    # The canonical example passed only by luck: `requestId: request.request_id` carries the
    # substring on the VALUE side. Change the value and the gate turned on correct code.
    camel_file = os.path.join(ctrl_dir, "camel_controller.rb")
    with open(camel_file, "w") as f:
        f.write('rid = request.uuid\n'
                'render json: { error: "Not found", code: "NOT_FOUND", status: 404, '
                'requestId: rid }, status: :not_found\n')
    assert_silent("correct camelCase envelope is not flagged", "api-design-checker.py", "Edit",
                  {"file_path": camel_file})

    # And the canonical form from errors-rails.md itself, value side included.
    canon_file = os.path.join(ctrl_dir, "canon_controller.rb")
    with open(canon_file, "w") as f:
        f.write('render json: { error: msg, code: code, status: 422, '
                'requestId: request.request_id }, status: :unprocessable_entity\n')
    assert_silent("canonical errors-rails.md envelope is not flagged", "api-design-checker.py",
                  "Edit", {"file_path": canon_file})

    # Present-but-snake_case is a DIFFERENT bug than absent, and gets its own remedy.
    snake_file = os.path.join(ctrl_dir, "snake_controller.rb")
    with open(snake_file, "w") as f:
        f.write('render json: { error: "Not found", code: "NOT_FOUND", status: 404, '
                'request_id: request.request_id }, status: :not_found\n')
    assert_output_contains("warns on snake_case requestId key", "api-design-checker.py", "Edit",
                           {"file_path": snake_file}, "camelCase")

    # `code` was matched as a bare substring, so `status_code` satisfied it.
    subst_file = os.path.join(ctrl_dir, "substring_controller.rb")
    with open(subst_file, "w") as f:
        f.write('render json: { error: "Boom", status_code: 500, requestId: rid }, '
                'status: :internal_server_error\n')
    assert_output_contains("`status_code` does not satisfy the `code` key",
                           "api-design-checker.py", "Edit", {"file_path": subst_file}, "code")

    # Test: POST create returning 200
    post_file = os.path.join(ctrl_dir, "items_controller.rb")
    with open(post_file, "w") as f:
        f.write("def create\n  item = Item.create!(params)\n  render json: item, status: :ok\nend\n")
    assert_output_contains("warns on POST returning 200", "api-design-checker.py", "Edit",
                           {"file_path": post_file}, "201")

    # Test: JS API unwrapped array
    api_dir = os.path.join(tmpdir, "mobile", "src", "api")
    os.makedirs(api_dir)
    js_array_file = os.path.join(api_dir, "users.ts")
    with open(js_array_file, "w") as f:
        f.write("res.json([user1, user2])\n")
    assert_output_contains("warns on unwrapped array (JS)", "api-design-checker.py", "Edit",
                           {"file_path": js_array_file}, "data key")

    # Test: clean controller passes silently
    clean_file = os.path.join(ctrl_dir, "clean_controller.rb")
    with open(clean_file, "w") as f:
        f.write("def index\n  render json: { data: users, meta: { total: count } }\nend\n")
    assert_silent("no warnings on clean controller", "api-design-checker.py", "Edit",
                  {"file_path": clean_file})

    # Cleanup temp files
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_vague_request_detector():
    print("\n[vague-request-detector.py]")
    global PASS, FAIL

    # --- Vague requests should trigger interactive prompt ---
    def assert_interactive(name, prompt, expected_substring):
        global PASS, FAIL
        code, stdout = run_prompt_hook("vague-request-detector.py", prompt)
        if code == 0 and expected_substring.lower() in stdout.lower():
            PASS += 1
            print(f"  PASS: {name}")
        else:
            FAIL += 1
            print(f"  FAIL: {name} — expected '{expected_substring}' in output, got exit={code}, output={stdout[:200]}")

    def assert_no_trigger(name, prompt):
        global PASS, FAIL
        code, stdout = run_prompt_hook("vague-request-detector.py", prompt)
        if code == 0 and stdout == "":
            PASS += 1
            print(f"  PASS: {name}")
        else:
            FAIL += 1
            print(f"  FAIL: {name} — expected silent exit, got exit={code}, output={stdout[:200]}")

    # Vague requests that should trigger
    assert_interactive(
        "triggers on 'we need a feature'",
        "we need a notification feature",
        "AskUserQuestion",
    )
    assert_interactive(
        "triggers on 'make it better'",
        "make it better and faster",
        "AskUserQuestion",
    )
    assert_interactive(
        "triggers on 'like uber app'",
        "build something like uber app",
        "AskUserQuestion",
    )
    assert_interactive(
        "triggers on one-word feature",
        "add notifications",
        "AskUserQuestion",
    )
    assert_interactive(
        "includes requirements-consultant routing",
        "we want a chat system module",
        "requirements-consultant",
    )

    # Clear requests that should NOT trigger
    assert_no_trigger(
        "skips short prompts",
        "fix bug",
    )
    assert_no_trigger(
        "skips slash commands",
        "/code-reviewer check my PR",
    )
    assert_no_trigger(
        "skips explicit requirements work",
        "help me clarify requirements for the auth system",
    )
    assert_no_trigger(
        "skips user stories request",
        "write user stories for the checkout flow",
    )
    assert_no_trigger(
        "skips specific implementation request",
        "Add a created_at index to the orders table in the backend migration",
    )


def test_ci_workflow_is_loadable():
    """Layer 7 must not vanish silently. A workflow file that does not parse is simply
    never run — GitHub reports nothing, every local signal stays green, and the external
    backstop is gone. That is the "dead gate masquerading as a green one" failure one
    layer up, so it gets the same treatment: a test."""
    print("\n[CI workflow — layer 7 must not vanish silently]")
    global PASS, FAIL
    import yaml

    wf = os.path.join(HOOKS_DIR, "..", ".github", "workflows", "ci.yml")
    if not os.path.isfile(wf):
        FAIL += 1
        print("  FAIL: .github/workflows/ci.yml is missing — layer 7 has no CI at all")
        return
    try:
        doc = yaml.safe_load(open(wf, encoding="utf-8"))
    except Exception as exc:
        FAIL += 1
        print(f"  FAIL: ci.yml does not parse — GitHub would silently never run it: {exc}")
        return

    PASS += 1
    print("  PASS: ci.yml parses (GitHub will actually run it)")

    jobs = doc.get("jobs") or {}
    # The gates that must exist for the plugin to practise the discipline it enforces.
    required = ["hook-fixtures", "plugin-manifest", "skills-lint", "sentinel-guard"]
    missing = [j for j in required if j not in jobs]
    if missing:
        FAIL += 1
        print(f"  FAIL: ci.yml lost required job(s): {missing}")
    else:
        PASS += 1
        print(f"  PASS: all required CI jobs present ({len(jobs)} jobs)")

    # Each job's inline python must at least be syntactically valid, or the job fails at
    # runtime for a reason no local check would have caught.
    import ast, re
    bad = []
    raw = open(wf, encoding="utf-8").read()
    for block in re.findall(r"python - <<'EOF'\n(.*?)\n\s*EOF", raw, re.S):
        src = "\n".join(line[10:] if line.startswith(" " * 10) else line.lstrip()
                        for line in block.split("\n"))
        try:
            ast.parse(src)
        except SyntaxError as exc:
            bad.append(str(exc).split("(")[0].strip())
    if bad:
        FAIL += 1
        print(f"  FAIL: inline CI python has syntax errors: {bad}")
    else:
        PASS += 1
        print("  PASS: every inline CI python block parses")


def test_deny_reasons_name_a_remedy():
    """Ch. 25 — "the model argues with a denial". Root cause: the reason names what is
    forbidden but not what to do INSTEAD. "Denied" invites retries; "denied because X,
    do Y instead" invites Y. Every deny reason must therefore name a remedy."""
    print("\n[deny reasons must name a remedy]")
    global PASS, FAIL
    import re, glob

    # A remedy tells the agent what to DO: an alternative action, or where to go.
    REMEDY = re.compile(
        r"instead|manual|prefer|revert|review it|open a pr|expected:|"
        r"use `|run `|`git |plan first|outside claude code",
        re.I,
    )
    checked = 0
    for path in sorted(glob.glob(os.path.join(HOOKS_DIR, "*.py"))):
        src = open(path, encoding="utf-8").read()
        for m in re.finditer(r'hooklib\.deny\(\s*((?:\s*(?:f?"[^"]*"|\'[^\']*\')\s*)+)', src):
            reason = " ".join(re.findall(r'"([^"]*)"', m.group(1)))
            if not reason.strip():
                continue
            checked += 1
            name = os.path.basename(path)
            if REMEDY.search(reason):
                PASS += 1
                print(f"  PASS: {name} deny names a remedy — {reason[:44].strip()}…")
            else:
                FAIL += 1
                print(f"  FAIL: {name} deny states a prohibition with NO remedy — {reason[:70]!r}")
    if checked == 0:
        FAIL += 1
        print("  FAIL: found no deny reasons to audit (regex drifted?)")


def test_terraform_command_gate():
    """Ch. 10 Pattern 3 — the three-tier command gate: DENY the never-legitimate,
    ASK the serious-but-real, ALLOW (fall through) the read-only surface. Fail-closed."""
    print("\n[terraform-command-gate.py — three-tier command gate]")

    # Tier 1 — DENY the irreversible
    for name, cmd in [
        ("denies terraform destroy", "terraform destroy"),
        ("denies tofu destroy (OpenTofu)", "tofu destroy"),
        ("denies destroy with flags before subcommand", "terraform -chdir=prod destroy"),
        ("denies state rm (state surgery)", "terraform state rm aws_db_instance.main"),
        ("denies state mv", "terraform state mv a b"),
        ("denies state push", "terraform state push new.tfstate"),
        ("denies force-unlock", "terraform force-unlock 1234"),
        ("denies apply -auto-approve", "terraform apply -auto-approve"),
        ("denies apply --auto-approve", "terraform apply --auto-approve"),
    ]:
        assert_blocked(name, "terraform-command-gate.py", "Bash", {"command": cmd})

    # Tier 2 — ASK on a real apply
    assert_warns("asks on terraform apply (human confirms)", "terraform-command-gate.py", "Bash",
                 {"command": "terraform apply"})
    assert_output_contains("apply ask carries the review checklist", "terraform-command-gate.py",
                           "Bash", {"command": "terraform apply"}, "plan")

    # Tier 3 — ALLOW the read-only surface (must fall through silently)
    for name, cmd in [
        ("allows terraform plan", "terraform plan"),
        ("allows plan -destroy (a PREVIEW, not a destroy)", "terraform plan -destroy"),
        ("allows validate", "terraform validate"),
        ("allows fmt", "terraform fmt -check"),
        ("allows output", "terraform output -json"),
        ("allows state list (read-only)", "terraform state list"),
        ("allows state show (read-only)", "terraform state show aws_vpc.main"),
        ("ignores non-terraform commands", "npm run build"),
        ("ignores non-Bash tools", None),
    ]:
        if cmd is None:
            assert_silent(name, "terraform-command-gate.py", "Edit", {"file_path": "main.tf"})
        else:
            assert_silent(name, "terraform-command-gate.py", "Bash", {"command": cmd})


def test_fail_open_is_not_silent():
    """Ch. 9: "Silent failure is invisible failure." Advisory hooks fail OPEN (a crash
    must never block the edit) but must NOT fail silently — a swallowed exception makes
    a dead gate indistinguishable from a passing one. Every fail-open path must emit an
    actionable HOOK ERROR line naming the checker."""
    print("\n[fail-open visibility — dead gates must not look green]")
    global PASS, FAIL
    import tempfile, os, json as _json

    def run(script, event):
        r = subprocess.run([sys.executable, script], input=_json.dumps(event),
                           capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout

    ev = {"tool_name": "Write", "tool_input": {"file_path": "x.rb", "content": "x"}}

    def assert_visible(name, body, expect_token):
        global PASS, FAIL
        probe = os.path.join(HOOKS_DIR, "_failvis_probe.py")
        with open(probe, "w", encoding="utf-8") as f:
            f.write(body)
        try:
            code, out = run(probe, ev)
            ok = code == 0 and "HOOK ERROR" in out and expect_token in out
            if ok:
                PASS += 1; print(f"  PASS: {name}")
            else:
                FAIL += 1
                print(f"  FAIL: {name} — exit={code} stdout={out[:120]!r}")
        finally:
            if os.path.exists(probe):
                os.remove(probe)

    # a checker that raises must still exit 0 (fail-open) AND announce itself
    assert_visible(
        "crashing checker reports HOOK ERROR and still exits 0",
        'import _hooklib as hooklib\n'
        'def check(event):\n'
        '    raise RuntimeError("boom")\n'
        'if __name__ == "__main__":\n'
        '    hooklib.run_post_checker(check)\n',
        "boom",
    )
    # the error names the failing script so it is actionable
    assert_visible(
        "HOOK ERROR names the failing checker",
        'import _hooklib as hooklib\n'
        'def check(event):\n'
        '    raise ValueError("bad regex")\n'
        'if __name__ == "__main__":\n'
        '    hooklib.run_post_checker(check)\n',
        "_failvis_probe.py",
    )
    # a healthy checker stays quiet — the signal must not be noise
    probe = os.path.join(HOOKS_DIR, "_failvis_ok.py")
    with open(probe, "w", encoding="utf-8") as f:
        f.write('import _hooklib as hooklib\n'
                'def check(event):\n'
                '    return []\n'
                'if __name__ == "__main__":\n'
                '    hooklib.run_post_checker(check)\n')
    try:
        code, out = run(probe, ev)
        if code == 0 and out.strip() == "":
            PASS += 1; print("  PASS: healthy checker emits nothing (no false alarms)")
        else:
            FAIL += 1; print(f"  FAIL: healthy checker emitted {out[:80]!r}")
    finally:
        if os.path.exists(probe):
            os.remove(probe)

    # the dispatcher must report a broken checker rather than skipping it silently
    disp = os.path.join(HOOKS_DIR, "post-edit-dispatch.py")
    src = open(disp, encoding="utf-8").read()
    if "hook_error" in src and "except Exception as exc" in src:
        PASS += 1; print("  PASS: dispatcher reports a failing checker instead of skipping silently")
    else:
        FAIL += 1; print("  FAIL: dispatcher still swallows checker exceptions silently")

    # A GAP IN THE AUDIT TRAIL MUST ANNOUNCE ITSELF. A silent logging failure leaves
    # invisible holes plus false confidence the trail is complete — worse than no trail.
    import shutil
    root = tempfile.mkdtemp()
    try:
        # make .claude a FILE so both makedirs() and the append fail
        with open(os.path.join(root, ".claude"), "w") as f:
            f.write("not a dir")
        r = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, "audit-logger.py")],
                           input=_json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                           capture_output=True, text=True, cwd=root, timeout=15)
        if r.returncode == 0 and "HOOK ERROR" in r.stdout and "gap" in r.stdout.lower():
            PASS += 1; print("  PASS: unwritable audit trail reports a gap (and never blocks)")
        else:
            FAIL += 1; print(f"  FAIL: audit trail gap was silent — exit={r.returncode} out={r.stdout[:90]!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # a malformed event must not produce a raw traceback at the user
    r = subprocess.run([sys.executable, os.path.join(HOOKS_DIR, "vague-request-detector.py")],
                       input='{"prompt":', capture_output=True, text=True, timeout=15)
    if r.returncode == 0 and "Traceback" not in r.stdout + r.stderr and "HOOK ERROR" in r.stdout:
        PASS += 1; print("  PASS: malformed event reports one line, not a traceback")
    else:
        FAIL += 1; print(f"  FAIL: malformed event — exit={r.returncode} err={r.stderr[:80]!r}")


def test_permission_sentinel():
    """Layer-4 sentinel (the 'plugin trap'): a plugin cannot ship `permissions`, so
    the SessionStart hook must verify the deny floor was copied into the consuming
    project and warn loudly when it wasn't. Silent absence -> visible warning."""
    print("\n[session-start-check.py — permission sentinel]")
    global PASS, FAIL
    import tempfile, os, shutil, json as _json

    def run_session_start(cwd):
        result = subprocess.run(
            [sys.executable, os.path.join(HOOKS_DIR, "session-start-check.py")],
            input=_json.dumps({"cwd": cwd}),
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode, result.stdout

    def case(name, deny, expect_gap, write_settings=True, raw=None):
        global PASS, FAIL
        root = tempfile.mkdtemp()
        try:
            if write_settings:
                os.makedirs(os.path.join(root, ".claude"))
                p = os.path.join(root, ".claude", "settings.json")
                with open(p, "w", encoding="utf-8") as f:
                    if raw is not None:
                        f.write(raw)
                    else:
                        _json.dump({"permissions": {"deny": deny}}, f)
            code, out = run_session_start(root.replace("\\", "/"))
            got_gap = "GOVERNANCE GAP" in out
            if code == 0 and got_gap == expect_gap:
                PASS += 1
                print(f"  PASS: {name}")
            else:
                FAIL += 1
                print(f"  FAIL: {name} — exit={code} gap={got_gap} expected_gap={expect_gap}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    # The authoritative floor is the plugin's own reference settings — so the check is
    # self-maintaining and detects a STALE floor, not just an absent one.
    ref = _json.load(open(os.path.join(HOOKS_DIR, "..", ".claude", "settings.json"),
                          encoding="utf-8"))["permissions"]["deny"]

    case("silent when the CURRENT floor is copied in full", ref, expect_gap=False)
    case("warns when the deny list is empty", [], expect_gap=True)
    case("warns when .claude/settings.json is absent", None, expect_gap=True, write_settings=False)
    case("warns when settings.json is unparseable", None, expect_gap=True, raw="{ not json")
    case("exits 0 even on a gap (informational, never blocks)", [], expect_gap=True)

    # STALENESS: a floor copied from an older plugin version is silently incomplete.
    # A hardcoded sample can prove a floor is ABSENT but never that it is CURRENT.
    stale = [r for r in ref if "terraform" not in r and "tofu" not in r]

    def stale_case(name, deny, expect_stale_wording):
        global PASS, FAIL
        root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, ".claude"))
            with open(os.path.join(root, ".claude", "settings.json"), "w", encoding="utf-8") as f:
                _json.dump({"permissions": {"deny": deny}}, f)
            code, out = run_session_start(root.replace("\\", "/"))
            ok = code == 0 and ("STALE" in out) == expect_stale_wording
            if ok:
                PASS += 1; print(f"  PASS: {name}")
            else:
                FAIL += 1; print(f"  FAIL: {name} — out={out[:110]!r}")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    import shutil
    stale_case("detects a STALE floor (older copy, missing newer denies)", stale, True)
    stale_case("an empty floor reads as absent, not stale", [], False)

    # and it must name the exact missing rules, not just say 'something is missing'
    root = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(root, ".claude"))
        with open(os.path.join(root, ".claude", "settings.json"), "w", encoding="utf-8") as f:
            _json.dump({"permissions": {"deny": stale}}, f)
        code, out = run_session_start(root.replace("\\", "/"))
        if "terraform destroy" in out and f"of {len(ref)}" in out:
            PASS += 1; print("  PASS: names the exact missing rules and the floor size")
        else:
            FAIL += 1; print(f"  FAIL: gap message not actionable — {out[:110]!r}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_hooklib_primitives():
    """Unit-test the wrapper-agnostic matching primitives in _hooklib directly."""
    print("\n[_hooklib primitives]")
    global PASS, FAIL
    sys.path.insert(0, HOOKS_DIR)
    import _hooklib as h

    def check(name, got, want):
        global PASS, FAIL
        if got == want:
            PASS += 1
            print(f"  PASS: {name}")
        else:
            FAIL += 1
            print(f"  FAIL: {name} — got {got!r} want {want!r}")

    check("under matches standard wrapper", h.under("backend/app/models/u.rb", "app/models"), True)
    check("under matches non-standard wrapper", h.under("api/app/models/u.rb", "app/models"), True)
    check("under matches repo root", h.under("app/models/u.rb", "app/models"), True)
    check("under rejects partial segment", h.under("myapp/models/u.rb", "app/models"), False)
    check("replace_first_segment preserves wrapper",
          h.replace_first_segment("api/app/models/u.rb", "app", "spec"), "api/spec/models/u.rb")
    check("replace_first_segment src->tests",
          h.replace_first_segment("frontend/src/x.tsx", "src", "tests"), "frontend/tests/x.tsx")
    check("detect_framework path fallback (rails)", h.detect_framework("zz/app/models/u.rb"), "rails")
    check("detect_framework path fallback (react-native)", h.detect_framework("zz/src/screens/H.tsx"), "react-native")
    check("detect_framework path fallback (vite)", h.detect_framework("zz/src/pages/D.tsx"), "vite")


def test_wrapper_agnostic():
    """Conventions must auto-load regardless of the wrapper directory name.
    The SAME canonical structure under a NON-STANDARD wrapper (api/, server/,
    frontend/, platform/, ...) must trigger the same checkers as the standard
    layout. Each fixture is rooted at an isolated temp dir with a .git sentinel
    so detect_framework's ancestor walk does not leak markers between cases."""
    print("\n[wrapper-agnostic detection]")
    import tempfile, os, shutil

    def fixture(files):
        """Create an isolated project root (.git sentinel) with the given
        {relpath: content} files. Returns (root, {relpath: abs_forward_path})."""
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, ".git"))
        paths = {}
        for rel, content in files.items():
            full = os.path.join(root, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            paths[rel] = full.replace("\\", "/")
        return root, paths

    # A leaked secret, not a missing request_id: the request_id-per-line check was removed —
    # Rails injects that id via `config.log_tags`, so it is never in the source, and the remedy
    # for its absence is config rather than the call site. The sensitive-data check is what
    # monitoring-checker still owns, so that is what must prove wrapper-agnostic here.
    LOG_RB = ('class XController\n  def show\n'
              '    Rails.logger.info("user #{user.password} in")\n  end\nend\n')
    LONG_MODEL = "class User\n" + "\n".join("  # c%d" % i for i in range(205)) + "\nend\n"
    IMG = '<img src="/logo.png" width={100} />\n'

    # monitoring-checker: Rails controller under api/ (not backend/)
    root, p = fixture({"api/app/controllers/x_controller.rb": LOG_RB})
    assert_output_contains("monitoring warns under api/ wrapper", "monitoring-checker.py",
                           "Write", {"file_path": p["api/app/controllers/x_controller.rb"]},
                           "sensitive")
    shutil.rmtree(root, ignore_errors=True)

    # code-quality-checker: 201-line Rails model under server/ (200-line model limit)
    root, p = fixture({"server/app/models/user.rb": LONG_MODEL})
    assert_output_contains("code-quality warns on long model under server/", "code-quality-checker.py",
                           "Write", {"file_path": p["server/app/models/user.rb"]}, "200-line")
    shutil.rmtree(root, ignore_errors=True)

    # api-design-checker: verb-in-path controller under api/
    root, p = fixture({"api/app/controllers/users_controller.rb": "get '/api/getUsers', to: 'users#index'\n"})
    assert_output_contains("api-design warns under api/ wrapper", "api-design-checker.py",
                           "Write", {"file_path": p["api/app/controllers/users_controller.rb"]}, "verb")
    shutil.rmtree(root, ignore_errors=True)

    # accessibility-checker: Vite web (vite.config marker) under frontend/ IS checked
    root, p = fixture({"frontend/vite.config.ts": "export default {}\n",
                       "frontend/src/components/Hero.tsx": IMG})
    assert_output_contains("accessibility warns for Vite under frontend/", "accessibility-checker.py",
                           "Write", {"file_path": p["frontend/src/components/Hero.tsx"]}, "alt text")
    shutil.rmtree(root, ignore_errors=True)

    # accessibility-checker: React Native (react-native + metro markers) IS skipped
    root, p = fixture({"client/package.json": '{"dependencies":{"react-native":"0.74.0"}}',
                       "client/metro.config.js": "module.exports = {}\n",
                       "client/src/components/Hero.tsx": IMG})
    assert_silent("accessibility skips React Native (marker-detected)", "accessibility-checker.py",
                  "Write", {"file_path": p["client/src/components/Hero.tsx"]})
    shutil.rmtree(root, ignore_errors=True)

    # test-coverage-checker: source under platform/ wrapper warns when no test exists
    root, p = fixture({"platform/src/utils/helpers.ts": "export const f = () => 1;\n"})
    assert_output_contains("test-coverage warns under platform/ wrapper", "test-coverage-checker.py",
                           "Write", {"file_path": p["platform/src/utils/helpers.ts"]}, "No test file")
    shutil.rmtree(root, ignore_errors=True)

    # negative: a model (not controller/job) stays silent for monitoring under any wrapper
    root, p = fixture({"api/app/models/user.rb": 'Rails.logger.info "x"\n'})
    assert_silent("monitoring silent for non-controller under api/", "monitoring-checker.py",
                  "Write", {"file_path": p["api/app/models/user.rb"]})
    shutil.rmtree(root, ignore_errors=True)


def run_hook_env(hook_script, payload, env_extra):
    """Run a hook with extra environment, returning (exit_code, stdout)."""
    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook_script)],
        input=json.dumps(payload), capture_output=True, text=True, timeout=15, env=env,
    )
    return proc.returncode, proc.stdout.strip()


def test_configurable_at_the_edges():
    """Ch. 13 — "It's configurable at the edges": hard-coding a team's branch names makes
    the plugin unusable in a repo that calls its trunk something else, and "test the plugin
    in a repo that isn't yours before shipping it". The core rule (don't push straight to
    the trunk) is universal; WHICH branches are the trunk is a parameter. Defaults must not
    change, or this is a silent behavioural break for every existing consumer."""
    print("\n[configurable at the edges — SDH_PROTECTED_BRANCHES]")
    global PASS, FAIL

    # 1. Defaults unchanged: main/master/develop still gated with no env set.
    for branch in ("main", "master", "develop"):
        code, out = run_hook_env("pre-commit-check.py",
                                 {"tool_name": "Bash", "tool_input": {"command": f"git push origin {branch}"}},
                                 {"SDH_PROTECTED_BRANCHES": ""})
        if '"permissionDecision": "ask"' in out and f"'{branch}'" in out:
            PASS += 1
            print(f"  PASS: default still gates a direct push to {branch}")
        else:
            FAIL += 1
            print(f"  FAIL: default no longer gates a direct push to {branch} — silent break: {out[:120]}")

    # 2. A repo whose trunk is `trunk` can protect it.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin trunk"}},
                             {"SDH_PROTECTED_BRANCHES": "trunk,release-line"})
    if "trunk" in out and ("ask" in out.lower() or "deny" in out.lower()):
        PASS += 1
        print("  PASS: SDH_PROTECTED_BRANCHES=trunk gates a push to trunk")
    else:
        FAIL += 1
        print(f"  FAIL: override did not gate the configured trunk: {out[:160]}")

    # 3. Overriding must actually REPLACE the defaults, or the override is decorative.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
                             {"SDH_PROTECTED_BRANCHES": "trunk"})
    if "permissionDecision" not in out:
        PASS += 1
        print("  PASS: override replaces the defaults (main not gated when trunk is the trunk)")
    else:
        FAIL += 1
        print(f"  FAIL: override did not replace defaults — main still gated: {out[:120]}")

    # 4. A blank override means "unset", not "protect nothing" — the unprotected
    #    reading is the dangerous one, so it must fall back to the defaults.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
                             {"SDH_PROTECTED_BRANCHES": "   ,  ,"})
    if "permissionDecision" in out:
        PASS += 1
        print("  PASS: a blank override falls back to defaults (does not silently unprotect)")
    else:
        FAIL += 1
        print("  FAIL: a blank SDH_PROTECTED_BRANCHES silently unprotected every branch")

    # 5. Regex-special branch names must not corrupt the pattern.
    code, out = run_hook_env("pre-commit-check.py",
                             {"tool_name": "Bash", "tool_input": {"command": "git push origin release/v1.0"}},
                             {"SDH_PROTECTED_BRANCHES": "release/v1.0"})
    if "permissionDecision" in out:
        PASS += 1
        print("  PASS: branch names with regex metacharacters are escaped, not broken")
    else:
        FAIL += 1
        print(f"  FAIL: a branch name with '/' or '.' broke the pattern: {out[:120]}")


def test_missing_tool_says_so_once():
    """Ch. 13 — a hook whose tool is missing "should say so once and exit 0, not crash on
    every write". Both failure modes are real: crashing punishes a repo we did not design
    for not having our toolchain, and exiting silently is Ch. 9's "silent failure is
    invisible failure" — the user watches formatting never happen and never learns why."""
    print("\n[works on day one — a missing formatter says so once]")
    global PASS, FAIL
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "example.rb")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("puts 1\n")

        notices = os.path.join(tmp, "notices")
        payload = {"session_id": "sess-abc", "tool_name": "Write",
                   "tool_input": {"file_path": target}}
        # An empty PATH guarantees no formatter is found, whatever the machine has.
        env = {"PATH": os.path.join(tmp, "empty-bin"), "TMPDIR": notices, "TEMP": notices,
               "TMP": notices}
        os.makedirs(os.path.join(tmp, "empty-bin"), exist_ok=True)
        os.makedirs(notices, exist_ok=True)

        code1, out1 = run_hook_env("auto-format.py", payload, env)
        code2, out2 = run_hook_env("auto-format.py", payload, env)

        if code1 == 0 and code2 == 0:
            PASS += 1
            print("  PASS: a missing formatter never blocks the edit (exit 0 both times)")
        else:
            FAIL += 1
            print(f"  FAIL: a missing formatter changed the exit code ({code1}, {code2})")

        if "rubocop" in out1 and "not on PATH" in out1:
            PASS += 1
            print("  PASS: first edit names the missing binary (not silent)")
        else:
            FAIL += 1
            print(f"  FAIL: first edit said nothing about the missing formatter: {out1!r}")

        if "gem install rubocop" in out1:
            PASS += 1
            print("  PASS: the notice names a remedy, not just a gap")
        else:
            FAIL += 1
            print(f"  FAIL: the notice does not say how to fix it: {out1!r}")

        if out2 == "":
            PASS += 1
            print("  PASS: the second edit is silent (said ONCE, not on every write)")
        else:
            FAIL += 1
            print(f"  FAIL: the notice repeats on every write — that is noise: {out2!r}")

        # A different session must hear it again — the notice is per-session, not forever.
        code3, out3 = run_hook_env("auto-format.py", dict(payload, session_id="sess-xyz"), env)
        if "rubocop" in out3:
            PASS += 1
            print("  PASS: a new session hears the notice again (per-session, not once ever)")
        else:
            FAIL += 1
            print(f"  FAIL: a new session never learns the formatter is missing: {out3!r}")


def test_contrast_table_matches_the_tokens():
    """The design-token contrast table was headed "Verified" and 9 of its 10 ratios were wrong —
    three claiming "Passes AA" while measuring below 4.5:1 (`--success` was 3.00:1, `--error`
    3.61:1). The errors ran in BOTH directions (`--warning` 6.79 vs a claimed 5.8), which rules
    out a systematic miscalculation: the numbers had never been computed at all.

    These are the DEFAULT tokens, copied verbatim into theme-presets. A team trusting the word
    "Verified" shipped body text that this plugin's own accessibility-auditor fails.

    Prose cannot be imported, so the table is recomputed here from the file's own `:root`/`.dark`
    blocks. The formula is validated against two published values before it is trusted."""
    print("\n[the contrast table must match the tokens it documents]")
    global PASS, FAIL
    import colorsys
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    p = os.path.join(repo, "skills", "theming", "references", "design-tokens.md")
    if not os.path.isfile(p):
        FAIL += 1
        print("  FAIL: design-tokens.md is missing")
        return
    lines = open(p, encoding="utf-8").read().split("\n")

    def to_rgb(v):
        m = re.match(r"([\d.]+)\s+([\d.]+)%\s+([\d.]+)%$", v.strip())
        if not m:
            return None
        r, g, b = colorsys.hls_to_rgb(float(m.group(1)) / 360, float(m.group(3)) / 100,
                                      float(m.group(2)) / 100)
        return (round(r * 255), round(g * 255), round(b * 255))

    def lum(c):
        def f(x):
            x /= 255
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
        r, g, b = (f(v) for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def ratio(a, b):
        la, lb = lum(a), lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    # Validate the formula itself before trusting a single cell.
    if abs(ratio((255, 255, 255), (0, 0, 0)) - 21.0) < 0.01 and \
       abs(ratio((0x76, 0x76, 0x76), (255, 255, 255)) - 4.54) < 0.02:
        PASS += 1
        print("  PASS: contrast formula validated (white/black=21.00, #767676/white=4.54)")
    else:
        FAIL += 1
        print("  FAIL: the contrast formula itself is wrong — every cell below is untrustworthy")
        return

    def block(start):
        out = {}
        for l in lines[start:]:
            if l.strip() == "}":
                break
            m = re.match(r"\s*(--[\w-]+)\s*:\s*([^;]+);", l)
            if m:
                out[m.group(1)] = m.group(2).strip()
        return out

    try:
        li = next(i for i, l in enumerate(lines) if l.strip() == ":root {" and i > 110)
        di = next(i for i, l in enumerate(lines) if l.strip() == ".dark {" and i > 160)
    except StopIteration:
        FAIL += 1
        print("  FAIL: could not locate the :root/.dark token blocks — did the file restructure?")
        return
    light, dark = block(li), block(di)

    rows = re.findall(r"^\| `(--[\w-]+)` \| `(--[\w-]+)` \| ([\d.]+):1 \| ([\d.]+):1 \|",
                      "\n".join(lines), re.M)
    if not rows:
        FAIL += 1
        print("  FAIL: no contrast rows parsed — the table shape changed")
        return

    drift = below = 0
    for bg, fg, claim_l, claim_d in rows:
        if bg not in light or fg not in light:
            continue
        al = ratio(to_rgb(light[bg]), to_rgb(light[fg]))
        ad = ratio(to_rgb(dark.get(bg, light[bg])), to_rgb(dark.get(fg, light[fg])))
        if abs(al - float(claim_l)) > 0.05 or abs(ad - float(claim_d)) > 0.05:
            drift += 1
            print(f"  FAIL: {bg} claims {claim_l}/{claim_d}, measures {al:.2f}/{ad:.2f}")
        if min(al, ad) < 4.5:
            below += 1
            print(f"  FAIL: {bg} measures {min(al, ad):.2f}:1 — below AA, and it is a DEFAULT token")
    if drift:
        FAIL += 1
    else:
        PASS += 1
        print(f"  PASS: all {len(rows)} documented ratios match the tokens ({'±0.05'})")
    if below:
        FAIL += 1
    else:
        PASS += 1
        print(f"  PASS: every default token pair clears 4.5:1 in both light and dark")

    # ------------------------------------------------------------------
    # The presets, which are the whole point of the file next door.
    #
    # This check exists because the fix above did not propagate. `design-tokens.md` was
    # corrected (--success 36.3% -> 28%, --error 60.2% -> 47%, ...) and gated — but this test
    # only ever read design-tokens.md, and `theme-presets.md` carried the SAME defaults, copied.
    # Three presets x light+dark = 6 blocks, and 13 pairs were still below AA: --success at
    # 2.54:1 in Modern, --info at 2.99:1 in Corporate dark.
    #
    # A preset is worse than a spec: theme-presets.md says "Copy the relevant :root and .dark
    # blocks into your project's token stylesheet." It is written to be taken wholesale. So a
    # team picks Modern, ships it, and this plugin's own accessibility-auditor fails the result.
    #
    # The lesson is about the GATE, not the tokens: a check scoped to one file proves nothing
    # about the copy next to it. Scope to the invariant ("no shipped token pair is below AA"),
    # not to the file you happened to be fixing.
    presets = os.path.join(repo, "skills", "theming", "references", "theme-presets.md")
    if os.path.isfile(presets):
        ptext = open(presets, encoding="utf-8").read().split("\n")
        pblocks, cur = [], None
        for line in ptext:
            if re.match(r"^\s*(:root|\.dark)\s*\{", line):
                cur = {}
                pblocks.append(cur)
                continue
            if cur is not None:
                if line.strip() == "}":
                    cur = None
                    continue
                mm = re.match(r"\s*(--[\w-]+)\s*:\s*([^;]+);", line)
                if mm:
                    cur[mm.group(1)] = mm.group(2).strip()

        pairs = [("--success", "--success-foreground"), ("--error", "--error-foreground"),
                 ("--warning", "--warning-foreground"), ("--info", "--info-foreground"),
                 ("--primary", "--primary-foreground"), ("--muted-foreground", "--muted")]
        preset_fails, checked_pairs = [], 0
        for blk in pblocks:
            for bg_k, fg_k in pairs:
                if bg_k not in blk or fg_k not in blk:
                    continue
                a, b = to_rgb(blk[bg_k]), to_rgb(blk[fg_k])
                if not a or not b:
                    continue
                checked_pairs += 1
                r = ratio(a, b)
                if r < 4.5:
                    preset_fails.append(f"{bg_k}/{fg_k} = {r:.2f}:1")

        if not pblocks or not checked_pairs:
            FAIL += 1
            print("  FAIL: parsed no token pairs out of theme-presets.md — this check's parser "
                  "broke, not the presets. Fix it before trusting a PASS.")
        elif preset_fails:
            FAIL += 1
            print(f"  FAIL: theme-presets.md ships {len(preset_fails)} pair(s) below AA — and a "
                  f"preset is written to be copied wholesale: {'; '.join(preset_fails[:6])}")
        else:
            PASS += 1
            print(f"  PASS: all {checked_pairs} preset pairs across {len(pblocks)} theme blocks "
                  f"clear 4.5:1")

        # Corporate is not "a preset" — it is design-tokens.md's palette under another name (same
        # hue and saturation on every shared token). So the two must carry the SAME numbers, or
        # they are one token with two values, which is how this drifted in the first place.
        # Modern and Minimal are genuinely different palettes and are not compared.
        if pblocks:
            corp_light = pblocks[0]
            drift = []
            for k in ("--success", "--error", "--muted-foreground", "--warning", "--info",
                      "--primary"):
                if k in corp_light and k in light and corp_light[k] != light[k]:
                    drift.append(f"{k}: preset={corp_light[k]!r} vs spec={light[k]!r}")
            if drift:
                FAIL += 1
                print(f"  FAIL: the Corporate preset shares design-tokens.md's palette but states "
                      f"different values — one token, two numbers: {'; '.join(drift)}")
            else:
                PASS += 1
                print(f"  PASS: the Corporate preset matches design-tokens.md's canonical palette")


def test_every_token_utility_is_registered():
    """A Tailwind utility naming an unregistered token compiles to NOTHING — no error, no
    warning, no CSS. `bg-destructive` on a Delete button renders transparent with inherited
    text. It reads like a token, reviews like a token, and silently is not one.

    Four registries (Tailwind v4 @theme, Tailwind v3 colors, RN light, RN dark) unanimously
    define `error` and `muted`; none define `destructive` or `neutral`. Yet the docs taught
    `bg-destructive` in 4 files and `bg-neutral text-neutral-foreground` in the rule literally
    titled "Atoms Must Use Design Tokens". design-token-checker.py has no allowlist, so it read
    them as well-formed token classes and passed.

    This is the "data needs a test" case: the registry is DATA, and prose cannot be imported.

    Scope is deliberately tight — class strings inside fenced code only. A first pass over raw
    prose reported `to-many` (from "many-to-many") and `gray` (from `bg-gray-100`): a gate that
    flags correct code is a gate people learn to ignore."""
    print("\n[every token utility in the docs must resolve to a registered token]")
    global PASS, FAIL
    import glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    cfg_path = os.path.join(repo, "skills", "theming", "references", "platform-integration.md")
    if not os.path.isfile(cfg_path):
        FAIL += 1
        print("  FAIL: platform-integration.md (the token registry) is missing")
        return
    cfg = open(cfg_path, encoding="utf-8").read()

    registered = set(re.findall(r"--color-([a-z-]+):", cfg))          # Tailwind v4 @theme
    registered |= set(re.findall(r"^\s{8}([a-z-]+):\s*\{", cfg, re.M))  # Tailwind v3 colors
    if "error" not in registered or "muted" not in registered:
        FAIL += 1
        print("  FAIL: registry parse found neither `error` nor `muted` — the parser broke, "
              "not the docs. Fix this test before trusting it.")
        return
    registered |= {r + "-foreground" for r in list(registered)}

    # Tailwind ships these; they are valid without being OUR tokens.
    BUILTIN = {"gray", "slate", "zinc", "neutral", "stone", "red", "orange", "amber", "yellow",
               "lime", "green", "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet",
               "purple", "fuchsia", "pink", "rose", "white", "black", "transparent", "current",
               "inherit"}
    # Share a prefix with colour utilities but take no colour (text-sm, border-solid, bg-cover).
    NON_COLOR = {"xs", "sm", "base", "lg", "xl", "left", "center", "right", "justify", "start",
                 "end", "wrap", "nowrap", "balance", "pretty", "ellipsis", "clip", "solid",
                 "dashed", "dotted", "double", "hidden", "none", "collapse", "separate", "x",
                 "y", "t", "r", "b", "l", "s", "e", "fixed", "local", "scroll", "cover",
                 "contain", "auto", "repeat", "top", "bottom", "inset", "offset"}

    class_ctx = re.compile(
        r"""class(?:Name)?\s*[:=]\s*["'{]([^"'}]*)"""
        r"""|["']([a-z0-9 :/\[\]().-]*-(?:foreground|\d+)[a-z0-9 :/\[\]().-]*)["']""")
    util = re.compile(r"\b(?:bg|text|border|ring)-([a-z]+(?:-foreground)?)(?![-\w])(?:/\d+)?")

    hits = {}
    for p in (glob.glob(os.path.join(repo, "skills", "**", "*.md"), recursive=True)
              + glob.glob(os.path.join(repo, "agents", "*.md"))):
        src = open(p, encoding="utf-8").read()
        # A tutorial that DEFINES a token may then use it: defining-tokens.md registers
        # `--brand` and demos `bg-brand`, which is the file working as intended.
        local = set(re.findall(r"--([a-z-]+):\s*[\d.]", src))
        local |= {t + "-foreground" for t in local}
        for fence in re.findall(r"```[a-z]*\n(.*?)```", src, re.S):
            for cm in class_ctx.finditer(fence):
                for name in util.findall(cm.group(1) or cm.group(2) or ""):
                    if (name in registered or name in BUILTIN or name in NON_COLOR
                            or name in local):
                        continue
                    hits.setdefault(name, set()).add(os.path.relpath(p, repo))

    if hits:
        FAIL += 1
        for name, files in sorted(hits.items()):
            print(f"  FAIL: `{name}` is used as a token but is registered in no registry — "
                  f"compiles to no CSS. Use a registered token, or register it in "
                  f"skills/theming/references/platform-integration.md. "
                  f"Files: {', '.join(sorted(files))}")
    else:
        PASS += 1
        print(f"  PASS: every token utility resolves against the {len(registered) // 2} "
              f"registered tokens")


def test_file_scoped_hooks_name_a_loadable_skill():
    """A hook that fires on a FILE and says "per the `std-x` skill" is naming a remedy (Ch. 25).
    If `std-x` has no `paths:`, it never auto-loads on that file — the pointer names a document
    the reader has no mechanism to receive.

    `error-handling-checker.py` names `std-error-handling` five times. That skill shipped with no
    `paths:`, so it auto-loaded on nothing, ever.

    Bash-scoped hooks are exempt and that is not a loophole: `pre-commit-check.py` fires on
    `git commit`, where there is no file path to key on. `std-git-workflow` is enforced BY that
    hook — Ch. 7's placement test says a rule that must hold whether or not it is read is a hook,
    not context — and the hook names it as the remedy when it denies. Giving it a `paths:` would
    be inventing a trigger to satisfy a checker."""
    print("\n[a file-scoped hook must name a skill that can actually load]")
    global PASS, FAIL
    import json
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    cfg = json.load(open(os.path.join(HOOKS_DIR, "hooks.json"), encoding="utf-8"))["hooks"]

    file_scoped = set()
    for entries in cfg.values():
        for e in entries:
            if not re.search(r"Edit|Write", e.get("matcher", "")):
                continue
            for h in e.get("hooks", []):
                file_scoped.update(re.findall(r"([\w-]+\.py)", h.get("command", "") or ""))
    # Advisory checkers register through the dispatcher, not directly.
    disp = os.path.join(HOOKS_DIR, "post-edit-dispatch.py")
    if os.path.isfile(disp):
        body = open(disp, encoding="utf-8").read()
        m = re.search(r"CHECKERS\s*=\s*\[(.*?)\]", body, re.S)
        if m:
            file_scoped.update(re.findall(r"[\"']([\w-]+\.py)[\"']", m.group(1)))
    if "error-handling-checker.py" not in file_scoped:
        FAIL += 1
        print("  FAIL: the dispatcher/hooks.json parse found no error-handling-checker.py — "
              "this test's parser broke, not the hooks. Fix it before trusting a PASS.")
        return

    def has_paths(skill):
        p = os.path.join(repo, "skills", skill, "SKILL.md")
        if not os.path.isfile(p):
            return None
        src = open(p, encoding="utf-8").read()
        fm = src.split("---")[1] if src.startswith("---") else ""
        return bool(re.search(r"^paths:", fm, re.M))

    broken = []
    checked = 0
    for hook in sorted(file_scoped):
        hp = os.path.join(HOOKS_DIR, hook)
        if not os.path.isfile(hp):
            continue
        for skill in sorted(set(re.findall(r"`(std-[\w-]+)`", open(hp, encoding="utf-8").read()))):
            checked += 1
            ok = has_paths(skill)
            if ok is None:
                broken.append(f"{hook} names `{skill}`, which does not exist")
            elif not ok:
                broken.append(
                    f"{hook} fires on files and names `{skill}`, but that skill has no `paths:` "
                    f"— it never auto-loads, so the pointer is unreachable. Add `paths:` to "
                    f"skills/{skill}/SKILL.md covering the files this hook checks.")

    if broken:
        FAIL += 1
        for b in broken:
            print(f"  FAIL: {b}")
    else:
        PASS += 1
        print(f"  PASS: all {checked} skill pointers from file-scoped hooks resolve to a "
              f"loadable skill")


def test_agent_reference_pointers_resolve():
    """CI's skills-lint validates the references a SKILL body indexes. It globs `skills/*/SKILL.md`
    — `agents/*.md` is never checked. So an agent could point at
    `@skills/std-database/references/DOES-NOT-EXIST.md` and the whole suite stayed green;
    measured by injecting exactly that.

    The sibling test next door catches the dead `@rules/` layout, which is a different thing: it
    proves an agent does not point into the pre-plugin world, not that what it points at today
    exists. This matters more as agents get wired to references: an agent that reads a pointer to
    nothing does not fail — it silently reviews without the material and reports as if it had,
    which is exactly how `phlex-developer.md`'s step 9 no-opped.

    Both spellings are accepted, matching what CI's skills-lint already accepts on the skill side:
    `@skills/x/references/y.md` and the bare `x/references/y.md`. Scoping this to the `@`-form
    alone would have missed the two bare pointers in security-auditor — measured, not assumed.

    A file path is not a judgement call, so this has no false-positive surface.

    Extended to reference files themselves. CI's skills-lint validates the pointers a skill BODY
    indexes; nothing validated the pointers one reference makes to another. 21 such cross-links
    exist and all resolve today — this is the gate that keeps it that way, since a reference is
    exactly where a stale pointer hides longest (nothing loads it until someone needs it, and by
    then they are mid-task)."""
    print("\n[every reference pointer in an agent or reference must resolve]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    agent_files = sorted(_glob.glob(os.path.join(repo, "agents", "*.md"))
                         + _glob.glob(os.path.join(repo, "skills", "*", "references", "*.md")))
    if not agent_files:
        FAIL += 1
        print("  FAIL: no agents found — this test's glob broke, not the agents.")
        return

    pointer = re.compile(
        r"@?(?:skills/)?((?:\.\./)?[a-z0-9-]+/references/[a-z0-9-]+\.md)")
    # `monorepo-architect` points at the whole directory ("Read `skills/x/references/` for the
    # depth behind each area") rather than naming files. That is a legitimate, weaker form — and
    # it dangles just as silently if the directory is ever renamed.
    dir_pointer = re.compile(r"@?(?:skills/)?([a-z0-9-]+/references)/(?![a-z0-9-]+\.md)")

    broken, checked = [], 0
    for p in agent_files:
        rel = os.path.relpath(p, repo).replace(chr(92), "/")
        text = open(p, encoding="utf-8").read()
        for m in pointer.finditer(text):
            checked += 1
            target = m.group(1).lstrip("./")
            if not os.path.isfile(os.path.join(repo, "skills", target)):
                broken.append(
                    f"{rel} points at `{m.group(0)}`, which does not exist. An agent that "
                    f"reads a pointer to nothing does not fail — it proceeds without the "
                    f"material and reports as if it had it. Fix the path or drop the pointer.")
        for m in dir_pointer.finditer(text):
            checked += 1
            if not os.path.isdir(os.path.join(repo, "skills", m.group(1))):
                broken.append(
                    f"{rel} points at the directory `{m.group(0)}`, which does not "
                    f"exist. Name the reference files, or fix the path.")

    if broken:
        FAIL += 1
        for b in broken:
            print(f"  FAIL: {b}")
    else:
        PASS += 1
        print(f"  PASS: all {checked} reference pointer(s) resolve "
              f"({len(agent_files)} agents + reference files checked)")


def test_rails_routes_checker():
    """`mount Sidekiq::Web => '/sidekiq'` with nothing wrapping it exposes every job's arguments
    — which on this stack routinely carry user ids, emails and tokens — and lets any visitor
    retry or kill jobs. Two lines, no error message, and this repo commits to Sidekiq.

    Ch. 7's placement test makes this a hook rather than a line in the security-auditor agent:
    it must hold whether or not anybody runs an audit.

    The `init` case is the whole reason this check reads from disk. The idiomatic protection for
    an API-only Rails app is `Sidekiq::Web.use Rack::Auth::Basic` in
    `config/initializers/sidekiq.rb` — NOT in routes.rb, because Devise's `authenticate` route
    helper needs Warden session middleware that API-only does not load. A routes.rb-only check
    would flag a correctly-secured app, and a gate that flags correct code is a gate people learn
    to ignore."""
    print("\n[rails-routes-checker.py]")
    import os as _os
    import tempfile

    assert_silent("skips non-routes ruby", "rails-routes-checker.py", "Edit",
                  {"file_path": "backend/app/models/user.rb"})
    assert_silent("skips empty input", "rails-routes-checker.py", "Edit", {"file_path": ""})

    tmp = tempfile.mkdtemp()

    def routes(case, body, initializer=None):
        d = _os.path.join(tmp, case, "config")
        _os.makedirs(_os.path.join(d, "initializers"), exist_ok=True)
        p = _os.path.join(d, "routes.rb")
        with open(p, "w") as f:
            f.write(body)
        if initializer:
            with open(_os.path.join(d, "initializers", "sidekiq.rb"), "w") as f:
                f.write(initializer)
        return p

    bare = routes("bare", "Rails.application.routes.draw do\n"
                          "  mount Sidekiq::Web => '/sidekiq'\n"
                          "  resources :users\nend\n")
    assert_output_contains("warns on unauthenticated Sidekiq::Web", "rails-routes-checker.py",
                           "Edit", {"file_path": bare}, "no authentication")

    guarded = routes("guarded", "Rails.application.routes.draw do\n"
                                "  authenticate :user, ->(u) { u.admin? } do\n"
                                "    mount Sidekiq::Web => '/sidekiq'\n"
                                "  end\nend\n")
    assert_silent("silent when wrapped in an authenticate block", "rails-routes-checker.py",
                  "Edit", {"file_path": guarded})

    # The API-only idiom: protection lives in the initializer, not routes.rb.
    init = routes("init", "Rails.application.routes.draw do\n"
                          "  mount Sidekiq::Web => '/sidekiq'\nend\n",
                  initializer="require 'sidekiq/web'\n"
                              "Sidekiq::Web.use Rack::Auth::Basic do |u, p|\n"
                              "  ActiveSupport::SecurityUtils.secure_compare(u, ENV['SK_USER'])\n"
                              "end\n")
    assert_silent("silent when the initializer protects the Rack app", "rails-routes-checker.py",
                  "Edit", {"file_path": init})

    # A routes.rb with no Sidekiq mount at all must never fire.
    plain = routes("plain", "Rails.application.routes.draw do\n  resources :orders\nend\n")
    assert_silent("silent on routes with no Sidekiq mount", "rails-routes-checker.py", "Edit",
                  {"file_path": plain})


def test_skill_phase_counts_match_their_agent():
    """`requirements-consultant/SKILL.md` said "The agent follows a structured **six-phase**
    protocol" and documented Phases 1-6. The agent has Phase 0 through Phase 6 — **seven**.

    The omitted phase was exactly the broken one: Phase 0 told an agent holding
    `Read, Grep, Glob` to "Name 3+ competitors and their approach" and "Evaluate cost,
    reliability, and vendor lock-in" for third-party services. With no web access it could only
    recall training data — stale by construction, confident in tone, and landing directly in
    build/buy and scope decisions where nobody can cheaply check it. Phase 0 was bolted on later
    and the skill was never updated, which is why the count drifted and why the drift pointed
    straight at the defect.

    The number is DATA, and prose cannot be imported — so it is counted here rather than
    restated. This is the same class as the hook limits and the token registry."""
    print("\n[a skill's claimed phase count must match its agent]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10}

    problems = []
    checked = 0
    for skill_md in sorted(_glob.glob(os.path.join(repo, "skills", "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(skill_md))
        agent_md = os.path.join(repo, "agents", name + ".md")
        if not os.path.isfile(agent_md):
            continue
        src = open(skill_md, encoding="utf-8").read()
        m = re.search(r"\b(" + "|".join(WORDS) + r")-phase\b", src, re.I)
        if not m:
            continue
        checked += 1
        claimed = WORDS[m.group(1).lower()]
        actual = len(set(re.findall(r"^#+\s*Phase\s+(\d+)", open(agent_md, encoding="utf-8").read(),
                                    re.M | re.I)))
        if actual and claimed != actual:
            problems.append(
                f"skills/{name}/SKILL.md claims a {m.group(1).lower()}-phase protocol; "
                f"agents/{name}.md defines {actual} phases. A phase the skill does not document "
                f"is a phase nobody reviews — update the count and describe the missing phase.")

    if problems:
        FAIL += 1
        for p in problems:
            print(f"  FAIL: {p}")
    else:
        PASS += 1
        print(f"  PASS: {checked} skill(s) claiming a phase count match their agent")


def test_agents_do_not_glob_hardcoded_wrapper_dirs():
    """`design-system-architect` and `design-critique` globbed `web/src/components/**/*.tsx`,
    `next/src/components/**`, `mobile/src/components/**` and `backend/app/components/**`.

    The plugin's central monorepo claim is that it is WRAPPER-DIRECTORY AGNOSTIC — package dirs
    can be named anything, and detection keys on canonical structure plus marker files. So in any
    repo that does not happen to use those four names — `apps/web-client`, `frontend`, a flat
    layout — those globs matched nothing, and an auditing agent that finds nothing reports
    CLEAN. A fabricated clean bill is worse than an error: nobody investigates it.

    Both files were internally inconsistent, which is what proves drift rather than design:
    design-system-architect already globbed `**/globals.css` and `**/styles/**` correctly two
    lines above the hardcoded ones.

    Scope is narrow on purpose. A blanket ban on `backend/app/` across the repo would flag ~300
    occurrences in 46 files, nearly all of them legitimate — an EXAMPLE needs a concrete path,
    and `e.g. backend/app/models/user.rb` reads better than a glob. The defect is only a
    hardcoded wrapper inside an instruction the agent EXECUTES. Gating the prose too would be
    the exact failure this suite keeps catching elsewhere: a gate that flags correct code is a
    gate people learn to ignore.

    TWO REFINEMENTS, both learned by missing something:

    1. The verb list was `Glob|Read|Grep`, and `phlex-developer` step 3 said "**Search**
       `backend/app/components/` for reusable atoms/molecules". Same defect, different verb, and
       the gate sailed past it — so the agent would search a path that does not exist in a
       differently-named repo, find nothing, and build a duplicate of a component it already
       had. An instruction to go look somewhere is the defect however it is phrased.
    2. Fenced blocks are stripped first. `phlex-developer` draws its Atomic Design directory
       tree as a `backend/app/components/` diagram — that is an illustration of SHAPE, and
       flagging it would be flagging correct documentation."""
    print("\n[agents must not Glob hardcoded wrapper directories]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    instr = re.compile(
        r"(?:^|\b)(?:Glob|Read|Grep|Search|Scan|Look in|Inspect)\b[^.\n]{0,80}?[`\"']?"
        r"(?<![\w./*-])(web|next|mobile|backend|frontend)/(?:src|app)/", re.I | re.M)

    agent_files = sorted(_glob.glob(os.path.join(repo, "agents", "*.md")))
    if not agent_files:
        FAIL += 1
        print("  FAIL: no agents found — this test's glob broke, not the agents.")
        return

    problems = []
    for p in agent_files:
        name = os.path.basename(p)
        prose = re.sub(r"```.*?```", "", open(p, encoding="utf-8").read(), flags=re.S)
        for m in instr.finditer(prose):
            problems.append(
                f"agents/{name}: \"{m.group(0).strip()[:52]}\" hardcodes the wrapper directory "
                f"`{m.group(1)}/`. This plugin is wrapper-directory agnostic — in a repo that "
                f"names it anything else this finds nothing and the agent reports clean. Glob "
                f"the marker file (`**/next.config.*`, `**/vite.config.*`, `**/metro.config.js`, "
                f"`**/Gemfile`) and search from its directory instead.")

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        print(f"  PASS: no agent globs a hardcoded wrapper dir ({len(agent_files)} checked)")


def test_agents_can_run_what_they_are_told_to_run():
    """`refactor-specialist` shipped with `Read, Grep, Glob, Write, Edit` — no Bash — while its
    protocol said "Run the test suite to confirm it passes", "Execute the relevant test suite
    after every change", "NEVER refactor without tests... the single most important rule", and
    required it to report "Test results (pass/fail count)".

    It could not run a single one of them. And it held Write and Edit, so it was the worst
    combination available: full power to mutate the code, zero power to verify, and a protocol
    demanding a pass/fail count. The only way to comply was to invent one — and the entire safety
    argument for that agent is that the tests were green before and after.

    It was also the ONLY agent in the plugin that could write but not verify. devops-engineer,
    phlex-developer and test-generator all pair Write/Edit with Bash; the read-only agents
    correctly have neither. An outlier, not a design decision.

    Ch. 8's removed-capability trap: taking a tool away does not remove the instruction that
    needs it — it just makes the instruction unsatisfiable, and the model still has to answer.
    Ch. 25: an instruction with no achievable path is a denial with no remedy."""
    print("\n[an agent told to run something must be able to run it]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    # Deliberately narrow: an imperative to EXECUTE a suite, not prose that mentions testing.
    # Measured across all 13 agents, this fires on exactly refactor-specialist and
    # test-generator — the two that really do demand a run — and nothing else.
    demand = re.compile(
        r"^\s*[-*\d.]*\s*(?:\*\*)?(?:Run|Execute)\b[^.\n]{0,60}"
        r"(?:test suite|tests|specs|rspec|vitest|jest|the suite|benchmark|linter)",
        re.I | re.M)

    agent_files = sorted(_glob.glob(os.path.join(repo, "agents", "*.md")))
    if not agent_files:
        FAIL += 1
        print("  FAIL: no agents found — this test's glob broke, not the agents.")
        return

    problems = []
    demanding = 0
    for p in agent_files:
        name = os.path.basename(p)[:-3]
        src = open(p, encoding="utf-8").read()
        fm = src.split("---")[1] if src.startswith("---") else ""
        m = re.search(r"^tools:\s*(.+)$", fm, re.M)
        tools = [t.strip() for t in m.group(1).split(",")] if m else []
        hits = demand.findall(src)
        if not hits:
            continue
        demanding += 1
        if "Bash" not in tools:
            problems.append(
                f"agents/{name}.md tells itself to run a suite ({len(hits)} place(s), e.g. "
                f"\"{hits[0].strip()[:48]}\") but its `tools:` has no Bash. It cannot comply, so "
                f"it can only claim compliance. Add Bash, or rewrite the protocol as advice for "
                f"the human to run.")
        # Writing without verifying is the specific trap that made this expensive.
        if {"Write", "Edit"} & set(tools) and "Bash" not in tools:
            problems.append(
                f"agents/{name}.md holds Write/Edit but no Bash: it can change code and cannot "
                f"test it.")

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        print(f"  PASS: all {demanding} agent(s) that demand a test run can actually run one "
              f"({len(agent_files)} agents checked)")


def test_the_palette_recipe_produces_passing_colors():
    """`brand-identity` GENERATES the palettes this repo then ships, and its recipe
    (`references/color-theory.md`) prescribed semantic-colour lightness *ranges* with **no
    foreground named** — then instructed, one step later, "create foreground pairs meeting WCAG
    4.5:1".

    Measured against the usual near-white `*-foreground`, the **entire** prescribed Success range
    (36-45%) and the **entire** Info range (46-54%) fail — best case 3.40:1 and 3.12:1. Steps 1-5
    made step 6 unsatisfiable. That is not a hypothetical: all three presets in
    `theme-presets.md` were built from this recipe and 13 of their pairs measured below AA.
    **The recipe was the bug and the palettes inherited it.**

    So the caps are gated against the arithmetic they claim, rather than trusted as prose. A
    generator that emits failing colours is upstream of every contrast finding in this repo —
    fixing the presets without fixing this would just regenerate them.

    Warning is deliberately excluded: amber takes a DARK foreground (there is no lightness in the
    usable amber range that clears 4.5:1 against white), so a white-foreground cap is meaningless
    for it — which is exactly why the table names its foreground instead of quoting a bare range."""
    print("\n[the palette recipe must produce colours that pass]")
    global PASS, FAIL
    import colorsys
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    p = os.path.join(repo, "skills", "brand-identity", "references", "color-theory.md")
    if not os.path.isfile(p):
        FAIL += 1
        print("  FAIL: color-theory.md is missing — the palette recipe is gone.")
        return

    rows = re.findall(
        r"\|\s*(Success|Error|Info)\s*\|\s*HSL\((\d+),\s*(\d+)-(\d+)%\)\s*\|\s*\*\*≤\s*(\d+)%\*\*",
        open(p, encoding="utf-8").read())
    if len(rows) != 3:
        FAIL += 1
        print(f"  FAIL: parsed {len(rows)} capped semantic rows out of color-theory.md, expected 3 "
              f"— this test's parser broke, or the table lost its foreground-aware caps. Fix "
              f"before trusting a PASS.")
        return

    def rgb(h, s, l):
        r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
        return (r * 255, g * 255, b * 255)

    def lum(c):
        def f(x):
            x /= 255
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
        r, g, b = (f(v) for v in c)
        return .2126 * r + .7152 * g + .0722 * b

    def ratio(a, b):
        la, lb = lum(a), lum(b)
        return (max(la, lb) + .05) / (min(la, lb) + .05)

    white = rgb(0, 0, 98)          # the near-white foreground the table names
    if abs(ratio(rgb(0, 0, 0), rgb(0, 0, 100)) - 21.0) > 0.01:
        FAIL += 1
        print("  FAIL: contrast formula self-check failed (black/white != 21) — fix the test.")
        return

    problems = []
    for name, h, s_lo, s_hi, cap in rows:
        h, s_lo, s_hi, cap = int(h), int(s_lo), int(s_hi), int(cap)
        # At the stated cap, every saturation in range must still clear AA.
        for s in (s_lo, s_hi):
            r = ratio(rgb(h, s, cap), white)
            if r < 4.5:
                problems.append(
                    f"{name}: the table caps lightness at {cap}%, but HSL({h}, {s}%, {cap}%) "
                    f"measures {r:.2f}:1 against a near-white foreground — the cap it prescribes "
                    f"does not itself pass. Lower the cap.")
        # And one step above the cap must fail, or the cap is loose enough to be misleading.
        if all(ratio(rgb(h, s, cap + 4), white) >= 4.5 for s in (s_lo, s_hi)):
            problems.append(
                f"{name}: {cap + 4}% also passes, so the cap of {cap}% is needlessly tight — "
                f"it will push palettes darker than AA requires.")

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        print(f"  PASS: all {len(rows)} capped semantic ranges produce AA-passing colours at their "
              f"stated cap")


def test_required_tags_match_the_skills_that_document_them():
    """Same invariant as `test_limits_match_the_skill_that_documents_them`, for the other piece of
    hook-enforced **data** in this repo: `terraform-checker.py`'s
    `REQUIRED_TAGS = ["project", "environment", "team", "managed-by"]`.

    Three sources state that list — the hook, `std-terraform-conventions` (which auto-loads on
    `**/*.tf`), and `terraform/rules/resource-required-tags.md`. They agree today. Ungated, they
    would not stay that way: add a fifth required tag to the hook alone and a developer reads the
    skill, writes the four it documents, gets warned anyway, and concludes the hook is noise.
    That is not hypothetical — it is exactly what happened with `code-quality-checker`'s 200-line
    limit, which is why the sibling test exists.

    A tag list is data, and prose cannot be imported. Imported from the hook rather than restated
    here, so the test cannot drift from the thing it is gating."""
    print("\n[enforced required tags must match the skills that document them]")
    global PASS, FAIL
    import importlib.util

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    spec = importlib.util.spec_from_file_location(
        "tfc", os.path.join(HOOKS_DIR, "terraform-checker.py"))
    tfc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tfc)

    tags = list(getattr(tfc, "REQUIRED_TAGS", []))
    if not tags:
        FAIL += 1
        print("  FAIL: terraform-checker.py exposes no REQUIRED_TAGS — this test's anchor is "
              "gone. Fix the test before trusting a PASS.")
        return

    documented = {
        "std-terraform-conventions": os.path.join(
            repo, "skills", "std-terraform-conventions", "SKILL.md"),
        "terraform/rules/resource-required-tags.md": os.path.join(
            repo, "skills", "terraform", "rules", "resource-required-tags.md"),
    }
    problems = []
    for label, path in documented.items():
        if not os.path.isfile(path):
            problems.append(f"{label} is missing — the hook names a rule nobody can read.")
            continue
        body = open(path, encoding="utf-8").read()
        missing = [t for t in tags if t not in body]
        if missing:
            problems.append(
                f"{label} never states the required tag(s) {missing}, but terraform-checker.py "
                f"warns when they are absent. The developer writes what the skill documents and "
                f"is warned anyway — that is how a gate becomes noise.")

    if problems:
        FAIL += 1
        for p in problems:
            print(f"  FAIL: {p}")
    else:
        PASS += 1
        print(f"  PASS: all {len(tags)} enforced tags ({', '.join(tags)}) are documented in both "
              f"skills that carry them")


def test_centrifugo_examples_use_this_clients_api():
    """`react-native-dev` taught a `useChatMessages` hook built on `centrifuge.subscribe(channel)`.
    That is not this client's API — subscriptions are **created** with `newSubscription()` and
    retrieved with `getSubscription()`, and `.subscribe()` is a method on the Subscription object,
    not a channel-taking method on the client. The example could not run.

    Worse, the shape it taught had the exact leak its own owner
    (`std-react-native/references/realtime-centrifugo.md`) exists to prevent. Against that
    reference the snippet was wrong four ways: wrong creation call; never started the subscription;
    cleaned up with `sub.unsubscribe()` while leaving its handler attached (*"every remount stacks
    another one and the cache update runs N times per message"*); and never called
    `removeSubscription`, so the channel stayed in the registry and the next `newSubscription`
    threw on navigation.

    Scoped to fenced code blocks, and that is load-bearing rather than incidental: the fix's own
    prose says the words `centrifuge.subscribe(channel)` in order to warn against them. A gate
    that flags the correction is the trap that killed an earlier attempt at a negation-aware
    check — markdown emphasis defeats a lookbehind. Code is where the defect lives, so code is
    all this reads."""
    print("\n[Centrifugo examples must use this client's API]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))

    def code_only(text):
        return "\n".join(re.findall(r"```[a-z]*\n(.*?)```", text, re.S))

    bad = re.compile(r"\bcentrifuge\.subscribe\s*\(", re.I)
    good = re.compile(r"getSubscription\s*\(")

    problems, seen_good = [], 0
    for p in sorted(_glob.glob(os.path.join(repo, "skills", "**", "*.md"), recursive=True)
                    + _glob.glob(os.path.join(repo, "agents", "*.md"))):
        code = code_only(open(p, encoding="utf-8").read())
        seen_good += len(good.findall(code))
        if bad.search(code):
            problems.append(
                f"{os.path.relpath(p, repo).replace(chr(92), '/')} calls "
                f"`centrifuge.subscribe(channel)` in a code example. This client creates "
                f"subscriptions with `newSubscription()` and fetches existing ones with "
                f"`getSubscription()`; `.subscribe()` belongs to the Subscription object. Use "
                f"`centrifuge.getSubscription(ch) ?? centrifuge.newSubscription(ch)` — see "
                f"skills/std-react-native/references/realtime-centrifugo.md.")

    if not seen_good:
        FAIL += 1
        print("  FAIL: no `getSubscription(` found in any code example — the canonical idiom has "
              "vanished, so this test's anchor is gone. Fix it before trusting a PASS.")
        return

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        print(f"  PASS: no code example uses the wrong Centrifuge API "
              f"({seen_good} use `getSubscription`)")


def test_the_bundle_budget_matches_the_config_that_enforces_it():
    """`std-reactjs` states the Vite SPA's initial-JS budget as **< 300KB** and enforces it as
    `build.chunkSizeWarningLimit: 300` in `vite.config.ts`. Prose and config, one number, six
    files. This is the `test_limits_match_the_skill_that_documents_them` shape: a documented
    budget that disagrees with the thing that actually warns is worse than no budget — the
    developer writes to the doc, the build complains anyway, and concludes the warning is noise.

    **Units are the real hazard here, and a test cannot catch them.** `chunkSizeWarningLimit`
    compares against the *minified, uncompressed* chunk; `performance-profiler`'s benchmark table
    quotes *gzipped* figures (`< 150KB`) — a different measure of the same bundle, convertible only
    via that bundle's real compression ratio. Those are not competing budgets and neither is stricter — but a reader handed "150KB" and "300KB" with no units
    cannot tell, and will pick whichever is convenient. All three sites now state their unit; this
    test only holds the number that is mechanically checkable."""
    print("\n[the bundle budget must match the config that enforces it]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    stated = re.compile(r"[Ii]nitial JS[^.\n|]*?<\s*(\d+)\s*KB|budget:\s*<\s*(\d+)\s*KB", re.I)
    configured = re.compile(r"chunkSizeWarningLimit:\s*(\d+)")

    budgets, limits = {}, {}
    for p in sorted(_glob.glob(os.path.join(repo, "skills", "**", "*.md"), recursive=True)):
        text = open(p, encoding="utf-8").read()
        rel = os.path.relpath(p, repo).replace("\\", "/")
        for m in stated.finditer(text):
            budgets.setdefault(int(m.group(1) or m.group(2)), []).append(rel)
        for m in configured.finditer(text):
            limits.setdefault(int(m.group(1)), []).append(rel)

    if not budgets or not limits:
        FAIL += 1
        print(f"  FAIL: parsed {len(budgets)} stated budget(s) and {len(limits)} config limit(s) "
              f"— this test's anchors are gone. Fix the test before trusting a PASS.")
        return

    problems = []
    if len(budgets) > 1:
        problems.append(f"the initial-JS budget is stated as {sorted(budgets)} in different "
                        f"files: {budgets}. One budget, one number.")
    if len(limits) > 1:
        problems.append(f"`chunkSizeWarningLimit` is set to {sorted(limits)} in different files: "
                        f"{limits}. The build cannot warn at two thresholds.")
    if len(budgets) == 1 and len(limits) == 1:
        b, l = next(iter(budgets)), next(iter(limits))
        if b != l:
            problems.append(
                f"the documented budget is {b}KB but `chunkSizeWarningLimit` is {l} — the doc and "
                f"the thing that actually warns disagree. A developer writes to {b} and the build "
                f"complains at {l}, which is how a warning becomes noise.")

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        n = sum(len(v) for v in budgets.values()) + sum(len(v) for v in limits.values())
        print(f"  PASS: the budget and the config agree at {next(iter(budgets))}KB across {n} site(s)")


def test_the_page_size_default_has_one_value():
    """`std-api-design` owns the pagination defaults and states them three times (its body, and
    both pagination references): **default 25, maximum 100**. `api-designer` — the skill a person
    actually opens to design an API — said **20**, in three places of its own (the step, the
    collection example, and its `api-conventions.md`).

    Three-to-one, and the odd family out was the one being read. A developer following
    `/api-designer` shipped a 20-default API while `std-api-design` auto-loaded on their
    controller saying 25. Nothing failed; the numbers just disagreed forever.

    Same class as the error envelope: a number with an owner, restated wrong. The remedy is the
    same — one owner, cite it — and the gate is the same, because prose cannot be imported.

    Scoped to lines that literally say "default page size". Every unqualified number in an API
    doc (`limit=20` in a URL example, `"pageSize": 25` in a JSON body) is not a statement of the
    default, and asserting they all match would flag correct examples."""
    print("\n[the default page size must have one value]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    owner_path = os.path.join(repo, "skills", "std-api-design", "SKILL.md")
    rx = re.compile(
        r"[Dd]efault page size[^.\n]*?\**(\d+)\**[^.\n]*?maximum\s+\**(\d+)"
        r"|[Dd]efault page size:?\s*\**(\d+)", re.I)

    def values(path):
        if not os.path.isfile(path):
            return []
        out = []
        for m in rx.finditer(open(path, encoding="utf-8").read()):
            out.append((int(m.group(1) or m.group(3)),
                        int(m.group(2)) if m.group(2) else None))
        return out

    owner = values(owner_path)
    if not owner:
        FAIL += 1
        print("  FAIL: std-api-design/SKILL.md no longer states a default page size — this "
              "test's anchor is gone. Fix the test before trusting a PASS.")
        return
    default, maximum = owner[0]

    problems, checked = [], 0
    for p in sorted(_glob.glob(os.path.join(repo, "skills", "**", "*.md"), recursive=True)):
        if os.path.abspath(p) == os.path.abspath(owner_path):
            continue
        for d, mx in values(p):
            checked += 1
            rel = os.path.relpath(p, repo).replace("\\", "/")
            if d != default:
                problems.append(f"{rel} states a default page size of {d}; `std-api-design` owns "
                                f"it at {default}. Cite the skill rather than restating it.")
            if mx is not None and maximum is not None and mx != maximum:
                problems.append(f"{rel} states a maximum page size of {mx}; `std-api-design` owns "
                                f"it at {maximum}.")

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        print(f"  PASS: all {checked} restatement(s) of the page size default match "
              f"std-api-design's {default}/{maximum}")


def test_the_pr_size_limit_has_one_value():
    """`std-git-workflow` owns the PR size target ("under 400 lines changed per PR"); `onboarding`
    restates it in the doc it generates for a new developer. Two copies of a number, no gate.

    Found while chasing a worse version of the same thing next door: `onboarding`'s body said
    reviews land "within 24 hours" while its OWN reference said "within 4 business hours" — a
    contradiction inside one skill, aimed at the one reader with no way to tell which is right.
    That number turned out to have no owner at all (neither CLAUDE.md nor `std-git-workflow` pins
    an SLA), so it became a `{review-sla}` placeholder rather than a third invented value.
    The 400 is different: it HAS an owner, so it gets a gate instead.

    Scoped to lines that mention a PR. A bare `under (\\d+) lines` also matches the 200-line FILE
    limit in `std-react-native` and `phlex-developer` — different data, already covered by
    `test_limits_match_the_skill_that_documents_them` — and asserting all of them agree would
    have failed on correct docs."""
    print("\n[the PR size limit must have one value]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    owner_path = os.path.join(repo, "skills", "std-git-workflow", "SKILL.md")
    rx = re.compile(
        r"^.*\bPRs?\b.*?under\s+\**(\d+)\s+lines.*$|^.*under\s+\**(\d+)\s+lines.*?\bper\s+PR\b.*$",
        re.I | re.M)

    def values(path):
        if not os.path.isfile(path):
            return []
        return [int(m.group(1) or m.group(2))
                for m in rx.finditer(open(path, encoding="utf-8").read())]

    owner = values(owner_path)
    if not owner:
        FAIL += 1
        print("  FAIL: std-git-workflow no longer states a PR size target — this test's anchor "
              "is gone. Fix the test before trusting a PASS.")
        return
    canonical = owner[0]

    problems, checked = [], 0
    for p in sorted(_glob.glob(os.path.join(repo, "skills", "**", "*.md"), recursive=True)
                    + _glob.glob(os.path.join(repo, "agents", "*.md"))):
        if os.path.abspath(p) == os.path.abspath(owner_path):
            continue
        for v in values(p):
            checked += 1
            if v != canonical:
                problems.append(
                    f"{os.path.relpath(p, repo)} states a PR target of {v} lines; "
                    f"`std-git-workflow` owns it at {canonical}. Restating a number is how it "
                    f"drifts — cite the skill, or match it.")

    if problems:
        FAIL += 1
        for pr in problems:
            print(f"  FAIL: {pr}")
    else:
        PASS += 1
        print(f"  PASS: all {checked} restatement(s) of the PR size target match "
              f"std-git-workflow's {canonical}")


def test_the_adr_template_has_one_section_set():
    """The ADR template exists in two places that both legitimately need it inline:
    `architecture-advisor` emits it as its **output contract** (every task it runs produces one —
    Ch. 7 puts that in the body), and `doc-generator` offers it as one document type among seven.
    CLAUDE.md pins the shape a third time.

    Unlike the error envelope, neither copy is *wrong* — the drift was cosmetic
    (`ADR-[NUMBER]` vs `ADR-NNN`, and architecture-advisor spelling out `Alternative 1/2`). So the
    fix is not to delete one: it is to hold the SECTION SET in sync, because that is the part
    people depend on. ADRs get grepped — `rg '^## Status' docs/adr/` only works if every ADR has
    the same headings, and a template that quietly grows or loses one breaks that silently.

    Compared at `##` level deliberately: the section set is the contract, `###` sub-detail is
    editorial and the two are allowed to differ there.

    The number is data, and prose cannot be imported."""
    print("\n[the ADR template must have one section set]")
    global PASS, FAIL
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))

    def adr_sections(rel, marker):
        p = os.path.join(repo, rel)
        if not os.path.isfile(p):
            return None
        src = open(p, encoding="utf-8").read()
        if marker not in src:
            return None
        block = re.search(r"```markdown\n(.*?)```", src[src.index(marker):], re.S)
        if not block:
            return None
        return [l[3:].strip() for l in block.group(1).split("\n") if re.match(r"^## [^#]", l)]

    advisor = adr_sections("agents/architecture-advisor.md",
                           "## Output Format — Architecture Decision Record")
    generator = adr_sections("skills/doc-generator/references/design-docs.md",
                             "## Architecture Decision Record (ADR)")
    if not advisor or not generator:
        FAIL += 1
        print("  FAIL: could not parse an ADR template out of architecture-advisor "
              f"({advisor}) or doc-generator's design-docs.md ({generator}) — this test's parser "
              "broke, not the docs. Fix it before trusting a PASS.")
        return

    problems = []
    if advisor != generator:
        problems.append(
            f"agents/architecture-advisor.md emits {advisor} but "
            f"skills/doc-generator/references/design-docs.md templates {generator}. Two ADR "
            f"shapes means `rg '^## Status' docs/adr/` misses whichever ADRs used the other one. "
            f"Reconcile the section set.")

    # CLAUDE.md pins the shape; both templates must at least contain what it names.
    m = re.search(r"ADR format \(ADR-NNN: ([^)]+)\)", open(os.path.join(repo, "CLAUDE.md"),
                                                           encoding="utf-8").read())
    if not m:
        problems.append("CLAUDE.md no longer states the ADR format — this test's anchor is gone.")
    else:
        named = {x.strip() for x in m.group(1).split(",")} - {"Title"}
        for label, got in (("architecture-advisor", advisor), ("doc-generator", generator)):
            missing = named - set(got)
            if missing:
                problems.append(f"{label}'s ADR template is missing {sorted(missing)}, which "
                                f"CLAUDE.md names as part of the format.")

    if problems:
        FAIL += 1
        for p in problems:
            print(f"  FAIL: {p}")
    else:
        PASS += 1
        print(f"  PASS: both ADR templates agree on {advisor}, and contain everything CLAUDE.md "
              f"names")


def test_the_error_envelope_has_one_shape():
    """The API error envelope had THREE incompatible shapes across four files, disagreeing on
    every axis a client parses:

      std-error-handling/SKILL.md   {error: str, code: 422 (int), type, details: {}, request_id}
      std-api-design/errors-*.md    {error: str, code: "STR", status: 422, details: [], requestId}
      api-designer/SKILL.md + ref   {error: {code, message, details: [], requestId}}

    Is `error` a string or an object? Is `code` the HTTP status or a machine-readable string?
    Is `details` an object or an array? `request_id` or `requestId`? A client written against one
    breaks on the others — and `std-error-handling` auto-loads on EVERY .rb/.ts file, so its copy
    was the one most likely to be read.

    The contradiction was self-aware: std-error-handling/SKILL.md said "owned elsewhere — do not
    duplicate" roughly 30 lines after duplicating it. Ownership decided it: that pointer names
    std-api-design, whose two references (Rails and TypeScript) already agreed with each other,
    and SKILL.md:54 states the casing rule outright.

    Prose cannot be imported, so the shape is re-parsed from the owner here rather than restated.
    """
    print("\n[the error envelope must have exactly one shape]")
    global PASS, FAIL
    import json as _json
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    owner = os.path.join(repo, "skills", "std-api-design", "references", "errors-rails.md")
    if not os.path.isfile(owner):
        FAIL += 1
        print("  FAIL: the owning reference errors-rails.md is missing")
        return

    def first_envelope(path):
        """The first JSON block that looks like an error envelope."""
        src = open(path, encoding="utf-8").read()
        for block in re.findall(r"```json\n(.*?)```", src, re.S):
            try:
                obj = _json.loads(block)
            except ValueError:
                continue
            if isinstance(obj, dict) and "error" in obj:
                return obj
        return None

    canonical = first_envelope(owner)
    if not canonical:
        FAIL += 1
        print("  FAIL: could not parse an envelope out of errors-rails.md — this test's parser "
              "broke, not the docs. Fix it before trusting a PASS.")
        return
    expected_keys = set(canonical) | {"details"}

    # Every file that shows the envelope must show THIS envelope.
    others = [
        os.path.join(repo, "skills", "std-api-design", "references", "errors-typescript.md"),
        os.path.join(repo, "skills", "api-designer", "SKILL.md"),
        os.path.join(repo, "skills", "api-designer", "references", "api-conventions.md"),
    ]
    problems = []
    checked = 0
    for p in others:
        if not os.path.isfile(p):
            continue
        env = first_envelope(p)
        if env is None:
            continue
        checked += 1
        rel = os.path.relpath(p, repo)
        if isinstance(env.get("error"), dict):
            problems.append(f"{rel}: `error` is a nested object; the owner makes it a string. "
                            f"Flatten it to match errors-rails.md.")
            continue
        if not isinstance(env.get("code"), str):
            problems.append(f"{rel}: `code` is {type(env.get('code')).__name__}; the owner makes "
                            f"it a machine-readable string ('VALIDATION_ERROR') with the HTTP "
                            f"status in `status`.")
        if "details" in env and not isinstance(env["details"], list):
            problems.append(f"{rel}: `details` is {type(env['details']).__name__}; the owner "
                            f"makes it an array (two errors can land on one field).")
        for snake in [k for k in env if "_" in k]:
            problems.append(f"{rel}: key `{snake}` is snake_case; JSON response keys are camelCase "
                            f"(std-api-design/SKILL.md:54).")
        extra = set(env) - expected_keys
        if extra:
            problems.append(f"{rel}: key(s) {sorted(extra)} are not in the owner's envelope "
                            f"({sorted(expected_keys)}).")

    # std-error-handling must not carry a copy at all — it auto-loads on every source file.
    seh = os.path.join(repo, "skills", "std-error-handling", "SKILL.md")
    if os.path.isfile(seh) and first_envelope(seh) is not None:
        problems.append("skills/std-error-handling/SKILL.md: carries its own copy of the "
                        "envelope. That file auto-loads on every .rb/.ts/.tsx file and says "
                        "'owned elsewhere — do not duplicate'. Point at std-api-design instead.")

    if problems:
        FAIL += 1
        for p in problems:
            print(f"  FAIL: {p}")
    else:
        PASS += 1
        print(f"  PASS: {checked} envelope(s) match the owner's shape "
              f"{sorted(expected_keys)}, and std-error-handling keeps no copy")


def test_framework_skills_load_for_their_own_framework():
    """`paths:` autoload is a pure glob. It cannot read a marker file, so it cannot tell
    `next/app/page.tsx` from `mobile/app/index.tsx` — `app/` is a directory name owned by Next's
    App Router, Expo Router, and Rails at the same time. CLAUDE.md describes detection as
    marker-based (`next.config.*`, `metro.config.js`), and that IS true of hooks
    (`_hooklib.is_react_native`), but skill autoload has no such mechanism.

    The globs land correctly on the stack this repo actually commits to, and this test pins that
    so a later path edit cannot quietly undo it. Loading the WRONG framework skill is worse than
    loading none: it is confident, on-topic, and wrong.

    Known and accepted, because they are off-stack (CLAUDE.md commits to Rails API-only,
    @react-navigation, and the App Router) — but they are real, so they are written down:
      - `app/javascript/**/*.tsx`  (Rails + jsbundling) would load std-nextjs
      - `mobile/app/(tabs)/*.tsx`  (Expo Router)        would load std-nextjs
      - `src/pages/**/*.tsx`       (Next Pages Router)  loads std-reactjs, not std-nextjs
    Adopt any of those shapes and the fix is a marker-aware hook, not a cleverer glob."""
    print("\n[each framework skill must load for its own framework's canonical paths]")
    global PASS, FAIL
    import glob as _glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))

    def matches(pat, path):
        rx = (re.escape(pat).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*")
              .replace(r"\*", "[^/]*"))
        return re.fullmatch(rx, path) is not None

    skills = {}
    for p in sorted(_glob.glob(os.path.join(repo, "skills", "std-*", "SKILL.md"))):
        n = os.path.basename(os.path.dirname(p))
        src = open(p, encoding="utf-8").read()
        fm = src.split("---")[1] if src.startswith("---") else ""
        m = re.search(r"^paths:\s*\n((?:\s+-.*\n)+)", fm, re.M)
        if m:
            skills[n] = re.findall(r'-\s*["\']?([^"\'\n]+?)["\']?\s*$', m.group(1), re.M)
    if "std-nextjs" not in skills:
        FAIL += 1
        print("  FAIL: no std-nextjs paths parsed — this test's parser broke, not the skills.")
        return

    FRAMEWORK = ("std-reactjs", "std-nextjs", "std-react-native", "std-phlex-conventions")
    # (path on the documented stack, the ONE framework skill that should claim it)
    cases = [
        ("web/src/pages/Dashboard.tsx", "std-reactjs"),      # Vite SPA — CLAUDE.md: React Router
        ("web/vite.config.ts", "std-reactjs"),
        ("next/src/app/page.tsx", "std-nextjs"),             # App Router — CLAUDE.md's Next shape
        ("next/next.config.mjs", "std-nextjs"),
        ("mobile/src/screens/Home.tsx", "std-react-native"),  # @react-navigation, not Expo Router
        ("backend/app/components/button.rb", "std-phlex-conventions"),
    ]
    bad = 0
    for path, expect in cases:
        hits = sorted(s for s, pats in skills.items()
                      if s in FRAMEWORK and any(matches(p, path) for p in pats))
        if hits != [expect]:
            bad += 1
            extra = [h for h in hits if h != expect]
            if expect not in hits:
                print(f"  FAIL: {path} loads {hits or 'NOTHING'} — `{expect}` never loads for "
                      f"its own framework. Add a pattern to skills/{expect}/SKILL.md.")
            else:
                print(f"  FAIL: {path} also loads {extra} — that is another framework's skill "
                      f"claiming this file. Narrow its `paths:`.")
    if bad:
        FAIL += 1
    else:
        PASS += 1
        print(f"  PASS: all {len(cases)} canonical stack paths load exactly one framework skill")


def test_checks_match_this_stack():
    """Two checks were written against a syntax this stack does not use, so they were dead:

      1. accessibility-checker matched `outline: none` (CSS) while only reading .tsx/.jsx —
         where the idiom is Tailwind's `outline-none`. Matcher and scope were disjoint, so it
         could never fire. Its docstring promised "without visible replacement" and the code
         never checked for one, so widening it naively would have flagged
         `focus-visible:outline-none focus-visible:ring-2` — this repo's OWN recommendation.
      2. monitoring-checker warned when a log line lacked "request_id" — a string Rails injects
         via `config.log_tags`, so it is never in the source. On a correctly configured app it
         was a false positive; on a broken one the remedy is config, not the call site."""
    print("\n[checks must match the syntax this stack actually writes]")
    global PASS, FAIL
    import importlib.util
    import tempfile

    spec = importlib.util.spec_from_file_location(
        "ac", os.path.join(HOOKS_DIR, "accessibility-checker.py"))
    sys.path.insert(0, HOOKS_DIR)
    ac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ac)

    for label, content, should in (
            ("the repo's own focus-visible+ring idiom",
             'className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"', False),
            ("Tailwind outline-none with no ring",
             '<a href="/s" className="focus:outline-none">Settings</a>', True),
            ("CSS outline:none with no replacement", "a:focus {\n  outline: none;\n}", True),
            ("CSS outline:none + box-shadow", "a:focus {\n  outline: none;\n  box-shadow: 0 0 0 2px #00f;\n}", False),
            ("no outline at all", '<button className="px-4">Go</button>', False)):
        got = bool(ac.check_focus_indicator_removed(content))
        if got == should:
            PASS += 1
            print(f"  PASS: focus check {'fires' if should else 'quiet'} — {label}")
        else:
            FAIL += 1
            print(f"  FAIL: focus check {'MISSED' if should else 'FALSE-FIRES on'} — {label}")

    if ".css" in ac.ALLOWED_EXTENSIONS:
        PASS += 1
        print("  PASS: .css/.scss are in scope (CSS syntax needs a CSS file to live in)")
    else:
        FAIL += 1
        print("  FAIL: CSS syntax matched but .css excluded — matcher and scope disjoint again")

    # monitoring: the request_id-per-line check must be gone; the sensitive-data check must stay.
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "app", "controllers")
        os.makedirs(d)
        for name, body, should in (
                ("clean.rb", 'Rails.logger.info({ msg: "order created", order_id: order.id })\n', False),
                ("plain.rb", 'Rails.logger.info("order created")\n', False),
                ("leak.rb", 'Rails.logger.info("user #{user.password} in")\n', True)):
            f = os.path.join(d, name)
            open(f, "w", encoding="utf-8").write(body)
            out = run_hook("monitoring-checker.py", "Write", {"file_path": f})[1]
            fired = bool(out.strip())
            if fired == should:
                PASS += 1
                print(f"  PASS: monitoring {'warns' if should else 'quiet'} on {name}")
            else:
                FAIL += 1
                print(f"  FAIL: monitoring {'MISSED' if should else 'FALSE-FIRES on'} {name}: {out[:80]}")


def test_gates_actually_fire_where_registered():
    """The inverse of the false-positive test, and the more dangerous half: a gate that never
    runs looks exactly like a gate that passed (Ch. 9). Both cases below were found by audit:

      1. hooks.json registered migration-validator under matcher "Write" while the hook itself
         accepts ("Write", "Edit") — so the canonical Rails path (`rails g migration`, then Edit
         the body) never reached the gate at all.
      2. terraform-checker's resource pattern used `\\w+`, which cannot match a hyphen. A
         kebab-named resource did not fail the snake_case check — it was invisible to it. And
         because the tags check derives its resource list from the same pattern, an all-kebab
         file yielded an empty list and the tags check silently skipped entirely."""
    print("\n[gates must actually fire where they are registered]")
    global PASS, FAIL
    import json as _json
    import re
    import tempfile

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))

    # 1. Every hook's declared matcher must cover the tools its check() actually accepts.
    cfg = _json.load(open(os.path.join(HOOKS_DIR, "hooks.json"), encoding="utf-8"))
    registered = {}
    for group in cfg["hooks"].get("PreToolUse", []):
        for h in group.get("hooks", []):
            name = h.get("command", "").rstrip('"').split("/")[-1]
            registered.setdefault(name, set()).update(group.get("matcher", "").split("|"))
    for script, tools in registered.items():
        path = os.path.join(HOOKS_DIR, script)
        if not os.path.isfile(path):
            continue
        src = open(path, encoding="utf-8").read()
        m = re.search(r'tool_name\(event\)\s+not\s+in\s+\(([^)]*)\)', src)
        if not m:
            continue
        accepted = set(re.findall(r'"(\w+)"', m.group(1)))
        unreachable = accepted - tools
        if unreachable:
            FAIL += 1
            print(f"  FAIL: {script} handles {sorted(unreachable)} but hooks.json never routes "
                  f"them (matcher={sorted(tools)}) — that branch is dead")
        else:
            PASS += 1
            print(f"  PASS: {script} matcher {sorted(tools)} covers everything its check() accepts")

    # Live fire: editing a migration must reach the validator.
    out = run_hook("migration-validator.py", "Edit",
                   {"file_path": "backend/db/migrate/20240101_x.rb",
                    "old_string": "def change", "new_string": "def change\n    drop_table :users"})[1]
    if "permissionDecision" in out:
        PASS += 1
        print("  PASS: an Edit to a migration reaches the validator")
    else:
        FAIL += 1
        print("  FAIL: an Edit to a migration is not validated")

    # 2. terraform: a kebab-named resource must be visible to BOTH checks.
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "main.tf")
        open(f, "w", encoding="utf-8").write(
            'resource "aws_ecs_service" "rails-app" {\n  name = "x"\n}\n')
        out = run_hook("terraform-checker.py", "Write", {"file_path": f})[1]
        if "snake_case" in out:
            PASS += 1
            print("  PASS: a kebab-named resource trips the naming check")
        else:
            FAIL += 1
            print("  FAIL: kebab name invisible — the check cannot see what it exists to catch")
        if "tag" in out.lower():
            PASS += 1
            print("  PASS: ...and the tags check still runs on it (it silently skipped before)")
        else:
            FAIL += 1
            print("  FAIL: the tags check skipped — an empty resource list disabled it")

    # And snake_case must still pass cleanly.
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "ok.tf")
        open(f, "w", encoding="utf-8").write(
            'provider "aws" {\n  default_tags {\n    tags = {\n      project = "p"\n'
            '      environment = "dev"\n      team = "t"\n      managed-by = "terraform"\n'
            '    }\n  }\n}\n\nresource "aws_ecs_service" "rails_app" {\n  name = "x"\n}\n')
        out = run_hook("terraform-checker.py", "Write", {"file_path": f})[1]
        if "snake_case" not in out:
            PASS += 1
            print("  PASS: a snake_case resource stays quiet (no new false positive)")
        else:
            FAIL += 1
            print(f"  FAIL: the widened pattern now flags correct snake_case: {out[:120]}")


def test_gates_do_not_fire_on_correct_work():
    """The repo states this principle in migration-validator.py:23 — "a gate that flags correct
    code is a gate people learn to ignore" — and then violated it in three of its own hooks. An
    adversarially-verified audit reproduced all three end-to-end:

      1. api-design-checker compiled its route regex with re.IGNORECASE while relying on `[A-Z]`
         to mean "camelCase follows the verb". IGNORECASE voids that, so `/posts` — a plural
         noun — was told "Use plural nouns for resources".
      2. task-completed-checker matched `"test" in task_text`, so "Deploy the la-test- build"
         was HARD REJECTED (exit 2) against a remedy that cannot exist.
      3. teammate-idle-checker matched `"add" in description` ("address") and `"fix"`
         ("prefix"), and pushed read-only agents to write code they hold no tool for.

    Every case below is a FALSE POSITIVE that shipped. The true-positive half is asserted too:
    a fix that silences the real detection is not a fix."""
    print("\n[gates must not fire on correct work]")
    global PASS, FAIL
    import subprocess as sp
    import tempfile

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))

    # --- 1. api-design-checker: plural nouns that start with a verb ---
    with tempfile.TemporaryDirectory() as tmp:
        api = os.path.join(tmp, "web", "src", "api")
        os.makedirs(api)
        f = os.path.join(api, "resources.ts")
        open(f, "w", encoding="utf-8").write(
            "axios.get('/posts');\naxios.get('/addresses');\naxios.get('/listings');\n"
            "axios.get('/editions');\naxios.get('/api/v1/posts');\n"
            "axios.get('/getUser');\naxios.post('/createOrder');\naxios.delete('/api/deleteItem');\n")
        out = run_hook("api-design-checker.py", "Write", {"file_path": f})[1]
        for noun in ("'/posts'", "'/addresses'", "'/listings'", "'/editions'"):
            if noun in out:
                FAIL += 1
                print(f"  FAIL: warns on {noun} — a plural noun told to 'use plural nouns'")
            else:
                PASS += 1
                print(f"  PASS: quiet on {noun} (plural noun starting with a verb)")
        for camel in ("getUser", "createOrder", "deleteItem"):
            if camel in out:
                PASS += 1
                print(f"  PASS: still catches /{camel}")
            else:
                FAIL += 1
                print(f"  FAIL: no longer catches /{camel} — the fix broke detection")

    # --- 2 & 3. the substring gates, in a clean scratch repo so unrelated gates stay quiet ---
    def run_in_clean_repo(script, payload):
        with tempfile.TemporaryDirectory() as tmp:
            sp.run(["git", "init", "-q"], cwd=tmp, capture_output=True)
            r = sp.run([sys.executable, os.path.join(HOOKS_DIR, script)], cwd=tmp,
                       input=json.dumps(payload), capture_output=True, text=True, timeout=15)
            return r.returncode, r.stdout

    for subject, should_fire in (("Deploy the latest build", False),
                                 ("Inspect the payment flow", False),
                                 ("Review the retrospective notes", False),
                                 ("Add tests for checkout", True),
                                 ("Improve test coverage", True),
                                 ("Write specs for the API", True)):
        _, out = run_in_clean_repo("task-completed-checker.py",
                                   {"task_subject": subject, "task_description": ""})
        fired = "mentions testing" in out
        if fired == should_fire:
            PASS += 1
            print(f"  PASS: task gate {'fires' if should_fire else 'quiet'} on {subject!r}")
        else:
            FAIL += 1
            print(f"  FAIL: task gate {'MISSED' if should_fire else 'FALSE-FIRES on'} {subject!r}")

    for agent_name, desc, should_fire in (
            ("test-generator", "Review the address validation approach", False),
            ("test-generator", "Check the prefix handling in the parser", False),
            # A read-only agent holds no write tool — demanding code is unsatisfiable.
            ("architecture-advisor", "Create an ADR for the caching strategy", False),
            ("design-critique", "Add findings about the button hierarchy", False),
            ("test-generator", "Implement the checkout flow", True),
            ("phlex-developer", "Fix the login bug", True)):
        _, out = run_in_clean_repo("teammate-idle-checker.py",
                                   {"agent_name": agent_name, "task_description": desc})
        fired = "require code changes" in out
        if fired == should_fire:
            PASS += 1
            print(f"  PASS: idle gate {'fires' if should_fire else 'quiet'} — {agent_name}: {desc[:38]!r}")
        else:
            FAIL += 1
            print(f"  FAIL: idle gate {'MISSED' if should_fire else 'FALSE-FIRES on'} — {agent_name}: {desc[:38]!r}")


def test_commit_types_match_the_skill():
    """`pre-commit-check.py` BLOCKS a commit whose type is not in its pattern, and its message
    names the `std-git-workflow` skill. So that pattern is a hard interface: a type the hook
    accepts but the skill omits is undiscoverable except by being denied, and a type the skill
    documents but the hook rejects is a documented instruction that cannot be followed.

    The hook accepted `revert`; neither the skill nor CLAUDE.md mentioned it. Same shape as the
    200-vs-300 line limit: a list in code and a list in prose drift silently."""
    print("\n[commit types: the blocking list must equal the documented list]")
    global PASS, FAIL
    import re as _re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    hook_src = open(os.path.join(HOOKS_DIR, "pre-commit-check.py"), encoding="utf-8").read()
    m = _re.search(r"r'\^\(([a-z|]+)\)", hook_src)
    if not m:
        FAIL += 1
        print("  FAIL: could not find the conventional-commit pattern — did it move?")
        return
    hook_types = set(m.group(1).split("|"))

    skill_path = os.path.join(repo, "skills", "std-git-workflow", "SKILL.md")
    skill_types = set(_re.findall(r"^\| `([a-z]+)`", open(skill_path, encoding="utf-8").read(), _re.M))

    blocked = skill_types - hook_types          # documented, but the hook denies it
    undocumented = hook_types - skill_types     # accepted, but nobody can find it

    if blocked:
        FAIL += 1
        print(f"  FAIL: std-git-workflow documents {sorted(blocked)}, which the hook BLOCKS — "
              f"a documented instruction that cannot be followed")
    else:
        PASS += 1
        print("  PASS: every documented type is accepted by the hook")

    if undocumented:
        FAIL += 1
        print(f"  FAIL: the hook accepts {sorted(undocumented)} but the skill never lists them — "
              f"undiscoverable except by being denied")
    else:
        PASS += 1
        print(f"  PASS: every accepted type is documented ({len(hook_types)} types)")

    # Live fire, both directions.
    ok = run_hook("pre-commit-check.py", "Bash",
                  {"command": 'git commit -m "revert: feat(auth): add SSO login"'})[1]
    if "permissionDecision" not in ok or "deny" not in ok.lower():
        PASS += 1
        print("  PASS: a documented type ('revert') is actually accepted")
    else:
        FAIL += 1
        print(f"  FAIL: 'revert' is documented but denied: {ok[:120]}")

    bad = run_hook("pre-commit-check.py", "Bash",
                   {"command": 'git commit -m "wibble: do a thing"'})[1]
    if "deny" in bad.lower():
        PASS += 1
        print("  PASS: an undocumented type is still blocked (the gate is live)")
    else:
        FAIL += 1
        print("  FAIL: the conventional-commit gate accepts anything")


def test_autoformat_never_changes_semantics():
    """A formatter may reshape code; it must not change what the code MEANS.

    `auto-format.py` runs unattended on every write, with stdout/stderr sent to DEVNULL. It
    used to run `rubocop --autocorrect-all` — which RuboCop's own CLI documents as "Autocorrect
    offenses (safe and unsafe)", against a default config that marks 53 cops
    `SafeAutoCorrect: false`. So it silently applied corrections RuboCop's maintainers flag as
    able to change behaviour, to code nobody re-read.

    `-a/--autocorrect` is "only when it's safe". Unsafe corrections are a deliberate human act."""
    print("\n[auto-format must not silently change semantics]")
    global PASS, FAIL
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "af", os.path.join(HOOKS_DIR, "auto-format.py"))
    af = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(af)

    unsafe_flags = {"--autocorrect-all", "-A", "--auto-correct-all"}
    offenders = []
    for ext, (binary, cmd) in af.FORMATTER_MAP.items():
        bad = unsafe_flags.intersection(cmd)
        if bad:
            offenders.append(f".{ext} runs {binary} with {sorted(bad)}")
    if offenders:
        FAIL += 1
        print(f"  FAIL: unattended formatter applies UNSAFE corrections: {offenders}")
    else:
        PASS += 1
        print("  PASS: no formatter runs an unsafe-autocorrect flag unattended")

    # Ruby must still be autocorrected — the safe half is the whole point of the hook.
    rb = af.FORMATTER_MAP.get("rb")
    if rb and "--autocorrect" in rb[1]:
        PASS += 1
        print("  PASS: .rb still autocorrects, with the safe flag")
    else:
        FAIL += 1
        print(f"  FAIL: .rb lost its autocorrect entirely: {rb}")

    # The other formatters are layout-only by nature; assert they stayed that way.
    for ext, expect in (("ts", "prettier"), ("py", "black"), ("tf", "terraform")):
        entry = af.FORMATTER_MAP.get(ext)
        if entry and entry[0] == expect:
            PASS += 1
            print(f"  PASS: .{ext} -> {expect} (layout only, no semantic rewrites)")
        else:
            FAIL += 1
            print(f"  FAIL: .{ext} formatter changed unexpectedly: {entry}")


def test_limits_match_the_skill_that_documents_them():
    """A gate whose number disagrees with the skill it names is worse than no gate: the
    developer reads the skill, writes to that number, gets warned anyway, and concludes the
    hook is noise. `code-quality-checker.py` warns at 200 lines for models/components and names
    the `std-code-standards` skill — which said only "300" and never mentioned 200.

    Numbers in code and numbers in prose drift silently. This is the same shape as the rule
    taxonomy check: gate the invariant that the two agree."""
    print("\n[enforced limits must match the skill that documents them]")
    global PASS, FAIL
    import importlib.util

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    spec = importlib.util.spec_from_file_location(
        "cqc", os.path.join(HOOKS_DIR, "code-quality-checker.py"))
    cqc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cqc)

    skill = os.path.join(repo, "skills", "std-code-standards", "SKILL.md")
    body = open(skill, encoding="utf-8").read()

    # Every number the hook enforces must appear in the skill that its message points at.
    enforced = {
        "MODEL_LIMIT": cqc.MODEL_LIMIT,
        "COMPONENT_LIMIT": cqc.COMPONENT_LIMIT,
        "DEFAULT_LIMIT": cqc.DEFAULT_LIMIT,
        "MAX_FUNCTION_LINES": cqc.MAX_FUNCTION_LINES,
        "MAX_PARAMS": cqc.MAX_PARAMS,
        "MAX_NESTING": cqc.MAX_NESTING,
    }
    missing = [f"{k}={v}" for k, v in enforced.items() if str(v) not in body]
    if missing:
        FAIL += 1
        print(f"  FAIL: std-code-standards never states: {', '.join(missing)} — the hook warns on "
              f"numbers the skill it names does not document")
    else:
        PASS += 1
        print(f"  PASS: all {len(enforced)} enforced limits are documented in std-code-standards")

    # The always-on skill consumers actually get must agree too (a plugin's CLAUDE.md is NOT
    # shipped as consumer context, so documenting a limit only there reaches nobody).
    always_on = os.path.join(repo, "skills", "sdh-engineering-standards", "SKILL.md")
    if os.path.isfile(always_on):
        text = open(always_on, encoding="utf-8").read()
        gaps = [str(v) for v in (cqc.MODEL_LIMIT, cqc.DEFAULT_LIMIT, cqc.MAX_FUNCTION_LINES)
                if str(v) not in text]
        if gaps:
            FAIL += 1
            print(f"  FAIL: sdh-engineering-standards (always-on) omits: {', '.join(gaps)}")
        else:
            PASS += 1
            print("  PASS: the always-on skill states the same headline limits")

    # And prove the gate fires: a model over MODEL_LIMIT must warn.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "backend", "app", "models")
        os.makedirs(d)
        f = os.path.join(d, "order.rb")
        open(f, "w", encoding="utf-8").write(
            "class Order < ApplicationRecord\n"
            + "".join(f"  # line {i}\n" for i in range(cqc.MODEL_LIMIT + 20)) + "end\n")
        out = cqc.check({"tool_name": "Write", "tool_input": {"file_path": f}})
        if any(str(cqc.MODEL_LIMIT) in w for w in out):
            PASS += 1
            print(f"  PASS: a model over {cqc.MODEL_LIMIT} lines warns (the gate is live)")
        else:
            FAIL += 1
            print(f"  FAIL: a model over {cqc.MODEL_LIMIT} lines produced no warning: {out}")


def test_mcp_install_gate():
    """An MCP server is an instruction source, not a library: its tool descriptions are prompts
    the model obeys, and the docs say plainly "Verify you trust each server before connecting
    it. Servers that fetch external content can expose you to prompt injection risk." So the
    human picks it (layer 6). The `mcp-advisor` skill cannot guarantee that — guidance only
    works if read — which is why this is a gate (Ch. 7's placement test).

    `ask`, never `deny`: MCP servers are legitimate and useful, and a deny here just gets the
    plugin disabled."""
    print("\n[mcp-install-gate.py]")
    assert_warns("asks on `claude mcp add` (stdio)", "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add airtable -- npx -y airtable-mcp-server"})
    assert_warns("asks on `claude mcp add --transport http`", "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add --transport http notion https://mcp.notion.com/mcp"})
    assert_warns("asks on `claude mcp add-json`", "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add-json weather '{\"type\":\"stdio\"}'"})
    assert_warns("asks on add-from-claude-desktop (a bulk import of servers)",
                 "mcp-install-gate.py", "Bash",
                 {"command": "claude mcp add-from-claude-desktop"})

    # The team-wide path: project scope ships to everyone, so the reason must say so.
    assert_output_contains("names the team-wide blast radius for --scope project",
                           "mcp-install-gate.py", "Bash",
                           {"command": "claude mcp add --transport http --scope project acme https://mcp.acme.com/mcp"},
                           "EVERY teammate")
    # A deny reason must name a remedy (Ch. 25) — here, where to find vetted servers.
    assert_output_contains("names a remedy: the reviewed directory", "mcp-install-gate.py", "Bash",
                           {"command": "claude mcp add foo -- npx foo"},
                           "claude.ai/directory")

    # Editing .mcp.json adds servers for the whole team with no CLI involved. Gating only the
    # CLI would be a gate with a door next to it.
    assert_warns("asks when .mcp.json is written directly", "mcp-install-gate.py", "Write",
                 {"file_path": "/repo/.mcp.json",
                  "content": '{"mcpServers": {"acme": {"type": "http", "url": "https://mcp.acme.com"}}}'})

    # Must NOT fire on things that reduce or merely inspect capability, or the gate becomes
    # noise people click through.
    assert_allowed("silent on `claude mcp list`", "mcp-install-gate.py", "Bash",
                   {"command": "claude mcp list"})
    assert_allowed("silent on `claude mcp remove` (reduces capability)", "mcp-install-gate.py",
                   "Bash", {"command": "claude mcp remove airtable"})
    assert_allowed("silent on `claude mcp get`", "mcp-install-gate.py", "Bash",
                   {"command": "claude mcp get airtable"})
    assert_allowed("silent on unrelated bash", "mcp-install-gate.py", "Bash",
                   {"command": "npm run build"})
    assert_allowed("silent on unrelated file writes", "mcp-install-gate.py", "Write",
                   {"file_path": "/repo/package.json", "content": '{"name":"x"}'})


def test_hook_messages_point_somewhere_real():
    """Ch. 13 — "It explains its denials … the deny reasons are your plugin's user interface,
    and they're the only part most users will ever read." Ch. 25 adds that a reason must name a
    remedy. A pointer to a file that does not exist fails both: the user greps for it, finds
    nothing, and learns that the guidance is unreachable.

    This is not hypothetical. Converting `.claude/rules/*.md` into `std-*` skills left **37
    messages across 10 hooks** pointing at `accessibility.md`, `security.md`, `database.md` and
    friends — none of which existed any more. Every one of those hooks fired correctly and sent
    the reader nowhere."""
    print("\n[hook messages must point at something that exists]")
    global PASS, FAIL
    import glob
    import re

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    skills = {os.path.basename(os.path.dirname(p))
              for p in glob.glob(os.path.join(repo, "skills", "*", "SKILL.md"))}

    dangling, skill_refs = [], 0
    for path in sorted(glob.glob(os.path.join(HOOKS_DIR, "*.py"))):
        text = open(path, encoding="utf-8").read()
        name = os.path.basename(path)

        # 1. Any `something.md` named in a hook must exist on disk somewhere in the repo.
        for m in re.finditer(r"\b([a-z][a-z0-9_-]*\.md)\b", text):
            target = m.group(1)
            if not glob.glob(os.path.join(repo, "**", target), recursive=True):
                dangling.append(f"{name}: points at '{target}', which does not exist")

        # 2. Any `std-x` skill it names must be a real skill directory.
        for m in re.finditer(r"`(std-[a-z0-9-]+)`", text):
            skill_refs += 1
            if m.group(1) not in skills:
                dangling.append(f"{name}: names skill '{m.group(1)}', which does not exist")

    if dangling:
        FAIL += 1
        for d in dangling[:10]:
            print(f"  FAIL: {d}")
        print(f"  ({len(dangling)} dangling pointer(s) — a reason nobody can follow is not a reason)")
    else:
        PASS += 1
        print(f"  PASS: every file/skill named by a hook exists ({skill_refs} skill pointers checked)")

    # Prove the check FIRES rather than merely agreeing with today's tree.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        fake = os.path.join(tmp, "fake-hook.py")
        open(fake, "w", encoding="utf-8").write(
            '"""Checks things per totally-made-up-rules.md."""\n')
        text = open(fake, encoding="utf-8").read()
        found = [m.group(1) for m in re.finditer(r"\b([a-z][a-z0-9_-]*\.md)\b", text)
                 if not glob.glob(os.path.join(repo, "**", m.group(1)), recursive=True)]
        if found:
            PASS += 1
            print("  PASS: the check catches an invented .md pointer")
        else:
            FAIL += 1
            print("  FAIL: the check would not notice a dangling pointer")

    # A hook that warns must also say WHERE the rule lives. The earlier fix guaranteed that a
    # named skill exists; this guarantees one is named at all. 8 hooks warned into the void
    # while 11 pointed somewhere — a developer hit by the design-token checker had nowhere to
    # learn the rule.
    #
    # `[a-z0-9-]` and not `[a-z-]`: `std-i18n` has digits in it. The narrower class silently
    # reported i18n-checker as pointing nowhere when it pointed correctly — a false positive
    # that would have "fixed" working code.
    # The .claude/rules/*.md -> std-* skills conversion left dangling pointers everywhere, not
    # just in hooks. The earlier fix swept HOOKS ONLY and the regression test was scoped to hook
    # messages — so 19 more survived in agents/ and skills/, including
    # phlex-developer.md's step 9 ("Verify compliance -- check against @rules/phlex-conventions.md"):
    # the compliance step pointed at nothing, so it no-opped and the agent reported a check it
    # never performed. Neither .claude/rules/ nor .claude/agents/ has existed since the plugin
    # conversion.
    dead_layout = []
    for path in sorted(glob.glob(os.path.join(repo, "agents", "*.md"))
                       + glob.glob(os.path.join(repo, "skills", "*", "SKILL.md"))
                       + glob.glob(os.path.join(repo, "skills", "*", "references", "*.md"))):
        text = open(path, encoding="utf-8").read()
        for m in re.finditer(r"@rules/|\.claude/rules/|\.claude/agents/", text):
            rel = os.path.relpath(path, repo).replace("\\", "/")
            dead_layout.append(f"{rel}: '{m.group(0)}' — that layout has not existed since the plugin conversion")
    if dead_layout:
        FAIL += 1
        for d in dead_layout[:6]:
            print(f"  FAIL: {d}")
        print(f"  ({len(dead_layout)} pointer(s) into a directory that does not exist)")
    else:
        PASS += 1
        print("  PASS: no agent or skill points into the pre-plugin .claude/rules|agents layout")

    EXEMPT = {
        # Names an install command ("gem install rubocop"), which is the actual remedy.
        # No skill teaches "have rubocop on your PATH".
        "auto-format.py": "names an install command, not a rule",
        "audit-logger.py": "records, never warns",
        "capture-event.py": "developer tool, not a gate",
        "session-start-check.py": "reports environment state; the sentinel names the rules inline",
    }
    silent = []
    for path in sorted(glob.glob(os.path.join(HOOKS_DIR, "*.py"))):
        name = os.path.basename(path)
        if name.startswith("_") or name in EXEMPT:
            continue
        text = open(path, encoding="utf-8").read()
        if not re.search(r"warnings\.append|hooklib\.(ask|deny)|notice_once", text):
            continue
        if not re.search(r"`[a-z0-9-]+` skill", text):
            silent.append(name)
    if silent:
        FAIL += 1
        print(f"  FAIL: warns but names no skill, so the reader has nowhere to go: {silent}")
    else:
        PASS += 1
        print("  PASS: every warning-emitting hook names the skill that carries the rule")


def test_release_hygiene_checker():
    """Ch. 13 — "pin, don't float", with the mechanical edge the plugin docs spell out: a
    `version` that does not move means "pushing new commits ... does nothing for existing
    users". That is a SILENT delivery failure — everything merges, CI is green, and no
    installed user receives any of it. The gate is inert until the first tag exists, so it
    would otherwise be a gate that has only ever printed a note. Prove it fires."""
    print("\n[release hygiene — a stale version delivers nothing]")
    global PASS, FAIL
    import shutil
    import tempfile

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    script = os.path.join(repo, ".github", "scripts", "check_release_hygiene.py")
    if not os.path.isfile(script):
        FAIL += 1
        print("  FAIL: .github/scripts/check_release_hygiene.py is missing")
        return

    def run(cwd, env_extra=None):
        env = dict(os.environ)
        env.pop("GITHUB_REF", None)
        env.update(env_extra or {})
        proc = subprocess.run([sys.executable, script], cwd=cwd, capture_output=True,
                              text=True, timeout=60, env=env)
        return proc.returncode, proc.stdout + proc.stderr

    code, out = run(repo)
    if code == 0:
        PASS += 1
        print("  PASS: the real tree passes")
    else:
        FAIL += 1
        print(f"  FAIL: the real tree fails its own release gate:\n{out}")
    # The gate has two legitimate states, and the correct assertion depends on which one the
    # repo is in. Before v2.0.0 there were no tags, so this asserted the INERT announcement —
    # and then the release made the announcement correctly disappear, failing a test that had
    # hard-coded a pre-release world. The gate was right; the test was stale.
    has_tag = bool(git_tags := subprocess.run(
        ["git", "tag", "-l", "v*"], cwd=repo, capture_output=True, text=True).stdout.strip())
    if not has_tag:
        # No release yet: silence here would be indistinguishable from a passing gate.
        if "INERT" in out:
            PASS += 1
            print("  PASS: with no tags the gate announces it is inert (not silently green)")
        else:
            FAIL += 1
            print("  FAIL: an inert delivery gate stayed quiet — indistinguishable from a pass")
    else:
        # Released: the gate is live, so it must NOT still be claiming it cannot verify
        # anything — that would be a stale message telling the reader the opposite of the truth.
        if "INERT" not in out:
            PASS += 1
            print(f"  PASS: a release exists ({git_tags.splitlines()[-1]}), so the delivery gate "
                  f"is live and no longer announces itself inert")
        else:
            FAIL += 1
            print("  FAIL: a tag exists but the gate still reports itself INERT")

    def git(cwd, *args):
        subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)

    def scaffold(tmp, version="1.0.0", entry_version=None):
        work = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(work, ".claude-plugin"))
        os.makedirs(os.path.join(work, "skills", "demo"))
        shutil.copytree(os.path.join(repo, ".github", "scripts"),
                        os.path.join(work, ".github", "scripts"))
        entry = {"name": "sdh", "source": "./"}
        if entry_version:
            entry["version"] = entry_version
        json.dump({"name": "sdh", "version": version},
                  open(os.path.join(work, ".claude-plugin", "plugin.json"), "w"))
        json.dump({"name": "m", "plugins": [entry]},
                  open(os.path.join(work, ".claude-plugin", "marketplace.json"), "w"))
        open(os.path.join(work, "skills", "demo", "SKILL.md"), "w").write("# demo\n")
        open(os.path.join(work, "CHANGELOG.md"), "w").write(
            "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-01-01\n\n- initial\n")
        git(work, "init", "-q")
        git(work, "config", "user.email", "t@t.t")
        git(work, "config", "user.name", "t")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "init")
        git(work, "tag", "v1.0.0")
        return work

    # The real regression: plugin content changes, version does not.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp)
        open(os.path.join(work, "skills", "demo", "SKILL.md"), "a").write("a new rule\n")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "change a skill")
        code, out = run(work)
        if code != 0 and "does nothing for existing users" in out.lower():
            PASS += 1
            print("  PASS: catches changed plugin content under an unchanged version")
        else:
            FAIL += 1
            print(f"  FAIL: MISSED the silent-delivery bug — this is the whole point: {out[:200]}")

        # Bumping the version is what makes the change deliverable.
        manifest = os.path.join(work, ".claude-plugin", "plugin.json")
        json.dump({"name": "sdh", "version": "1.1.0"}, open(manifest, "w"))
        git(work, "add", "-A")
        git(work, "commit", "-qm", "bump")
        code, out = run(work)
        if code == 0:
            PASS += 1
            print("  PASS: a bumped version passes (the gate is satisfiable)")
        else:
            FAIL += 1
            print(f"  FAIL: gate still fails after a correct bump — it would be routed around: {out[:200]}")

    # A test-only change ships NOTHING: hooks.json never references hooks/tests/, so a
    # consumer's session cannot execute it. Demanding a version bump for it is a gate crying
    # wolf — and this exact false positive turned `main` red after a test-only fix, which is
    # how a CI step earns a `|| true`.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp)
        tests_dir = os.path.join(work, "hooks", "tests")
        os.makedirs(tests_dir)
        open(os.path.join(tests_dir, "run-all.py"), "w").write("# a test\n")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "add a test")
        code, out = run(work)
        if code == 0:
            PASS += 1
            print("  PASS: a test-only change needs no version bump (ships no behaviour)")
        else:
            FAIL += 1
            print(f"  FAIL: cries wolf on a test-only change: {out[:160]}")

        # ...but a real hook change in the same tree must still fail, or the exclusion is a hole.
        open(os.path.join(work, "hooks", "auto-format.py"), "w").write("# a real hook\n")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "change a hook")
        code, out = run(work)
        if code != 0 and "auto-format.py" in out:
            PASS += 1
            print("  PASS: a real hook change still requires a bump, and the message names the file")
        else:
            FAIL += 1
            print(f"  FAIL: the tests/ exclusion swallowed a real behaviour change: {out[:160]}")

    # A tag push must be internally consistent.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp, version="1.1.0")
        code, out = run(work, {"GITHUB_REF": "refs/tags/v9.9.9"})
        if code != 0 and "does not match" in out:
            PASS += 1
            print("  PASS: catches a tag that disagrees with plugin.json")
        else:
            FAIL += 1
            print("  FAIL: a tag naming a version the manifest never declared was allowed")

        # CHANGELOG has no [1.1.0] section, and [Unreleased] is empty -> the missing-section
        # failure must fire on its own.
        code, out = run(work, {"GITHUB_REF": "refs/tags/v1.1.0"})
        if code != 0 and "no `## [1.1.0]` section" in out:
            PASS += 1
            print("  PASS: catches releasing a version the CHANGELOG never documents")
        else:
            FAIL += 1
            print(f"  FAIL: released an undocumented version: {out[:200]}")

    # Draining [Unreleased] is part of cutting a release.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp, version="1.1.0")
        open(os.path.join(work, "CHANGELOG.md"), "w").write(
            "# Changelog\n\n## [Unreleased]\n\n- a change nobody moved\n\n"
            "## [1.1.0] - 2026-02-02\n\n- released\n")
        code, out = run(work, {"GITHUB_REF": "refs/tags/v1.1.0"})
        if code != 0 and "Unreleased" in out:
            PASS += 1
            print("  PASS: catches a release that left entries stranded under [Unreleased]")
        else:
            FAIL += 1
            print("  FAIL: released with undrained [Unreleased] — the version misdescribes itself")

    # Two versions, one silently ignored.
    with tempfile.TemporaryDirectory() as tmp:
        work = scaffold(tmp, version="1.0.0", entry_version="2.0.0")
        code, out = run(work)
        if code != 0 and "WITHOUT WARNING" in out:
            PASS += 1
            print("  PASS: catches a marketplace entry version that plugin.json silently masks")
        else:
            FAIL += 1
            print(f"  FAIL: allowed two conflicting versions: {out[:200]}")


def test_rule_taxonomy_checker():
    """Ch. 9 — a gate that has only ever passed is untested. This one exists because
    react-native-best-practices had silently collapsed its 14 canonical sections into 8
    invented ones, dropping "Core Rendering" (CRITICAL — "violations cause runtime crashes")
    and promoting List Performance into the vacant slot. The body is what the model reads, so
    a wrong impact there mis-prioritises real work. Prove the checker CATCHES that regression
    rather than merely agreeing with today's tree."""
    print("\n[rule taxonomy — the body must match rules/_sections.md]")
    global PASS, FAIL
    import shutil
    import tempfile

    repo = os.path.abspath(os.path.join(HOOKS_DIR, ".."))
    script = os.path.join(repo, ".github", "scripts", "check_rule_taxonomy.py")
    if not os.path.isfile(script):
        FAIL += 1
        print("  FAIL: .github/scripts/check_rule_taxonomy.py is missing — the taxonomy gate is gone")
        return

    def run(cwd):
        proc = subprocess.run([sys.executable, script], cwd=cwd,
                              capture_output=True, text=True, timeout=60)
        return proc.returncode, proc.stdout + proc.stderr

    # 1. The real tree must pass, or the gate is crying wolf.
    code, out = run(repo)
    if code == 0:
        PASS += 1
        print("  PASS: the real tree passes the taxonomy gate")
    else:
        FAIL += 1
        print(f"  FAIL: the real tree does not satisfy its own taxonomy gate:\n{out}")

    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(work, ".github"))
        shutil.copytree(os.path.join(repo, "skills"), os.path.join(work, "skills"))
        shutil.copytree(os.path.join(repo, ".github", "scripts"),
                        os.path.join(work, ".github", "scripts"))
        body_path = os.path.join(work, "skills", "react-native-best-practices", "SKILL.md")
        original = open(body_path, encoding="utf-8").read()

        # 2. Reconstruct the actual regression and prove the gate fires on it.
        cases = [
            ("a CRITICAL section downgraded",
             lambda t: t.replace("### 1. Core Rendering (CRITICAL)",
                                 "### 1. Core Rendering (MEDIUM)")),
            ("an impact relabelled upward",
             lambda t: t.replace("### 2. List Performance (HIGH)",
                                 "### 2. List Performance (CRITICAL)")),
            ("a section dropped from the body",
             lambda t: t.replace("### 14. Fonts (LOW)", "### 14. Fonts")),
        ]
        for label, mutate in cases:
            open(body_path, "w", encoding="utf-8", newline="\n").write(mutate(original))
            code, out = run(work)
            if code != 0:
                PASS += 1
                print(f"  PASS: gate catches {label}")
            else:
                FAIL += 1
                print(f"  FAIL: gate MISSED {label} — it would merge")

        # 3. A rule file on disk that no section prefix claims must be caught: the body
        #    cannot group it, so the model never learns it exists.
        open(body_path, "w", encoding="utf-8", newline="\n").write(original)
        orphan = os.path.join(work, "skills", "react-native-best-practices", "rules",
                              "zzz-unclaimed-rule.md")
        open(orphan, "w", encoding="utf-8").write("# orphan\n")
        code, out = run(work)
        if code != 0 and "claimed by no section" in out:
            PASS += 1
            print("  PASS: gate catches a rule file no section claims")
        else:
            FAIL += 1
            print("  FAIL: gate MISSED an unclaimed rule file")
        os.remove(orphan)

        # 4. Numbering is house style, not an invariant. Both conventions are in use; a gate
        #    that fires on a legitimate variation trains people to ignore it.
        open(body_path, "w", encoding="utf-8", newline="\n").write(
            original.replace("### 1. Core Rendering (CRITICAL)", "### Core Rendering (CRITICAL)"))
        code, out = run(work)
        if code == 0:
            PASS += 1
            print("  PASS: unnumbered headings accepted (gates the invariant, not house style)")
        else:
            FAIL += 1
            print("  FAIL: gate rejects a legitimate heading style — it will be ignored as noise")


def main():
    print("=" * 60)
    print("Hook Test Harness")
    print("=" * 60)

    test_dangerous_command_blocker()
    test_migration_validator()
    test_deployment_gate()
    test_pre_commit_check()
    test_accessibility_checker()
    test_api_design_checker()
    test_ci_workflow_is_loadable()
    test_deny_reasons_name_a_remedy()
    test_terraform_command_gate()
    test_fail_open_is_not_silent()
    test_permission_sentinel()
    test_hooklib_primitives()
    test_wrapper_agnostic()
    test_vague_request_detector()
    test_rule_taxonomy_checker()
    test_contrast_table_matches_the_tokens()
    test_every_token_utility_is_registered()
    test_file_scoped_hooks_name_a_loadable_skill()
    test_agent_reference_pointers_resolve()
    test_rails_routes_checker()
    test_skill_phase_counts_match_their_agent()
    test_agents_do_not_glob_hardcoded_wrapper_dirs()
    test_agents_can_run_what_they_are_told_to_run()
    test_the_palette_recipe_produces_passing_colors()
    test_required_tags_match_the_skills_that_document_them()
    test_centrifugo_examples_use_this_clients_api()
    test_the_bundle_budget_matches_the_config_that_enforces_it()
    test_the_page_size_default_has_one_value()
    test_the_pr_size_limit_has_one_value()
    test_the_adr_template_has_one_section_set()
    test_the_error_envelope_has_one_shape()
    test_framework_skills_load_for_their_own_framework()
    test_checks_match_this_stack()
    test_gates_actually_fire_where_registered()
    test_gates_do_not_fire_on_correct_work()
    test_commit_types_match_the_skill()
    test_autoformat_never_changes_semantics()
    test_limits_match_the_skill_that_documents_them()
    test_mcp_install_gate()
    test_hook_messages_point_somewhere_real()
    test_release_hygiene_checker()
    test_configurable_at_the_edges()
    test_missing_tool_says_so_once()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
