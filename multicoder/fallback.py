import time
from multicoder.providers.base import BaseProvider, ProviderError


def run_with_fallback(
    providers: list[tuple[str, BaseProvider]],
    task_file: str,
    output_file: str,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> str:
    """Try providers in order with retries. Returns the name of the provider that succeeded.

    For transient errors: retry up to max_retries times with exponential backoff.
    For non-transient errors: skip to next provider immediately.
    If all providers fail: raise ProviderError.
    """
    errors = []

    for provider_name, provider in providers:
        attempt = 0
        while attempt < max_retries:
            try:
                provider.run(task_file=task_file, output_file=output_file)
                return provider_name
            except ProviderError as e:
                errors.append((provider_name, attempt + 1, str(e)))
                if not e.transient:
                    break
                attempt += 1
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** (attempt - 1)))

    error_summary = "; ".join(f"{name}(attempt {a}): {msg}" for name, a, msg in errors)
    raise ProviderError(f"All providers failed. {error_summary}", transient=False)
