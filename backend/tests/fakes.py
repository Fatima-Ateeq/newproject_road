"""Stand-ins for the language model and the tools' inputs, so the agent can be tested without any API."""

import json

from app.ai.classifier import Prediction
from app.ai.context import ComplaintContext
from app.ai.duplicates import DuplicateMatch
from app.ai.llm import LLMReply, ToolCall
from app.core.enums import ComplaintCategory


class ScriptedLLM:
    """Replies with a prepared list of answers, one per call, and records what it was sent."""

    def __init__(self, replies: list) -> None:
        self._replies = iter(replies)
        self.calls: list = []

    def generate(self, messages, tools):
        self.calls.append((list(messages), list(tools)))
        item = next(self._replies)
        if isinstance(item, Exception):
            raise item
        return item


def tool_call(name: str, call_id: str = "c1") -> ToolCall:
    return ToolCall(call_id, name, {})


def ask_tools(*names: str) -> LLMReply:
    return LLMReply(tool_calls=tuple(tool_call(name, f"c{i}") for i, name in enumerate(names, start=1)))


def final_answer(**overrides) -> LLMReply:
    answer = {
        "category": "Road Damage",
        "priority": "High",
        "rationale": "A deep pothole near a school is dangerous.",
        "responsible_unit": "Roads Maintenance",
        "draft_note": "Inspect the pothole and schedule a repair.",
        "possible_duplicates": [],
        **overrides,
    }
    return LLMReply(content=json.dumps(answer))


class FixedClassifier:
    def __init__(self, category: ComplaintCategory = ComplaintCategory.ROAD_DAMAGE, confidence: float = 0.9) -> None:
        self._prediction = Prediction(category, confidence)

    def predict(self, text: str) -> Prediction:
        return self._prediction


class FixedDuplicates:
    def __init__(self, matches: list[DuplicateMatch] | None = None) -> None:
        self._matches = matches if matches is not None else [DuplicateMatch("RW-2026-000002", 40, 0.5)]

    def find(self, context: ComplaintContext) -> list[DuplicateMatch]:
        return self._matches


class FakeClock:
    """Moves forward by `step` seconds every time it is read."""

    def __init__(self, step: float) -> None:
        self._now = 0.0
        self._step = step

    def __call__(self) -> float:
        self._now += self._step
        return self._now


CONTEXT = ComplaintContext(1, "RW-2026-000001", "Big pothole near the school gate", 31.5, 74.3, False)
