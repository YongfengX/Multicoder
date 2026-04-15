# Multicoder Design Spec

## Overview

Multicoder is a Claude Code skill + Python orchestration script that coordinates multiple AI models to collaboratively complete development tasks. It enforces a strict separation between a "thinker" layer (decision-making) and an "executor" layer (task execution), ensuring that the model analyzing the task never writes code, and the model writing code never makes architectural decisions.

## Core Principles

1. **Thinker-Executor separation** — The thinker handles all decisions (requirements analysis, architecture design, task decomposition, review strategy, fix planning). Executors only follow instructions.
2. **Configurable roles** — Both thinker and executors are configurable. No model is hardcoded.
3. **Per-task review** — Each coding sub-task is reviewed immediately after completion, not batched.
4. **Mandatory global review** — After all sub-tasks pass, a final global review checks overall integration.
5. **File-based context passing** — All intermediate outputs are written to files. No in-memory state passing between models.
6. **Context-aware sessions** — When context is near capacity, the session can be saved and resumed in a new conversation.
7. **Semi-automatic with checkpoints** — The pipeline flows automatically but pauses at key checkpoints for user confirmation.

## Architecture

### Two-Layer Model

```
┌─────────────────────────────────────────────┐
│  Thinker Layer (configurable, default: Claude) │
│  - Analyze requirements                       │
│  - Design architecture                        │
│  - Decompose into sub-tasks                   │
│  - Decide review strategy                     │
│  - Interpret review results                   │
│  - Plan fixes                                 │
│  - All "judgment" work                        │
└──────────────────┬──────────────────────────┘
                   ↓ instruction files
┌──────────────────┴──────────────────────────┐
│  Executor Layer (configurable per task type)  │
│  - code: write/modify code (default: Codex)   │
│  - review: audit code (default: MiniMax)       │
└───────────────────────────────────────────────┘
```

### Components

1. **`/multicoder` skill** — Entry point. Drives the thinker within the current LLM session. Displays results, handles user confirmations, invokes the Python script for executor tasks.

2. **`multicoder.py`** — Orchestration script. Does NOT think. Responsibilities:
   - Call executor models (CLI or API) with instruction files
   - Write results back to files
   - Manage session state (update `state.json`)
   - Estimate context usage and warn when nearing capacity

3. **`.multicoder.json`** — Project-level configuration file.

4. **`docs/multicoder/sessions/<session-id>/`** — Per-session output directory for all intermediate artifacts.

## Configuration

### `.multicoder.json`

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

### Provider Types

| Type | Description | How it's called |
|------|-------------|-----------------|
| `current` | The current LLM session | No external call; the skill itself handles it. Only valid when the model running the skill IS the configured provider (e.g., thinker=claude while running in Claude Code). If thinker is set to a non-current provider, it is called via `cli` or `api` through `multicoder.py`, same as executors. |
| `cli` | A locally installed CLI tool | `Bash` tool runs the command (e.g., `codex`) |
| `api` | HTTP API with API key | `multicoder.py` sends HTTP requests |

### Runtime Overrides

Users can override executor assignments at invocation time:

- `/multicoder --code=qwen` — use Qwen for coding this run
- `/multicoder --review=claude` — use Claude for review this run
- `/multicoder --thinker=qwen` — use Qwen as thinker this run

## Workflow

### Full Pipeline

```
1. thinker: Analyze requirements
      → writes 01-analysis.md
      → PAUSE: user confirms

2. thinker: Design architecture
      → writes 02-architecture.md
      → PAUSE: user confirms

3. thinker: Decompose into sub-tasks
      → writes 03-tasks.json + 03-task-XX.md per task
      → PAUSE: user confirms task list

4. For each sub-task (respecting dependency order):
   a. thinker: Generate coding instructions
         → writes XX-code-task.md
   b. executor(code): Execute coding instructions
         → writes XX-code-result.md
   c. thinker: Generate review instructions
         → writes XX-review-task.md
   d. executor(review): Execute review
         → writes XX-review-result.md
   e. thinker: Evaluate review results
         → PASS: move to next sub-task
         → FAIL: generate fix instructions → XX-fix-task.md
   f. executor(code): Execute fix
         → writes XX-fix-result.md
   g. Loop (c)-(f) up to max_review_cycles times
   h. If max cycles reached: PAUSE, user decides

5. thinker: Generate global review instructions
      → writes final-review-task.md
6. executor(review): Execute global review
      → writes final-review-result.md
7. thinker: Evaluate global review
      → PASS: done
      → FAIL: fix cycle (same as per-task)
```

### Task Decomposition Format

`03-tasks.json`:

```json
[
  {
    "id": 1,
    "name": "Database models",
    "file": "03-task-01.md",
    "deps": []
  },
  {
    "id": 2,
    "name": "API endpoints",
    "file": "03-task-02.md",
    "deps": [1]
  },
  {
    "id": 3,
    "name": "Frontend components",
    "file": "03-task-03.md",
    "deps": [1]
  }
]
```

