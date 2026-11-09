"""Controlled values shared by the database, the API and (later) the AI layer.

Each list lives here once. Changing a category or status name is a one-line edit.
"""

from enum import Enum


class ComplaintStatus(str, Enum):
    PENDING = "Pending"
    UNDER_REVIEW = "Under Review"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class ComplaintCategory(str, Enum):
    ROAD_DAMAGE = "Road Damage"
    TRAFFIC_CONGESTION = "Traffic Congestion"
    RAILWAY_CROSSING = "Railway Crossing"
    MISSING_TRAFFIC_CONTROL = "Missing Traffic Control"
    OTHER = "Other"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TriageSource(str, Enum):
    """Who produced a triage suggestion."""

    AGENT = "agent"
    FALLBACK = "fallback"
