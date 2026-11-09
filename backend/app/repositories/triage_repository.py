from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import TriageSuggestion


class TriageRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, suggestion: TriageSuggestion) -> None:
        self._db.add(suggestion)
        self._db.flush()

    def latest_for(self, complaint_id: int) -> TriageSuggestion | None:
        statement = (
            select(TriageSuggestion)
            .where(TriageSuggestion.complaint_id == complaint_id)
            .order_by(TriageSuggestion.id.desc())
            .options(selectinload(TriageSuggestion.steps))
        )
        return self._db.scalars(statement).first()
