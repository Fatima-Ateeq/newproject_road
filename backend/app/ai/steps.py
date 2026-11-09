"""One recorded tool call, and the helper that runs and times it."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.ai.tools import ToolRegistry


@dataclass(frozen=True)
class AgentStep:
    number: int
    tool_name: str
    arguments: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int


def run_tool(
    tools: ToolRegistry,
    name: str,
    arguments: dict[str, Any],
    steps: list[AgentStep],
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run one tool, append it to `steps` (the audit trail) and return its output."""
    started = clock()
    output = tools.call(name, arguments)
    duration_ms = round((clock() - started) * 1000)
    steps.append(AgentStep(len(steps) + 1, name, arguments, output, duration_ms))
    return output
