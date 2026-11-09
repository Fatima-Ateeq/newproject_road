"""Rule-based triage, used whenever the language model cannot give a valid answer."""

from app.ai.schemas import TriageResult
from app.ai.steps import AgentStep, run_tool
from app.ai.tools import ToolRegistry
from app.ai.units import UNIT_BY_CATEGORY
from app.core.enums import ComplaintCategory, Priority

_PRIORITY_ORDER = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]

_BASE_PRIORITY = {
    ComplaintCategory.ROAD_DAMAGE: Priority.MEDIUM,
    ComplaintCategory.TRAFFIC_CONGESTION: Priority.LOW,
    ComplaintCategory.RAILWAY_CROSSING: Priority.HIGH,
    ComplaintCategory.MISSING_TRAFFIC_CONTROL: Priority.MEDIUM,
    ComplaintCategory.OTHER: Priority.LOW,
}

# Words that suggest danger to people. English, Roman Urdu and Urdu.
_DANGER_WORDS = (
    "accident", "hadsa", "hadsay", "injur", "died", "death", "dangerous", "khatarnak", "children", "bachon",
    "bachay", "bache", "school", "hospital", "حادثہ", "حادثے", "خطرناک", "بچوں", "بچے", "اسکول", "ہسپتال",
)
_MANY_DUPLICATES = 2  # this many similar open complaints nearby means many people are affected


def _raise(priority: Priority) -> Priority:
    return _PRIORITY_ORDER[min(_PRIORITY_ORDER.index(priority) + 1, len(_PRIORITY_ORDER) - 1)]


class FallbackTriage:
    def __init__(self, tools: ToolRegistry, description: str) -> None:
        self._tools = tools
        self._description = description

    def run(self) -> tuple[TriageResult, list[AgentStep]]:
        steps: list[AgentStep] = []
        classification = run_tool(self._tools, "classify_text", {}, steps)
        duplicates = run_tool(self._tools, "find_duplicates", {}, steps)

        category = self._category(classification)
        codes = [match["complaint_id"] for match in duplicates.get("matches", [])]
        danger = [word for word in _DANGER_WORDS if word in self._description.casefold()]

        priority = _BASE_PRIORITY[category]
        reasons = [f"category {category.value} (rule-based)"]
        if danger:
            priority = _raise(priority)
            reasons.append(f"danger words found: {', '.join(danger[:3])}")
        if len(codes) >= _MANY_DUPLICATES:
            priority = _raise(priority)
            reasons.append(f"{len(codes)} similar unresolved complaints nearby")

        unit = UNIT_BY_CATEGORY[category]
        result = TriageResult(
            category=category,
            priority=priority,
            rationale="Rule-based triage: " + "; ".join(reasons) + ".",
            responsible_unit=unit,
            draft_note=f"Review this {category.value.lower()} complaint (suggested priority {priority.value}) and assign it to {unit}.",
            possible_duplicates=codes,
        )
        return result, steps

    @staticmethod
    def _category(classification: dict) -> ComplaintCategory:
        try:
            return ComplaintCategory(classification["category"])
        except (KeyError, ValueError):
            return ComplaintCategory.OTHER
