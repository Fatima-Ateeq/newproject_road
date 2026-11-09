from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.core.enums import ComplaintCategory, Priority, TriageSource
from app.db.base import Base
from app.db.types import enum_type


class TriageSuggestion(Base):
    """What the triage agent (or its fallback) suggested for a complaint. The administrator decides."""

    __tablename__ = "triage_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    category: Mapped[ComplaintCategory] = mapped_column(enum_type(ComplaintCategory))
    priority: Mapped[Priority] = mapped_column(enum_type(Priority))
    rationale: Mapped[str] = mapped_column(Text)
    responsible_unit: Mapped[str] = mapped_column(String(100))
    draft_note: Mapped[str] = mapped_column(Text)
    possible_duplicates: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[TriageSource] = mapped_column(enum_type(TriageSource))
    fallback_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    steps: Mapped[list["AgentLog"]] = relationship(
        back_populates="suggestion", cascade="all, delete-orphan", order_by="AgentLog.step_number"
    )


class AgentLog(Base):
    """One tool call made while producing a suggestion: the audit trail of the agent."""

    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion_id: Mapped[int] = mapped_column(ForeignKey("triage_suggestions.id"), index=True)
    step_number: Mapped[int]
    tool_name: Mapped[str] = mapped_column(String(50))
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    suggestion: Mapped[TriageSuggestion] = relationship(back_populates="steps")
