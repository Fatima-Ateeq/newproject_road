"""All database queries for complaints. No business rules here."""

from datetime import date, datetime, time, timedelta, timezone, tzinfo

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ComplaintStatus
from app.core.geo import BoundingBox
from app.models import Complaint, StatusHistory
from app.schemas.complaint_query import ComplaintQuery


class ComplaintRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, complaint: Complaint) -> None:
        self._db.add(complaint)
        self._db.flush()

    def get(self, complaint_id: int) -> Complaint | None:
        statement = (
            select(Complaint)
            .where(Complaint.id == complaint_id)
            .options(
                selectinload(Complaint.photo),
                selectinload(Complaint.history).selectinload(StatusHistory.admin),
            )
        )
        return self._db.scalars(statement).first()

    def find_unresolved_in_box(self, box: BoundingBox, exclude_id: int) -> list[Complaint]:
        statement = select(Complaint).where(
            Complaint.id != exclude_id,
            Complaint.status != ComplaintStatus.RESOLVED,
            Complaint.latitude.between(box.min_latitude, box.max_latitude),
            Complaint.longitude.between(box.min_longitude, box.max_longitude),
        )
        return list(self._db.scalars(statement))

    def search(self, query: ComplaintQuery, local_tz: tzinfo = timezone.utc) -> tuple[list[Complaint], int]:
        """Filter and page complaints. Date filters are whole days in `local_tz`."""
        conditions = self._conditions(query, local_tz)
        total = self._db.scalar(select(func.count(Complaint.id)).where(*conditions)) or 0
        statement = (
            select(Complaint)
            .where(*conditions)
            .order_by(Complaint.created_at.desc(), Complaint.id.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        return list(self._db.scalars(statement)), total

    @staticmethod
    def _conditions(query: ComplaintQuery, local_tz: tzinfo) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if query.status:
            conditions.append(Complaint.status == query.status)
        if query.category:
            conditions.append(Complaint.category == query.category)
        if query.priority:
            conditions.append(Complaint.priority == query.priority)
        if query.search:
            pattern = f"%{query.search}%"
            conditions.append(
                or_(Complaint.description.ilike(pattern), Complaint.address_text.ilike(pattern))
            )
        if query.date_from:
            conditions.append(Complaint.created_at >= _start_of_day_utc(query.date_from, local_tz))
        if query.date_to:
            conditions.append(Complaint.created_at < _start_of_day_utc(query.date_to + timedelta(days=1), local_tz))
        return conditions


def _start_of_day_utc(day: date, local_tz: tzinfo) -> datetime:
    """Midnight at the start of `day` in the local time zone, converted to UTC (how timestamps are stored)."""
    return datetime.combine(day, time.min, tzinfo=local_tz).astimezone(timezone.utc)
