import requests
from pathlib import Path
from .base import BaseProvider, ProviderError

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
NON_TRANSIENT_STATUS_CODES = {400, 401, 403}


class APIProvider(BaseProvider):
    def __init__(self, base_url: str, model: str, api_key: str | None, timeout: int = 120):
        if not api_key:
            raise ProviderError("API key is required but not provided", transient=False)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def run(self, task_file: str, output_file: str) -> None:
        task_content = Path(task_file).read_text()

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": task_content}]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise ProviderError(
                f"API request timed out after {self.timeout}s: {self.base_url}",
                transient=True
            )
        except requests.exceptions.ConnectionError:
            raise ProviderError(
                f"Connection error: {self.base_url}",
                transient=True
            )

        if response.status_code in TRANSIENT_STATUS_CODES:
            raise ProviderError(
                f"API error {response.status_code}: {response.text[:300]}",
                transient=True
            )

        if response.status_code in NON_TRANSIENT_STATUS_CODES:
            raise ProviderError(
                f"API error {response.status_code}: {response.text[:300]}",
                transient=False
            )

        if response.status_code != 200:
            raise ProviderError(
                f"Unexpected API status {response.status_code}: {response.text[:300]}",
                transient=False
            )

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        Path(output_file).write_text(content)
