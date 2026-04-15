# Multicoder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill + Python orchestration script that coordinates multiple AI models (thinker for decisions, executors for code/review) with fallback chains, session persistence, and resume capability.

**Architecture:** A `/multicoder` skill drives the thinker layer (decision-making) within the LLM session. A `multicoder.py` Python script acts as a stateless executor — it calls external models via CLI or API, writes results to files, and manages session state. All context passes through files in `docs/multicoder/sessions/`.

**Tech Stack:** Python 3.11+, `requests` (HTTP API calls), `argparse` (CLI), Claude Code skill (markdown-based)

---

## File Structure

```
multicoder/
├── multicoder.py                  # Main orchestration script
├── multicoder/                    # Python package
│   ├── __init__.py
│   ├── config.py                  # Load & validate .multicoder.json
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract provider interface
│   │   ├── cli_provider.py       # CLI provider (codex exec)
│   │   └── api_provider.py       # HTTP API provider (minimax, qwen, etc.)
│   ├── session.py                # Session state management (state.json)
│   └── fallback.py               # Fallback chain logic with retries
├── skills/
│   └── multicoder/
│       └── SKILL.md              # Claude Code skill definition
├── tests/
│   ├── test_config.py
│   ├── test_providers.py
│   ├── test_session.py
│   └── test_fallback.py
├── .multicoder.json              # Default config (example/template)
├── requirements.txt
└── README.md                     # Already written
```

---

### Task 1: Project scaffolding & config loader

**Files:**
- Create: `multicoder/__init__.py`
- Create: `multicoder/config.py`
- Create: `tests/test_config.py`
- Create: `.multicoder.json`
- Create: `requirements.txt`

- [ ] **Step 1: Write the failing test for config loading**

```python
# tests/test_config.py
import json
import os
import tempfile
import pytest
from multicoder.config import load_config, ConfigError


def test_load_config_from_file():
    config_data = {
        "thinker": "claude",
        "executors": {
            "code": "codex-cli",
            "code_fallback": ["qwen"],
            "review": "minimax",
            "review_fallback": ["qwen"],
            "default": "codex-cli",
            "default_fallback": ["qwen"]
        },
        "max_review_cycles": 3,
        "output_dir": "docs/multicoder",
        "providers": {
            "claude": {"type": "current"},
            "codex-cli": {"type": "cli", "command": "codex"},
            "minimax": {
                "type": "api",
                "base_url": "https://api.minimax.chat/v1",
                "model": "minimax-m1",
                "api_key_env": "MINIMAX_API_KEY"
            },
            "qwen": {
                "type": "api",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen-plus",
                "api_key_env": "DASHSCOPE_API_KEY"
            }
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        config = load_config(f.name)

    assert config["thinker"] == "claude"
    assert config["executors"]["code"] == "codex-cli"
    assert config["executors"]["code_fallback"] == ["qwen"]
    assert config["max_review_cycles"] == 3
    assert config["providers"]["minimax"]["type"] == "api"
    os.unlink(f.name)


def test_load_config_missing_file():
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/.multicoder.json")


def test_load_config_missing_required_fields():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"thinker": "claude"}, f)
        f.flush()
        with pytest.raises(ConfigError, match="executors"):
            load_config(f.name)
    os.unlink(f.name)


def test_load_config_with_runtime_overrides():
    config_data = {
        "thinker": "claude",
        "executors": {
            "code": "codex-cli",
            "review": "minimax",
            "default": "codex-cli"
        },
        "max_review_cycles": 3,
        "output_dir": "docs/multicoder",
        "providers": {
            "claude": {"type": "current"},
            "codex-cli": {"type": "cli", "command": "codex"},
            "minimax": {"type": "api", "base_url": "https://api.minimax.chat/v1", "model": "minimax-m1", "api_key_env": "MINIMAX_API_KEY"},
            "qwen": {"type": "api", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "api_key_env": "DASHSCOPE_API_KEY"}
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        config = load_config(f.name, overrides={"code": "qwen", "thinker": "qwen"})

    assert config["executors"]["code"] == "qwen"
    assert config["thinker"] == "qwen"
    # original review unchanged
    assert config["executors"]["review"] == "minimax"
    os.unlink(f.name)


def test_load_config_unknown_provider_in_override():
    config_data = {
        "thinker": "claude",
        "executors": {"code": "codex-cli", "review": "minimax", "default": "codex-cli"},
        "max_review_cycles": 3,
        "output_dir": "docs/multicoder",
        "providers": {"claude": {"type": "current"}, "codex-cli": {"type": "cli", "command": "codex"}}
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        with pytest.raises(ConfigError, match="unknown provider"):
            load_config(f.name, overrides={"code": "nonexistent"})
    os.unlink(f.name)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'multicoder'`

