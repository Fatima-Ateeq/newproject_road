"""Business rules for complaints: submitting, tracking and administrator updates."""

from datetime import tzinfo
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.complaint_code import parse_complaint_code
from app.core.enums import ComplaintStatus
from app.core.exceptions import NotFoundError
from app.models import AdminUser, Complaint, Photo, StatusHistory
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.admin_complaint import ComplaintUpdate
from app.schemas.complaint import ComplaintCreate
from app.schemas.complaint_query import ComplaintQuery
from app.services.photo_storage import PhotoStorage


class ComplaintService:
    def __init__(
        self, db: Session, complaints: ComplaintRepository, storage: PhotoStorage, local_tz: tzinfo
    ) -> None:
        self._db = db
        self._local_tz = local_tz
        self._complaints = complaints
        self._storage = storage

    def submit(self, data: ComplaintCreate, photo_bytes: bytes | None) -> Complaint:
        complaint = Complaint(**data.model_dump(exclude={"website"}), status=ComplaintStatus.PENDING)
        complaint.history.append(StatusHistory(old_status=None, new_status=ComplaintStatus.PENDING))
        stored = self._storage.save(photo_bytes) if photo_bytes is not None else None
        try:
            if stored:
                complaint.photo = Photo(file_path=stored.file_name, content_type=stored.content_type)
            self._complaints.add(complaint)
            self._db.commit()
        except Exception:
            self._db.rollback()
            if stored:
                self._storage.delete(stored.file_name)
            raise
        return complaint

    def get_by_code(self, code: str) -> Complaint:
        parsed = parse_complaint_code(code)
        complaint = self._complaints.get(parsed[1]) if parsed else None
        if complaint is None or complaint.created_at.year != parsed[0]:
            raise NotFoundError("Complaint not found.")
        return complaint

    def search(self, query: ComplaintQuery) -> tuple[list[Complaint], int]:
        return self._complaints.search(query, self._local_tz)

    def update(self, code: str, changes: ComplaintUpdate, admin: AdminUser) -> Complaint:
        complaint = self.get_by_code(code)
        previous_status = complaint.status
        if changes.category is not None:
            complaint.category = changes.category
        if changes.priority is not None:
            complaint.priority = changes.priority
        if changes.status is not None:
            complaint.status = changes.status

        if complaint.status != previous_status or changes.action_note:
            complaint.history.append(
                StatusHistory(
                    old_status=previous_status,
                    new_status=complaint.status,
                    action_note=changes.action_note,
                    admin=admin,
                )
            )
        complaint.updated_at = utc_now()
        self._db.commit()
        return complaint

    def get_photo(self, code: str) -> tuple[Path, str]:
        photo = self.get_by_code(code).photo
        if photo is None:
            raise NotFoundError("This complaint has no photo.")
        return self._storage.path_of(photo.file_path), photo.content_type
