import json
import os
import tempfile
import shutil
import pytest
from multicoder.session import Session


def test_session_create():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude", "executors": {"code": "codex-cli"}}
        )
        assert session.session_id == "2026-04-14-test"
        assert session.state["status"] == "in_progress"
        assert session.state["current_phase"] == "analyze"
        state_path = os.path.join(tmpdir, "2026-04-14-test", "state.json")
        assert os.path.exists(state_path)


def test_session_update_phase():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude"}
        )
        session.update(current_phase="code", current_task_id=1)
        assert session.state["current_phase"] == "code"
        assert session.state["current_task_id"] == 1

        reloaded = Session.load(tmpdir, "2026-04-14-test")
        assert reloaded.state["current_phase"] == "code"


def test_session_complete_task():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude"}
        )
        session.complete_task(1)
        session.complete_task(2)
        assert session.state["completed_tasks"] == [1, 2]


def test_session_load_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError):
            Session.load(tmpdir, "nonexistent-session")


def test_session_write_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude"}
        )
        session.write_artifact("01-analysis.md", "# Analysis\nThis is the analysis.")
        artifact_path = os.path.join(tmpdir, "2026-04-14-test", "01-analysis.md")
        assert os.path.exists(artifact_path)
        with open(artifact_path) as f:
            assert "This is the analysis" in f.read()


def test_session_read_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude"}
        )
        session.write_artifact("01-analysis.md", "hello")
        content = session.read_artifact("01-analysis.md")
        assert content == "hello"


def test_session_read_missing_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude"}
        )
        with pytest.raises(FileNotFoundError):
            session.read_artifact("nonexistent.md")


def test_session_log_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session.create(
            base_dir=tmpdir,
            session_id="2026-04-14-test",
            config_snapshot={"thinker": "claude"}
        )
        session.log_fallback(task_id=1, primary="codex-cli", used="qwen", reason="rate_limit")
        logs = session.state["fallback_log"]
        assert len(logs) == 1
        assert logs[0]["primary"] == "codex-cli"
        assert logs[0]["used"] == "qwen"
