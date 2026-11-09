"""The category list, taken from the backend so it is defined in exactly one place."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.enums import ComplaintCategory  # noqa: E402

CATEGORIES: list[str] = [category.value for category in ComplaintCategory]
