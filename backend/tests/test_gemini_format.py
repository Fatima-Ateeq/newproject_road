import json

import pytest

from app.ai.gemini_format import from_response, to_request_body
from app.ai.llm import LLMError, Message, ToolCall, ToolSpec

NO_ARGS = ToolSpec("classify_text", "Suggest a category.", {"type": "object", "properties": {}})
WITH_ARGS = ToolSpec("lookup", "Look something up.", {"type": "object", "properties": {"q": {"type": "string"}}})


def test_system_messages_become_the_system_instruction():
    body = to_request_body([Message("system", "Be brief."), Message("user", "Hello")], [])
    assert body["systemInstruction"] == {"parts": [{"text": "Be brief."}]}
    assert body["contents"] == [{"role": "user", "parts": [{"text": "Hello"}]}]
    assert "tools" not in body


def test_tools_without_arguments_omit_the_parameters_schema_that_gemini_rejects():
    declarations = to_request_body([Message("user", "x")], [NO_ARGS, WITH_ARGS])["tools"][0]["functionDeclarations"]
    assert "parameters" not in declarations[0]
    assert declarations[1]["parameters"]["properties"] == {"q": {"type": "string"}}


def test_a_tool_call_and_its_answer_round_trip_with_the_thought_signature():
    call = ToolCall("call_1", "classify_text", {}, extra={"thoughtSignature": "sig-A"})
    messages = [
        Message("user", "complaint"),
        Message("assistant", "", (call,)),
        Message("tool", json.dumps({"category": "Road Damage"}), tool_call_id="call_1", tool_name="classify_text"),
    ]
    contents = to_request_body(messages, [NO_ARGS])["contents"]
    assert contents[1] == {
        "role": "model",
        "parts": [{"functionCall": {"name": "classify_text", "args": {}}, "thoughtSignature": "sig-A"}],
    }
    assert contents[2] == {
        "role": "user",
        "parts": [{"functionResponse": {"name": "classify_text", "response": {"category": "Road Damage"}}}],
    }


def test_answers_to_parallel_calls_share_one_turn():
    calls = (ToolCall("call_1", "a", {}), ToolCall("call_2", "b", {}))
    messages = [
        Message("user", "x"),
        Message("assistant", "", calls),
        Message("tool", "{}", tool_call_id="call_1", tool_name="a"),
        Message("tool", "{}", tool_call_id="call_2", tool_name="b"),
    ]
    contents = to_request_body(messages, [])["contents"]
    assert len(contents) == 3
    assert [part["functionResponse"]["name"] for part in contents[2]["parts"]] == ["a", "b"]


def test_a_text_reply_is_parsed_and_thinking_parts_are_ignored():
    data = {"candidates": [{"content": {"parts": [{"text": "private reasoning", "thought": True}, {"text": "ready"}]}}]}
    reply = from_response(data)
    assert reply.content == "ready"
    assert reply.tool_calls == ()


def test_a_function_call_is_parsed_with_its_signature():
    data = {"candidates": [{"content": {"parts": [
        {"functionCall": {"name": "find_duplicates", "args": {}}, "thoughtSignature": "sig-B"},
    ]}}]}
    call = from_response(data).tool_calls[0]
    assert (call.name, call.arguments, call.extra) == ("find_duplicates", {}, {"thoughtSignature": "sig-B"})


def test_a_blocked_prompt_raises_a_clear_error():
    with pytest.raises(LLMError, match="SAFETY"):
        from_response({"promptFeedback": {"blockReason": "SAFETY"}})


def test_an_empty_answer_raises_a_clear_error():
    with pytest.raises(LLMError, match="MAX_TOKENS"):
        from_response({"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]})


def test_thinking_level_is_sent_only_when_configured():
    plain = to_request_body([Message("user", "x")], [])
    assert "thinkingConfig" not in plain["generationConfig"]
    low = to_request_body([Message("user", "x")], [], thinking_level="low")
    assert low["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}
