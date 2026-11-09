"""The answer the triage agent must produce."""

from pydantic import BaseModel, Field, field_validator

from app.ai.units import RESPONSIBLE_UNITS
from app.core.enums import ComplaintCategory, Priority


class TriageResult(BaseModel):
    category: ComplaintCategory
    priority: Priority
    rationale: str = Field(min_length=5, max_length=600, description="Why this category and priority")
    responsible_unit: str = Field(description=f"One of: {', '.join(RESPONSIBLE_UNITS)}")
    draft_note: str = Field(min_length=5, max_length=1000, description="Short note for the administrator")
    possible_duplicates: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("responsible_unit")
    @classmethod
    def unit_must_be_known(cls, value: str) -> str:
        if value not in RESPONSIBLE_UNITS:
            raise ValueError(f"responsible_unit must be one of {RESPONSIBLE_UNITS}")
        return value
