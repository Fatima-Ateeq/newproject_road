"""Public complaint IDs such as RW-2026-000042.

The code is derived from the creation year and the database id, so no extra
column is needed and two complaints can never receive the same code.
"""

import re

_CODE_PATTERN = re.compile(r"^RW-(\d{4})-(\d{6})$")


def format_complaint_code(year: int, complaint_id: int) -> str:
    return f"RW-{year}-{complaint_id:06d}"


def parse_complaint_code(code: str) -> tuple[int, int] | None:
    """Return (year, complaint_id), or None if the text is not a valid code."""
    match = _CODE_PATTERN.match(code)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))
