from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider call fails."""
    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = transient


class BaseProvider(ABC):
    @abstractmethod
    def run(self, task_file: str, output_file: str) -> None:
        """Read instructions from task_file, execute, write result to output_file.

        Raises ProviderError on failure. Set transient=True for retryable errors.
        """
        pass
