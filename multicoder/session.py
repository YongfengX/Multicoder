import json
from datetime import datetime, timezone
from pathlib import Path


class Session:
    def __init__(self, session_dir: Path, state: dict):
        self.session_dir = session_dir
        self.state = state
        self.session_id = state["session_id"]

    @classmethod
    def create(cls, base_dir: str, session_id: str, config_snapshot: dict) -> "Session":
        session_dir = Path(base_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()
        state = {
            "session_id": session_id,
            "status": "in_progress",
            "current_phase": "analyze",
            "current_task_id": None,
            "review_cycle": 0,
            "completed_tasks": [],
            "fallback_log": [],
            "config_snapshot": config_snapshot,
            "created_at": now,
            "updated_at": now
        }

        session = cls(session_dir, state)
        session._save()
        return session

    @classmethod
    def load(cls, base_dir: str, session_id: str) -> "Session":
        session_dir = Path(base_dir) / session_id
        state_path = session_dir / "state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        with open(state_path) as f:
            state = json.load(f)

        return cls(session_dir, state)

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            self.state[key] = value
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def complete_task(self, task_id: int) -> None:
        if task_id not in self.state["completed_tasks"]:
            self.state["completed_tasks"].append(task_id)
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def log_fallback(self, task_id: int, primary: str, used: str, reason: str) -> None:
        self.state["fallback_log"].append({
            "task_id": task_id,
            "primary": primary,
            "failed": True,
            "used": used,
            "reason": reason
        })
        self._save()

    def write_artifact(self, filename: str, content: str) -> None:
        path = self.session_dir / filename
        path.write_text(content)

    def read_artifact(self, filename: str) -> str:
        path = self.session_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {filename}")
        return path.read_text()

    def artifact_exists(self, filename: str) -> bool:
        return (self.session_dir / filename).exists()

    def _save(self) -> None:
        state_path = self.session_dir / "state.json"
        with open(state_path, "w") as f:
            json.dump(self.state, f, indent=2)
