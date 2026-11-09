"""What administrators send and see."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import ComplaintCategory, ComplaintStatus, Priority


class HistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    old_status: ComplaintStatus | None
    new_status: ComplaintStatus
    action_note: str | None
    changed_by: str | None = Field(validation_alias="admin_username")
    changed_at: datetime


class ComplaintSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: str = Field(validation_alias="code")
    description: str
    category: ComplaintCategory | None
    priority: Priority | None
    status: ComplaintStatus
    latitude: float
    longitude: float
    created_at: datetime


class ComplaintDetail(ComplaintSummary):
    address_text: str | None
    contact: str | None
    has_photo: bool
    updated_at: datetime
    history: list[HistoryEntry]


class ComplaintPage(BaseModel):
    items: list[ComplaintSummary]
    total: int
    page: int
    page_size: int


class ComplaintUpdate(BaseModel):
    """Fields left out (or null) stay unchanged. At least one must be provided."""

    status: ComplaintStatus | None = None
    category: ComplaintCategory | None = None
    priority: Priority | None = None
    action_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_a_change(self) -> "ComplaintUpdate":
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("Provide at least one field to update.")
        return self
