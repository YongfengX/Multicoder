# tests/test_cli.py
import os
import json
import tempfile
import subprocess
import sys


def test_cli_exec_missing_config():
    """multicoder.py should error when config is missing."""
    result = subprocess.run(
        [sys.executable, "multicoder.py", "exec",
         "--session", "test-session",
         "--task-file", "task.md",
         "--provider", "codex-cli",
         "--output", "out.md",
         "--config", "/nonexistent/.multicoder.json"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    assert result.returncode != 0
    assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()


def test_cli_context_check():
    """context-check should report session file sizes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = os.path.join(tmpdir, "test-session")
        os.makedirs(session_dir)
        state = {
            "session_id": "test-session",
            "status": "in_progress",
            "current_phase": "code",
            "current_task_id": 1,
            "review_cycle": 0,
            "completed_tasks": [],
            "fallback_log": [],
            "config_snapshot": {},
            "created_at": "2026-04-14T00:00:00Z",
            "updated_at": "2026-04-14T00:00:00Z"
        }
        with open(os.path.join(session_dir, "state.json"), "w") as f:
            json.dump(state, f)
        with open(os.path.join(session_dir, "01-analysis.md"), "w") as f:
            f.write("x" * 1000)

        config_path = os.path.join(tmpdir, ".multicoder.json")
        config = {
            "thinker": "claude",
            "executors": {"default": "codex-cli"},
            "providers": {"claude": {"type": "current"}, "codex-cli": {"type": "cli", "command": "codex"}},
            "output_dir": tmpdir
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        result = subprocess.run(
            [sys.executable, "multicoder.py", "context-check",
             "--session", "test-session",
             "--config", config_path],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "test-session" in result.stdout
