"""Endpoints for logged-in administrators."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.api.deps import AdminDep, ComplaintServiceDep, TriageServiceDep, get_current_admin
from app.schemas.admin_complaint import ComplaintDetail, ComplaintPage, ComplaintSummary, ComplaintUpdate
from app.schemas.complaint_query import ComplaintQuery
from app.schemas.triage import TriageSuggestionOut

router = APIRouter(
    prefix="/admin/complaints",
    tags=["Administrator"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("")
def list_complaints(
    query: Annotated[ComplaintQuery, Query()], service: ComplaintServiceDep
) -> ComplaintPage:
    complaints, total = service.search(query)
    return ComplaintPage(
        items=[ComplaintSummary.model_validate(c) for c in complaints],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


@router.get("/{code}")
def get_complaint(code: str, service: ComplaintServiceDep) -> ComplaintDetail:
    return ComplaintDetail.model_validate(service.get_by_code(code))


@router.patch("/{code}")
def update_complaint(
    code: str, changes: ComplaintUpdate, admin: AdminDep, service: ComplaintServiceDep
) -> ComplaintDetail:
    return ComplaintDetail.model_validate(service.update(code, changes, admin))


@router.get("/{code}/photo")
def get_complaint_photo(code: str, service: ComplaintServiceDep) -> FileResponse:
    path, content_type = service.get_photo(code)
    return FileResponse(path, media_type=content_type)


@router.post("/{code}/triage")
def run_triage(code: str, service: TriageServiceDep) -> TriageSuggestionOut:
    """Run the triage agent for this complaint and save its suggestion."""
    return TriageSuggestionOut.model_validate(service.run(code))


@router.get("/{code}/triage")
def get_latest_triage(code: str, service: TriageServiceDep) -> TriageSuggestionOut:
    return TriageSuggestionOut.model_validate(service.latest(code))
