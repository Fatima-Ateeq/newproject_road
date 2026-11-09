"""What citizens send and see."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import ComplaintCategory, ComplaintStatus


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(min_length=10, max_length=1000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address_text: str | None = Field(default=None, max_length=255)
    contact: str | None = Field(default=None, max_length=100)
    website: str = Field(
        default="",
        max_length=200,
        description="Anti-spam field. Leave empty. Hidden in the real form and never stored.",
    )

    @field_validator("address_text", "contact")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        return value or None


class ComplaintCreated(BaseModel):
    complaint_id: str


class TimelineEntry(BaseModel):
    """A status event as the citizen sees it. Admin names are never exposed."""

    model_config = ConfigDict(from_attributes=True)

    status: ComplaintStatus = Field(validation_alias="new_status")
    changed_at: datetime
    note: str | None = Field(default=None, validation_alias="action_note")


class PublicComplaint(BaseModel):
    """Tracking view. Contact details, location and photo are deliberately left out."""

    model_config = ConfigDict(from_attributes=True)

    complaint_id: str = Field(validation_alias="code")
    status: ComplaintStatus
    category: ComplaintCategory | None
    created_at: datetime
    updated_at: datetime
    timeline: list[TimelineEntry] = Field(validation_alias="history")
