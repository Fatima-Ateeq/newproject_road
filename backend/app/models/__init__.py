"""Importing this package registers every table on Base.metadata (needed by Alembic)."""

from app.models.admin_user import AdminUser
from app.models.complaint import Complaint
from app.models.photo import Photo
from app.models.status_history import StatusHistory
from app.models.triage import AgentLog, TriageSuggestion

__all__ = ["AdminUser", "AgentLog", "Complaint", "Photo", "StatusHistory", "TriageSuggestion"]
