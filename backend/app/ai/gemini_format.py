"""Translates between our provider-neutral messages and the Gemini generateContent JSON format.

Pure functions, no network. See https://ai.google.dev/gemini-api/docs/function-calling
"""

import json
from typing import Any

from app.ai.llm import LLMError, LLMReply, Message, ToolCall, ToolSpec

TEMPERATURE = 0.2  # low, so triage answers are steady from run to run


def _declaration(tool: ToolSpec) -> dict[str, Any]:
    declaration: dict[str, Any] = {"name": tool.name, "description": tool.description}
    if tool.parameters.get("properties"):  # Gemini rejects an object schema with no properties
        declaration["parameters"] = tool.parameters
    return declaration


def _tool_response(message: Message) -> dict[str, Any]:
    try:
        output = json.loads(message.content)
    except json.JSONDecodeError:
        output = {"result": message.content}
    if not isinstance(output, dict):
        output = {"result": output}
    return {"functionResponse": {"name": message.tool_name, "response": output}}


def _model_parts(message: Message) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"text": message.content}] if message.content else []
    for call in message.tool_calls:
        part: dict[str, Any] = {"functionCall": {"name": call.name, "args": call.arguments}}
        if call.extra and "thoughtSignature" in call.extra:
            part["thoughtSignature"] = call.extra["thoughtSignature"]  # Gemini 3 and newer require this back
        parts.append(part)
    return parts


def to_request_body(
    messages: list[Message], tools: list[ToolSpec], thinking_level: str | None = None
) -> dict[str, Any]:
    contents: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "user":
            contents.append({"role": "user", "parts": [{"text": message.content}]})
        elif message.role == "assistant":
            contents.append({"role": "model", "parts": _model_parts(message)})
        elif message.role == "tool":
            # Answers to parallel calls must all sit in one turn.
            if contents and contents[-1]["role"] == "user" and "functionResponse" in contents[-1]["parts"][0]:
                contents[-1]["parts"].append(_tool_response(message))
            else:
                contents.append({"role": "user", "parts": [_tool_response(message)]})

    body: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": TEMPERATURE}}
    if thinking_level:
        # How long the model may reason before answering. Newer Gemini models think a lot by default,
        # which is slow. Triage is a short task, so a low level is usually enough.
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": thinking_level}
    system_text = "\n\n".join(m.content for m in messages if m.role == "system")
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}
    if tools:
        body["tools"] = [{"functionDeclarations": [_declaration(tool) for tool in tools]}]
    return body


def from_response(data: dict[str, Any]) -> LLMReply:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates returned")
        raise LLMError(f"Gemini gave no answer ({reason})")

    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part["text"] for part in parts if "text" in part and not part.get("thought"))
    calls = tuple(
        ToolCall(
            id=f"call_{number}",
            name=part["functionCall"]["name"],
            arguments=dict(part["functionCall"].get("args") or {}),
            extra={"thoughtSignature": part["thoughtSignature"]} if "thoughtSignature" in part else None,
        )
        for number, part in enumerate(parts, start=1)
        if "functionCall" in part
    )
    if not text and not calls:
        raise LLMError(f"Gemini gave an empty answer (finishReason: {candidate.get('finishReason', 'unknown')})")
    return LLMReply(content=text, tool_calls=calls)
