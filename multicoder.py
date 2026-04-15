#!/usr/bin/env python3
# multicoder.py — Stateless executor for the Multicoder skill.
# Called by the Claude Code skill via Bash. Does NOT make decisions.

import argparse
import os
import sys
from pathlib import Path

# Load .env file if present (optional dependency)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables directly

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

    chain_display = ", ".join(
        f"{name} ({p.model_info})" for name, p in providers
    )
    print(f"[{args.task_type}] Provider chain: {chain_display}")

    try:
        used = run_with_fallback(
            providers=providers,
            task_file=task_path,
            output_file=output_path,
            max_retries=3
        )
        used_model = next((p.model_info for name, p in providers if name == used), used)
        if used != chain_names[0]:
            session.log_fallback(
                task_id=session.state.get("current_task_id", 0),
                primary=chain_names[0],
                used=used,
                reason="primary_failed"
            )
        print(f"OK: completed with provider '{used}' (model: {used_model}). Output: {args.output}")
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
    exec_parser.add_argument("--config", default=".multicoder.json", help="Path to config file")

    # review command (shorthand for exec --task-type review)
    review_parser = subparsers.add_parser("review", help="Execute a review task")
    review_parser.add_argument("--session", required=True)
    review_parser.add_argument("--task-file", required=True)
    review_parser.add_argument("--output", required=True)
    review_parser.add_argument("--config", default=".multicoder.json", help="Path to config file")

    # context-check command
    ctx_parser = subparsers.add_parser("context-check", help="Check session context size")
    ctx_parser.add_argument("--session", required=True)
    ctx_parser.add_argument("--config", default=".multicoder.json", help="Path to config file")

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
