"""Public endpoints used by citizens."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.anti_spam import limit_submissions
from app.api.deps import ComplaintServiceDep, SettingsDep
from app.api.uploads import read_photo
from app.core.clock import utc_now
from app.core.complaint_code import format_complaint_code
from app.schemas.complaint import ComplaintCreate, ComplaintCreated, PublicComplaint

router = APIRouter(prefix="/complaints", tags=["Citizen"])


@router.post("", status_code=201, dependencies=[Depends(limit_submissions)])
def submit_complaint(
    data: Annotated[ComplaintCreate, Form()],
    service: ComplaintServiceDep,
    settings: SettingsDep,
    photo: Annotated[UploadFile | None, File()] = None,
) -> ComplaintCreated:
    if data.website:
        # Honeypot: the form hides this field, so only bots fill it in. Answer as if it
        # worked, but save nothing. Complaint number 0 never exists, so the ID tracks nowhere.
        return ComplaintCreated(complaint_id=format_complaint_code(utc_now().year, 0))
    complaint = service.submit(data, read_photo(photo, settings.max_photo_bytes))
    return ComplaintCreated(complaint_id=complaint.code)


@router.get("/{code}")
def track_complaint(code: str, service: ComplaintServiceDep) -> PublicComplaint:
    return PublicComplaint.model_validate(service.get_by_code(code))
