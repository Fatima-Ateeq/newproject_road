from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.enums import ComplaintStatus
from app.db.base import Base
from app.db.types import enum_type

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.complaint import Complaint


class StatusHistory(Base):
    """One row per status event. old_status and admin are empty for the first entry."""

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    old_status: Mapped[ComplaintStatus | None] = mapped_column(enum_type(ComplaintStatus))
    new_status: Mapped[ComplaintStatus] = mapped_column(enum_type(ComplaintStatus))
    action_note: Mapped[str | None] = mapped_column(Text)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    complaint: Mapped["Complaint"] = relationship(back_populates="history")
    admin: Mapped["AdminUser | None"] = relationship()

    @property
    def admin_username(self) -> str | None:
        return self.admin.username if self.admin else None
