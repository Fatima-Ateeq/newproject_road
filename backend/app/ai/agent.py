"""The triage agent: the model decides which tools to call, within strict limits."""

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from app.ai.llm import LLMClient, LLMError, Message
from app.ai.prompts import build_system_prompt, build_user_prompt
from app.ai.schemas import TriageResult
from app.ai.steps import AgentStep, run_tool
from app.ai.tools import ToolRegistry
from app.core.enums import TriageSource

_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class _AgentFailure(Exception):
    """The model path failed. The message becomes the recorded fallback reason."""


class Fallback(Protocol):
    def run(self) -> tuple[TriageResult, list[AgentStep]]: ...


@dataclass(frozen=True)
class AgentRun:
    result: TriageResult
    source: TriageSource
    steps: list[AgentStep]
    fallback_reason: str | None = None


class TriageAgent:
    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        fallback: Fallback,
        max_tool_calls: int = 5,
        timeout_seconds: float = 20,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._fallback = fallback
        self._max_tool_calls = max_tool_calls
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def run(self, description: str, has_photo: bool) -> AgentRun:
        steps: list[AgentStep] = []
        try:
            result = self._converse(description, has_photo, steps)
            return AgentRun(result, TriageSource.AGENT, steps)
        except _AgentFailure as failure:
            fallback_result, fallback_steps = self._fallback.run()
            all_steps = [AgentStep(n, s.tool_name, s.arguments, s.output, s.duration_ms)
                         for n, s in enumerate(steps + fallback_steps, start=1)]
            return AgentRun(fallback_result, TriageSource.FALLBACK, all_steps, str(failure))

    def _converse(self, description: str, has_photo: bool, steps: list[AgentStep]) -> TriageResult:
        started = self._clock()
        messages = [
            Message("system", build_system_prompt(self._max_tool_calls)),
            Message("user", build_user_prompt(description, has_photo)),
        ]
        calls_used = 0
        for _ in range(self._max_tool_calls + 2):  # a hard cap, so a misbehaving model cannot loop forever
            if self._clock() - started > self._timeout_seconds:
                raise _AgentFailure("time limit exceeded")
            tools_offered = self._tools.specs() if calls_used < self._max_tool_calls else []
            try:
                reply = self._llm.generate(messages, tools_offered)
            except LLMError as error:
                raise _AgentFailure(f"LLM unavailable: {error}") from error

            if not reply.tool_calls:
                return self._parse(reply.content, steps)

            messages.append(Message("assistant", reply.content, reply.tool_calls))
            for call in reply.tool_calls:
                if calls_used >= self._max_tool_calls:
                    output = {"error": "Tool call limit reached. Give your final answer now."}
                else:
                    calls_used += 1
                    output = run_tool(self._tools, call.name, call.arguments, steps, self._clock)
                messages.append(Message("tool", json.dumps(output, ensure_ascii=False), tool_call_id=call.id, tool_name=call.name))
        raise _AgentFailure("no final answer within the allowed turns")

    @staticmethod
    def _parse(content: str, steps: list[AgentStep]) -> TriageResult:
        try:
            result = TriageResult.model_validate_json(_CODE_FENCE.sub("", content.strip()))
        except (ValidationError, ValueError) as error:
            raise _AgentFailure(f"invalid LLM output: {str(error).splitlines()[0]}") from error
        known_ids = {
            match["complaint_id"]
            for step in steps if step.tool_name == "find_duplicates"
            for match in step.output.get("matches", [])
        }
        # Keep only ids a tool really returned, so the model cannot invent complaints.
        return result.model_copy(update={"possible_duplicates": [c for c in result.possible_duplicates if c in known_ids]})
