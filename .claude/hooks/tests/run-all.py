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


def main():
    print("=" * 60)
    print("Hook Test Harness")
    print("=" * 60)

    test_dangerous_command_blocker()
    test_migration_validator()
    test_deployment_gate()
    test_pre_commit_check()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
