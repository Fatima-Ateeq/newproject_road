"""Logic for hand-labeling complaints. Nothing here prints or asks for input."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ml.common.categories import CATEGORIES
from ml.text.csv_io import append_row, read_rows, write_rows

LABEL_FIELDS = ["id", "text", "label", "labeler"]


@dataclass(frozen=True)
class Item:
    id: str
    text: str
    language: str


def load_items(rows: Iterable[dict[str, str]]) -> list[Item]:
    return [Item(row["id"], row["text"], row.get("language", "")) for row in rows]


def parse_choice(raw: str) -> str | None:
    """Turn '1'..'5' into the matching category name, or None if it is not a valid choice."""
    raw = raw.strip()
    if raw.isdigit() and 1 <= int(raw) <= len(CATEGORIES):
        return CATEGORIES[int(raw) - 1]
    return None


def format_menu() -> str:
    return "\n".join(f"  {number}  {name}" for number, name in enumerate(CATEGORIES, start=1))


class LabelStore:
    """One labeler's saved answers, kept in their own CSV file."""

    def __init__(self, path: Path, labeler: str) -> None:
        self._path = path
        self._labeler = labeler

    def rows(self) -> list[dict[str, str]]:
        return read_rows(self._path) if self._path.exists() else []

    def labeled_ids(self) -> set[str]:
        return {row["id"] for row in self.rows()}

    def add(self, item: Item, label: str) -> None:
        row = {"id": item.id, "text": item.text, "label": label, "labeler": self._labeler}
        append_row(self._path, row, LABEL_FIELDS)

    def undo(self) -> None:
        rows = self.rows()
        if rows:
            write_rows(self._path, rows[:-1], LABEL_FIELDS)
