"""Runs the triage agent for a complaint and saves what it suggested."""

from sqlalchemy.orm import Session

from app.ai.agent import TriageAgent
from app.ai.classifier import TextClassifier
from app.ai.context import ComplaintContext
from app.ai.duplicates import NearbyDuplicateFinder
from app.ai.fallback import FallbackTriage
from app.ai.llm import LLMClient
from app.ai.triage_tools import build_tools
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models import AgentLog, TriageSuggestion
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.triage_repository import TriageRepository
from app.services.complaint_service import ComplaintService


class TriageService:
    def __init__(
        self,
        db: Session,
        complaint_service: ComplaintService,
        complaints: ComplaintRepository,
        triage: TriageRepository,
        llm: LLMClient,
        classifier: TextClassifier,
        settings: Settings,
    ) -> None:
        self._db = db
        self._complaint_service = complaint_service
        self._complaints = complaints
        self._triage = triage
        self._llm = llm
        self._classifier = classifier
        self._settings = settings

    def run(self, code: str) -> TriageSuggestion:
        complaint = self._complaint_service.get_by_code(code)
        context = ComplaintContext(
            complaint.id, complaint.code, complaint.description,
            complaint.latitude, complaint.longitude, complaint.has_photo,
        )
        tools = build_tools(context, self._classifier, NearbyDuplicateFinder(self._complaints))
        agent = TriageAgent(
            self._llm, tools, FallbackTriage(tools, context.description),
            self._settings.triage_max_tool_calls, self._settings.triage_timeout_seconds,
        )
        run = agent.run(context.description, context.has_photo)

        result = run.result
        suggestion = TriageSuggestion(
            complaint_id=complaint.id,
            category=result.category,
            priority=result.priority,
            rationale=result.rationale,
            responsible_unit=result.responsible_unit,
            draft_note=result.draft_note,
            possible_duplicates=result.possible_duplicates,
            source=run.source,
            fallback_reason=run.fallback_reason,
            steps=[
                AgentLog(step_number=s.number, tool_name=s.tool_name, arguments=s.arguments,
                         output=s.output, duration_ms=s.duration_ms)
                for s in run.steps
            ],
        )
        self._triage.add(suggestion)
        self._db.commit()
        return suggestion

    def latest(self, code: str) -> TriageSuggestion:
        complaint = self._complaint_service.get_by_code(code)
        suggestion = self._triage.latest_for(complaint.id)
        if suggestion is None:
            raise NotFoundError("No triage suggestion has been created for this complaint yet.")
        return suggestion
