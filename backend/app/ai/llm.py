"""The contract every language model provider must follow. The agent only knows this file.

A provider (Gemini, Groq, ...) is a small adapter that turns these messages into its own API
format. Switching provider means writing one adapter; the agent does not change.
"""

from dataclasses import dataclass
from typing import Any, Literal, Protocol


class LLMError(Exception):
    """The model could not be reached or answered with an error."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    # Opaque data a provider needs echoed back with the call, for example Gemini's thought signature.
    # The agent never looks inside it; it only passes it along unchanged.
    extra: dict[str, Any] | None = None


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()  # set on assistant messages that ask for tools
    tool_call_id: str | None = None  # set on tool messages, to say which call they answer
    tool_name: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema


@dataclass(frozen=True)
class LLMReply:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class LLMClient(Protocol):
    def generate(self, messages: list[Message], tools: list[ToolSpec]) -> LLMReply: ...


class UnavailableLLM:
    """Used while no provider is configured. The agent then falls back to rule-based triage."""

    def generate(self, messages: list[Message], tools: list[ToolSpec]) -> LLMReply:
        raise LLMError("No LLM provider is configured.")
