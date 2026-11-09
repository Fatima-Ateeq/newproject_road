"""Distances between map points."""

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_000


@dataclass(frozen=True)
class BoundingBox:
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance over the earth's surface in metres (haversine formula)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bounding_box(latitude: float, longitude: float, radius_m: float) -> BoundingBox:
    """A rectangle that fully contains the circle, cheap to use in a database query."""
    delta_lat = math.degrees(radius_m / EARTH_RADIUS_M)
    delta_lon = delta_lat / max(math.cos(math.radians(latitude)), 0.01)
    return BoundingBox(latitude - delta_lat, latitude + delta_lat, longitude - delta_lon, longitude + delta_lon)
