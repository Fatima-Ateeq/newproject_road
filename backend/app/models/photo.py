from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.complaint import Complaint


class Photo(Base):
    """The single photo attached to a complaint. file_path is relative to the upload folder."""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), unique=True)
    file_path: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    complaint: Mapped["Complaint"] = relationship(back_populates="photo")
