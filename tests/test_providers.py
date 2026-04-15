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
