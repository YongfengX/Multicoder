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
