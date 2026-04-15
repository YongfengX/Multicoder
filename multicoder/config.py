import json
import copy
from pathlib import Path


class ConfigError(Exception):
    pass


REQUIRED_FIELDS = ["thinker", "executors", "providers"]
REQUIRED_EXECUTOR_FIELDS = ["default"]

GLOBAL_CONFIG_PATH = Path.home() / ".multicoder.json"
LOCAL_CONFIG_NAME = ".multicoder.json"


def resolve_config_path(explicit_path: str | None = None) -> Path:
    """Resolve config path: explicit > local project > global ~/.multicoder.json"""
    if explicit_path and explicit_path != LOCAL_CONFIG_NAME:
        # User explicitly passed a non-default path — must exist
        p = Path(explicit_path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {explicit_path}")
        return p

    local = Path.cwd() / LOCAL_CONFIG_NAME
    if local.exists():
        return local

    if GLOBAL_CONFIG_PATH.exists():
        return GLOBAL_CONFIG_PATH

    raise ConfigError(
        f"No config found. Tried:\n"
        f"  {local}\n"
        f"  {GLOBAL_CONFIG_PATH}\n\n"
        f"Run: cp ~/.local/lib/multicoder/.multicoder.json ~/.multicoder.json\n"
        f"Or:  cp ~/.local/lib/multicoder/.multicoder.json ./.multicoder.json"
    )


def load_config(path: str = LOCAL_CONFIG_NAME, overrides: dict | None = None) -> dict:
    """Load and validate config, optionally applying runtime overrides.

    Config resolution order:
    1. Explicit path (if provided and not the default sentinel)
    2. ./.multicoder.json (project-level)
    3. ~/.multicoder.json (global)
    """
    config_path = resolve_config_path(path)

    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config ({config_path}): {e}")

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
