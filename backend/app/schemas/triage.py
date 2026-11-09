"""How a triage suggestion is shown to administrators."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import ComplaintCategory, Priority, TriageSource


class AgentStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    tool_name: str
    arguments: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int


class TriageSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: ComplaintCategory
    priority: Priority
    rationale: str
    responsible_unit: str
    draft_note: str
    possible_duplicates: list[str]
    source: TriageSource
    fallback_reason: str | None
    created_at: datetime
    steps: list[AgentStepOut]
