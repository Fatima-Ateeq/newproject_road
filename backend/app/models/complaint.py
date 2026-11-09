from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.complaint_code import format_complaint_code
from app.core.enums import ComplaintCategory, ComplaintStatus, Priority
from app.db.base import Base
from app.db.types import enum_type
from app.models.photo import Photo
from app.models.status_history import StatusHistory


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float]
    longitude: Mapped[float]
    address_text: Mapped[str | None] = mapped_column(String(255))
    contact: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[ComplaintCategory | None] = mapped_column(enum_type(ComplaintCategory))
    priority: Mapped[Priority | None] = mapped_column(enum_type(Priority))
    status: Mapped[ComplaintStatus] = mapped_column(
        enum_type(ComplaintStatus), default=ComplaintStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    photo: Mapped[Photo | None] = relationship(
        back_populates="complaint", cascade="all, delete-orphan"
    )
    history: Mapped[list[StatusHistory]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at, StatusHistory.id",
    )

    @property
    def code(self) -> str:
        """The public complaint ID shown to citizens, for example RW-2026-000042."""
        return format_complaint_code(self.created_at.year, self.id)

    @property
    def has_photo(self) -> bool:
        return self.photo is not None
