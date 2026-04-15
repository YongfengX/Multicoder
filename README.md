# Multicoder

A Claude Code skill that orchestrates multiple AI models to collaboratively complete development tasks. Each model plays to its strengths — one thinks, others execute.

## How It Works

Multicoder enforces a strict **Thinker-Executor** separation:

- **Thinker** (default: Claude) handles all decision-making — requirements analysis, architecture design, task decomposition, review strategy, fix planning.
- **Executors** (default: Codex CLI for coding, MiniMax for review) follow the thinker's instructions. They never make architectural decisions.

```
Thinker: analyze → design → decompose tasks
             ↓
Executor:    code task 1 → review → fix (loop)
             code task 2 → review → fix (loop)
             code task 3 → review → fix (loop)
             ↓
         global review → fix (loop) → done
```

Every step produces a file. The pipeline pauses at key checkpoints for human confirmation.

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- At least one executor available:
  - [Codex CLI](https://github.com/openai/codex) (for coding tasks)
  - API keys for MiniMax / Qwen / DashScope (for review or coding)

### Setup

1. Clone this repo into your project or install as a Claude Code skill.

2. Create `.multicoder.json` in your project root:

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
    }
  }
}
```

3. Set your API keys as environment variables:

```bash
export MINIMAX_API_KEY="your-key"
export DASHSCOPE_API_KEY="your-key"
```

## Usage

### Full Pipeline

```
/multicoder "build a user login page with JWT auth"
```

This runs the full pipeline: analyze → architect → decompose → code → review → fix → global review.

### Start from a Specific Stage

If you've already done brainstorming or planning (e.g., with superpowers), skip ahead:

```
/multicoder --start-from code "build a user login page"
/multicoder --start-from review
/multicoder --start-from architect
```

Available stages: `analyze`, `architect`, `decompose`, `code`, `review`.

### Resume a Saved Session

When context gets full, Multicoder saves progress automatically. Resume in a new conversation:

```
/multicoder --resume 2026-04-14-login-feature
```

### Override Models at Runtime

```
/multicoder --code=qwen "build a REST API"
/multicoder --review=claude "refactor the auth module"
/multicoder --thinker=qwen "add dark mode"
```

## Pipeline Details

### Stages

| Stage | What happens | Who does it |
|-------|-------------|-------------|
| **Analyze** | Understand requirements, define scope | Thinker |
| **Architect** | Design architecture, file structure, interfaces | Thinker |
| **Decompose** | Break work into sub-tasks with dependencies | Thinker |
| **Code** | Write code for each sub-task | Executor (code) |
| **Review** | Audit code per thinker's review strategy | Executor (review) |
| **Fix** | Fix issues found in review | Executor (code) |
| **Global Review** | Final integration review across all tasks | Executor (review) |

### Checkpoints

The pipeline pauses for user confirmation after:
- Requirements analysis
- Architecture design
- Task decomposition
- Max review cycles reached (user decides whether to continue or stop)

### Review-Fix Loop

Each sub-task goes through a review-fix cycle:

1. Thinker decides what to review and how
2. Reviewer executes the review
3. Thinker evaluates results — pass or fail
4. If fail: thinker plans the fix, coder executes it
5. Loop up to `max_review_cycles` times (default: 3)

After all sub-tasks pass, a mandatory global review checks overall integration.

## Fallback & Error Handling

When a provider fails, Multicoder tries the fallback chain automatically:

```
Primary provider (with retries)
  → Fallback provider 1 (with retries)
    → Fallback provider 2 (with retries)
      → Save session, pause for user
```

- **Transient errors** (rate limit, network, 5xx): exponential backoff, up to 3 retries per provider
- **Non-transient errors** (401, 400): skip retries, jump to next fallback
- **User interrupts** (Ctrl+C): progress saved immediately, resumable later

## Provider Types

| Type | Description | Example |
|------|-------------|---------|
| `current` | The LLM session running the skill | Claude (when running in Claude Code) |
| `cli` | Locally installed CLI tool | Codex CLI |
| `api` | HTTP API with API key | MiniMax, Qwen, DashScope |

All roles (thinker and executors) are fully configurable. Nothing is hardcoded.

## Session Files

All intermediate outputs are persisted to `docs/multicoder/sessions/<session-id>/`:

```
sessions/2026-04-14-login-feature/
  state.json              # Current progress, resumable state
  01-analysis.md          # Requirements analysis
  02-architecture.md      # Architecture design
  03-tasks.json           # Task decomposition
  03-task-01.md           # Sub-task 1 instructions
  03-code-result-01.md    # Sub-task 1 code output
  03-review-task-01.md    # Sub-task 1 review instructions
  03-review-result-01.md  # Sub-task 1 review output
  ...
  final-review-task.md    # Global review instructions
  final-review-result.md  # Global review output
```

## Project Structure

```
multicoder/
  README.md
  .multicoder.json          # Project-level config
  multicoder.py             # Orchestration script (calls executors)
  skills/
    multicoder/SKILL.md     # Claude Code skill definition
  docs/
    multicoder/
      sessions/             # Session outputs
    superpowers/
      specs/                # Design specs
```

## Roadmap

- [ ] tmux-based parallel task execution (run independent sub-tasks concurrently)
- [ ] Git integration (auto-commit after each task passes review)
- [ ] Streaming output from executors
- [ ] Plugin marketplace distribution

## License

MIT
