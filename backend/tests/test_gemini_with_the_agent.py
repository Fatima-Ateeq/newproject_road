"""The whole agent talking to a pretend Gemini server that answers in Gemini's JSON format."""

import json

import httpx
from pydantic import SecretStr

from app.ai.agent import TriageAgent
from app.ai.fallback import FallbackTriage
from app.ai.gemini_client import GeminiClient
from app.ai.triage_tools import build_tools
from app.api.deps import get_llm_client
from app.ai.llm import UnavailableLLM
from app.core.enums import TriageSource
from tests.fakes import CONTEXT, FixedClassifier, FixedDuplicates

ANSWER = {
    "category": "Road Damage", "priority": "High", "rationale": "Pothole next to a school.",
    "responsible_unit": "Roads Maintenance", "draft_note": "Inspect and repair.", "possible_duplicates": [],
}


def test_the_agent_completes_a_tool_conversation_and_echoes_the_thought_signature():
    requests: list[dict] = []
    replies = iter([
        {"candidates": [{"content": {"parts": [
            {"functionCall": {"name": "classify_text", "args": {}}, "thoughtSignature": "sig-A"}]}}]},
        {"candidates": [{"content": {"parts": [{"text": json.dumps(ANSWER)}]}}]},
    ])

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=next(replies))

    client = GeminiClient("k", "m", http=httpx.Client(transport=httpx.MockTransport(handler)))
    tools = build_tools(CONTEXT, FixedClassifier(), FixedDuplicates())
    run = TriageAgent(client, tools, FallbackTriage(tools, CONTEXT.description)).run(CONTEXT.description, False)

    assert run.source == TriageSource.AGENT
    assert [step.tool_name for step in run.steps] == ["classify_text"]
    second_request = requests[1]["contents"]
    assert second_request[1]["parts"][0]["thoughtSignature"] == "sig-A"                    # echoed back unchanged
    assert second_request[2]["parts"][0]["functionResponse"]["response"]["category"] == "Road Damage"


def test_a_gemini_outage_makes_the_agent_fall_back_instead_of_failing():
    client = GeminiClient("k", "m", max_retries=0,
                          http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503, json={"error": {"message": "overloaded"}}))))
    tools = build_tools(CONTEXT, FixedClassifier(), FixedDuplicates())
    run = TriageAgent(client, tools, FallbackTriage(tools, CONTEXT.description)).run(CONTEXT.description, False)
    assert run.source == TriageSource.FALLBACK
    assert "HTTP 503" in run.fallback_reason


def test_gemini_is_used_only_when_both_the_key_and_the_model_are_configured(settings):
    assert isinstance(get_llm_client(settings), UnavailableLLM)
    assert isinstance(get_llm_client(settings.model_copy(update={"gemini_api_key": SecretStr("k")})), UnavailableLLM)
    configured = settings.model_copy(update={"gemini_api_key": SecretStr("k"), "gemini_model": "m"})
    assert isinstance(get_llm_client(configured), GeminiClient)
