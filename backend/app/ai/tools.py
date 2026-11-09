"""What a tool is, and a registry that runs tools safely."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.ai.llm import ToolSpec


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: Callable[[dict[str, Any]], dict[str, Any]]

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, self.parameters)


class ToolRegistry:
    """Only tools registered here can ever run. Anything else the model asks for is refused."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run a tool. Problems come back as {'error': ...} so the agent can carry on."""
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Unknown tool '{name}'. Available tools: {sorted(self._tools)}"}
        try:
            return tool.run(arguments)
        except Exception as error:  # a broken tool must not crash the triage
            return {"error": f"{type(error).__name__}: {error}"}
