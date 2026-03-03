import httpx

PISTON_API_URL = "http://127.0.0.1:2000/api/v2/execute"
DEFAULT_TIMEOUT = 10.0  # seconds


class PistonClient:
    """Async client for interacting with the Piston code execution API."""

    def __init__(self, base_url: str = PISTON_API_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    async def execute_code(self, language: str, code: str) -> dict:
        """
        Execute code via the Piston API.

        Args:
            language: Programming language identifier (e.g. "python", "javascript").
            code:     Source code string to execute.

        Returns:
            The parsed JSON response from the Piston API.

        Raises:
            httpx.TimeoutException: If the request exceeds the configured timeout.
            httpx.HTTPStatusError: If the API returns a non-2xx response.
        """
        payload = {
            "language": language,
            "version": "*",  # use the latest installed version for the language
            "files": [
                {
                    "name": "main",
                    "content": code,
                }
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, json=payload)
            response.raise_for_status()
            return response.json()