- [ ] **Step 3: Create package init and requirements.txt**

```python
# multicoder/__init__.py
```

```
# requirements.txt
requests>=2.28.0
```

- [ ] **Step 4: Implement config loader**

```python
# multicoder/config.py
import json
import copy
from pathlib import Path


class ConfigError(Exception):
    pass


REQUIRED_FIELDS = ["thinker", "executors", "providers"]
REQUIRED_EXECUTOR_FIELDS = ["default"]


def load_config(path: str, overrides: dict | None = None) -> dict:
    """Load and validate .multicoder.json, optionally applying runtime overrides."""
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config: {e}")

    # Validate required top-level fields
    for field in REQUIRED_FIELDS:
        if field not in config:
            raise ConfigError(f"Missing required field: {field}")

    # Validate executors has at least 'default'
    executors = config.get("executors", {})
    if "default" not in executors:
        raise ConfigError(f"Missing required field in executors: default")

    # Set defaults
    config.setdefault("max_review_cycles", 3)
    config.setdefault("output_dir", "docs/multicoder")

    # Apply runtime overrides
    if overrides:
        config = _apply_overrides(config, overrides)

    return config


def _apply_overrides(config: dict, overrides: dict) -> dict:
    """Apply runtime overrides like --code=qwen, --review=claude, --thinker=qwen."""
    config = copy.deepcopy(config)
    providers = config.get("providers", {})

    for key, provider_name in overrides.items():
        if provider_name not in providers:
            raise ConfigError(f"Runtime override references unknown provider: {provider_name}")
        if key == "thinker":
            config["thinker"] = provider_name
        elif key in ("code", "review", "default"):
            config["executors"][key] = provider_name

    return config


def get_provider_config(config: dict, provider_name: str) -> dict:
    """Get the provider configuration by name."""
    providers = config.get("providers", {})
    if provider_name not in providers:
        raise ConfigError(f"Unknown provider: {provider_name}")
    return providers[provider_name]


def get_executor_for_task(config: dict, task_type: str) -> str:
    """Get the executor provider name for a given task type (code, review, etc.)."""
    executors = config.get("executors", {})
    return executors.get(task_type, executors.get("default"))


def get_fallback_chain(config: dict, task_type: str) -> list[str]:
    """Get the fallback chain for a task type. Returns [primary, fallback1, fallback2, ...]."""
    executors = config.get("executors", {})
    primary = executors.get(task_type, executors.get("default"))
    fallback_key = f"{task_type}_fallback"
    fallbacks = executors.get(fallback_key, executors.get("default_fallback", []))
    return [primary] + fallbacks
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Create the default .multicoder.json**

```json
{
  "thinker": "claude",
  "executors": {
    "code": "codex-cli",
    "code_fallback": ["qwen", "dashscope"],
    "review": "minimax",
    "review_fallback": ["qwen"],
    "default": "codex-cli",
    "default_fallback": ["qwen"]
  },
  "max_review_cycles": 3,
  "output_dir": "docs/multicoder",
  "providers": {
    "claude": {
      "type": "current"
    },
    "codex-cli": {
      "type": "cli",
      "command": "codex"
    },
    "minimax": {
      "type": "api",
      "base_url": "https://api.minimax.chat/v1",
      "model": "minimax-m1",
      "api_key_env": "MINIMAX_API_KEY"
    },
    "qwen": {
      "type": "api",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-plus",
      "api_key_env": "DASHSCOPE_API_KEY"
    },
    "dashscope": {
      "type": "api",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-max",
      "api_key_env": "DASHSCOPE_API_KEY"
    }
  }
}
```

- [ ] **Step 7: Commit**

```bash
git add multicoder/__init__.py multicoder/config.py tests/test_config.py .multicoder.json requirements.txt
git commit -m "feat: add config loader with validation and runtime overrides"
```

---

### Task 2: Provider base class and CLI provider

**Files:**
- Create: `multicoder/providers/__init__.py`
- Create: `multicoder/providers/base.py`
- Create: `multicoder/providers/cli_provider.py`
- Create: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test for CLI provider**

```python
# tests/test_providers.py
import os
import tempfile
import pytest
from multicoder.providers.base import ProviderError
from multicoder.providers.cli_provider import CLIProvider