Tasks with no unmet dependencies can theoretically run in parallel (future enhancement with tmux).

### Starting from Mid-Point

Users who have already completed earlier stages (e.g., brainstorming with superpowers) can skip ahead:

- `/multicoder --start-from analyze` — Skip nothing, start from requirements analysis (default).
- `/multicoder --start-from architect` — Expects `01-analysis.md` to exist. Starts from architecture design.
- `/multicoder --start-from decompose` — Expects analysis + architecture files. Starts from task decomposition.
- `/multicoder --start-from code` — Expects `03-tasks.json` and task files. Starts coding the first pending task.
- `/multicoder --start-from review` — Expects code to already exist. Starts from review.
- `/multicoder --resume <session-id>` — Resumes a saved session from where it left off.

When starting from a mid-point, the skill validates that required upstream files exist before proceeding.

## Session Management & Context Recovery

### Session Directory Structure

```
docs/multicoder/sessions/
  2026-04-14-login-feature/
    state.json
    01-analysis.md
    02-architecture.md
    03-tasks.json
    03-task-01.md
    03-code-result-01.md
    03-review-task-01.md
    03-review-result-01.md
    ...
    final-review-task.md
    final-review-result.md
```

### state.json

```json
{
  "session_id": "2026-04-14-login-feature",
  "status": "in_progress",
  "current_phase": "code",
  "current_task_id": 2,
  "review_cycle": 0,
  "completed_tasks": [1],
  "config_snapshot": {
    "thinker": "claude",
    "executors": { "code": "codex-cli", "review": "minimax" },
    "fallback_log": [
      {"task_id": 1, "primary": "codex-cli", "failed": true, "used": "qwen", "reason": "rate_limit"}
    ]
  },
  "created_at": "2026-04-14T10:00:00Z",
  "updated_at": "2026-04-14T10:30:00Z"
}
```

### Context Recovery Flow

When context nears capacity:

1. The skill writes current progress to `state.json`
2. Displays a message: "Context is getting full. Session saved to `<session-id>`. Start a new conversation and run `/multicoder --resume <session-id>` to continue."
3. In the new conversation, the skill reads `state.json` and the relevant output files to reconstruct context, then continues from the saved point.

## multicoder.py Interface

The Python script is invoked by the skill via Bash. It is a stateless executor.

### Commands

```bash
# Execute a coding task
python multicoder.py exec \
  --session 2026-04-14-login-feature \
  --task-file 03-task-01.md \
  --provider codex-cli \
  --output 03-code-result-01.md

# Execute a review task
python multicoder.py review \
  --session 2026-04-14-login-feature \
  --task-file 03-review-task-01.md \
  --provider minimax \
  --output 03-review-result-01.md

# Check context usage estimate
python multicoder.py context-check \
  --session 2026-04-14-login-feature
```

### Provider Calling Logic

**CLI type (`codex-cli`):**
```bash
codex -q --prompt "$(cat instruction-file.md)" > result-file.md
```

**API type (`minimax`, `qwen`, `dashscope`):**
- Read instruction file
- Send HTTP POST to the provider's chat completions endpoint
- Write response content to result file
- Handle errors (rate limits, timeouts) with retries

### Error Handling & Fallback

**Retry logic:**
- Transient errors (rate limit, network timeout, 5xx) → exponential backoff retry, up to 3 attempts
- Non-transient errors (401 auth, 400 bad request) → no retry, go straight to fallback

**Fallback chain:**
When the primary provider fails after retries, `multicoder.py` tries the fallback providers in order:
1. Try primary provider (e.g., `codex-cli`) with retries
2. If all retries fail → try `code_fallback[0]` (e.g., `qwen`) with retries
3. If that fails → try `code_fallback[1]` (e.g., `dashscope`) with retries
4. If entire fallback chain exhausted → write error to result file, save session state, pause for user decision

**Other error scenarios:**
- CLI process timeout (configurable, default 5 min) → treat as transient, enter fallback chain
- Missing config → exit with clear error message pointing to `.multicoder.json`
- Missing API key env var → skip this provider in fallback chain, try next; if no providers have valid keys, pause for user
- User interrupts (Ctrl+C / SIGINT) → save current progress to `state.json` immediately before exiting, so `/multicoder --resume` can pick up

## First Version Scope

### Included

- `/multicoder` skill entry point
- `multicoder.py` with `exec`, `review`, `context-check` commands
- Provider support: `current` (Claude), `cli` (Codex CLI), `api` (MiniMax, Qwen, DashScope)
- `.multicoder.json` configuration
- Full pipeline: analyze → architect → decompose → (code → review → fix) × N → global review
- `--start-from`, `--resume`, runtime model overrides
- Session file persistence and context recovery

### Excluded (Future)

- tmux-based parallel task execution
- Web UI or dashboard
- Git integration (auto-commit per task)
- Plugin marketplace distribution
- Streaming output from executors
