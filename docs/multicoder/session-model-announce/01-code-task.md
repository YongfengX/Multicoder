# Task 01: Add `model_info` property to providers

## Goal
Add a `model_info` property to each provider class so callers can display a human-readable model name.

## Files to modify

### 1. `/Users/feierkang/Desktop/UCSD/Multicoder/multicoder/providers/base.py`

Add a `model_info` property to `BaseProvider` with a default implementation:

```python
@property
def model_info(self) -> str:
    return self.__class__.__name__
```

Full file after change:
```python
from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider call fails."""
    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = transient


class BaseProvider(ABC):
    @property
    def model_info(self) -> str:
        """Human-readable model identifier for display purposes."""
        return self.__class__.__name__

    @abstractmethod
    def run(self, task_file: str, output_file: str) -> None:
        """Read instructions from task_file, execute, write result to output_file.

        Raises ProviderError on failure. Set transient=True for retryable errors.
        """
        pass
```

### 2. `/Users/feierkang/Desktop/UCSD/Multicoder/multicoder/providers/api_provider.py`

Add `model_info` property that returns `self.model` (the actual model ID like `minimax-m2.7`):

After the `__init__` method, add:
```python
@property
def model_info(self) -> str:
    return self.model
```

### 3. `/Users/feierkang/Desktop/UCSD/Multicoder/multicoder/providers/cli_provider.py`

Add `model_info` property that returns `self.command` (e.g. `codex`):

After the `__init__` method, add:
```python
@property
def model_info(self) -> str:
    return self.command
```

## Expected result
- `APIProvider(...).model_info` returns the model string, e.g. `"minimax-m2.7"`
- `CLIProvider(...).model_info` returns the command string, e.g. `"codex"`
- `BaseProvider` has a default fallback implementation
