import json

import httpx
import pytest

from app.ai.gemini_client import GeminiClient
from app.ai.llm import LLMError, Message

KEY = "secret-key-123"
OK = {"candidates": [{"content": {"parts": [{"text": "ready"}]}}]}


def make_client(handler, **kwargs) -> GeminiClient:
    waits: list[float] = []
    client = GeminiClient(KEY, "test-model", http=httpx.Client(transport=httpx.MockTransport(handler)),
                          sleep=waits.append, **kwargs)
    client.waits = waits
    return client


def ask(client):
    return client.generate([Message("user", "hi")], [])


def test_a_successful_call_sends_the_key_in_a_header_to_the_right_model():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["key"], seen["body"] = str(request.url), request.headers["x-goog-api-key"], json.loads(request.content)
        return httpx.Response(200, json=OK)

    reply = ask(make_client(handler))
    assert reply.content == "ready"
    assert seen["url"].endswith("/models/test-model:generateContent")
    assert KEY not in seen["url"]                       # never in the address, where logs would record it
    assert seen["key"] == KEY
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "hi"


def test_a_rate_limit_is_retried_and_then_succeeds():
    replies = iter([httpx.Response(429, json={"error": {"message": "slow down"}}, headers={"retry-after": "1"}),
                    httpx.Response(200, json=OK)])
    client = make_client(lambda request: next(replies))
    assert ask(client).content == "ready"
    assert client.waits == [1.0]


def test_a_persistent_rate_limit_gives_a_clear_error_after_the_retries():
    client = make_client(lambda request: httpx.Response(429, json={"error": {"message": "quota exceeded"}}))
    with pytest.raises(LLMError, match="rate limit or quota reached"):
        ask(client)
    assert len(client.waits) == 2                       # two retries, then give up


def test_waiting_for_a_retry_is_capped_so_the_agent_stays_within_its_time_limit():
    replies = iter([httpx.Response(429, headers={"retry-after": "60"}), httpx.Response(200, json=OK)])
    client = make_client(lambda request: next(replies))
    ask(client)
    assert client.waits == [5]


def test_a_bad_key_is_reported_without_retrying_and_without_leaking_the_key():
    client = make_client(lambda request: httpx.Response(400, json={"error": {"message": f"API key not valid: {KEY}"}}))
    with pytest.raises(LLMError) as error:
        ask(client)
    assert "HTTP 400" in str(error.value)
    assert KEY not in str(error.value)
    assert client.waits == []


def test_a_timeout_and_a_network_failure_become_llm_errors():
    def timeout(request):
        raise httpx.ReadTimeout("slow")

    def offline(request):
        raise httpx.ConnectError("no network")

    with pytest.raises(LLMError, match="timed out"):
        ask(make_client(timeout))
    with pytest.raises(LLMError, match="could not reach"):
        ask(make_client(offline))


def test_a_response_that_is_not_json_is_an_llm_error():
    with pytest.raises(LLMError, match="not JSON"):
        ask(make_client(lambda request: httpx.Response(200, text="<html>oops</html>")))


def test_list_models_returns_only_models_that_can_generate_content():
    data = {"models": [
        {"name": "models/flash-a", "supportedGenerationMethods": ["generateContent", "countTokens"]},
        {"name": "models/embed-b", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/flash-c", "supportedGenerationMethods": ["generateContent"]},
    ]}
    assert make_client(lambda request: httpx.Response(200, json=data)).list_models() == ["flash-a", "flash-c"]


def test_the_thinking_level_is_sent_and_the_token_usage_is_remembered():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={**OK, "usageMetadata": {"promptTokenCount": 40, "thoughtsTokenCount": 7}})

    client = make_client(handler, thinking_level="minimal")
    ask(client)
    assert seen["body"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "minimal"}
    assert client.last_usage["thoughtsTokenCount"] == 7
