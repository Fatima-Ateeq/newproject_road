"""Merge the complaint sheets filled in by team members and friends into one test pool."""

from dataclasses import dataclass, field

from ml.text.cleaning import dedupe_key, normalize_text

LANGUAGES = ("en", "roman_ur", "ur")
POOL_FIELDS = ["id", "text", "language", "scenario", "writer"]


@dataclass
class MergeResult:
    rows: list[dict[str, str]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    duplicates: int = 0


def _clean_keys(row: dict[str, str]) -> dict[str, str]:
    """Header names from Excel may have stray spaces or capitals."""
    return {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}


def merge(files: dict[str, list[dict[str, str]]]) -> MergeResult:
    """Combine rows from several files (name -> rows). Ids T001, T002, ... follow file name order."""
    result = MergeResult()
    seen: set[str] = set()
    for file_name in sorted(files):
        for line_number, raw in enumerate(files[file_name], start=2):  # line 1 is the header
            row = _clean_keys(raw)
            text = normalize_text(row.get("text", ""))
            if not text:
                continue
            language = row.get("language", "").lower()
            if language not in LANGUAGES:
                result.problems.append(f"{file_name} line {line_number}: language must be one of {LANGUAGES}, got '{language}'")
                continue
            key = dedupe_key(text)
            if key in seen:
                result.duplicates += 1
                continue
            seen.add(key)
            result.rows.append(
                {
                    "id": f"T{len(result.rows) + 1:03d}",
                    "text": text,
                    "language": language,
                    "scenario": row.get("scenario", ""),
                    "writer": row.get("writer", "") or file_name,
                }
            )
    return result
