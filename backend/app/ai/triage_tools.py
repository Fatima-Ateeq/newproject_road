"""The tools the triage agent can call. Each works on the complaint in `context`."""

from dataclasses import asdict

from app.ai.classifier import TextClassifier
from app.ai.context import ComplaintContext
from app.ai.duplicates import DuplicateFinder
from app.ai.tools import Tool, ToolRegistry

REVIEW_THRESHOLD = 0.5  # below this confidence the category needs a human look
_NO_ARGUMENTS = {"type": "object", "properties": {}}


def build_tools(context: ComplaintContext, classifier: TextClassifier, duplicates: DuplicateFinder) -> ToolRegistry:
    def classify_text(_: dict) -> dict:
        prediction = classifier.predict(context.description)
        return {
            "category": prediction.category.value,
            "confidence": round(prediction.confidence, 2),
            "needs_manual_review": prediction.confidence < REVIEW_THRESHOLD,
        }

    def find_duplicates(_: dict) -> dict:
        return {"matches": [asdict(match) for match in duplicates.find(context)]}

    return ToolRegistry(
        [
            Tool(
                "classify_text",
                "Suggest a category for the complaint text, with a confidence between 0 and 1.",
                _NO_ARGUMENTS,
                classify_text,
            ),
            Tool(
                "find_duplicates",
                "List other unresolved complaints within 100 metres whose text is similar. "
                "Each match has a complaint_id, distance_m and similarity.",
                _NO_ARGUMENTS,
                find_duplicates,
            ),
        ]
    )