def test_cli_provider_run_success():
    """Test CLI provider with a simple echo command as stand-in."""
    provider = CLIProvider(command="echo", timeout=30)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as task_f:
        task_f.write("hello world")
        task_f.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as out_f:
            provider.run(task_file=task_f.name, output_file=out_f.name)
            with open(out_f.name) as f:
                result = f.read()
            assert "hello world" in result
    os.unlink(task_f.name)
    os.unlink(out_f.name)


def test_cli_provider_command_not_found():
    provider = CLIProvider(command="nonexistent_cmd_12345", timeout=10)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as task_f:
        task_f.write("test")
        task_f.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as out_f:
            with pytest.raises(ProviderError, match="failed"):
                provider.run(task_file=task_f.name, output_file=out_f.name)
    os.unlink(task_f.name)
    os.unlink(out_f.name)


def test_cli_provider_timeout():
    provider = CLIProvider(command="sleep", timeout=1)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as task_f:
        task_f.write("10")  # sleep 10 should timeout
        task_f.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as out_f:
            with pytest.raises(ProviderError, match="timed out"):
                provider.run(task_file=task_f.name, output_file=out_f.name)
    os.unlink(task_f.name)
    os.unlink(out_f.name)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_providers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'multicoder.providers'`

- [ ] **Step 3: Implement provider base class**

```python
# multicoder/providers/__init__.py
```

```python
# multicoder/providers/base.py
from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider call fails."""
    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = transient


class BaseProvider(ABC):
    @abstractmethod
    def run(self, task_file: str, output_file: str) -> None:
        """Read instructions from task_file, execute, write result to output_file.

        Raises ProviderError on failure. Set transient=True for retryable errors.
        """
        pass
```

- [ ] **Step 4: Implement CLI provider**

```python
# multicoder/providers/cli_provider.py
import subprocess
from pathlib import Path
from .base import BaseProvider, ProviderError


class CLIProvider(BaseProvider):
    def __init__(self, command: str, timeout: int = 300):
        self.command = command
        self.timeout = timeout

    def run(self, task_file: str, output_file: str) -> None:
        task_content = Path(task_file).read_text()

        # For codex, use: codex exec "prompt"
        # For generic CLI, pass content as argument
        if self.command == "codex":
            cmd = ["codex", "exec", task_content]
        else:
            cmd = [self.command, task_content]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
        except FileNotFoundError:
            raise ProviderError(f"CLI command failed: '{self.command}' not found", transient=False)
        except subprocess.TimeoutExpired:
            raise ProviderError(
                f"CLI command timed out after {self.timeout}s: {self.command}",
                transient=True
            )

        if result.returncode != 0:
            raise ProviderError(
                f"CLI command failed (exit {result.returncode}): {result.stderr[:500]}",
                transient=True
            )

        Path(output_file).write_text(result.stdout)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_providers.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add multicoder/providers/__init__.py multicoder/providers/base.py multicoder/providers/cli_provider.py tests/test_providers.py
git commit -m "feat: add provider base class and CLI provider with timeout support"
```

---

### Task 3: API provider

**Files:**
- Create: `multicoder/providers/api_provider.py`
- Modify: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test for API provider**

Append to `tests/test_providers.py`:

```python
import json
from unittest.mock import patch, MagicMock
from multicoder.providers.api_provider import APIProvider


def test_api_provider_success():
    provider = APIProvider(
        base_url="https://api.example.com/v1",
        model="test-model",
        api_key="test-key"
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "reviewed code looks good"}}]
    }

    with patch("multicoder.providers.api_provider.requests.post", return_value=mock_response):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as task_f:
            task_f.write("Review this code for bugs")
            task_f.flush()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as out_f:
                provider.run(task_file=task_f.name, output_file=out_f.name)
                result = open(out_f.name).read()
                assert "reviewed code looks good" in result
        os.unlink(task_f.name)
        os.unlink(out_f.name)


def test_api_provider_rate_limit():
    provider = APIProvider(
        base_url="https://api.example.com/v1",
        model="test-model",
        api_key="test-key"
    )
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "rate limit exceeded"

    with patch("multicoder.providers.api_provider.requests.post", return_value=mock_response):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as task_f:
            task_f.write("test")
            task_f.flush()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as out_f:
                with pytest.raises(ProviderError) as exc_info:
                    provider.run(task_file=task_f.name, output_file=out_f.name)
                assert exc_info.value.transient is True
        os.unlink(task_f.name)
        os.unlink(out_f.name)


def test_api_provider_auth_error():
    provider = APIProvider(
        base_url="https://api.example.com/v1",
        model="test-model",
        api_key="bad-key"
    )
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "unauthorized"

    with patch("multicoder.providers.api_provider.requests.post", return_value=mock_response):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as task_f:
            task_f.write("test")
            task_f.flush()
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as out_f:
                with pytest.raises(ProviderError) as exc_info:
                    provider.run(task_file=task_f.name, output_file=out_f.name)
                assert exc_info.value.transient is False
        os.unlink(task_f.name)
        os.unlink(out_f.name)


def test_api_provider_missing_api_key():
    with pytest.raises(ProviderError, match="API key"):
        APIProvider(
            base_url="https://api.example.com/v1",
            model="test-model",
            api_key=None
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_providers.py::test_api_provider_success -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'multicoder.providers.api_provider'`

- [ ] **Step 3: Implement API provider**

```python
# multicoder/providers/api_provider.py
import requests
from pathlib import Path
from .base import BaseProvider, ProviderError

# HTTP status codes
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
NON_TRANSIENT_STATUS_CODES = {400, 401, 403}


class APIProvider(BaseProvider):
    def __init__(self, base_url: str, model: str, api_key: str | None, timeout: int = 120):
        if not api_key:
            raise ProviderError("API key is required but not provided", transient=False)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def run(self, task_file: str, output_file: str) -> None:
        task_content = Path(task_file).read_text()

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": task_content}]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise ProviderError(
                f"API request timed out after {self.timeout}s: {self.base_url}",
                transient=True
            )
        except requests.exceptions.ConnectionError:
            raise ProviderError(
                f"Connection error: {self.base_url}",
                transient=True
            )

        if response.status_code in TRANSIENT_STATUS_CODES:
            raise ProviderError(
                f"API error {response.status_code}: {response.text[:300]}",
                transient=True
            )

        if response.status_code in NON_TRANSIENT_STATUS_CODES:
            raise ProviderError(
                f"API error {response.status_code}: {response.text[:300]}",
                transient=False
            )

        if response.status_code != 200:
            raise ProviderError(
                f"Unexpected API status {response.status_code}: {response.text[:300]}",
                transient=False
            )

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        Path(output_file).write_text(content)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_providers.py -v`
Expected: All 7 tests PASS (3 CLI + 4 API)

- [ ] **Step 5: Commit**

```bash
git add multicoder/providers/api_provider.py tests/test_providers.py
git commit -m "feat: add API provider with transient/non-transient error classification"
```

---

### Task 4: Fallback chain with retries

**Files:**
- Create: `multicoder/fallback.py`
- Create: `tests/test_fallback.py`

- [ ] **Step 1: Write the failing test for fallback logic**

```python
# tests/test_fallback.py
import pytest
from unittest.mock import MagicMock, call
from multicoder.providers.base import ProviderError
from multicoder.fallback import run_with_fallback


def _make_provider(side_effect=None):
    p = MagicMock()
    if side_effect:
        p.run.side_effect = side_effect
    return p


def test_fallback_primary_succeeds():
    primary = _make_provider()
    fallback1 = _make_provider()
    run_with_fallback(
        providers=[("primary", primary), ("fallback1", fallback1)],
        task_file="task.md",
        output_file="out.md",
        max_retries=3
    )
    primary.run.assert_called_once_with(task_file="task.md", output_file="out.md")
    fallback1.run.assert_not_called()


def test_fallback_primary_fails_fallback_succeeds():
    primary = _make_provider(side_effect=ProviderError("rate limit", transient=True))
    fallback1 = _make_provider()
    used = run_with_fallback(
        providers=[("primary", primary), ("fallback1", fallback1)],
        task_file="task.md",
        output_file="out.md",
        max_retries=1
    )
    assert used == "fallback1"
    fallback1.run.assert_called_once()


def test_fallback_non_transient_skips_retries():
    primary = _make_provider(side_effect=ProviderError("auth error", transient=False))
    fallback1 = _make_provider()
    used = run_with_fallback(
        providers=[("primary", primary), ("fallback1", fallback1)],
        task_file="task.md",
        output_file="out.md",
        max_retries=3
    )
    # Non-transient: should NOT retry primary, should go straight to fallback
    assert primary.run.call_count == 1
    assert used == "fallback1"


def test_fallback_all_fail():
    primary = _make_provider(side_effect=ProviderError("fail1", transient=True))
    fallback1 = _make_provider(side_effect=ProviderError("fail2", transient=True))
    with pytest.raises(ProviderError, match="All providers failed"):
        run_with_fallback(
            providers=[("primary", primary), ("fallback1", fallback1)],
            task_file="task.md",
            output_file="out.md",
            max_retries=1
        )


def test_fallback_retries_transient_before_moving_on():
    call_count = 0
    def fail_twice_then_succeed(task_file, output_file):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ProviderError("transient", transient=True)
        # success on third call

    primary = _make_provider()
    primary.run.side_effect = fail_twice_then_succeed
    fallback1 = _make_provider()

    used = run_with_fallback(
        providers=[("primary", primary), ("fallback1", fallback1)],
        task_file="task.md",
        output_file="out.md",
        max_retries=3
    )
    assert used == "primary"
    assert primary.run.call_count == 3
    fallback1.run.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_fallback.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'multicoder.fallback'`

- [ ] **Step 3: Implement fallback chain**

```python
# multicoder/fallback.py
import time
from multicoder.providers.base import BaseProvider, ProviderError


def run_with_fallback(
    providers: list[tuple[str, BaseProvider]],
    task_file: str,
    output_file: str,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> str:
    """Try providers in order with retries. Returns the name of the provider that succeeded.

    For transient errors: retry up to max_retries times with exponential backoff.
    For non-transient errors: skip to next provider immediately.
    If all providers fail: raise ProviderError.
    """
    errors = []

    for provider_name, provider in providers:
        attempt = 0
        while attempt < max_retries:
            try:
                provider.run(task_file=task_file, output_file=output_file)
                return provider_name
            except ProviderError as e:
                errors.append((provider_name, attempt + 1, str(e)))
                if not e.transient:
                    break  # non-transient, skip to next provider
                attempt += 1
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** (attempt - 1)))

    error_summary = "; ".join(f"{name}(attempt {a}): {msg}" for name, a, msg in errors)
    raise ProviderError(f"All providers failed. {error_summary}", transient=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_fallback.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add multicoder/fallback.py tests/test_fallback.py
git commit -m "feat: add fallback chain with exponential backoff retries"
```

---

### Task 5: Session state management

**Files:**
- Create: `multicoder/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write the failing test for session management**

```python
# tests/test_session.py
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
        # state.json should exist on disk
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

        # Verify persisted to disk
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_session.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'multicoder.session'`

- [ ] **Step 3: Implement session manager**

```python
# multicoder/session.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_session.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add multicoder/session.py tests/test_session.py
git commit -m "feat: add session state management with artifact read/write and fallback logging"
```

---

### Task 6: Main CLI entry point (multicoder.py)

**Files:**
- Create: `multicoder.py` (project root)

- [ ] **Step 1: Write the failing test**

Append a new test file:

```python
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
        # Write a dummy artifact
        with open(os.path.join(session_dir, "01-analysis.md"), "w") as f:
            f.write("x" * 1000)

        # Need a minimal config
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_cli.py -v`
Expected: FAIL — file `multicoder.py` doesn't exist or missing subcommand handling

- [ ] **Step 3: Implement multicoder.py CLI**

```python
#!/usr/bin/env python3
# multicoder.py — Stateless executor for the Multicoder skill.
# Called by the Claude Code skill via Bash. Does NOT make decisions.

import argparse
import os
import sys
from pathlib import Path

from multicoder.config import load_config, get_provider_config, get_fallback_chain, ConfigError
from multicoder.providers.cli_provider import CLIProvider
from multicoder.providers.api_provider import APIProvider
from multicoder.providers.base import ProviderError
from multicoder.fallback import run_with_fallback
from multicoder.session import Session


def build_provider(provider_name: str, config: dict):
    """Instantiate a provider from config."""
    pconfig = get_provider_config(config, provider_name)
    ptype = pconfig["type"]

    if ptype == "current":
        raise ConfigError(
            f"Provider '{provider_name}' has type 'current' and cannot be called externally. "
            "It should be handled by the skill layer, not multicoder.py."
        )
    elif ptype == "cli":
        return CLIProvider(
            command=pconfig["command"],
            timeout=pconfig.get("timeout", 300)
        )
    elif ptype == "api":
        api_key_env = pconfig.get("api_key_env", "")
        api_key = os.environ.get(api_key_env)
        return APIProvider(
            base_url=pconfig["base_url"],
            model=pconfig["model"],
            api_key=api_key,
            timeout=pconfig.get("timeout", 120)
        )
    else:
        raise ConfigError(f"Unknown provider type: {ptype}")


def cmd_exec(args, config):
    """Execute a coding or review task with fallback."""
    session = Session.load(config["output_dir"], args.session)
    chain_names = get_fallback_chain(config, args.task_type or "code")

    providers = []
    skipped = []
    for name in chain_names:
        try:
            providers.append((name, build_provider(name, config)))
        except (ProviderError, ConfigError) as e:
            skipped.append((name, str(e)))

    if not providers:
        print(f"ERROR: No usable providers. Skipped: {skipped}", file=sys.stderr)
        sys.exit(1)

    task_path = str(session.session_dir / args.task_file)
    output_path = str(session.session_dir / args.output)

    try:
        used = run_with_fallback(
            providers=providers,
            task_file=task_path,
            output_file=output_path,
            max_retries=3
        )
        if used != chain_names[0]:
            session.log_fallback(
                task_id=session.state.get("current_task_id", 0),
                primary=chain_names[0],
                used=used,
                reason="primary_failed"
            )
        print(f"OK: completed with provider '{used}'. Output: {args.output}")
    except ProviderError as e:
        session.write_artifact(args.output, f"# Error\n\n{str(e)}")
        session.update(status="error")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_context_check(args, config):
    """Report session file sizes to estimate context usage."""
    session = Session.load(config["output_dir"], args.session)
    total_bytes = 0
    files = []
    for path in sorted(session.session_dir.iterdir()):
        size = path.stat().st_size
        total_bytes += size
        files.append((path.name, size))

    print(f"Session: {args.session}")
    print(f"Total size: {total_bytes:,} bytes (~{total_bytes // 4} tokens est.)")
    print(f"Files:")
    for name, size in files:
        print(f"  {name}: {size:,} bytes")


def main():
    parser = argparse.ArgumentParser(description="Multicoder orchestration script")
    parser.add_argument("--config", default=".multicoder.json", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command")

    # exec command
    exec_parser = subparsers.add_parser("exec", help="Execute a task")
    exec_parser.add_argument("--session", required=True)
    exec_parser.add_argument("--task-file", required=True)
    exec_parser.add_argument("--provider", help="Override provider (deprecated, use --task-type)")
    exec_parser.add_argument("--task-type", default="code", help="Task type: code, review")
    exec_parser.add_argument("--output", required=True)

    # review command (shorthand for exec --task-type review)
    review_parser = subparsers.add_parser("review", help="Execute a review task")
    review_parser.add_argument("--session", required=True)
    review_parser.add_argument("--task-file", required=True)
    review_parser.add_argument("--output", required=True)

    # context-check command
    ctx_parser = subparsers.add_parser("context-check", help="Check session context size")
    ctx_parser.add_argument("--session", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        config = load_config(args.config)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "exec":
        cmd_exec(args, config)
    elif args.command == "review":
        args.task_type = "review"
        cmd_exec(args, config)
    elif args.command == "context-check":
        cmd_context_check(args, config)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/test_cli.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add multicoder.py tests/test_cli.py
git commit -m "feat: add multicoder.py CLI with exec, review, and context-check commands"
```

---

### Task 7: Claude Code skill definition

**Files:**
- Create: `skills/multicoder/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p skills/multicoder
```

- [ ] **Step 2: Write the skill definition**

```markdown
<!-- skills/multicoder/SKILL.md -->
---
name: multicoder
description: Orchestrate multiple AI models for development tasks — one thinks, others execute code and review. Use when you want to coordinate Claude (planning), Codex (coding), MiniMax/Qwen (review) on a development task.
---

# Multicoder

You are the **thinker** in a multi-model development pipeline. You make all decisions. Other models (executors) follow your instructions.

## Your Role

You handle ALL judgment work:
- Analyze requirements
- Design architecture
- Decompose into sub-tasks
- Write instructions for coders and reviewers
- Evaluate review results
- Plan fixes

You NEVER write production code yourself. You produce instruction files, and executors write code.

## Arguments

Parse the user's `/multicoder` invocation for these arguments:
- `--start-from <phase>`: Start from a specific phase (analyze, architect, decompose, code, review). Default: analyze.
- `--resume <session-id>`: Resume a saved session.
- `--code=<provider>`: Override the code executor for this run.
- `--review=<provider>`: Override the review executor for this run.
- `--thinker=<provider>`: Override the thinker for this run.
- Everything else is the task description.

## Pipeline

### Phase 1: Analyze Requirements
- Read the user's task description
- Analyze what needs to be built
- Write findings to `01-analysis.md` in the session directory
- **PAUSE**: Show analysis to user, ask for confirmation

### Phase 2: Design Architecture
- Based on the analysis, design the technical approach
- Define file structure, interfaces, data flow
- Write to `02-architecture.md`
- **PAUSE**: Show architecture to user, ask for confirmation

### Phase 3: Decompose into Sub-tasks
- Break the work into independent, ordered sub-tasks
- Define dependencies between tasks
- Write `03-tasks.json` (task list with deps) and `03-task-XX.md` (detailed instructions per task)
- **PAUSE**: Show task list to user, ask for confirmation

### Phase 4: Execute Sub-tasks (loop)

For each sub-task in dependency order:

1. **Generate coding instructions**: Write clear, specific instructions for the coder. Include:
   - Exact files to create/modify
   - Expected behavior
   - Code patterns to follow
   - Save to `XX-code-task.md`

2. **Call the coder**: Run via Bash:
   ```bash
   python3 multicoder.py exec --session <id> --task-file XX-code-task.md --task-type code --output XX-code-result.md --config .multicoder.json
   ```

3. **Generate review instructions**: Decide what the reviewer should focus on. Save to `XX-review-task.md`.

4. **Call the reviewer**: Run via Bash:
   ```bash
   python3 multicoder.py review --session <id> --task-file XX-review-task.md --output XX-review-result.md --config .multicoder.json
   ```

5. **Evaluate review results**: Read `XX-review-result.md`. Decide:
   - **PASS**: Mark task complete, move to next
   - **FAIL**: Write fix instructions to `XX-fix-task.md`, call coder again
   - Loop up to `max_review_cycles` times. If max reached, **PAUSE** and ask user.

### Phase 5: Global Review

After all sub-tasks pass:
1. Write `final-review-task.md` — comprehensive review instructions covering integration, consistency, edge cases
2. Call reviewer
3. Evaluate results — PASS means done, FAIL means fix cycle

## Session Management

- At the start, create a session: read `.multicoder.json`, create session dir under the configured `output_dir`
- Use `python3 multicoder.py context-check --session <id> --config .multicoder.json` periodically to check context size
- If context is getting large (>100k tokens estimated), save state and tell the user to start a new conversation with `--resume`

## Resuming

When `--resume <session-id>` is used:
1. Read `state.json` from the session directory
2. Read the latest artifacts to restore context
3. Continue from `current_phase` and `current_task_id`

## Starting from Mid-Point

When `--start-from <phase>` is used:
1. Validate required upstream artifacts exist
2. If missing, tell the user what's needed
3. If present, skip to the specified phase

## Rules

1. You are the thinker. NEVER write production code in your responses.
2. All instructions to executors must be written as files, then passed to `multicoder.py`.
3. Always show results to the user at checkpoints.
4. If an executor fails and fallback is used, inform the user which provider was used instead.
5. Keep instruction files specific and actionable — executors are skilled but have no context beyond what you write.
```

- [ ] **Step 3: Commit**

```bash
git add skills/multicoder/SKILL.md
git commit -m "feat: add /multicoder Claude Code skill definition"
```

---

### Task 8: Git init and initial commit

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```
# .gitignore
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
.env
docs/multicoder/sessions/
```

- [ ] **Step 2: Initialize git repo and make initial commit**

```bash
cd /Users/feierkang/Desktop/UCSD/Multicoder
git init
git add .gitignore README.md docs/superpowers/
git commit -m "docs: add project README and design spec"
```

- [ ] **Step 3: Verify repo state**

Run: `git log --oneline`
Expected: One commit with the docs

---

### Task 9: Run full test suite and verify

- [ ] **Step 1: Install dependencies**

```bash
cd /Users/feierkang/Desktop/UCSD/Multicoder
pip3 install -r requirements.txt
pip3 install pytest
```

- [ ] **Step 2: Run all tests**

Run: `cd /Users/feierkang/Desktop/UCSD/Multicoder && python3 -m pytest tests/ -v`
Expected: All tests pass (5 config + 7 provider + 5 fallback + 8 session + 2 cli = 27 tests)

- [ ] **Step 3: Final commit with all implementation**

```bash
git add -A
git commit -m "feat: implement multicoder orchestration with providers, fallback, session management, and skill"
```
