"""Builds services for each request and identifies the logged-in administrator."""

import logging
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.ai.classifier import KeywordTextClassifier, TextClassifier
from app.ai.gemini_client import get_gemini_client
from app.ai.llm import LLMClient, UnavailableLLM
from app.ai.sklearn_classifier import load_classifier
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.db.session import get_db
from app.models import AdminUser
from app.repositories.admin_repository import AdminRepository
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.triage_repository import TriageRepository
from app.services.auth_service import AuthService
from app.services.complaint_service import ComplaintService
from app.services.photo_storage import PhotoStorage
from app.services.triage_service import TriageService

logger = logging.getLogger(__name__)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def get_complaint_service(db: DbDep, settings: SettingsDep) -> ComplaintService:
    return ComplaintService(
        db, ComplaintRepository(db), PhotoStorage(settings.upload_dir), ZoneInfo(settings.timezone)
    )


def get_auth_service(db: DbDep, settings: SettingsDep) -> AuthService:
    return AuthService(db, AdminRepository(db), settings)


ComplaintServiceDep = Annotated[ComplaintService, Depends(get_complaint_service)]


def get_llm_client(settings: SettingsDep) -> LLMClient:
    """Gemini when GEMINI_API_KEY and GEMINI_MODEL are set, otherwise a stand-in that triggers the fallback."""
    if settings.gemini_api_key and settings.gemini_model:
        return get_gemini_client(
            settings.gemini_api_key.get_secret_value(), settings.gemini_model,
            settings.llm_timeout_seconds, settings.gemini_thinking_level or None,
        )
    return UnavailableLLM()


def get_text_classifier(settings: SettingsDep) -> TextClassifier:
    """The trained classifier if its file exists, otherwise the keyword baseline."""
    if settings.text_classifier_path.exists():
        try:
            return load_classifier(settings.text_classifier_path)
        except Exception:  # for example a scikit-learn version mismatch: retrain with python -m ml.text.train_classifier
            logger.warning("Could not load %s. Using the keyword baseline.", settings.text_classifier_path, exc_info=True)
    return KeywordTextClassifier()


def get_triage_service(
    db: DbDep,
    settings: SettingsDep,
    complaint_service: ComplaintServiceDep,
    llm: Annotated[LLMClient, Depends(get_llm_client)],
    classifier: Annotated[TextClassifier, Depends(get_text_classifier)],
) -> TriageService:
    return TriageService(
        db, complaint_service, ComplaintRepository(db), TriageRepository(db), llm, classifier, settings
    )


TriageServiceDep = Annotated[TriageService, Depends(get_triage_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

_bearer = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: AuthServiceDep,
) -> AdminUser:
    if credentials is None:
        raise AuthenticationError("Not authenticated.")
    return auth.admin_from_token(credentials.credentials)


AdminDep = Annotated[AdminUser, Depends(get_current_admin)]
