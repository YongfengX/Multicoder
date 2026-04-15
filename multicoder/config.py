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

    for field in REQUIRED_FIELDS:
        if field not in config:
            raise ConfigError(f"Missing required field: {field}")

    executors = config.get("executors", {})
    if "default" not in executors:
        raise ConfigError(f"Missing required field in executors: default")

    config.setdefault("max_review_cycles", 3)
    config.setdefault("output_dir", "docs/multicoder")

    if overrides:
        config = _apply_overrides(config, overrides)

    return config


def _apply_overrides(config: dict, overrides: dict) -> dict:
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
    providers = config.get("providers", {})
    if provider_name not in providers:
        raise ConfigError(f"Unknown provider: {provider_name}")
    return providers[provider_name]


def get_executor_for_task(config: dict, task_type: str) -> str:
    executors = config.get("executors", {})
    return executors.get(task_type, executors.get("default"))


def get_fallback_chain(config: dict, task_type: str) -> list[str]:
    executors = config.get("executors", {})
    primary = executors.get(task_type, executors.get("default"))
    fallback_key = f"{task_type}_fallback"
    fallbacks = executors.get(fallback_key, executors.get("default_fallback", []))
    return [primary] + fallbacks
