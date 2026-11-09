"""Finding open complaints that may describe the same problem."""

from dataclasses import dataclass
from typing import Protocol

from app.ai.context import ComplaintContext
from app.ai.similarity import jaccard
from app.core.geo import bounding_box, distance_m
from app.repositories.complaint_repository import ComplaintRepository


@dataclass(frozen=True)
class DuplicateMatch:
    complaint_id: str
    distance_m: int
    similarity: float


class DuplicateFinder(Protocol):
    def find(self, context: ComplaintContext) -> list[DuplicateMatch]: ...


class NearbyDuplicateFinder:
    """Unresolved complaints close by whose text shares enough words with this one."""

    def __init__(
        self,
        complaints: ComplaintRepository,
        radius_m: int = 100,
        min_similarity: float = 0.15,
        limit: int = 5,
    ) -> None:
        self._complaints = complaints
        self._radius_m = radius_m
        self._min_similarity = min_similarity
        self._limit = limit

    def find(self, context: ComplaintContext) -> list[DuplicateMatch]:
        box = bounding_box(context.latitude, context.longitude, self._radius_m)
        matches = []
        for other in self._complaints.find_unresolved_in_box(box, exclude_id=context.complaint_id):
            distance = distance_m(context.latitude, context.longitude, other.latitude, other.longitude)
            similarity = jaccard(context.description, other.description)
            if distance <= self._radius_m and similarity >= self._min_similarity:
                matches.append(DuplicateMatch(other.code, round(distance), round(similarity, 2)))
        matches.sort(key=lambda match: (-match.similarity, match.distance_m))
        return matches[: self._limit]
