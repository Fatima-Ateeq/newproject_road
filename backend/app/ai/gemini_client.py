"""Gemini adapter: sends our messages to the Gemini API and returns its reply.

The agent only knows the LLMClient contract. This is the one place that knows about HTTP, the API key,
retries and Gemini's error messages.
"""

import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import httpx

from app.ai.gemini_format import from_response, to_request_body
from app.ai.llm import LLMError, LLMReply, Message, ToolSpec

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_RETRYABLE = {429, 500, 502, 503, 504}
_MAX_WAIT_SECONDS = 5  # the agent has a time limit, so never wait long for a retry


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 10,
        max_retries: int = 2,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        thinking_level: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._http = http or httpx.Client()
        self._sleep = sleep
        self._thinking_level = thinking_level
        self.last_usage: dict[str, Any] = {}  # token counts of the latest reply, for diagnostics

    def generate(self, messages: list[Message], tools: list[ToolSpec]) -> LLMReply:
        body = to_request_body(messages, tools, self._thinking_level)
        data = self._post(f"{BASE_URL}/models/{self._model}:generateContent", body)
        self.last_usage = data.get("usageMetadata") or {}
        return from_response(data)

    def list_models(self) -> list[str]:
        """Names of the models this key can use for generateContent. Handy for choosing GEMINI_MODEL."""
        data = self._request("GET", f"{BASE_URL}/models?pageSize=200", None)
        return sorted(
            model["name"].removeprefix("models/")
            for model in data.get("models", [])
            if "generateContent" in model.get("supportedGenerationMethods", [])
        )

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", url, body)

    def _request(self, method: str, url: str, body: dict[str, Any] | None) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                response = self._http.request(
                    method, url, json=body, headers={"x-goog-api-key": self._api_key}, timeout=self._timeout_seconds
                )
            except httpx.TimeoutException as error:
                raise LLMError("the request to Gemini timed out") from error
            except httpx.HTTPError as error:
                raise LLMError(f"could not reach Gemini ({type(error).__name__})") from error

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as error:
                    raise LLMError("Gemini returned a response that is not JSON") from error
            if response.status_code in _RETRYABLE and attempt < self._max_retries:
                self._sleep(self._wait_seconds(response, attempt))
                continue
            raise LLMError(self._describe(response))
        raise LLMError("Gemini did not answer")  # not reachable, keeps the type checker content

    @staticmethod
    def _wait_seconds(response: httpx.Response, attempt: int) -> float:
        try:
            requested = float(response.headers.get("retry-after", ""))
        except ValueError:
            requested = 2**attempt
        return min(requested, _MAX_WAIT_SECONDS)

    def _describe(self, response: httpx.Response) -> str:
        """A short, safe description of an error response. The API key is never included."""
        try:
            message = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = response.text[:200]
        message = str(message).replace(self._api_key, "***").splitlines()[0][:200]
        if response.status_code == 429:
            return f"Gemini rate limit or quota reached (HTTP 429): {message}"
        return f"Gemini returned HTTP {response.status_code}: {message}"


@lru_cache
def get_gemini_client(
    api_key: str, model: str, timeout_seconds: float, thinking_level: str | None = None
) -> GeminiClient:
    """One client (and one connection pool) per process."""
    return GeminiClient(api_key, model, timeout_seconds, thinking_level=thinking_level)
