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
    assert_allowed("allows safe git commands", "dangerous-command-blocker.py", "Bash",
                   {"command": "git status"})
    assert_allowed("allows npm commands", "dangerous-command-blocker.py", "Bash",
                   {"command": "npm run test"})
    assert_allowed("skips non-Bash tools", "dangerous-command-blocker.py", "Read",
                   {"file_path": "/etc/passwd"})


def test_migration_validator():
    print("\n[migration-validator.py]")
    assert_warns("warns on up without down", "migration-validator.py", "Write", {
        "file_path": "db/migrate/20240101_add_column.rb",
        "content": "class AddColumn < ActiveRecord::Migration\n  def up\n    add_column :users, :age, :integer\n  end\nend"
    })
    assert_warns("warns on remove_column in change", "migration-validator.py", "Write", {
        "file_path": "db/migrate/20240102_remove_field.rb",
        "content": "class RemoveField < ActiveRecord::Migration\n  def change\n    remove_column :users, :legacy_field\n  end\nend"
    })
    assert_warns("warns on SQL interpolation", "migration-validator.py", "Write", {
        "file_path": "db/migrate/20240103_custom.rb",
        "content": 'class Custom < ActiveRecord::Migration\n  def up\n    execute "UPDATE users SET name = \'#{value}\'"\n  end\nend'
    })
    assert_allowed("allows safe migration", "migration-validator.py", "Write", {
        "file_path": "db/migrate/20240104_safe.rb",
        "content": "class Safe < ActiveRecord::Migration\n  def change\n    add_column :users, :nickname, :string\n  end\nend"
    })
    assert_allowed("skips non-migration files", "migration-validator.py", "Write", {
        "file_path": "app/models/user.rb",
        "content": "class User < ApplicationRecord\nend"
    })


def test_deployment_gate():
    print("\n[deployment-gate.py]")
    assert_warns("warns on git push to main", "deployment-gate.py", "Bash",
                 {"command": "git push origin main"})
    assert_warns("warns on force push", "deployment-gate.py", "Bash",
                 {"command": "git push -f origin feature"})
    assert_warns("warns on terraform apply", "deployment-gate.py", "Bash",
                 {"command": "terraform apply -auto-approve"})
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
                  {"file_path": "app/models/user.rb"})
    assert_silent("skips Python files", "accessibility-checker.py", "Edit",
                  {"file_path": ".claude/hooks/test-runner.py"})
    assert_silent("skips tsx outside web/next/frontend", "accessibility-checker.py", "Edit",
                  {"file_path": "src/components/Button.tsx"})
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
                  {"file_path": "app/models/user.rb"})
    assert_silent("skips view files", "api-design-checker.py", "Edit",
                  {"file_path": "web/src/components/Button.tsx"})
    assert_silent("skips empty input", "api-design-checker.py", "Edit",
                  {"file_path": ""})

    # --- Warnings on matching files ---
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    ctrl_dir = os.path.join(tmpdir, "app", "controllers")
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

    # Test: POST create returning 200
    post_file = os.path.join(ctrl_dir, "items_controller.rb")
    with open(post_file, "w") as f:
        f.write("def create\n  item = Item.create!(params)\n  render json: item, status: :ok\nend\n")
    assert_output_contains("warns on POST returning 200", "api-design-checker.py", "Edit",
                           {"file_path": post_file}, "201")

    # Test: JS API unwrapped array
    api_dir = os.path.join(tmpdir, "src", "api")
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

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
