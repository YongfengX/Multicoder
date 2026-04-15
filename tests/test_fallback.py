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
        max_retries=3,
        base_delay=0
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
        max_retries=1,
        base_delay=0
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
        max_retries=3,
        base_delay=0
    )
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
            max_retries=1,
            base_delay=0
        )


def test_fallback_retries_transient_before_moving_on():
    call_count = 0
    def fail_twice_then_succeed(task_file, output_file):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ProviderError("transient", transient=True)

    primary = _make_provider()
    primary.run.side_effect = fail_twice_then_succeed
    fallback1 = _make_provider()

    used = run_with_fallback(
        providers=[("primary", primary), ("fallback1", fallback1)],
        task_file="task.md",
        output_file="out.md",
        max_retries=3,
        base_delay=0
    )
    assert used == "primary"
    assert primary.run.call_count == 3
    fallback1.run.assert_not_called()
