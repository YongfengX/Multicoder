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
