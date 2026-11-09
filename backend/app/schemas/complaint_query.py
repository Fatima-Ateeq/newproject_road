from datetime import date

from pydantic import BaseModel, Field

from app.core.enums import ComplaintCategory, ComplaintStatus, Priority


class ComplaintQuery(BaseModel):
    """Filters and paging for the administrator's complaint list."""

    status: ComplaintStatus | None = None
    category: ComplaintCategory | None = None
    priority: Priority | None = None
    search: str | None = Field(default=None, max_length=100)
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
