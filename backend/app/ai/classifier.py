"""Text classification. Today a transparent keyword baseline; the trained model replaces it later."""

from dataclasses import dataclass
from typing import Protocol

from app.core.enums import ComplaintCategory


@dataclass(frozen=True)
class Prediction:
    category: ComplaintCategory
    confidence: float


class TextClassifier(Protocol):
    def predict(self, text: str) -> Prediction: ...


# Order matters: on a tie the earlier category wins. That follows the labeling guide, which says to
# label the root cause (a railway crossing first, then road damage, then missing controls, then congestion).
_KEYWORDS: dict[ComplaintCategory, tuple[str, ...]] = {
    ComplaintCategory.RAILWAY_CROSSING: (
        "railway", "phatak", "level crossing", "gatekeeper", "ریلوے", "پھاٹک", "ٹرین",
    ),
    ComplaintCategory.ROAD_DAMAGE: (
        "pothole", "gaddha", "gaddhe", "gadhe", "crack", "daraar", "dararen", "tooti", "broken road", "caved",
        "sunk", "dhans", "asphalt", "tarmac", "tarcol", "ukhar", "گڑھا", "گڑھے", "دراڑ", "دھنس", "تارکول",
    ),
    ComplaintCategory.MISSING_TRAFFIC_CONTROL: (
        "traffic light", "traffic signal", "signal", "sign board", "signboard", "road sign", "zebra",
        "speed breaker", "lane marking", "lakeer", "stop sign", "blinker", "سگنل", "سائن", "زیبرا",
        "اسپیڈ بریکر", "لکیر",
    ),
    ComplaintCategory.TRAFFIC_CONGESTION: (
        "traffic jam", "jam", "congest", "queue", "qatar", "rush", "standstill", "stuck", "phans",
        "ٹریفک", "جام", "قطار", "پھنس",
    ),
}


class KeywordTextClassifier:
    """Counts category keywords. Simple on purpose: the trained model has to beat this baseline."""

    def predict(self, text: str) -> Prediction:
        lowered = text.casefold()
        hits = {
            category: sum(1 for keyword in keywords if keyword in lowered)
            for category, keywords in _KEYWORDS.items()
        }
        if hits[ComplaintCategory.RAILWAY_CROSSING] > 0:
            return Prediction(ComplaintCategory.RAILWAY_CROSSING, self._confidence(hits[ComplaintCategory.RAILWAY_CROSSING]))
        category, count = max(hits.items(), key=lambda item: item[1])  # first maximum wins ties
        if count == 0:
            return Prediction(ComplaintCategory.OTHER, 0.3)
        return Prediction(category, self._confidence(count))

    @staticmethod
    def _confidence(hits: int) -> float:
        return min(0.95, 0.5 + 0.15 * hits)
