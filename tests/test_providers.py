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
