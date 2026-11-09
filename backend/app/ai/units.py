"""Which unit should handle which kind of complaint. Edit here to change the routing."""

from app.core.enums import ComplaintCategory

UNIT_BY_CATEGORY: dict[ComplaintCategory, str] = {
    ComplaintCategory.ROAD_DAMAGE: "Roads Maintenance",
    ComplaintCategory.TRAFFIC_CONGESTION: "Traffic Police",
    ComplaintCategory.RAILWAY_CROSSING: "Railway Liaison",
    ComplaintCategory.MISSING_TRAFFIC_CONTROL: "Traffic Police",
    ComplaintCategory.OTHER: "Municipal Services",
}

RESPONSIBLE_UNITS: tuple[str, ...] = tuple(sorted(set(UNIT_BY_CATEGORY.values())))
