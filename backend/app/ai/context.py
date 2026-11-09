from dataclasses import dataclass


@dataclass(frozen=True)
class ComplaintContext:
    """The complaint being triaged. Tools read from here, so the model never retypes the data."""

    complaint_id: int
    code: str
    description: str
    latitude: float
    longitude: float
    has_photo: bool
